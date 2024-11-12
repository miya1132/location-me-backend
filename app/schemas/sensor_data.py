from typing import Any, Dict, Optional

from pydantic import BaseModel


class SensorData(BaseModel):
    sensor_type: str  # センサーの種類 (例: "DHT11", "DHT22")
    retrieved_at: str  # データ取得時刻
    mac_address: str  # MACアドレス
    data: Optional[Dict[str, Any]] = None  # JSON形式のセンサーデータ
