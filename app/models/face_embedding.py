"""`face_embeddings` table: ArcFace vector for one detected face.

Storage notes
-------------
* PostgreSQL: the vector is stored as a pgvector column (`vector(512)`).
  PostgreSQL is the single source of truth - there is no separate search
  index to rebuild. Retrieval uses the `<=>` cosine-distance operator,
  which computes 1 - cos(a, b) and is therefore **magnitude-invariant**:
  the raw ArcFace outputs written by the processing pipeline rank
  correctly as-is, so that pipeline stays untouched.
* SQLite (unit tests): pgvector has no SQLite backend, so a JSON list is
  used via `with_variant`; the Python-side value is `list[float]` either
  way. Consequence: similarity search itself cannot be exercised on
  SQLite - integration tests for search need PostgreSQL.

`DIMENSIONS` must match the embedding model actually in use (ArcFace ->
512). Changing models later requires a schema migration for this column,
which is exactly why `model_name` / `model_version` are recorded per row.
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, utcnow

# Output dimension of the ArcFace model used by app/processing/embeding.py.
DIMENSIONS = 512

# One column type, two renderings: vector(512) on PostgreSQL, JSON list on SQLite.
EmbeddingVector = Vector(DIMENSIONS).with_variant(JSON(), "sqlite")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    # A face is embedded at most once (re-embedding would replace the row).
    __table_args__ = (UniqueConstraint("face_id", name="uq_face_embeddings_face_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    face_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("faces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # list[float] of length DIMENSIONS. Written by the embedding pipeline;
    # similarity search is done in SQL with `<=>`, so no pre-normalization
    # is required (see module docstring).
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector, nullable=False)

    # Which model produced this vector, e.g. "ArcFace" / "deepface-0.0.102".
    # Vectors from different models or preprocessing pipelines must never be
    # compared, so every search should filter on these.
    model_name: Mapped[str] = mapped_column(
        String(64), nullable=False, default="ArcFace", server_default="ArcFace"
    )
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    face: Mapped["Face"] = relationship(back_populates="embedding")

    def __repr__(self) -> str:
        return (
            f"<FaceEmbedding id={self.id} face_id={self.face_id} "
            f"model={self.model_name!r}>"
        )
