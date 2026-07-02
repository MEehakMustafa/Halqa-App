from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.goal import Goal
from models.halaqa import Halaqa
from models.membership import Membership
from models.post import Post
from models.user import User
from schemas.goal import GoalResponse
from schemas.halaqa import HalaqaCreate, HalaqaResponse
from schemas.membership import MemberResponse
from schemas.post import PostCreate, PostResponse
from core.auth import get_current_user, get_current_user_optional
from core.pagination import PageParams, paginate

router = APIRouter(prefix="/halaqas", tags=["halaqas"])


def get_halaqa_or_404(db: Session, halaqa_id: int) -> Halaqa:
    halaqa = db.query(Halaqa).filter(Halaqa.id == halaqa_id).first()
    if not halaqa:
        raise HTTPException(status_code=404, detail="Halaqa not found")
    return halaqa


def get_membership(db: Session, user_id: int, halaqa_id: int) -> Membership | None:
    return (
        db.query(Membership)
        .filter(Membership.user_id == user_id, Membership.halaqa_id == halaqa_id)
        .first()
    )


def require_member(db: Session, user: User, halaqa: Halaqa) -> Membership:
    membership = get_membership(db, user.id, halaqa.id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this halaqa to do that",
        )
    return membership


def require_can_view(db: Session, user: User | None, halaqa: Halaqa) -> None:
    """Public halaqas are readable by anyone; private ones by members only."""
    if not halaqa.is_private:
        return
    if user is None or not get_membership(db, user.id, halaqa.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This halaqa is private",
        )


@router.post("/", response_model=HalaqaResponse, status_code=201)
def create_halaqa(
    halaqa: HalaqaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_halaqa = Halaqa(
        name=halaqa.name,
        description=halaqa.description,
        is_private=halaqa.is_private,
        created_by=current_user.id
    )
    db.add(new_halaqa)
    db.flush()  # assigns new_halaqa.id before the membership insert
    db.add(Membership(user_id=current_user.id, halaqa_id=new_halaqa.id, role="admin"))
    db.commit()
    db.refresh(new_halaqa)
    return new_halaqa


@router.get("/", response_model=list[HalaqaResponse])
def get_halaqas(db: Session = Depends(get_db), page: PageParams = Depends()):
    return paginate(
        db.query(Halaqa)
        .filter(Halaqa.is_private == False)
        .options(selectinload(Halaqa.memberships), joinedload(Halaqa.creator))
        .order_by(Halaqa.created_at.desc(), Halaqa.id.desc()),
        page,
    )


@router.get("/{halaqa_id}", response_model=HalaqaResponse)
def get_halaqa(halaqa_id: int, db: Session = Depends(get_db)):
    return get_halaqa_or_404(db, halaqa_id)


@router.post("/{halaqa_id}/join", response_model=MemberResponse, status_code=201)
def join_halaqa(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    halaqa = get_halaqa_or_404(db, halaqa_id)

    if get_membership(db, current_user.id, halaqa.id):
        raise HTTPException(status_code=400, detail="Already a member of this halaqa")

    membership = Membership(user_id=current_user.id, halaqa_id=halaqa.id, role="member")
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/{halaqa_id}/leave")
def leave_halaqa(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_halaqa_or_404(db, halaqa_id)

    membership = get_membership(db, current_user.id, halaqa_id)
    if not membership:
        raise HTTPException(status_code=400, detail="You are not a member of this halaqa")

    db.delete(membership)
    db.commit()
    return {"detail": "Left halaqa"}


@router.get("/{halaqa_id}/members", response_model=list[MemberResponse])
def get_members(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    page: PageParams = Depends()
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_can_view(db, current_user, halaqa)

    return paginate(
        db.query(Membership)
        .options(joinedload(Membership.user))
        .filter(Membership.halaqa_id == halaqa_id)
        .order_by(Membership.joined_at, Membership.id),
        page,
    )


@router.post("/{halaqa_id}/posts", response_model=PostResponse, status_code=201)
def create_post(
    halaqa_id: int,
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_member(db, current_user, halaqa)

    new_post = Post(content=post.content, halaqa_id=halaqa.id, author_id=current_user.id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.get("/{halaqa_id}/posts", response_model=list[PostResponse])
def get_posts(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    page: PageParams = Depends()
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_can_view(db, current_user, halaqa)

    return paginate(
        db.query(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.halaqa),
            selectinload(Post.comments),
        )
        .filter(Post.halaqa_id == halaqa_id)
        .order_by(Post.created_at.desc(), Post.id.desc()),
        page,
    )


@router.get("/{halaqa_id}/goals", response_model=list[GoalResponse])
def get_halaqa_goals(
    halaqa_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    page: PageParams = Depends()
):
    halaqa = get_halaqa_or_404(db, halaqa_id)
    require_can_view(db, current_user, halaqa)

    return paginate(
        db.query(Goal)
        .options(joinedload(Goal.owner))
        .filter(Goal.halaqa_id == halaqa_id, Goal.is_private == False)
        .order_by(Goal.created_at.desc(), Goal.id.desc()),
        page,
    )
