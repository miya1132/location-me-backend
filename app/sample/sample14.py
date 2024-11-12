# %%

import yfinance as yf


def get_consecutive_dividend_increase_years(ticker):
    stock = yf.Ticker(ticker)
    div_history = stock.dividends

    # 配当履歴がない場合
    if div_history.empty:
        return 0

    # 年ごとの配当金合計を計算
    div_history_yearly = div_history.resample("Y").sum()

    # 連続増配年数をカウント
    increase_years = 0
    current_streak = 0

    for i in range(1, len(div_history_yearly)):
        if div_history_yearly[i] > div_history_yearly[i - 1]:
            current_streak += 1
            increase_years = max(increase_years, current_streak)
        else:
            current_streak = 0

    return increase_years


# 例: Apple の連続増配年数を取得
ticker = "SPYD"
consecutive_increase_years = get_consecutive_dividend_increase_years(ticker)
print(f"{ticker} の連続増配年数: {consecutive_increase_years}")
