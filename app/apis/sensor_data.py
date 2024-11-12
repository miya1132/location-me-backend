import json
from typing import Optional

from core import database
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from schemas import sensor_data

router = APIRouter()


@router.get("")
async def read_devices(
    limit: Optional[int] = Query(100),
    retrieved_start_at: Optional[str] = Query(None, description="検索開始日時(yyyy-MM-dd hh24:mi:ss)"),
    retrieved_end_at: Optional[str] = Query(None, description="検索終了日時(yyyy-MM-dd hh24:mi:ss"),
):
    q_retrieved_start_at = "" if retrieved_start_at is None else "AND retrieved_at >= '" + retrieved_start_at + "'"
    q_retrieved_end_at = "" if retrieved_end_at is None else "AND retrieved_at <= '" + retrieved_end_at + "'"

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            sql = f"""
                    SELECT * FROM sensor_data
                    WHERE 1 = 1 {q_retrieved_start_at} {q_retrieved_end_at}
                    ORDER BY retrieved_at desc
                    {"" if limit == 0 else f"LIMIT {limit}"}
                    """
            cursor.execute(sql)
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            sensor_data = [dict(zip(column_names, row)) for row in results]
    return sensor_data


# @router.get("/{id}")
# async def read_device(id):
#     device = database.get_device(id)
#     if device is None:
#         return JSONResponse(status_code=404, content={"message": "No device is registered."})
#     return device


@router.post("")
async def create_sensor_data(data: sensor_data.SensorData):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            # レコードを挿入
            sql = """
              insert into sensor_data(sensor_type, retrieved_at, mac_address, data)
              values (%s, %s, %s, %s)
              """

            cursor.execute(
                sql,
                (
                    data.sensor_type,
                    data.retrieved_at,
                    data.mac_address,
                    json.dumps(data.data),  # data.data を JSON 形式に変換
                ),
            )

            if data.sensor_type == "GPS":
                # データの変換
                latitude = float(data.data["latitude"])
                longitude = float(data.data["longitude"])
                altitude = float(data.data["altitude"])
                speed = float(data.data["speed"])
                satellites = int(data.data["satellites"])  # 数値型に変換
                retrieved_at = data.retrieved_at  # そのまま利用
                course = float(data.data["course"])

                # レコードを挿入
                sql = """
                insert into locations(
                    location_at, latitude, longitude, accuracy,
                    altitude, speed, speed_accuracy, heading, device_id, mode)
                values (%s, %s, %s , %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    sql,
                    (
                        retrieved_at,
                        latitude,
                        longitude,
                        satellites,  # ここはおそらく精度や衛星数として扱う
                        altitude,
                        speed,
                        0,  # speed_accuracyが不明な場合は0を使用
                        course,  # headingが不明な場合は0を使用
                        0,  # device_idが不明な場合は0を使用
                        0,  # modeが不明な場合は0を使用
                    ),
                )
                connection.commit()  # データベースに変更を保存

            return JSONResponse(status_code=200, content={"message": "SensorData successfully registered."})

            # if device is None:
            #     cursor.execute(f"insert into sensor_data(device_id) values ('{data.device_id}')")
            #     return JSONResponse(status_code=200, content={"message": "Device successfully registered."})
            # else:
            #     return JSONResponse(status_code=409, content={"error": "The device_id is already registered."})


# @router.put("/{id}")
# async def update_device(id, device: device.DeviceUpdate):
#     with database.get_connection() as connection:
#         with connection.cursor() as cursor:
#             cursor.execute(f"update devices set name = '{device.name}', is_enabled={device.is_enabled} where id = {id}")

#     return JSONResponse(status_code=200, content={"message": "Device successfully updated."})


# @router.delete("/{id}")
# async def delete_device(id):
#     with database.get_connection() as connection:
#         with connection.cursor() as cursor:
#             cursor.execute(f"delete from devices where id = {id}")

#     return JSONResponse(status_code=200, content={"message": "Device successfully deleted."})
#     return JSONResponse(status_code=200, content={"message": "Device successfully deleted."})
