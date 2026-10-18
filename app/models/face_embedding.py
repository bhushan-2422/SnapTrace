"""`face_embeddings` table: ArcFace vector for one detected face.

Storage notes
------------
* PostgreSQL: the vector is stored as a FLOAT array (`ARRAY(Float)`).
  PostgreSQL is only the persistent copy - it lets us rebuild a FAISS index
  from the database without re-running detection. All similarity search goes
  through FAISS, so no vector extension is required.
* SQLite (unit tests): the array type is unavailable, so a JSON list is used
  via `with_variant`; the Python-side value is `list[float]` either way.

The dimension of the vector must match the ArcFace model actually in use;
it is intentionally not constrained in the schema.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, utcnow

# One column type, two renderings: FLOAT4[] on PostgreSQL, JSON list on SQLite.
EmbeddingVector = ARRAY(Float).with_variant(JSON(), "sqlite")


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

    # list[float] - already L2-normalized by the embedder so FAISS can use
    # IndexFlatIP (inner product == cosine similarity).
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVector, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    face: Mapped["Face"] = relationship(back_populates="embedding")

    def __repr__(self) -> str:
        return f"<FaceEmbedding id={self.id} face_id={self.face_id}>"
