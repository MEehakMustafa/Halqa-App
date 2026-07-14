from datetime import datetime

from pydantic import BaseModel, field_validator

from core.dates import is_valid_timezone


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    timezone: str = "Asia/Karachi"

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, v: str) -> str:
        if not is_valid_timezone(v):
            raise ValueError(f"Unknown timezone: {v!r} (use IANA names like 'Asia/Karachi')")
        return v


class UserUpdate(BaseModel):
    name: str | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_must_exist(cls, v: str | None) -> str | None:
        if v is not None and not is_valid_timezone(v):
            raise ValueError(f"Unknown timezone: {v!r} (use IANA names like 'Asia/Karachi')")
        return v


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(BaseModel):
    refresh_token: str
