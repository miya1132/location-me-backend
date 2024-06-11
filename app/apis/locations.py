import json
import time
from typing import Optional

import numpy as np
import pandas as pd
from core import database, util
from core.config import Config
from core.constants import Constants
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pywebpush import WebPushException, webpush
from schemas import location
from sqlalchemy import create_engine

router = APIRouter()


@router.get(
    "",
    summary="場所",
    description="場所の取得",
)
async def get_locations(
    limit: int = Query(500, description="検索結果の取得上限"),
    location_start_at: Optional[str] = Query(None, description="検索開始日時(yyyy-MM-dd hh24:mi:ss)"),
    location_end_at: Optional[str] = Query(None, description="検索終了日時(yyyy-MM-dd hh24:mi:ss"),
    mode: Optional[int] = Query(None),
):
    q_location_start_at = "" if location_start_at is None else "AND location_at >= '" + location_start_at + "'"
    q_location_end_at = "" if location_end_at is None else "AND location_at <= '" + location_end_at + "'"
    q_mode = "" if mode is None else f"AND mode = {mode}"

    sql = f"""
            SELECT jsonb_build_object(
                'type',     'FeatureCollection',
                'features', jsonb_agg(features.feature)
            )
            FROM (
                SELECT jsonb_build_object(
                'type',       'Feature',
                'id',         id,
                'geometry',   ST_AsGeoJSON(geom)::jsonb,
                'properties', to_jsonb(inputs) - 'geom'
                ) AS feature
                FROM (
                SELECT
                    id,
                    location_at,
                    latitude,
                    longitude,
                    accuracy,
                    altitude,
                    speed,
                    speed_accuracy,
                    heading,
                    device_id,
                    mode,
                    ST_GeogFromText('SRID=4326;POINT(' || longitude || ' ' || latitude || ')')::geometry geom
                FROM locations
                WHERE 1 = 1 {q_mode} {q_location_start_at} {q_location_end_at}
                ORDER BY location_at desc
                {"" if limit == 0 else f"LIMIT {limit}"}
                ) inputs) features;
            """
    print(sql)
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()[0][0]

    return results


@router.post(
    "",
    summary="場所",
    description="場所の登録",
)
async def post_location(data: location.Location):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            # TODO：ここでは登録させない　登録用の子機を用意
            # デバイスを新規登録
            device = database.get_device(data.device_id)
            if device is None or device["is_enabled"] is False:
                return JSONResponse(status_code=404, content={"error": "Is the device not registered? Not enabled."})

            # レコードを挿入
            sql = """
              insert into locations(
                location_at, latitude, longitude, accuracy, altitude, speed, speed_accuracy, heading, device_id, mode)
              values (%s, %s, %s , %s, %s, %s, %s, %s, %s, %s)
              """
            cursor.execute(
                sql,
                (
                    data.location_at,
                    data.latitude,
                    data.longitude,
                    data.accuracy,
                    data.altitude,
                    data.speed,
                    data.speed_accuracy,
                    data.heading,
                    data.device_id,
                    data.mode,
                ),
            )

            sql = "update devices set location_at = %s, latitude = %s, longitude = %s where id = %s"
            cursor.execute(sql, (data.location_at, data.latitude, data.longitude, device["id"]))

    # ドライブモードのみ通知を処理する
    if data.mode == 0:
        notifications = util.get_notifications()

        unsubscribe_notifications = []
        targets = [n for n in notifications if n.mode == Constants.subscribe_mode.PROXIMITY_GUIDE]
        for target in targets:
            latigude = target.data["latitude"]
            longitude = target.data["longitude"]
            radius = target.data["radius"]
            distince = haversine(float(latigude), float(longitude), float(data.latitude), float(data.longitude))

            print(
                f"""
                    alat:{latigude} alng:{longitude}
                    blat{float(data.latitude)} blng:{float(data.longitude)}
                    radius:{radius} distince:{int(distince)}
                """
            )

            if distince <= radius:
                try:
                    webpush(
                        subscription_info=target.subscription.dict(),
                        data=json.dumps(
                            {
                                "title": "LocationMe",
                                "message": f"{int(distince)}mまで接近中！！急いで準備してください！！",
                            }
                        ),
                        vapid_private_key="private_key.pem",
                        vapid_claims={"sub": Config.VAPID_EMAIL},
                    )

                    # 購読を解除用に追加
                    unsubscribe_notifications.append(target)
                except WebPushException as ex:
                    print(f"Failed to send push: {ex}")

        for unsubscribe_notification in unsubscribe_notifications:
            print(f"Removing invalid subscription: {unsubscribe_notifications}")
            notifications.remove(unsubscribe_notification)

    return {"status": 200}


# SQLAlchemyのエンジンを作成
engine = create_engine("postgresql://postgres:Humanway=1974@location_me_db:5432/location_me_db")


@router.get("/walkings")
def get_data(
    location_start_at: Optional[str] = Query(None, description="検索開始日時(yyyy-MM-dd hh24:mi:ss)"),
    location_end_at: Optional[str] = Query(None, description="検索終了日時(yyyy-MM-dd hh24:mi:ss"),
):
    q_location_start_at = "" if location_start_at is None else "AND location_at >= '" + location_start_at + "'"
    q_location_end_at = "" if location_end_at is None else "AND location_at <= '" + location_end_at + "'"

    try:
        start_time = time.time()
        batch_size = 5000  # バッチサイズを設定
        offset = 0
        result = pd.DataFrame()

        while True:
            query = f"""
                SELECT * FROM locations WHERE mode = 1 {q_location_start_at} {q_location_end_at}
                ORDER BY location_at LIMIT {batch_size} OFFSET {offset}
                """
            df = pd.read_sql_query(query, engine)

            if df.empty:
                break

            processed_df = process_batch(df)
            result = pd.concat([result, processed_df])

            offset += batch_size

        # 必要なカラムだけを選択してJSON形式に変換
        result_dict = result.to_dict(orient="records")
        print("Execution time: %s seconds" % (time.time() - start_time))

        return JSONResponse(content=result_dict)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


def process_batch(df):
    # シフトして次の地点を取得
    df["next_latitude"] = df["latitude"].shift(-1)
    df["next_longitude"] = df["longitude"].shift(-1)
    df["next_location_at"] = df["location_at"].shift(-1)

    # 最後の行はNaNになるので削除
    df = df[:-1]

    # 距離を計算
    df["distance"] = haversine_np(df["longitude"], df["latitude"], df["next_longitude"], df["next_latitude"])

    # 時間差を計算（秒単位）
    df["time_delta"] = (df["next_location_at"] - df["location_at"]).dt.total_seconds()

    # タイムスタンプをISO形式に変換
    df["location_at"] = df["location_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["next_location_at"] = df["next_location_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return df


def haversine(lon1, lat1, lon2, lat2):
    import math

    # 地球の半径（km）
    R = 6371.0

    # ラジアンに変換
    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)
    lon2 = math.radians(lon2)
    lat2 = math.radians(lat2)

    # 差の計算
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # ハーバーサインの公式による距離の計算
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c

    # 距離をメートルに変換
    distance_m = distance_km * 1000

    return distance_m


def haversine_np(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees).
    All args must be of equal length.
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    distance_km = 6371.0 * c

    # 距離をメートルに変換
    distance_m = distance_km * 1000
    return distance_m
