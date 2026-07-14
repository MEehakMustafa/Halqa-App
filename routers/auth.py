from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.user import Token, RefreshRequest
from core.auth import create_access_token, create_refresh_token, get_refresh_token_row

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """Rotate a refresh token: revoke the presented one, issue a new pair.
    A revoked, expired, or unknown token is rejected — reuse of an
    already-rotated token therefore always fails."""
    row = get_refresh_token_row(db, body.refresh_token)
    now = datetime.now(timezone.utc)

    if row is None or row.revoked_at is not None or row.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    row.revoked_at = now
    new_refresh = create_refresh_token(db, row.user_id)
    db.commit()

    access = create_access_token(data={"sub": row.user.email})
    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    """Revoke the refresh token. Idempotent — an unknown or already
    revoked token still returns 200, since the end state is the same."""
    row = get_refresh_token_row(db, body.refresh_token)
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"detail": "Logged out"}
