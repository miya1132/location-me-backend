import csv
import io
import json
from datetime import datetime

import pandas_datareader.data as data
import talib as ta
import uvicorn
from apis import devices as devices_router
from apis import locations as locations_router
from core import database
from core.config import Config
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pywebpush import WebPushException, webpush
from schemas import subscription as Schemas

# VAPID_PRIVATE_KEY = "TUlHSEFnRUFNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQkcwd2F3SUJBUVFnTlZOVGJocDhrV3J4a1VDbQ0KWGFQQitvdHZnbDZYNkxJbllxYm1Uemdtcnc2aFJBTkNBQVRublArOVpSMHltN09sMzdPREVaU1U1U1hXbDBJaA0KOVEvcEtqcmRnb0UyenE1dkhsZ1pOZDlYZnRoNi9wcUN5VS9veC9SQnZHWHg1VUdqM1d6KzFXOXM="  # noqa: E501
# VAPID_EMAIL = "mailto:miya1132@gmail.com"

notifications: list[Schemas.Notification] = []

app = FastAPI()

# 開発モードのみOpenAPIを有効にする
if Config.DEBUG is True:
    app = FastAPI()
else:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# CORS対策
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(locations_router.router, prefix="/locations", tags=["場所"])
app.include_router(devices_router.router, prefix="/devices", tags=["子機"])

notifications: list[Schemas.Notification] = []


# TODO：apisに移動させる
class Tracking(BaseModel):
    path: str
    access_at: str
    user_agent: str
    language: str
    screen_width: int
    screen_height: int
    city: str
    region: str
    country: str
    latitude: float
    longitude: float


