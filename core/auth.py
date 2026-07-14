import hashlib
import secrets

from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    """Insert a refresh-token row (hash only) and return the raw token.
    The caller is responsible for committing."""
    from models.refresh_token import RefreshToken

    raw_token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return raw_token


def get_refresh_token_row(db: Session, raw_token: str):
    from models.refresh_token import RefreshToken

    return (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .first()
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    from models.user import User
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
):
    """Like get_current_user, but anonymous (no token) is allowed.

    Used by routes that are public for public halaqas but need to know
    who is asking when the halaqa is private. A token that IS sent but
    is expired/invalid still raises 401 — silently downgrading to
    anonymous would surface as 403 on private content, and clients
    couldn't tell "please re-login" apart from "no access".
    """
    if token is None:
        return None

    return get_current_user(token=token, db=db)
