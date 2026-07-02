from pydantic import BaseModel, Field
from datetime import datetime

from schemas.comment import CommentResponse


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class PostResponse(BaseModel):
    id: int
    content: str
    halaqa_id: int
    halaqa_name: str
    author_id: int
    author_name: str
    comment_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostDetailResponse(PostResponse):
    comments: list[CommentResponse] = []
