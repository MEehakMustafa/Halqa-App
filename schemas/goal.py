from pydantic import BaseModel, Field
from datetime import datetime


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    halaqa_id: int | None = None
    is_private: bool = False
    target_days: int | None = Field(default=None, ge=1, le=3650)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    halaqa_id: int | None = None
    is_private: bool | None = None
    target_days: int | None = Field(default=None, ge=1, le=3650)


class GoalResponse(BaseModel):
    id: int
    title: str
    description: str | None
    user_id: int
    owner_name: str
    halaqa_id: int | None
    is_private: bool
    target_days: int | None
    created_at: datetime

    class Config:
        from_attributes = True
