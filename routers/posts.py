from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.comment import Comment
from models.post import Post
from models.user import User
from schemas.comment import CommentCreate, CommentResponse
from schemas.post import PostDetailResponse
from core.auth import get_current_user, get_current_user_optional
from core.pagination import PageParams, paginate
from routers.halaqas import require_can_view, require_member

router = APIRouter(prefix="/posts", tags=["posts"])


def get_post_or_404(db: Session, post_id: int) -> Post:
    post = (
        db.query(Post)
        .options(joinedload(Post.halaqa))
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.get("/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional)
):
    post = (
        db.query(Post)
        .options(
            joinedload(Post.author),
            joinedload(Post.halaqa),
            selectinload(Post.comments).joinedload(Comment.author),
        )
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    require_can_view(db, current_user, post.halaqa)
    return post


@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201)
def create_comment(
    post_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = get_post_or_404(db, post_id)
    require_member(db, current_user, post.halaqa)

    new_comment = Comment(
        content=comment.content, post_id=post.id, author_id=current_user.id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return new_comment


@router.get("/{post_id}/comments", response_model=list[CommentResponse])
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    page: PageParams = Depends()
):
    post = get_post_or_404(db, post_id)
    require_can_view(db, current_user, post.halaqa)

    return paginate(
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc()),
        page,
    )
