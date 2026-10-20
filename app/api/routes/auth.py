"""Auth: register, login, refresh, logout, current user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.controllers import auth_controller
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
)
from app.schemas.user import UserResponse
from app.services import user_service
from app.services.auth_service import RefreshTokenInvalid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return auth_controller.register(db, payload)
    except user_service.EmailAlreadyTaken:
        raise HTTPException(status_code=409, detail="Email already registered")


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_controller.login(db, payload)
    except user_service.InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange an expired access token's companion for a fresh pair."""
    try:
        return auth_controller.refresh(db, payload)
    except RefreshTokenInvalid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout():
    """Tokens are stateless, so the server cannot revoke them.

    The client should forget both tokens; they expire on their own
    (30 min / 14 days).  Server-side revocation would need a Redis
    denylist - see app/utils/security.py.
    """
    return {"detail": "Discard the access and refresh tokens on the client."}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return auth_controller.me(user)
