"""Auth endpoints orchestration (routes handle HTTP status codes)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPairResponse
from app.schemas.user import UserResponse
from app.services import auth_service


def register(db: Session, payload: RegisterRequest) -> UserResponse:
    user = auth_service.register(
        db, name=payload.name, email=payload.email, password=payload.password
    )
    return UserResponse.model_validate(user)


def _pair(pair: auth_service.TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


def login(db: Session, payload: LoginRequest) -> TokenPairResponse:
    user = auth_service.login(db, email=payload.email, password=payload.password)
    return _pair(auth_service.issue_tokens(user))


def refresh(db: Session, payload: RefreshRequest) -> TokenPairResponse:
    return _pair(auth_service.refresh_tokens(db, payload.refresh_token))


def me(user) -> UserResponse:
    return UserResponse.model_validate(user)
