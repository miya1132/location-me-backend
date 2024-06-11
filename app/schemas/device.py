from pydantic import BaseModel


class DeviceBase(BaseModel):
    device_id: str


class DeviceUpdate(DeviceBase):
    name: str
    is_enabled: bool
