import json
from typing import Optional

from core import database, util
from core.config import Config
from core.constants import Constants
from fastapi import APIRouter, Query
from pywebpush import WebPushException, webpush
from schemas import location

router = APIRouter()


@router.get(
    "",
    summary="場所",
    description="場所の取得",
)
async def get_locations(
    limit: int = Query(500, description="検索結果の取得上限"),
    location_start_at: Optional[str] = Query(None, description="検索k開始日時(yyyy-MM-dd hh24:mi:ss)"),
    location_end_at: Optional[str] = Query(None, description="検索終了日時(yyyy-MM-dd hh24:mi:ss"),
):
    q_location_start_at = "" if location_start_at is None else "AND location_at >= '" + location_start_at + "'"
    q_location_end_at = "" if location_end_at is None else "AND location_at <= '" + location_end_at + "'"

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
                    ST_GeogFromText('SRID=4326;POINT(' || longitude || ' ' || latitude || ')')::geometry geom
                FROM locations
                WHERE 1 = 1 {q_location_start_at} {q_location_end_at}
                ORDER BY location_at desc
                LIMIT {limit}
                ) inputs) features;
            """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()[0][0]

    print("---------------------------------------")
    print(results)
    print("---------------------------------------")
    return results


@router.post(
    "",
    summary="場所",
    description="場所の登録",
)

# async def post_location(
#     data: location.Location, notifications: list[subscription.Notification] = Depends(util.get_notifications)
# ):
async def post_location(data: location.Location):
    print("post location")
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            # レコードを挿入
            sql = """
              insert into locations(
                location_at, latitude, longitude, accuracy, altitude, speed, speed_accuracy, heading, device_id)
              values (%s, %s, %s , %s, %s, %s, %s, %s, %s)
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
                ),
            )

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
