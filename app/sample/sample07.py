# %%
import yfinance as yf

# 銘柄のティッカーシンボルを指定
ticker = "AAPL"

# ティッカーオブジェクトを作成
stock = yf.Ticker(ticker)

# 予想データを取得
recommendations = stock.recommendations
# earnings = stock.earnings
financials = stock.financials

print("Recommendations:\n", recommendations)
# print("Earnings:\n", earnings)
print("Financials:\n", financials)