@app.post("/tracking")
async def post_tracking(tracking: Tracking):
    sql = """
            insert into trackings(
                path,access_at,user_agent,language,screen_width,screen_height,city,region,country,latitude,longitude)
            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    tracking.path,
                    tracking.access_at,
                    tracking.user_agent,
                    tracking.language,
                    tracking.screen_width,
                    tracking.screen_height,
                    tracking.city,
                    tracking.region,
                    tracking.country,
                    tracking.latitude,
                    tracking.longitude,
                ),
            )
    return JSONResponse(status_code=200, content=None)


def set_ticker(ticker):
    df = data.DataReader(ticker, "stooq").sort_index()

    # 単純移動平均線設定
    close = df["Close"]
    df["sma5"], df["sma25"], df["sma75"] = ta.SMA(close, 5), ta.SMA(close, 25), ta.SMA(close, 75)

    # ゴールデンクロス、デッドクロスの列を追加
    df["golden_cross"] = (df["sma5"] > df["sma25"]) & (df["sma5"].shift(1) <= df["sma25"].shift(1))
    df["dead_cross"] = (df["sma5"] < df["sma25"]) & (df["sma5"].shift(1) >= df["sma25"].shift(1))

    # ゴールデンクロスが発生した日を取得
    golden_cross_dates = df[df["golden_cross"]].index
    days_since_golden_cross = 0
    # ゴールデンクロスが発生してからの経過日数を計算して新しい列を追加
    df["days_since_golden_cross"] = 0
    for i in range(1, len(df)):
        if df.index[i] in golden_cross_dates:
            days_since_golden_cross = 0
        else:
            days_since_golden_cross += 1
        df.at[df.index[i], "days_since_golden_cross"] = days_since_golden_cross

    # デッドクロスが発生した日を取得
    dead_cross_dates = df[df["dead_cross"]].index

    # デッドクロスが発生してからの経過日数を計算して新しい列を追加
    df["days_since_dead_cross"] = 0
    days_since_dead_cross = 0
    for i in range(1, len(df)):
        if df.index[i] in dead_cross_dates:
            days_since_dead_cross = 0
        else:
            days_since_dead_cross += 1
        df.at[df.index[i], "days_since_dead_cross"] = days_since_dead_cross

    df = df.dropna()  # NaNが含まれる行を削除

    print(df.tail())

    # データベースに登録
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            sql = "INSERT INTO tickers(ticker) values(%s)"
            cursor.execute(sql, (ticker,))

            df["Date"] = df.index.astype(str)
            records = df.to_dict(orient="records")

            sql = (
                "INSERT INTO stocks"
                "(stock_at,ticker,close,open,high,low,volume,sma5,sma25,sma75,golden_cross,dead_cross,days_since_golden_cross,days_since_dead_cross)"
                "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            for record in records:
                print(record)
                cursor.execute(
                    sql,
                    (
                        record["Date"],
                        ticker,
                        record["Close"],
                        record["Open"],
                        record["High"],
                        record["Low"],
                        record["Volume"],
                        record["sma5"],
                        record["sma25"],
                        record["sma75"],
                        record["golden_cross"],
                        record["dead_cross"],
                        record["days_since_golden_cross"],
                        record["days_since_dead_cross"],
                    ),
                )


# TODO：apisに移動させる
@app.get("/stocks")
async def get_stocks(ticker: str, months: int = Query(3)):
    end = datetime.today()
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM tickers WHERE ticker=%s"
            cursor.execute(sql, (ticker,))
            results = cursor.fetchone()
            if results is None:
                set_ticker(ticker)

            sql = "SELECT * FROM stocks WHERE ticker=%s and stock_at >= %s ORDER BY stock_at"
            cursor.execute(sql, (ticker, (end - relativedelta(months=months)).strftime("%Y-%m-%d")))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            stocks = [dict(zip(column_names, row)) for row in results]
    return stocks
    # # 本日の日付を取得
    # end = datetime.today()

    # df = data.DataReader(ticker, "stooq").sort_index()
    # close = df["Close"]
    # # 単純移動平均線
    # df["sma5"], df["sma25"], df["sma75"] = ta.SMA(close, 5), ta.SMA(close, 25), ta.SMA(close, 75)
    # print(df.head())

    # df = df.dropna()  # NaNが含まれる行を削除
    # # 辞書型に変換
    # df["Date"] = df.index.astype(str)
    # df = df[df.index >= (end - relativedelta(months=3)).strftime("%Y-%m-%d")]
    # result_dict = df.to_dict(orient="records")
    # return JSONResponse(content=result_dict)


# TODO：locationsに移動
@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    # CSVデータを処理するロジックをここに追加
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            try:
                # テーブルをtruncateしてIDをリセット
                cursor.execute("TRUNCATE TABLE locations RESTART IDENTITY")
                cursor.execute("ALTER SEQUENCE locations_id_seq RESTART WITH 1")

                # CSVデータを読み込み、データベースにインポート
                import_data = csv.reader(io.StringIO(content.decode("utf-8")))
                next(import_data)  # ヘッダー行をスキップ
                for row in import_data:
                    cursor.execute(
                        """
                        INSERT INTO locations
                            (mode,device_id,location_at,latitude,longitude,heading,accuracy,altitude,speed,speed_accuracy)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        row[1:],  # ID以外の要素を指定,
                    )

            except Exception as e:
                return JSONResponse(status_code=500, content={"message": str(e)})

    return JSONResponse(status_code=200, content={"message": "Upload csv received"})


# @app.get("/google_api_directions")
# async def google_api_directions(origin: str, destination: str):
#     apiKey = "AIzaSyBnEH0x0SchB0ox-IBkLwXlWzWxHtYBMi4"
#     # # 出発地点の住所または緯度経度
#     # origin = "33.5256198,130.42547847"
#     # # 到着地点の住所または緯度経度
#     # destination = "33.5799096985,130.420675277"
#     apiUrl = (
#         f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={apiKey}"
#     )
#     print(apiUrl)
#     async with httpx.AsyncClient() as client:
#         response = await client.get(apiUrl)
#         if response.status_code != 200:
#             raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from Google Map API")
#         return response.json()


