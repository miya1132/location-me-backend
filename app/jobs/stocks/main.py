#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import time
from typing import Any, Dict

import pandas_datareader.data as data
import psycopg2
import talib as ta
import yaml


def initialize_all(config: Dict[str, Any]):
    with get_connection(config["stocks"]["database_url"]) as connection:
        with connection.cursor() as cursor:
            # テーブルをtruncateしてIDをリセット
            print("truncate stocks")
            cursor.execute("TRUNCATE TABLE stocks RESTART IDENTITY")
            cursor.execute("ALTER SEQUENCE stocks_id_seq RESTART WITH 1")

            cursor.execute("SELECT * FROM tickers")
            tickers = cursor.fetchall()
            for ticker in tickers:
                initialize_ticker(ticker[1], connection, config)


def initialize_ticker(ticker: str, connection: psycopg2.extensions.connection, config: Dict[str, Any]):
    print("initialize_ticker")
    print(f"call data {ticker}")
    df = data.DataReader(ticker, "stooq").sort_index()
    print(f"call end data {ticker} {df.head()}")

    # 単純移動平均線設定
    close = df["Close"]
    df["sma5"], df["sma25"], df["sma75"] = ta.SMA(close, 5), ta.SMA(close, 25), ta.SMA(close, 75)

    # ゴールデンクロス、デッドクロスの列を追加
    df["golden_cross"] = (df["sma5"] > df["sma25"]) & (df["sma5"].shift(1) <= df["sma25"].shift(1))
    df["dead_cross"] = (df["sma5"] < df["sma25"]) & (df["sma5"].shift(1) >= df["sma25"].shift(1))

    # ゴールデンクロスが発生した日を取得
    golden_cross_dates = df[df["golden_cross"]].index
    days_since_golden_cross = 0
    df["days_since_golden_cross"] = 0
    for i in range(1, len(df)):
        if df.index[i] in golden_cross_dates:
            days_since_golden_cross = 0
        else:
            days_since_golden_cross += 1
        df.at[df.index[i], "days_since_golden_cross"] = days_since_golden_cross

    # デッドクロスが発生した日を取得
    dead_cross_dates = df[df["dead_cross"]].index
    days_since_dead_cross = 0
    df["days_since_dead_cross"] = 0
    for i in range(1, len(df)):
        if df.index[i] in dead_cross_dates:
            days_since_dead_cross = 0
        else:
            days_since_dead_cross += 1
        df.at[df.index[i], "days_since_dead_cross"] = days_since_dead_cross

    df = df.dropna()  # NaNが含まれる行を削除

    # データベースに登録
    with connection.cursor() as cursor:
        df["Date"] = df.index.astype(str)
        records = df.to_dict(orient="records")

        sql = (
            "INSERT INTO stocks "
            "(stock_at, ticker, close, open, high, low, volume, sma5, sma25, sma75, golden_cross, dead_cross, "
            " days_since_golden_cross, days_since_dead_cross) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        for record in records:
            cursor.execute(
                sql,
                (
                    record["Date"],
                    ticker,
                    record["Close"],
                    record["Open"],
                    record["High"],
                    record["Low"],
                    record["Volume"],
                    record["sma5"],
                    record["sma25"],
                    record["sma75"],
                    record["golden_cross"],
                    record["dead_cross"],
                    record["days_since_golden_cross"],
                    record["days_since_dead_cross"],
                ),
            )
        connection.commit()


def get_config() -> Dict[str, Any]:
    with open("./config.yml", "r", encoding="utf-8") as yml:
        config = yaml.safe_load(yml)
    return config


def get_connection(database_uri: str) -> psycopg2.extensions.connection:
    return psycopg2.connect(database_uri)


if __name__ == "__main__":
    start_time = time.time()

    parser = argparse.ArgumentParser(description="Process some arguments.")
    parser.add_argument("--mode", type=int, help="0：初期化、1：初期化（ティッカー指定）、2：")
    parser.add_argument("--ticker", type=str, help="ティッカー")
    args = parser.parse_args()

    config = get_config()

    # 初期化
    if args.mode == 0:
        initialize_all(config)

    print("Execution time: %s seconds" % (time.time() - start_time))
