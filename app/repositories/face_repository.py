"""Data access for the `faces` and `face_embeddings` tables.

Faces and their embeddings are read together, so one repository covers both
tables.  Contains no ML code and no business logic.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app.models.face import Face
from app.models.face_embedding import FaceEmbedding
from app.models.image import Image


class FaceRepository:
    """Queries for detected faces and their ArcFace vectors.

    Commits are owned by the calling service.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # -- faces -----------------------------------------------------------

    def get_by_id(self, face_id: int) -> Face | None:
        return self.db.get(Face, face_id)

    def list_by_image(self, image_id: int) -> list[Face]:
        stmt = (
            select(Face)
            .where(Face.image_id == image_id)
            .order_by(Face.id)
        )
        return list(self.db.scalars(stmt).all())

    def add(self, face: Face) -> Face:
        self.db.add(face)
        self.db.flush()
        return face

    def delete(self, face: Face) -> None:
        self.db.delete(face)
        self.db.flush()

    # -- embeddings ------------------------------------------------------

    def add_embedding(self, embedding: FaceEmbedding) -> FaceEmbedding:
        """Store the ArcFace vector for one face (face_id is unique)."""
        self.db.add(embedding)
        self.db.flush()
        return embedding

    def get_embedding_by_face(self, face_id: int) -> FaceEmbedding | None:
        stmt = select(FaceEmbedding).where(FaceEmbedding.face_id == face_id)
        return self.db.scalars(stmt).first()

    def list_embeddings_by_event(self, event_id: int) -> list[FaceEmbedding]:
        """All embeddings of an event with `face` and `image` pre-loaded.

        Used to rebuild that event's FAISS index straight from PostgreSQL,
        without N+1 queries.
        """
        stmt = (
            select(FaceEmbedding)
            .join(Face, FaceEmbedding.face_id == Face.id)
            .join(Image, Face.image_id == Image.id)
            .where(Image.event_id == event_id)
            .options(joinedload(FaceEmbedding.face).joinedload(Face.image))
            .order_by(FaceEmbedding.id)
        )
        return list(self.db.scalars(stmt).unique().all())

    # -- search-result mapping -------------------------------------------

    def image_ids_by_face_ids(self, face_ids: Sequence[int]) -> dict[int, int]:
        """face_id -> image_id for FAISS search results.

        FAISS returns vector positions, which are mapped to face ids first;
        this turns those face ids into image ids so the service can fetch
        records and build S3 URLs.  Returns {} for an empty input.
        """
        if not face_ids:
            return {}
        stmt = select(Face.id, Face.image_id).where(Face.id.in_(list(face_ids)))
        return {int(face_id): int(image_id) for face_id, image_id in self.db.execute(stmt).all()}

    # -- similarity search ------------------------------------------------

    def search_similar(
        self,
        event_id: int,
        query_embedding: list[float],
        *,
        threshold: float,
        limit: int,
        model_name: str,
    ) -> list[tuple[int, int, float]]:
        """Ranked (face_id, image_id, score) for one event, best first.

        score is the cosine similarity in [-1, 1]: pgvector's `<=>`
        returns the cosine *distance* and is magnitude-invariant, so the
        raw ArcFace vectors need no pre-normalisation.  The query never
        leaves the selected event (WHERE event_id = ...).
        """
        stmt = text(
            """
            SELECT f.id      AS face_id,
                   i.id      AS image_id,
                   1 - (fe.embedding <=> CAST(:query AS vector)) AS score
            FROM face_embeddings fe
            JOIN faces  f ON f.id = fe.face_id
            JOIN images i ON i.id = f.image_id
            WHERE i.event_id = :event_id
              AND fe.model_name = :model_name
              AND 1 - (fe.embedding <=> CAST(:query AS vector)) >= :threshold
            ORDER BY fe.embedding <=> CAST(:query AS vector)
            LIMIT :limit
            """
        )
        rows = self.db.execute(
            stmt,
            {
                "query": json.dumps([float(v) for v in query_embedding]),
                "event_id": event_id,
                "model_name": model_name,
                "threshold": threshold,
                "limit": limit,
            },
        ).all()
        return [(int(face_id), int(image_id), float(score)) for face_id, image_id, score in rows]
