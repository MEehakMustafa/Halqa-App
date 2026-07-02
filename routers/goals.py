from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.checkin import CheckIn
from models.goal import Goal
from models.user import User
from schemas.checkin import CheckInCreate, CheckInResponse, StreakResponse, StatsResponse
from schemas.goal import GoalCreate, GoalUpdate, GoalResponse
from core.auth import get_current_user, get_current_user_optional
from core.dates import user_today
from core.pagination import PageParams, paginate
from routers.halaqas import get_halaqa_or_404, require_can_view, require_member

router = APIRouter(prefix="/goals", tags=["goals"])


def get_owned_goal_or_404(db: Session, goal_id: int, user: User) -> Goal:
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the goal owner can do that",
        )
    return goal


def validate_halaqa_membership(db: Session, user: User, halaqa_id: int) -> None:
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_member(db, user, halaqa)


def get_viewable_goal_or_404(db: Session, goal_id: int, user: User | None) -> Goal:
    """Owner sees everything; a non-private halaqa goal is visible to anyone
    who can view its halaqa; private/personal goals are owner-only."""
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if user is not None and goal.user_id == user.id:
        return goal
    if goal.is_private or goal.halaqa_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This goal is private"
        )
    require_can_view(db, user, goal.halaqa)
    return goal


def checkin_dates(db: Session, goal_id: int) -> list[date]:
    rows = (
        db.query(CheckIn.date)
        .filter(CheckIn.goal_id == goal_id)
        .order_by(CheckIn.date.desc())
        .all()
    )
    return [row.date for row in rows]


def current_streak(dates: list[date], today: date) -> int:
    """Consecutive days ending today or yesterday (dates must be sorted desc)."""
    if not dates or dates[0] < today - timedelta(days=1):
        return 0
    streak = 1
    for prev, nxt in zip(dates, dates[1:]):
        if prev - nxt == timedelta(days=1):
            streak += 1
        else:
            break
    return streak


def longest_streak(dates: list[date]) -> int:
    if not dates:
        return 0
    longest = run = 1
    for prev, nxt in zip(dates, dates[1:]):
        run = run + 1 if prev - nxt == timedelta(days=1) else 1
        longest = max(longest, run)
    return longest


@router.post("/", response_model=GoalResponse, status_code=201)
def create_goal(
    goal: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if goal.halaqa_id is not None:
        validate_halaqa_membership(db, current_user, goal.halaqa_id)

    new_goal = Goal(
        title=goal.title,
        description=goal.description,
        user_id=current_user.id,
        halaqa_id=goal.halaqa_id,
        is_private=goal.is_private,
        target_days=goal.target_days,
    )
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    return new_goal


@router.get("/me", response_model=list[GoalResponse])
def get_my_goals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: PageParams = Depends()
):
    return paginate(
        db.query(Goal)
        .options(joinedload(Goal.owner))
        .filter(Goal.user_id == current_user.id)
        .order_by(Goal.created_at.desc(), Goal.id.desc()),
        page,
    )


@router.patch("/{goal_id}", response_model=GoalResponse)
def update_goal(
    goal_id: int,
    updates: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = get_owned_goal_or_404(db, goal_id, current_user)

    data = updates.model_dump(exclude_unset=True)
    if data.get("halaqa_id") is not None:
        validate_halaqa_membership(db, current_user, data["halaqa_id"])

    for field, value in data.items():
        setattr(goal, field, value)

    db.commit()
    db.refresh(goal)
    return goal


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = get_owned_goal_or_404(db, goal_id, current_user)
    db.delete(goal)
    db.commit()
    return {"detail": "Goal deleted"}


@router.post("/{goal_id}/checkin", response_model=CheckInResponse, status_code=201)
def check_in(
    goal_id: int,
    checkin: CheckInCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    goal = get_owned_goal_or_404(db, goal_id, current_user)

    today = user_today(current_user)
    already = (
        db.query(CheckIn)
        .filter(
            CheckIn.goal_id == goal.id,
            CheckIn.user_id == current_user.id,
            CheckIn.date == today,
        )
        .first()
    )
    if already:
        raise HTTPException(status_code=400, detail="Already checked in today")

    new_checkin = CheckIn(
        goal_id=goal.id, user_id=current_user.id, note=checkin.note, date=today
    )
    db.add(new_checkin)
    try:
        db.commit()
    except IntegrityError:
        # unique constraint backstop for two simultaneous check-ins
        db.rollback()
        raise HTTPException(status_code=400, detail="Already checked in today")
    db.refresh(new_checkin)
    return new_checkin


@router.get("/{goal_id}/checkins", response_model=list[CheckInResponse])
def get_checkins(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    page: PageParams = Depends()
):
    goal = get_viewable_goal_or_404(db, goal_id, current_user)
    return paginate(
        db.query(CheckIn)
        .filter(CheckIn.goal_id == goal.id)
        .order_by(CheckIn.date.desc()),
        page,
    )


@router.get("/{goal_id}/streak", response_model=StreakResponse)
def get_streak(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    goal = get_viewable_goal_or_404(db, goal_id, current_user)
    dates = checkin_dates(db, goal.id)
    today = user_today(goal.owner)  # streaks live on the owner's calendar
    return StreakResponse(
        goal_id=goal.id,
        current_streak=current_streak(dates, today),
        checked_in_today=bool(dates) and dates[0] == today,
    )


@router.get("/{goal_id}/stats", response_model=StatsResponse)
def get_stats(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    goal = get_viewable_goal_or_404(db, goal_id, current_user)
    dates = checkin_dates(db, goal.id)
    today = user_today(goal.owner)
    completion = (
        min(len(dates) / goal.target_days, 1.0) if goal.target_days else None
    )
    return StatsResponse(
        goal_id=goal.id,
        total_checkins=len(dates),
        current_streak=current_streak(dates, today),
        longest_streak=longest_streak(dates),
        checked_in_today=bool(dates) and dates[0] == today,
        target_days=goal.target_days,
        completion_rate=round(completion, 4) if completion is not None else None,
    )
