from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.answer import QuestionAnswer
from models.membership import Membership
from models.question import HalaqaQuestion
from models.user import User
from schemas.question import (
    QuestionCreate,
    AnswerSubmit,
    AnswerResponse,
    QuestionResponse,
    QuestionWithAnswersResponse,
    TodayQuestionResponse,
)
from core.auth import get_current_user
from core.dates import user_today
from core.pagination import PageParams, paginate
from routers.halaqas import get_halaqa_or_404, get_membership, require_member

router = APIRouter(prefix="/halaqas", tags=["questions"])
answers_router = APIRouter(prefix="/questions", tags=["questions"])


def require_admin(db: Session, user: User, halaqa) -> None:
    membership = get_membership(db, user.id, halaqa.id)
    if membership is None or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a halaqa admin can do that",
        )


@router.post("/{halaqa_id}/questions", response_model=QuestionResponse, status_code=201)
def create_question(
    halaqa_id: int,
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create today's question. active_date is fixed here, on the admin's
    calendar — members answer against this date regardless of their own
    timezone."""
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_admin(db, current_user, halaqa)

    today = user_today(current_user)
    existing = (
        db.query(HalaqaQuestion)
        .filter(HalaqaQuestion.halaqa_id == halaqa.id, HalaqaQuestion.active_date == today)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A question already exists for today",
        )

    new_question = HalaqaQuestion(
        halaqa_id=halaqa.id,
        text=question.text,
        created_by=current_user.id,
        active_date=today,
    )
    db.add(new_question)
    # unique (halaqa_id, active_date) backstops a race here; the global
    # IntegrityError handler turns it into a 409
    db.commit()
    db.refresh(new_question)
    return new_question


@router.get("/{halaqa_id}/questions/today", response_model=TodayQuestionResponse)
def get_today_question(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_member(db, current_user, halaqa)

    question = (
        db.query(HalaqaQuestion)
        .options(joinedload(HalaqaQuestion.creator))
        .filter(
            HalaqaQuestion.halaqa_id == halaqa.id,
            HalaqaQuestion.active_date == user_today(current_user),
        )
        .first()
    )

    memberships = (
        db.query(Membership)
        .options(joinedload(Membership.user))
        .filter(Membership.halaqa_id == halaqa.id)
        .order_by(Membership.joined_at, Membership.id)
        .all()
    )

    answers = []
    if question:
        answers = (
            db.query(QuestionAnswer)
            .options(joinedload(QuestionAnswer.user))
            .filter(QuestionAnswer.question_id == question.id)
            .order_by(QuestionAnswer.created_at, QuestionAnswer.id)
            .all()
        )

    answered_ids = {a.user_id for a in answers}
    pending = [m for m in memberships if m.user_id not in answered_ids]

    return TodayQuestionResponse(
        question=question,
        answers=answers,
        pending_members=pending,
        answered_count=len(answers),
        total_members=len(memberships),
    )


@router.get("/{halaqa_id}/questions/history", response_model=list[QuestionWithAnswersResponse])
def get_question_history(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: PageParams = Depends()
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_member(db, current_user, halaqa)

    return paginate(
        db.query(HalaqaQuestion)
        .options(
            joinedload(HalaqaQuestion.creator),
            selectinload(HalaqaQuestion.answers).joinedload(QuestionAnswer.user),
        )
        .filter(HalaqaQuestion.halaqa_id == halaqa.id)
        .order_by(HalaqaQuestion.active_date.desc(), HalaqaQuestion.id.desc()),
        page,
    )


@answers_router.post("/{question_id}/answer", response_model=AnswerResponse)
def answer_question(
    question_id: int,
    body: AnswerSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upsert: first submission creates the row; answering again updates
    it in place and sets edited_at. Only open while the question's
    active_date is still "today" on the requester's own calendar."""
    question = (
        db.query(HalaqaQuestion)
        .options(joinedload(HalaqaQuestion.halaqa))
        .filter(HalaqaQuestion.id == question_id)
        .first()
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    require_member(db, current_user, question.halaqa)

    if question.active_date != user_today(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This question is no longer open for answers",
        )

    existing = (
        db.query(QuestionAnswer)
        .filter(
            QuestionAnswer.question_id == question.id,
            QuestionAnswer.user_id == current_user.id,
        )
        .first()
    )
    if existing:
        existing.answer = body.answer
        existing.reflection = body.reflection
        existing.edited_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    new_answer = QuestionAnswer(
        question_id=question.id,
        user_id=current_user.id,
        answer=body.answer,
        reflection=body.reflection,
    )
    db.add(new_answer)
    # unique (question_id, user_id) backstops a double-submit race; the
    # global IntegrityError handler turns it into a 409
    db.commit()
    db.refresh(new_answer)
    return new_answer
