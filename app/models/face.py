"""`faces` table: one row per detected face inside an image.

An image may contain many people, so each face (not each image) is the unit
that gets a quality score and an embedding.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, utcnow

# Structured columns: JSONB on PostgreSQL (fast, typed-ish), plain JSON on
# SQLite so tests still work.
JsonObject = JSON().with_variant(JSONB(), "postgresql")


class Face(Base):
    __tablename__ = "faces"
    __table_args__ = (Index("ix_faces_image_id", "image_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    image_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("images.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Pixel coordinates of the detected face:
    # {"x1": ..., "y1": ..., "x2": ..., "y2": ...}
    bounding_box: Mapped[dict] = mapped_column(JsonObject, nullable=False)
    # RetinaFace detection confidence in [0, 1].
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    # Laplacian-variance sharpness of the face crop; NULL until assessed.
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Optional facial landmarks from the detector:
    # {"left_eye": [x, y], "right_eye": [x, y], ...}
    landmarks: Mapped[dict | None] = mapped_column(JsonObject, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    image: Mapped["Image"] = relationship(back_populates="faces")
    # Exactly zero or one embedding per face.
    embedding: Mapped["FaceEmbedding | None"] = relationship(
        back_populates="face",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Face id={self.id} image_id={self.image_id}>"
