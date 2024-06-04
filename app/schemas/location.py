from pydantic import BaseModel


class Location(BaseModel):
    location_at: str
    latitude: str
    longitude: str
    accuracy: str
    altitude: str
    speed: str
    speed_accuracy: str
    heading: str
    device_id: str
    mode: int
