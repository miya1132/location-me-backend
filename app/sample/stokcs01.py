# %%

import pandas_datareader as data
import talib as ta

# 株価取得
ticker = "VYM"
df = data.DataReader(ticker, "stooq").sort_index()

close = df["Close"]

# 単純移動平均線
df["sma5"], df["sma25"], df["sma75"] = ta.SMA(close, 5), ta.SMA(close, 25), ta.SMA(close, 75)
print(df.tail())
