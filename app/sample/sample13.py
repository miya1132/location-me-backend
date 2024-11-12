# %%
import yfinance as yf

# ティッカーシンボルを指定
ticker = "VYM"

# データを取得
data = yf.Ticker(ticker).history(period="max")
print(data.tail())

# 最高値を計算
all_time_high = data["High"].max()
print("過去最高値:", all_time_high)
