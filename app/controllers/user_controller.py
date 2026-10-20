"""The signed-in user's own profile."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserUpdate, UserResponse
from app.services import user_service


def me(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_me(db: Session, user: User, payload: UserUpdate) -> UserResponse:
    updated = user_service.update_user(
        db,
        user,
        name=payload.name,
        email=payload.email,
    )
    return UserResponse.model_validate(updated)
