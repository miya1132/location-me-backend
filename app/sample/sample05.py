# %%
import requests
from bs4 import BeautifulSoup

# Vanguardの公式サイトのURL
url = "https://investor.vanguard.com/etf/profile/portfolio/vym"

# URLからページの内容を取得
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# セクター配分情報を抽出
sector_data = []

# セクター情報が含まれるテーブルを見つける（サイトの構造に依存する）
table = soup.find("table", {"class": "sector-weightings__table"})
if table:
    rows = table.find_all("tr")
    for row in rows[1:]:  # ヘッダー行をスキップ
        cells = row.find_all("td")
        if len(cells) > 1:
            sector = cells[0].get_text(strip=True)
            weight = cells[1].get_text(strip=True)
            sector_data.append({"Sector": sector, "Weight": weight})

# セクター配分情報を表示
for data in sector_data:
    print(f"{data['Sector']}: {data['Weight']}")

if not sector_data:
    print("セクター配分情報が見つかりませんでした。")
