from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from database import get_db
from models.comment import Comment
from models.post import Post
from models.user import User
from schemas.comment import CommentCreate, CommentUpdate, CommentResponse
from schemas.post import PostUpdate, PostResponse, PostDetailResponse
from core.auth import get_current_user, get_current_user_optional
from core.pagination import PageParams, paginate
from routers.halaqas import get_membership, require_can_view, require_member

router = APIRouter(prefix="/posts", tags=["posts"])
comments_router = APIRouter(prefix="/comments", tags=["comments"])


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


def require_author(user: User, author_id: int, what: str) -> None:
    if author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the author can edit this {what}",
        )


def require_author_or_admin(db: Session, user: User, author_id: int, halaqa_id: int, what: str) -> None:
    """Deleting is allowed for the author, or for an admin of the halaqa."""
    if author_id == user.id:
        return
    membership = get_membership(db, user.id, halaqa_id)
    if membership is None or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the author or a halaqa admin can delete this {what}",
        )


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


@router.patch("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    updates: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = get_post_or_404(db, post_id)
    require_author(current_user, post.author_id, "post")

    post.content = updates.content
    post.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = get_post_or_404(db, post_id)
    require_author_or_admin(db, current_user, post.author_id, post.halaqa_id, "post")

    db.delete(post)  # comments go with it (FK ON DELETE CASCADE + ORM cascade)
    db.commit()
    return {"detail": "Post deleted"}


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


def get_comment_or_404(db: Session, comment_id: int) -> Comment:
    comment = (
        db.query(Comment)
        .options(joinedload(Comment.post).joinedload(Post.halaqa))
        .filter(Comment.id == comment_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@comments_router.patch("/{comment_id}", response_model=CommentResponse)
def update_comment(
    comment_id: int,
    updates: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = get_comment_or_404(db, comment_id)
    require_author(current_user, comment.author_id, "comment")

    comment.content = updates.content
    comment.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    return comment


@comments_router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = get_comment_or_404(db, comment_id)
    require_author_or_admin(
        db, current_user, comment.author_id, comment.post.halaqa_id, "comment"
    )

    db.delete(comment)
    db.commit()
    return {"detail": "Comment deleted"}
