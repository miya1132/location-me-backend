# %%
import yfinance as yf

# ティッカー情報を取得（例としてAAPLとVYM）
tickers = ["AAPL", "VYM"]

for ticker in tickers:
    ticker_info = yf.Ticker(ticker)
    info = ticker_info.info

    # 銘柄タイプを取得
    quote_type = info.get("quoteType", "N/A")

    # 銘柄タイプを表示
    if quote_type == "EQUITY":
        print(f"{ticker} は個別株です。")
    elif quote_type == "ETF":
        print(f"{ticker} はETFです。")
    else:
        print(f"{ticker} の銘柄タイプは不明です。")

    # 主要な情報も表示
    print(f"Name: {info.get('longName', 'N/A')}")
    print(f"Sector: {info.get('sector', 'N/A')}")
    print(f"Industry: {info.get('industry', 'N/A')}")
    print(f"Expense Ratio: {info.get('expenseRatio', 'N/A')}")
    # print()
