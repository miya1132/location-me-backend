# %%

import yfinance as yf

# VYMのティッカーシンボルを設定
ticker = "VYM"

# yfinanceでデータを取得
data = yf.download(ticker, period="max")

print(data)

# セクター分類を取得
sector_classification = data["Sector Classification"]

# 主要セクターを取得
primary_sector = sector_classification["primarySector"]

# セクターウェイトを取得
sector_weight = sector_classification["sectorWeight"]

# 結果を出力
print(f"VYMの主要セクター：{primary_sector}")
print(f"VYMのセクターウェイト：{sector_weight:.2f}%")
