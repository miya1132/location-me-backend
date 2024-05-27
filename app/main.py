import json

import uvicorn
from apis import location as location_router
from core.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pywebpush import WebPushException, webpush
from schemas import subscription as Schemas

VAPID_PUBLIC_KEY = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE55z_vWUdMpuzpd-zgxGUlOUl1pdCIfUP6So63YKBNs6ubx5YGTXfV37Yev6agslP6Mf0Qbxl8eVBo91s_tVvbA=="  # noqa: E501
VAPID_PRIVATE_KEY = "TUlHSEFnRUFNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQkcwd2F3SUJBUVFnTlZOVGJocDhrV3J4a1VDbQ0KWGFQQitvdHZnbDZYNkxJbllxYm1Uemdtcnc2aFJBTkNBQVRublArOVpSMHltN09sMzdPREVaU1U1U1hXbDBJaA0KOVEvcEtqcmRnb0UyenE1dkhsZ1pOZDlYZnRoNi9wcUN5VS9veC9SQnZHWHg1VUdqM1d6KzFXOXM="  # noqa: E501
VAPID_EMAIL = "mailto:miya1132@gmail.com"


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


@app.post("/subscribe")
async def subscribe(notification_data: dict):
    # 辞書型のデータをNotificationオブジェクトに変換
    subscription = Schemas.Subscription(**notification_data["subscription"])
    notification = Schemas.Notification(
        subscription=subscription, data=notification_data["data"], mode=notification_data["mode"]
    )
    print(notification)

    notifications.append(notification)
    return JSONResponse(status_code=201, content={"message": "Subscription received"})


@app.post("/send_push")
async def send_push():
    invalid_notifications = []

    for notification in notifications:
        # print(notification.subscription)
        # print(notification.data)
        print("call webpush ---------------------------------------------------------")
        try:
            webpush(
                # subscription_info=subscription,
                subscription_info=notification.subscription.dict(),
                data=json.dumps(
                    {
                        "title": "LocationMe",
                        "message": "お友達が接近しています！！",
                    }
                ),
                vapid_private_key="private_key.pem",
                vapid_claims={"sub": VAPID_EMAIL},
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
