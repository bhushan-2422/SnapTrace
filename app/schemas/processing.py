"""Schemas describing background-processing state and detected-face records."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.image import ImageStatus


class ImageProcessingStatusResponse(BaseModel):
    """State of one image: uploaded -> processing -> completed | failed."""

    model_config = ConfigDict(from_attributes=True)

    image_id: int
    status: ImageStatus


class EventProcessingStatusResponse(BaseModel):
    """Aggregate of images.status for a whole event (no ProcessingJob table -
    Redis holds the queue, this table holds the truth)."""

    event_id: int
    total: int
    uploaded: int
    processing: int
    completed: int
    failed: int


class FaceRecord(BaseModel):
    """One face detected in an image, as stored in the `faces` table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    image_id: int
    bounding_box: dict[str, float]
    confidence: float
    quality_score: float | None
    created_at: datetime
