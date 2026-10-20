"""SnapTrace API entry point.

    uvicorn app.main:app --reload        # development
    gunicorn -k uvicorn.workers.UvicornWorker app.main:app   # production-ish

Layering used across the app:

    routes/       HTTP concerns only (validation, status codes, auth deps)
    controllers/  per-request orchestration, response mapping
    services/     business rules, own the transaction
    repositories/ SQL only
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from app.api.dependencies import get_db
from app.api.routes import auth, events, images, search, users
from app.config import settings
from app.integrations import redis_client

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Log the effective configuration on boot (no secrets printed)."""
    logger.info("SnapTrace API starting")
    logger.info("storage: %s", "S3" if settings.s3_enabled() else "local /media (AWS keys not set)")
    logger.info(
        "limits: %d MB per file, %d files per upload, page size <= %d",
        settings.MAX_UPLOAD_MB,
        settings.MAX_FILES_PER_UPLOAD,
        settings.MAX_PAGE_SIZE,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SnapTrace API",
        summary="Cloud-based personal photo retrieval using facial recognition",
        version="0.1.0",
        lifespan=lifespan,
    )

    # --- CORS -------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,      # explicit list from .env
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # --- Body size guard --------------------------------------------------
    # Content-Length based: good enough for uploads sent by normal clients.
    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > settings.MAX_UPLOAD_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body is too large"},
                )
        return await call_next(request)

    # --- Routes -----------------------------------------------------------
    for router in (auth.router, users.router, events.router, images.router, search.router):
        app.include_router(router, prefix=API_PREFIX)

    # --- Photos served from disk in local mode ----------------------------
    settings.PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.PUBLIC_DIR), name="media")

    # --- Health -----------------------------------------------------------
    @app.get("/health", tags=["meta"])
    def health(db: Session = Depends(get_db)) -> dict:
        """Liveness/readiness: database, queue and storage at a glance."""
        try:
            db.execute(text("SELECT 1"))
            database = "ok"
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            logger.warning("health: database check failed: %s", exc)
            database = "error"
        redis_ok = redis_client.ping()
        return {
            "status": "ok" if database == "ok" and redis_ok else "degraded",
            "database": database,
            "redis": "ok" if redis_ok else "error",
            "queue_depth": redis_client.queue_length(),
            "storage": "s3" if settings.s3_enabled() else "local",
        }

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {"name": "SnapTrace API", "version": "0.1.0", "docs": "/docs"}

    return app


app = create_app()
