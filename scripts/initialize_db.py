"""Create every SnapTrace table in the configured database.

Run from the repository root:

    DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/snaptrace \
        python scripts/initialize_db.py

If DATABASE_URL is unset, the docker-compose default from
`app/db/database.py` is used.  The script only creates tables - it never
drops or modifies existing ones.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `app` importable when the script is executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app import models  # noqa: E402,F401  (importing registers the tables)
from app.db.database import Base, engine  # noqa: E402


def ensure_pgvector() -> None:
    """Create the `vector` extension (PostgreSQL only).

    Needs a role allowed to run CREATE EXTENSION - true for the
    `pgvector/pgvector` docker image and for managed services where the
    extension is allow-listed (RDS, Neon, Supabase, ...).
    """
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def main() -> int:
    try:
        ensure_pgvector()
    except Exception as exc:  # noqa: BLE001 - surface a usable hint, then fail
        raise SystemExit(
            "Could not enable the pgvector extension.\n"
            "On docker:  docker compose up -d db   (image: pgvector/pgvector)\n"
            "On a server: ask your DBA to run CREATE EXTENSION IF NOT EXISTS vector;\n"
            f"Original error: {exc}"
        ) from exc

    Base.metadata.create_all(bind=engine)
    tables = ", ".join(sorted(Base.metadata.tables))
    print(f"Database ready. Tables created (if missing): {tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
