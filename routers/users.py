from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.halaqa import Halaqa
from models.membership import Membership
from models.post import Post
from models.user import User
from schemas.halaqa import HalaqaResponse
from schemas.post import PostResponse
from schemas.user import UserCreate, UserUpdate, UserResponse, Token
from core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from core.pagination import PageParams, paginate

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hash_password(user.password),
        timezone=user.timezone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(db, user.id)
    db.commit()

    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    data = updates.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/halaqas", response_model=list[HalaqaResponse])
def get_my_halaqas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: PageParams = Depends()
):
    return paginate(
        db.query(Halaqa)
        .join(Membership, Membership.halaqa_id == Halaqa.id)
        .filter(Membership.user_id == current_user.id)
        .options(selectinload(Halaqa.memberships), joinedload(Halaqa.creator))
        .order_by(Membership.joined_at.desc(), Halaqa.id.desc()),
        page,
    )


@router.get("/me/feed", response_model=list[PostResponse])
def get_my_feed(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: PageParams = Depends()
):
    """Posts from every halaqa the user belongs to, newest first."""
    return paginate(
        db.query(Post)
        .join(Membership, Membership.halaqa_id == Post.halaqa_id)
        .filter(Membership.user_id == current_user.id)
        .options(
            joinedload(Post.author),
            joinedload(Post.halaqa),
            selectinload(Post.comments),
        )
        .order_by(Post.created_at.desc(), Post.id.desc()),
        page,
    )
