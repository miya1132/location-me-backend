# %%
import json

import yfinance as yf

# VYMのティッカー情報を取得
ticker_info = yf.Ticker("^SPX")
info = ticker_info.info
balance_sheet = ticker_info.balance_sheet
print(balance_sheet)

# long_business_summary = info.get("longBusinessSummary", None)
# print(long_business_summary)
# # 主要な情報を取得
# expense_ratio = info.get("expenseRatio", "N/A")
# yield_ = info.get("yield", "N/A")
# aum = info.get("totalAssets", "N/A")
# average_volume = info.get("averageVolume", "N/A")
# sector_weights = info.get("sectorWeightings", "N/A")

# # 主要な情報を表示
# print(f"Expense Ratio: {expense_ratio}")
# print(f"Dividend Yield: {yield_}")
# print(f"Assets Under Management (AUM): {aum}")
# print(f"Average Volume: {average_volume}")
# print(f"Sector Weightings: {sector_weights}")

# JSONファイルに保存
file_path = "ticker_info.json"
with open(file_path, "w") as f:
    json.dump(info, f, indent=4)
