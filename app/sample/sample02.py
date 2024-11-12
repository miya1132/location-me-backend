# %%

import yfinance as yf

ticker = yf.Ticker("GOOG")

print(ticker.info)
# # 主要な財務指標を取得
# pe_ratio = info.get("forwardPE", "N/A")
# pb_ratio = info.get("priceToBook", "N/A")
# dividend_yield = info.get("dividendYield", "N/A")
# revenue_growth = info.get("revenueGrowth", "N/A")
# earnings_growth = info.get("earningsGrowth", "N/A")
# current_ratio = info.get("currentRatio", "N/A")
# equity_ratio = info.get("equityToAssets", "N/A")  # これがない場合はカスタム計算が必要

# # 主要な財務指標を表示
# print(f"Forward P/E: {pe_ratio}")
# print("**PER（P/E Ratio）**が低ければ割安だが、業界平均と比較することも重要。")
# print(f"P/B Ratio: {pb_ratio}")
# print("**PBR（P/B Ratio）**が1以下なら資産価値に対して割安。")
# print(f"Dividend Yield: {dividend_yield}")
# print("配当利回りが高ければ、安定した収益を見込める。")
# print(f"Revenue Growth: {revenue_growth}")
# print(f"Earnings Growth: {earnings_growth}")
# print("売上高成長率と純利益成長率が高ければ、成長企業と判断できる。")
# print(f"Current Ratio: {current_ratio}")
# print(f"Equity Ratio: {equity_ratio}")
# print("流動比率と自己資本比率が高ければ、財務的に安定していると判断できる。")

# **PER（P/E Ratio）**が低ければ割安だが、業界平均と比較することも重要。
# **PBR（P/B Ratio）**が1以下なら資産価値に対して割安。
# 配当利回りが高ければ、安定した収益を見込める。
# 売上高成長率と純利益成長率が高ければ、成長企業と判断できる。
# 流動比率と自己資本比率が高ければ、財務的に安定していると判断できる。

# longBusinessSummary = info.get("longBusinessSummary", "N/A")
# print(longBusinessSummary)

# translator = Translator()
# translated_text = translator.translate(longBusinessSummary, src="en", dest="ja")

# print(translated_text.text)
