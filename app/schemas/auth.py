"""Request/response schemas for authentication (register/login/refresh)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    """POST /auth/register payload - mirrors UserCreate intentionally, so the
    auth contract stays independent of the user CRUD contract."""

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Claims decoded from a verified token (set by the auth dependency)."""

    user_id: int | None = None
