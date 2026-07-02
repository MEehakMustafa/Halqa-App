from pydantic import BaseModel
from datetime import datetime


class HalaqaCreate(BaseModel):
    name: str
    description: str | None = None
    is_private: bool = False


class HalaqaResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_private: bool
    created_by: int
    creator_name: str
    member_count: int
    created_at: datetime

    class Config:
        from_attributes = True
