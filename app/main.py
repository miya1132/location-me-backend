import csv
import io
import json

# import httpx
import uvicorn
from apis import location as location_router
from core import database
from core.config import Config
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pywebpush import WebPushException, webpush
from schemas import subscription as Schemas

# VAPID_PUBLIC_KEY = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE55z_vWUdMpuzpd-zgxGUlOUl1pdCIfUP6So63YKBNs6ubx5YGTXfV37Yev6agslP6Mf0Qbxl8eVBo91s_tVvbA=="  # noqa: E501
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

app.include_router(location_router.router, prefix="/locations", tags=["場所"])

notifications: list[Schemas.Notification] = []


@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    # CSVデータを処理するロジックをここに追加
    # print(content)
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
                            (speed,heading,accuracy,altitude,latitude,longitude,location_at,speed_accuracy)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        row[1:],  # ID以外の要素を指定,
                    )

            except Exception as e:
                return JSONResponse(status_code=500, content={"message": str(e)})

            # cursor.execute(sql)
            # results = cursor.fetchall()[0][0]

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

    # print("------------------------------------------------------")
    # for notification in notifications:
    #     print(notification.subscription)
    #     print(notification_data["data"])
    #     print(notification_data["mode"])
    # print("------------------------------------------------------")
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
