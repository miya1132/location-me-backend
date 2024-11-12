import csv
import io
import json
from datetime import datetime, timedelta

import pandas_datareader.data as data
import talib as ta
import uvicorn
import yfinance as yf
from apis import devices as devices_router
from apis import locations as locations_router
from apis import sensor_data as sensor_data_router
from core import database
from core.config import Config
from dateutil.relativedelta import relativedelta
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from googletrans import Translator
from pydantic import BaseModel
from pywebpush import WebPushException, webpush
from schemas import subscription as Schemas

# VAPID_PRIVATE_KEY = "TUlHSEFnRUFNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQkcwd2F3SUJBUVFnTlZOVGJocDhrV3J4a1VDbQ0KWGFQQitvdHZnbDZYNkxJbllxYm1Uemdtcnc2aFJBTkNBQVRublArOVpSMHltN09sMzdPREVaU1U1U1hXbDBJaA0KOVEvcEtqcmRnb0UyenE1dkhsZ1pOZDlYZnRoNi9wcUN5VS9veC9SQnZHWHg1VUdqM1d6KzFXOXM="  # noqa: E501
# VAPID_EMAIL = "mailto:miya1132@gmail.com"

# notifications: list[Schemas.Notification] = []

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
app.include_router(sensor_data_router.router, prefix="/sensor_data", tags=["センサー"])

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


def get_consecutive_dividend_increase_years(ticker):
    stock = yf.Ticker(ticker)
    div_history = stock.dividends

    # 配当履歴がない場合
    if div_history.empty:
        return 0

    # 年ごとの配当金合計を計算
    div_history_yearly = div_history.resample("Y").sum()

    # 連続増配年数をカウント
    increase_years = 0
    current_streak = 0

    for i in range(1, len(div_history_yearly)):
        if div_history_yearly[i] > div_history_yearly[i - 1]:
            current_streak += 1
            increase_years = max(increase_years, current_streak)
        else:
            current_streak = 0

    return increase_years


def update_stocks_task():
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            # テーブルをtruncateしてIDをリセット
            cursor.execute("TRUNCATE TABLE stocks RESTART IDENTITY")
            cursor.execute("ALTER SEQUENCE stocks_id_seq RESTART WITH 1")

            cursor.execute("SELECT * FROM tickers")
            tickers = cursor.fetchall()

            cursor.execute("TRUNCATE TABLE tickers RESTART IDENTITY")
            cursor.execute("ALTER SEQUENCE tickers_id_seq RESTART WITH 1")

            connection.commit()
            for ticker in tickers:
                set_ticker(ticker[1])


# curl -X 'GET' 'https://cowboy-t.net:8080/stocks/update' -H 'accept: application/json'で定期実行
@app.get("/stocks/update")
async def update_stocks(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_stocks_task)
    return {"message": "Update_stocks_task task started."}


@app.get("/exchange")
async def get_exchange():
    return yf.Ticker("USDJPY=X").history(period="1d").Close[0]


@app.get("/tickers/{ticker}")
def get_ticker(ticker):
    sql = "SELECT * FROM tickers WHERE ticker = %s"
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, (ticker,))
            ticker_tuple = cursor.fetchone()
            if ticker_tuple:
                column_names = [desc[0] for desc in cursor.description]
                return dict(zip(column_names, ticker_tuple))
            else:
                return JSONResponse(status_code=404, content={"message": "No ticker is registered."})


