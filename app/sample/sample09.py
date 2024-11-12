# %%

import yfinance as yf


# history = yf.Ticker("USDJPY=X").history(period="1d")
# print(history.head())
def fx_rates(ticker):
    return yf.Ticker(ticker).history(period="1d").Close[0]


print(fx_rates("USDJPY=X"))
# df = data.DataReader("USDJPY", "stooq").sort_index()
# print(df.tail())
