from pydantic import BaseModel, Field
from datetime import datetime


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    author_name: str
    created_at: datetime
    edited_at: datetime | None

    class Config:
        from_attributes = True
