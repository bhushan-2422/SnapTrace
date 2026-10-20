"""Registration, login and token issuing."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.utils import security
from app.utils.security import TokenError


class RefreshTokenInvalid(TokenError):
    """Refresh token expired, malformed or not a refresh token."""


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0  # access token lifetime, seconds


def register(db: Session, *, name: str, email: str, password: str) -> User:
    """Create the account (propagates EmailAlreadyTaken -> 409)."""
    from app.services import user_service

    return user_service.create_user(db, name=name, email=email, password=password)


def login(db: Session, *, email: str, password: str) -> User:
    """Verify credentials (propagates InvalidCredentials -> 401)."""
    from app.services import user_service

    return user_service.authenticate(db, email, password)


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=security.create_access_token(user.id),
        refresh_token=security.create_refresh_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def refresh_tokens(db: Session, refresh_token: str) -> TokenPair:
    """Validate a refresh token and rotate the pair.

    Stateless by design: the old refresh token stays valid until it
    expires (see app/utils/security.py for the trade-off).
    """
    from app.services import user_service

    try:
        claims = security.decode_token(refresh_token, security.REFRESH)
    except TokenError as exc:
        raise RefreshTokenInvalid(str(exc)) from exc

    user = user_service.get_user(db, claims["user_id"])
    if user is None:
        raise RefreshTokenInvalid("user no longer exists")
    return issue_tokens(user)
