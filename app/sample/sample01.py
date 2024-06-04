import time

import numpy as np
import pandas as pd
import psycopg2


def get_connection():
    return psycopg2.connect("postgresql://postgres:Humanway=1974@location_me_db:5432/location_me_db")


def haversine(lon1, lat1, lon2, lat2):
    import math

    # 地球の半径（km）
    R = 6371.0

    # ラジアンに変換
    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)
    lon2 = math.radians(lon2)
    lat2 = math.radians(lat2)

    # 差の計算
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # ハーバーサインの公式による距離の計算
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c

    # 距離をメートルに変換
    distance_m = distance_km * 1000

    return distance_m


def haversine_np(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees).
    All args must be of equal length.
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    km = 6371.0 * c
    # return km
    # 距離をメートルに変換
    distance_m = km * 1000
    return distance_m


start_time = time.time()

# conn = get_connection()

# df = pd.read_sql_query("SELECT latitude, longitude,
# location_at as timestamp FROM locations order by location_at", conn)
# conn.close()

# print(df.head())
# サンプルデータ生成
data = {
    "latitude": [35.6895, 34.0522, 40.7128] * 1000000,  # 簡略化のためにデータを繰り返し
    "longitude": [139.6917, -118.2437, -74.0060] * 1000000,
    "timestamp": pd.date_range("2024-06-04 08:00:00", periods=3000000, freq="S"),  # 秒単位で時刻を生成
}


df = pd.DataFrame(data)

# シフトして次の地点を取得
df["next_latitude"] = df["latitude"].shift(-1)
df["next_longitude"] = df["longitude"].shift(-1)
df["next_timestamp"] = df["timestamp"].shift(-1)

# 最後の行はNaNになるので削除
df = df[:-1]

# 距離を計算
df["distance"] = haversine_np(df["longitude"], df["latitude"], df["next_longitude"], df["next_latitude"])

# 時間差を計算（秒単位）
df["time_delta"] = (df["next_timestamp"] - df["timestamp"]).dt.total_seconds() / 3600.0  # 時間単位に変換

# 結果の確認
print(df[["distance", "time_delta"]].head())

# 上記の処理を実行
print("Execution time: %s seconds" % (time.time() - start_time))
