"""Application settings.

Everything that differs between environments lives in the environment
(or the repo-root `.env` file, which is gitignored).  This module reads
those variables once at import time and exposes them as plain module
attributes, so the rest of the code base can just do:

    from app.config import settings
    settings.MAX_UPLOAD_MB

No pydantic-settings, no singleton classes - one flat module is enough
for an app this size.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repository root (app/config/settings.py -> up two levels)
BASE_DIR = Path(__file__).resolve().parents[2]
PUBLIC_DIR = BASE_DIR / "public"
UPLOAD_DIR = PUBLIC_DIR / "upload"
SEARCH_DIR = PUBLIC_DIR / "search"
TEMP_DIR = BASE_DIR / "data" / "temp"

# Load .env before reading os.environ (env vars already set win over .env).
load_dotenv(BASE_DIR / ".env")


def _read_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _read_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _read_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Database / queue -------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://bhushan:pass1234@localhost:5432/snaptrace",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Auth -------------------------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = _read_int("ACCESS_TOKEN_EXPIRE_MINUTES", 30)
REFRESH_TOKEN_EXPIRE_DAYS = _read_int("REFRESH_TOKEN_EXPIRE_DAYS", 14)

# --- Object storage ---------------------------------------------------------
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET = os.getenv("S3_BUCKET", "")


def s3_enabled() -> bool:
    """S3 is used only when every credential is present.

    Until you paste the real keys into .env the app stores photos on
    local disk and serves them from /media - the rest of the code does
    not care which one is active.
    """
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET)


# --- Uploads / search limits ------------------------------------------------
MAX_UPLOAD_MB = _read_int("MAX_UPLOAD_MB", 10)
MAX_FILES_PER_UPLOAD = _read_int("MAX_FILES_PER_UPLOAD", 50)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Absolute cap for any request body (multi-file uploads use the big value,
# JSON endpoints only need a few KB - see app/main.py).
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024 * MAX_FILES_PER_UPLOAD

# Pagination / search caps
DEFAULT_PAGE_SIZE = _read_int("DEFAULT_PAGE_SIZE", 50)
MAX_PAGE_SIZE = _read_int("MAX_PAGE_SIZE", 100)
SEARCH_DEFAULT_TOP_K = _read_int("SEARCH_DEFAULT_TOP_K", 50)
SEARCH_MAX_TOP_K = _read_int("SEARCH_MAX_TOP_K", 200)
# Prototype threshold; revisit with labelled validation data (see §8).
SEARCH_DEFAULT_THRESHOLD = _read_float("SEARCH_DEFAULT_THRESHOLD", 0.45)

# --- HTTP -------------------------------------------------------------------
CORS_ORIGINS = _read_list(
    "CORS_ORIGINS",
    ["http://localhost:5173", "http://localhost:3000"],
)
