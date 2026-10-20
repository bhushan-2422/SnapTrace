"""User account operations.

Transaction rule (same as the repositories): every service function here
owns its transaction and commits; repositories only flush.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils import security


class EmailAlreadyTaken(Exception):
    """Raised when registration or email change hits an existing account."""


class InvalidCredentials(Exception):
    """Wrong email/password - the auth controller turns this into 401."""


def get_user(db: Session, user_id: int) -> User | None:
    return UserRepository(db).get_by_id(user_id)


def find_by_email(db: Session, email: str) -> User | None:
    return UserRepository(db).get_by_email(email.strip().lower())


def create_user(db: Session, *, name: str, email: str, password: str) -> User:
    """Hash the password and insert the account.

    The email is normalised to lower case once, here, so every lookup in
    the app compares the same form.
    """
    repo = UserRepository(db)
    email = email.strip().lower()
    if repo.get_by_email(email) is not None:
        raise EmailAlreadyTaken(email)

    user = User(name=name.strip(), email=email, password_hash=security.hash_password(password))
    repo.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = find_by_email(db, email)
    if user is None or not security.verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user


def update_user(db: Session, user: User, *, name: str | None = None, email: str | None = None) -> User:
    """Update the profile; raises EmailAlreadyTaken on a conflicting email."""
    repo = UserRepository(db)
    if name is not None:
        user.name = name.strip()
    if email is not None:
        email = email.strip().lower()
        existing = repo.get_by_email(email)
        if existing is not None and existing.id != user.id:
            raise EmailAlreadyTaken(email)
        user.email = email
    db.commit()
    db.refresh(user)
    return user
