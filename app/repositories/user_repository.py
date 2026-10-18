"""Data access for the `users` table. Contains no business logic."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Queries for users.

    Transaction rule for every repository in this project: repositories never
    commit - the calling service owns the transaction.  Writes only `flush`
    so that generated ids are available immediately.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Login / uniqueness lookup (case handling is the service's job)."""
        stmt = select(User).where(User.email == email)
        return self.db.scalars(stmt).first()

    def list(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.flush()
