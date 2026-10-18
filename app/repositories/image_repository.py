"""Data access for the `images` table. Contains no business logic."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.image import Image, ImageStatus


class ImageRepository:
    """Queries for images, including the status counters used by the
    "event/image processing status" endpoints.  Commits are owned by the
    calling service.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, image_id: int) -> Image | None:
        return self.db.get(Image, image_id)

    def list_by_event(
        self,
        event_id: int,
        *,
        status: ImageStatus | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[Image]:
        stmt = select(Image).where(Image.event_id == event_id)
        if status is not None:
            stmt = stmt.where(Image.status == status.value)
        stmt = stmt.order_by(Image.created_at.desc(), Image.id.desc())
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.scalars(stmt).all())

    def count_by_event(self, event_id: int) -> int:
        stmt = select(func.count()).select_from(Image).where(Image.event_id == event_id)
        return int(self.db.execute(stmt).scalar_one())

    def status_counts_by_event(self, event_id: int) -> dict[str, int]:
        """{"uploaded": n, "processing": n, "completed": n, "failed": n}.

        Statuses with no rows are reported as 0 so the caller always gets a
        complete picture.
        """
        stmt = (
            select(Image.status, func.count())
            .where(Image.event_id == event_id)
            .group_by(Image.status)
        )
        counts = {status.value: 0 for status in ImageStatus}
        counts.update({row_status: int(n) for row_status, n in self.db.execute(stmt).all()})
        return counts

    def add(self, image: Image) -> Image:
        self.db.add(image)
        self.db.flush()
        return image

    def add_many(self, images: list[Image]) -> list[Image]:
        """Batch insert for multi-photo uploads (still no commit)."""
        self.db.add_all(images)
        self.db.flush()
        return images

    def set_status(self, image_id: int, status: ImageStatus) -> Image | None:
        """Move one image through uploaded -> processing -> completed/failed.

        Returns None when the image does not exist (e.g. deleted mid-job).
        """
        image = self.get_by_id(image_id)
        if image is None:
            return None
        image.status = status.value
        self.db.flush()
        return image

    def delete(self, image: Image) -> None:
        """Removes the image row; faces/embeddings follow via cascade."""
        self.db.delete(image)
        self.db.flush()