# ETF用
def get_dividend_yield(ticker):
    # ETFの情報を取得します
    etf = yf.Ticker(ticker)

    # 現在の日付を取得します
    end_date = datetime.now()

    # 1年前の日付を計算します
    start_date = end_date - timedelta(days=365)

    # 1年間の配当データを取得します
    dividend_data = etf.history(start=start_date, end=end_date, actions=True)

    # 配当データから最新の配当金額を取得します
    latest_dividend = dividend_data["Dividends"].sum()

    # 最新の株価を取得します
    latest_price = etf.history(period="1d")["Close"].iloc[-1]

    # 分配金利回りを計算します
    dividend_yield = latest_dividend / latest_price

    # 配当の数をカウントします
    number_of_dividends = dividend_data[dividend_data["Dividends"] > 0]["Dividends"].count()

    # 配当が支払われた月を取得します
    dividend_months = dividend_data[dividend_data["Dividends"] > 0].index.month.unique()
    sorted_dividend_months = sorted(dividend_months)
    str_dividend_months = [str(sorted_dividend_month) for sorted_dividend_month in sorted_dividend_months]

    # 分配金利回りを計算します
    return (dividend_yield, int(number_of_dividends), ", ".join(str_dividend_months))


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
            # 株の情報を取得する
            ticker_info = yf.Ticker(ticker.replace(".JP", ".T"))
            info = ticker_info.info

            long_business_summary = info.get("longBusinessSummary", None)
            if long_business_summary == "N/A":
                long_business_summary = None
            long_business_summary_jp = None

            if long_business_summary is not None:
                translator = Translator()
                translate = translator.translate(long_business_summary, src="en", dest="ja")
                long_business_summary_jp = translate.text

            website = info.get("website", None)

            price_to_sales_trailing12_months = info.get("priceToSalesTrailing12Months", None)
            gross_profit_margin = info.get("grossMargins", None)
            roe = info.get("returnOnEquity", None)

            short_name = info.get("shortName", None)
            long_name = info.get("longName", None)
            quote_type = info.get("quoteType", None)
            sector = info.get("sector", None)
            industry = info.get("industry", None)
            forward_pe = info.get("forwardPE", None)
            trailing_pe = info.get("trailingPE", None)
            price_to_book = info.get("priceToBook", None)

            dividend_yield = info.get("dividendYield", None)
            number_of_dividends = None
            dividend_months = None
            if quote_type == "ETF":
                dividend = get_dividend_yield(ticker.replace(".JP", ".T"))
                dividend_yield = dividend[0]
                number_of_dividends = dividend[1]
                dividend_months = dividend[2]
            elif quote_type == "EQUITY":
                dividend = get_dividend_yield(ticker.replace(".JP", ".T"))
                number_of_dividends = dividend[1]
                dividend_months = dividend[2]

            revenue_growth = info.get("revenueGrowth", None)
            earnings_growth = info.get("earningsGrowth", None)
            current_ratio = info.get("currentRatio", None)

            equity_ratio = None
            total_assets = None
            stockholders_equity = None

            revenue_per_share = info.get("revenuePerShare", None)
            eps = info.get("trailingEps")
            book_value_per_share = info.get("bookValue", None)
            cash_per_share = info.get("totalCashPerShare", None)
            free_cashflow_per_share = (
                info.get("freeCashflow") / info.get("sharesOutstanding") if info.get("freeCashflow") and info.get("sharesOutstanding") else None
            )
            dividend_per_share = info.get("dividendRate", None)

            if quote_type == "ETF":
                total_assets = info.get("totalAssets", None)
            else:
                balance_sheet = ticker_info.balance_sheet
                if not balance_sheet.empty:
                    stockholders_equity = balance_sheet.loc["Stockholders Equity"].iloc[0]
                    total_assets = balance_sheet.loc["Total Assets"].iloc[0]
                    equity_ratio = stockholders_equity / total_assets
                else:
                    stockholders_equity = None
                    total_assets = None
                    equity_ratio = None

            fund_family = info.get("fundFamily", None)
            three_year_average_return = info.get("threeYearAverageReturn", None)
            five_year_average_return = info.get("fiveYearAverageReturn", None)

            fifty_two_week_high = info.get("fiftyTwoWeekHigh", None)
            fifty_two_week_low = info.get("fiftyTwoWeekLow", None)

            currency = info.get("currency", None)

            consecutive_increase_years = get_consecutive_dividend_increase_years(ticker)

            sql = (
                "INSERT INTO tickers"
                "(ticker,short_name,long_name,quote_type,sector,industry,forward_pe,trailing_pe,price_to_book,dividend_yield,"
                "revenue_growth,earnings_growth,current_ratio,equity_ratio,stockholders_equity,total_assets,fund_family,three_year_average_return,"
                "five_year_average_return,long_business_summary,long_business_summary_jp,website,price_to_sales_trailing12_months,"
                "gross_profit_margin,roe,revenue_per_share,eps,book_value_per_share,cash_per_share,free_cashflow_per_share,dividend_per_share,"
                "fifty_two_week_high,fifty_two_week_low,number_of_dividends,dividend_months,currency,consecutive_increase_years)"
                "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            cursor.execute(
                sql,
                (
                    ticker,
                    short_name,
                    long_name,
                    quote_type,
                    sector,
                    industry,
                    forward_pe,
                    trailing_pe,
                    price_to_book,
                    dividend_yield,
                    revenue_growth,
                    earnings_growth,
                    current_ratio,
                    equity_ratio,
                    stockholders_equity,
                    total_assets,
                    fund_family,
                    three_year_average_return,
                    five_year_average_return,
                    long_business_summary,
                    long_business_summary_jp,
                    website,
                    price_to_sales_trailing12_months,
                    gross_profit_margin,
                    roe,
                    revenue_per_share,
                    eps,
                    book_value_per_share,
                    cash_per_share,
                    free_cashflow_per_share,
                    dividend_per_share,
                    fifty_two_week_high,
                    fifty_two_week_low,
                    number_of_dividends,
                    dividend_months,
                    currency,
                    consecutive_increase_years,
                ),
            )

            df["Date"] = df.index.astype(str)
            records = df.to_dict(orient="records")

            sql = (
                "INSERT INTO stocks"
                "(stock_at,ticker,close,open,high,low,volume,sma5,sma25,sma75,golden_cross,dead_cross,days_since_golden_cross,days_since_dead_cross)"
                "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            for record in records:
                # print(record)
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

            # 現在値と前日値を更新
            current_value = records[-1]["Close"]
            previos_value = records[-2]["Close"]
            sql = "UPDATE tickers set current_value=%s, previos_value=%s WHERE ticker=%s"
            cursor.execute(sql, (current_value, previos_value, ticker))
            connection.commit()


# TODO：apisに移動させる
@app.get("/tickers")
async def get_tickers():
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM tickers"
            cursor.execute(sql)
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            tickers = [dict(zip(column_names, row)) for row in results]
    return tickers


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
    notification = Schemas.Notification(subscription=subscription, data=notification_data["data"], mode=notification_data["mode"])
    # print(notification)

    # 既存の購読リストから同じエンドポイントを持つ購読を削除
    global notifications
    notifications = [n for n in notifications if n.subscription.endpoint != subscription.endpoint and n.mode != notification_data["mode"]]

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
