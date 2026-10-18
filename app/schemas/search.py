"""Schemas for the face-similarity photo search (POST /events/{id}/search).

The selfie itself is uploaded as multipart/form-data; these schemas describe
the optional query parameters and the response.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchOptions(BaseModel):
    """Optional overrides for a single search. Omitting a field uses the
    configured default from app config, so thresholds stay configurable
    rather than hardcoded."""

    threshold: float | None = Field(
        default=None,
        ge=-1.0,
        le=1.0,
        description="Minimum cosine similarity for a match.",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of candidate faces to retrieve from FAISS.",
    )


class SearchMatch(BaseModel):
    """One photograph containing the searched person."""

    image_id: int
    face_id: int = Field(description="Face in the photo that matched the selfie.")
    s3_url: str | None = None
    score: float = Field(description="Cosine similarity with the query face (-1 to 1).")


class SearchResponse(BaseModel):
    event_id: int
    threshold: float = Field(description="Threshold actually applied.")
    match_count: int
    matches: list[SearchMatch]
