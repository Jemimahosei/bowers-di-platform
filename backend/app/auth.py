"""Auth helpers — stdlib only (hashlib + secrets, no new dependencies).

Passwords: hashlib.pbkdf2_hmac (SHA-256, per-user salt).
Sessions: secrets.token_urlsafe tokens stored in the DB with 7-day expiry,
presented as ``Authorization: Bearer <token>``.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

TOKEN_TTL = timedelta(days=7)
_PBKDF2_ITERATIONS = 200_000

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    ).hex()


def new_salt() -> bytes:
    return secrets.token_bytes(16)


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    return secrets.compare_digest(hash_password(password, salt), expected_hash)


def create_session(db: Session, user: models.User) -> models.SessionToken:
    token = secrets.token_urlsafe(32)
    row = models.SessionToken(
        token=token,
        user_id=user.id,
        expires_at=datetime.utcnow() + TOKEN_TTL,
    )
    db.add(row)
    db.commit()
    return row


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    row = (
        db.query(models.SessionToken)
        .filter(models.SessionToken.token == credentials.credentials)
        .first()
    )
    if row is None:
        raise _unauthorized("Invalid session token")
    if row.expires_at < datetime.utcnow():
        db.delete(row)
        db.commit()
        raise _unauthorized("Session expired")
    user = db.get(models.User, row.user_id)
    if user is None:
        raise _unauthorized("Invalid session token")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
