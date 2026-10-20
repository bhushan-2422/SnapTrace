"""The 1:N search: selfie in, matching photographs out.

Flow (identical preprocessing to the upload pipeline - the same
detect -> align -> embed code path, which is what makes the comparison
meaningful):

    selfie  ->  RetinaFace  ->  align  ->  ArcFace  ->  vector
    vector  ->  pgvector cosine search scoped to event_id
    face ids -> image ids (deduplicated, best score per photo)

The heavy TensorFlow import happens inside the worker thread, not at
module import, so the API process starts in milliseconds.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import constants, settings
from app.models.image import Image
from app.repositories.face_repository import FaceRepository
from app.repositories.image_repository import ImageRepository
from app.utils import file_utils, image_utils

logger = logging.getLogger(__name__)


class UnreadableSelfie(Exception):
    """The uploaded selfie cannot be decoded as an image."""


class NoFaceInSelfie(Exception):
    """No face was detected in the uploaded selfie."""


@dataclass(frozen=True)
class SearchHit:
    image_id: int
    face_id: int
    score: float  # cosine similarity in [-1, 1]
    image: Image


async def save_selfie(upload: UploadFile) -> Path:
    """Store the query photo in public/search/ (deleted once embedded)."""
    file_utils.validate_extension(upload.filename)
    destination = settings.SEARCH_DIR / f"{uuid.uuid4().hex}{file_utils.extension_of(upload.filename)}"
    try:
        await file_utils.save_upload(upload, destination)
    finally:
        await upload.close()
    return destination


async def search_selfie(
    db: Session,
    event_id: int,
    selfie_path: Path,
    *,
    threshold: float,
    top_k: int,
) -> list[SearchHit]:
    """Run the search, always cleaning the temporary selfie up afterwards.

    The matching runs in a worker thread so TensorFlow does not block
    the event loop for other requests.
    """
    try:
        return await run_in_threadpool(
            _find_matches, db, event_id, selfie_path, threshold, top_k
        )
    finally:
        selfie_path.unlink(missing_ok=True)


def _find_matches(
    db: Session,
    event_id: int,
    selfie_path: Path,
    threshold: float,
    top_k: int,
) -> list[SearchHit]:
    # Lazy: deepface/retinaface pull in TensorFlow (~seconds) on first use.
    from app.processing.alignment import alignFace
    from app.processing.detection import detectFaces
    from app.processing.embeding import getEmbedding

    img = image_utils.read_bgr(selfie_path)
    if img is None:
        raise UnreadableSelfie(selfie_path.name)

    faces = detectFaces(str(selfie_path))
    if not faces:
        raise NoFaceInSelfie("no face detected in the uploaded selfie")
    if len(faces) > 1:
        # A group selfie: use the most confident face and say so.
        logger.info("selfie contained %d faces, using the most confident one", len(faces))
    face = max(faces, key=lambda f: f["confidence"])

    aligned = alignFace(img, face["landmarks"])
    embedding = getEmbedding(aligned)

    rows = FaceRepository(db).search_similar(
        event_id,
        embedding,
        threshold=threshold,
        limit=top_k,
        model_name=constants.EMBEDDING_MODEL_NAME,
    )

    # Rows arrive best-first, so the first time we see an image is its
    # strongest face - exactly what we want when collapsing to photos.
    seen: dict[int, tuple[int, float]] = {}
    for face_id, image_id, score in rows:
        if image_id not in seen:
            seen[image_id] = (face_id, score)

    images = ImageRepository(db).get_by_ids(list(seen))
    hits: list[SearchHit] = []
    for image_id, (face_id, score) in seen.items():
        image = images.get(image_id)
        if image is not None:  # row deleted between query and fetch
            hits.append(SearchHit(image_id=image_id, face_id=face_id, score=score, image=image))
    return hits
