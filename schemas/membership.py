from pydantic import BaseModel
from datetime import datetime


class MemberResponse(BaseModel):
    user_id: int
    name: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True
