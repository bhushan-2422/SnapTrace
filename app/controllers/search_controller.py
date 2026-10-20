"""Search orchestration: selfie in, ranked photo matches out."""

from __future__ import annotations

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.event import Event
from app.schemas.search import SearchMatch, SearchResponse
from app.services import image_service, search_service


async def search(
    db: Session,
    event: Event,
    selfie: UploadFile,
    *,
    threshold: float | None = None,
    top_k: int | None = None,
) -> SearchResponse:
    applied_threshold = (
        settings.SEARCH_DEFAULT_THRESHOLD if threshold is None else threshold
    )
    applied_top_k = settings.SEARCH_DEFAULT_TOP_K if top_k is None else top_k

    path = await search_service.save_selfie(selfie)
    hits = await search_service.search_selfie(
        db,
        event.id,
        path,
        threshold=applied_threshold,
        top_k=applied_top_k,
    )

    matches = [
        SearchMatch(
            image_id=hit.image_id,
            face_id=hit.face_id,
            s3_url=image_service.public_url(hit.image),
            score=hit.score,
        )
        for hit in hits
    ]
    return SearchResponse(
        event_id=event.id,
        threshold=applied_threshold,
        match_count=len(matches),
        matches=matches,
    )
