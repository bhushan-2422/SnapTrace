"""Request/response schemas for user accounts.

Note: `UserCreate.password` is the plaintext value the API receives - it is
turned into `password_hash` by the auth service before reaching the model.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """All fields optional: only provided values are updated."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None


class UserResponse(BaseModel):
    """Safe representation of a user (never includes the password/hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime
