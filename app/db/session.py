"""Session factory and the FastAPI database dependency.

`database.py` creates the engine; this module creates sessions bound to it.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine

# expire_on_commit=False: a service may commit and then let controllers read
# attributes of the returned ORM objects without an extra refresh round-trip.
# autoflush=False: partial/in-progress state is only written when the service
# explicitly flushes or commits, which keeps query behaviour predictable.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield one session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
