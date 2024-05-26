from pydantic import BaseModel


class Subscription(BaseModel):
    endpoint: str
    keys: dict


class Notification(BaseModel):
    subscription: Subscription
    mode: int
    data: dict
