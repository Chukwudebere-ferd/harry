from datetime import datetime

from pydantic import BaseModel


class ConnectionResponse(BaseModel):
    connected: bool
    telegram_user_id: str | None = None
    connected_at: datetime | None = None
