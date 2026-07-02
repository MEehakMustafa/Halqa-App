import datetime

from pydantic import BaseModel, Field


class CheckInCreate(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class CheckInResponse(BaseModel):
    id: int
    goal_id: int
    user_id: int
    note: str | None
    date: datetime.date
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class StreakResponse(BaseModel):
    goal_id: int
    current_streak: int
    checked_in_today: bool


class StatsResponse(BaseModel):
    goal_id: int
    total_checkins: int
    current_streak: int
    longest_streak: int
    checked_in_today: bool
    target_days: int | None
    completion_rate: float | None  # fraction 0.0–1.0, only when target_days is set
