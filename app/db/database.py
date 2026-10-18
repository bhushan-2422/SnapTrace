"""Engine, declarative base and shared column defaults.

`database.py` owns connection-level objects; `session.py` owns per-request
sessions.  The connection string is resolved exclusively from the
`DATABASE_URL` environment variable so no credentials are ever hardcoded.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

# Default matches the docker-compose PostgreSQL service (db/user/pass/db name),
# so a local dev setup works without extra configuration.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://snaptrace:snaptrace@localhost:5432/snaptrace",
)

# pool_pre_ping reconnects stale connections (useful with long-lived workers).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    """Base class for every SQLAlchemy model in SnapTrace."""


def utcnow() -> datetime:
    """Timezone-aware timestamp used as the default for created_at/updated_at.

    Kept here (rather than duplicated in every model) so all tables record
    creation times identically.
    """
    return datetime.now(timezone.utc)
