from core import database
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from schemas import device

router = APIRouter()


@router.get("")
async def get_devices():
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM devices")
            results = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            devices = [dict(zip(column_names, row)) for row in results]
    return devices


@router.get("/{id}")
async def get_device(id):
    device = database.get_device(id)
    if device is None:
        return JSONResponse(status_code=404, content={"message": "No device is registered."})
    return device


@router.post("")
async def post_device(data: device.Device):
    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            device = database.get_device(data.device_id)

            if device is None:
                cursor.execute(f"insert into devices(device_id) values ('{data.device_id}')")
                return JSONResponse(status_code=200, content={"message": "Device successfully registered."})
            else:
                return JSONResponse(status_code=409, content={"error": "The device_id is already registered."})
