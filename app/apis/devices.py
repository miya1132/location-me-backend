from typing import Optional

from core import database
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from schemas import device

router = APIRouter()


@router.get("")
async def read_devices(limit: Optional[int] = Query(100), offset: Optional[int] = Query(0)):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM devices limit %s offset %s"
            cursor.execute(sql, (limit, offset))
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            devices = [dict(zip(column_names, row)) for row in results]
    return devices


@router.get("/{id}")
async def read_device(id):
    device = database.get_device(id)
    if device is None:
        return JSONResponse(status_code=404, content={"message": "No device is registered."})
    return device


@router.post("")
async def create_device(data: device.DeviceBase):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            device = database.get_device(data.device_id)

            if device is None:
                cursor.execute(f"insert into devices(device_id) values ('{data.device_id}')")
                return JSONResponse(status_code=200, content={"message": "Device successfully registered."})
            else:
                return JSONResponse(status_code=409, content={"error": "The device_id is already registered."})


@router.put("/{id}")
async def update_device(id, device: device.DeviceUpdate):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"update devices set name = '{device.name}', is_enabled={device.is_enabled} where id = {id}")

    return JSONResponse(status_code=200, content={"message": "Device successfully updated."})


@router.delete("/{id}")
async def delete_device(id):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"delete from devices where id = {id}")

    return JSONResponse(status_code=200, content={"message": "Device successfully deleted."})
