from datetime import date, datetime

from pydantic import BaseModel, Field

from schemas.membership import MemberResponse


class QuestionCreate(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class AnswerSubmit(BaseModel):
    answer: bool
    reflection: str | None = Field(default=None, max_length=2000)


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    user_id: int
    user_name: str
    answer: bool
    reflection: str | None
    created_at: datetime
    edited_at: datetime | None

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    halaqa_id: int
    text: str
    created_by: int
    creator_name: str
    active_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionWithAnswersResponse(QuestionResponse):
    answers: list[AnswerResponse] = []


class TodayQuestionResponse(BaseModel):
    """Today's question plus who has (and hasn't) answered — the frontend
    renders pending_members / answered_count as the nudge."""

    question: QuestionResponse | None
    answers: list[AnswerResponse]
    pending_members: list[MemberResponse]
    answered_count: int
    total_members: int
