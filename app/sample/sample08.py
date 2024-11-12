# %%
# import yfinance as yf

# ticker_info = yf.Ticker("VYM")
# # info = ticker_info.info
# # actions = ticker_info.actions  # アクション(配当、分割)を表示
# # print(actions)
# # dividends = ticker_info.dividends  # 配当
# # print(dividends)
# # splits = ticker_info.splits  # 分割
# # capital_gains = ticker_info.capital_gains
# # major_holders = ticker_info.major_holders  # 大株主
# # print(major_holders)
# # ticker_info.calendar
# # 配当利回りを取得します
# dividend_yield = ticker_info.info.get("dividendYield")

# # 個別株
# # print(f"配当利回り: {dividend_yield*100}%")
# print(f"配当利回り: {dividend_yield}%")


from datetime import datetime, timedelta

import yfinance as yf

ticker_symbol = "1478.T"

# ETFの情報を取得します
etf = yf.Ticker(ticker_symbol)

# 現在の日付を取得します
end_date = datetime.now()

# 1年前の日付を計算します
start_date = end_date - timedelta(days=365)

# 1年間の配当データを取得します
dividend_data = etf.history(start=start_date, end=end_date, actions=True)
# print(dividend_data)

# 配当の数をカウントします
number_of_dividends = dividend_data[dividend_data["Dividends"] > 0]["Dividends"].count()

# 配当データから最新の配当金額を取得します
latest_dividend = dividend_data["Dividends"].sum()

# 配当が支払われた月を取得します
dividend_months = dividend_data[dividend_data["Dividends"] > 0].index.month.unique()
sorted_dividend_months = sorted(dividend_months)

# 最新の株価を取得します
latest_price = etf.history(period="1d")["Close"].iloc[-1]

# 分配金利回りを計算します
dividend_yield = (latest_dividend / latest_price) * 100

print(f"{ticker_symbol}の分配金利回り: {dividend_yield:.2f}%")
print(f"{ticker_symbol}の過去1年間の配当回数: {number_of_dividends} 回")
print(f"{ticker_symbol}の過去1年間の配当が支払われた月: {sorted_dividend_months}")