# @app.get("/weather")
# async def get_weather():
#     locations = [
#         {"latitude": 33.606389, "longitude": 130.417968, "name": "福岡"},
#         {"latitude": 33.249351, "longitude": 130.298792, "name": "佐賀"},
#         {"latitude": 33.5256198, "longitude": 130.42547847, "name": "片縄"},
#     ]
#     # longitude = 130.42547847

#     for location in locations:
#         apiUrl = (
#             f"https://api.open-meteo.com/v1/forecast?"
#             f"past_days=1&forecast_days=0&"
#             f"latitude={location['latitude']}&longitude={location['longitude']}&"
#             f"timezone=Asia%2FTokyo&"
#             f"daily=weather_code,temperature_2m_max,temperature_2m_min&"
#             f"hourly=weather_code,temperature_2m,precipitation_probability,relative_humidity_2m"
#         )
#         print(apiUrl)
#         async with httpx.AsyncClient() as client:
#             response = await client.get(apiUrl)
#             print(response.json())

#             if response.status_code != 200:
#                 raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from Open Metro API")  # noqa: E501
#             # return response.json()

#     return {"status": 200}


@app.post("/exist_scribe")
async def exist_scribe(notification: dict):
    global notifications

    subscription = Schemas.Subscription(**notification)
    targets = [notification for notification in notifications if notification.subscription == subscription]

    if len(targets) > 0:
        return JSONResponse(status_code=200, content={"mode": targets[0].mode, "data": targets[0].data})
    else:
        return JSONResponse(status_code=200, content=None)


@app.post("/unscribe")
async def unsubscribe(notification: dict):
    global notifications

    subscription = Schemas.Subscription(**notification["subscription"])
    notifications = [notification for notification in notifications if notification.subscription != subscription]

    return JSONResponse(status_code=201, content={"message": "UnSubscription received"})


@app.post("/subscribe")
async def subscribe(notification_data: dict):
    # 辞書型のデータをNotificationオブジェクトに変換
    subscription = Schemas.Subscription(**notification_data["subscription"])
    notification = Schemas.Notification(
        subscription=subscription, data=notification_data["data"], mode=notification_data["mode"]
    )
    # print(notification)

    # 既存の購読リストから同じエンドポイントを持つ購読を削除
    global notifications
    notifications = [
        n
        for n in notifications
        if n.subscription.endpoint != subscription.endpoint and n.mode != notification_data["mode"]
    ]

    # 新しい購読をリストに追加
    notifications.append(notification)

    return JSONResponse(status_code=201, content={"message": "Subscription received"})


@app.post("/push")
async def send_push():
    invalid_notifications = []

    for notification in notifications:
        # print(notification.data)
        print("call webpush ---------------------------------------------------------")
        print(notification.subscription)
        try:
            webpush(
                # subscription_info=subscription,
                subscription_info=notification.subscription.dict(),
                data=json.dumps(
                    {
                        "title": "LocationMe",
                        "message": "プッシュ通知の確認用です。",
                    }
                ),
                vapid_private_key="private_key.pem",
                vapid_claims={"sub": Config.VAPID_EMAIL},
            )
        except WebPushException as ex:
            print(f"Failed to send push: {ex}")
            if ex.response.status_code == 410:  # HTTP 410 Gone
                invalid_notifications.append(notification)
            else:
                raise HTTPException(status_code=500, detail=str(ex))

    # 無効なsubscritionを削除
    for invalid_notification in invalid_notifications:
        print(f"Removing invalid subscription: {invalid_notification}")
        notifications.remove(invalid_notification)

    return JSONResponse(status_code=200, content={"message": "Push notifications sent"})


# リクエストの中身を取得して表示
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    if Config.DEBUG is True:
        print("header:", dict(request.headers))
        print("body:", await request.body())

    response = await call_next(request)
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info", workers=4)
