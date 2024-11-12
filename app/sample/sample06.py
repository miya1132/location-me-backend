# %%
import yfinance as yf

# ティッカーシンボルを指定してティッカー情報を取得
ticker_info = yf.Ticker("AAPL")  # 例としてAAPL（Apple Inc.）を使用

# 財務諸表を取得
balance_sheet = ticker_info.balance_sheet
# print(balance_sheet.head())
# balance_sheet.to_csv("balance_sheet.csv")
# print(balance_sheet)
# 自己資本（Equity）を取得
# print(balance_sheet.loc["Stockholders Equity"])
# stockholders_equity_sorted = balance_sheet.loc["Stockholders Equity"].sort_index(ascending=False)
stockholders_equity = balance_sheet.loc["Stockholders Equity"].iloc[0]
# print(stockholders_equity)
# 総資産（Total Assets）を取得
total_assets = balance_sheet.loc["Total Assets"].iloc[0]
print(balance_sheet.loc["Total Assets"])
# print(total_assets)

# 自己資本比率を計算
equity_ratio = stockholders_equity / total_assets
print("自己資本比率:", equity_ratio)
