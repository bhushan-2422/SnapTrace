"""Process a single image: detect -> align -> embed -> store -> S3.

This module is imported by the queue worker only; the API never touches
it.  TensorFlow/deepface are imported inside `process_image` so the
worker process starts quickly and loads the model on the first job.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import constants, settings
from app.integrations import s3_client
from app.models.face import Face
from app.models.face_embedding import FaceEmbedding
from app.models.image import Image, ImageStatus
from app.repositories.face_repository import FaceRepository
from app.repositories.image_repository import ImageRepository
from app.services import image_service
from app.utils import image_utils

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def process_image(db: Session, image_id: int) -> bool:
    """Run the whole pipeline for one image. Returns True when completed.

    Status transitions: uploaded -> processing -> completed | failed.
    Failures never crash the worker loop - the image is marked `failed`
    and the next job starts normally.
    """
    images = ImageRepository(db)
    image = images.get_by_id(image_id)
    if image is None:
        logger.warning("image %s no longer exists, skipping", image_id)
        return False
    if image.status == ImageStatus.COMPLETED.value:
        logger.info("image %s already completed, skipping", image_id)
        return True

    images.set_status(image_id, ImageStatus.PROCESSING)
    db.commit()

    new_key: str | None = None
    try:
        source = image_service.resolve_source(image)
        _extract_and_store(db, image, source)
        new_key = _maybe_upload_to_s3(image, source)

        if new_key:
            image.s3_key = new_key
            image.s3_url = None
        images.set_status(image_id, ImageStatus.COMPLETED)
        db.commit()
        logger.info(
            "image %s completed: %d face(s)", image_id,
            len(FaceRepository(db).list_by_image(image_id)),
        )
        if new_key:
            # Local copy was promoted to S3 - do not keep a second copy.
            source.unlink(missing_ok=True)
        return True

    except Exception:
        logger.exception("processing failed for image %s", image_id)
        db.rollback()
        images.set_status(image_id, ImageStatus.FAILED)
        db.commit()
        return False


def _extract_and_store(db: Session, image: Image, source: Path) -> None:
    """Detect every face, embed it, and write faces + embeddings.

    Previous rows for this image are removed first, so re-running a
    failed (or retried) image can never duplicate embeddings.
    """
    # Lazy imports: deepface/retinaface pull in TensorFlow on first use.
    from app.processing.alignment import alignFace
    from app.processing.detection import detectFaces
    from app.processing.embeding import getEmbedding

    img = image_utils.read_bgr(source)
    if img is None:
        raise ValueError(f"unreadable image file: {source}")

    faces = detectFaces(str(source))
    logger.info("image %s: %d face(s) detected", image.id, len(faces))

    face_repo = FaceRepository(db)
    for old_face in face_repo.list_by_image(image.id):
        face_repo.delete(old_face)
    db.flush()

    for face in faces:
        aligned = alignFace(img, face["landmarks"])
        embedding = getEmbedding(aligned)

        row = Face(
            image_id=image.id,
            bounding_box={
                "x1": face["bbox"][0],
                "y1": face["bbox"][1],
                "x2": face["bbox"][2],
                "y2": face["bbox"][3],
            },
            confidence=face["confidence"],
            quality_score=image_utils.sharpness_score(aligned),
            landmarks=face["landmarks"],
        )
        face_repo.add(row)
        face_repo.add_embedding(
            FaceEmbedding(
                face_id=row.id,
                embedding=[float(v) for v in embedding],
                model_name=constants.EMBEDDING_MODEL_NAME,
                model_version=constants.EMBEDDING_MODEL_VERSION,
            )
        )
    db.flush()


def _maybe_upload_to_s3(image: Image, source: Path) -> str | None:
    """Move the photo to S3 when credentials are configured.

    Returns the new object key, or None when S3 is off (local mode) or
    the file we processed was already fetched from S3.
    """
    if not settings.s3_enabled():
        return None
    if not str(source).startswith(str(settings.PUBLIC_DIR)):
        return None  # source was a temp download - it is already in S3

    ext = source.suffix.lower()
    key = f"events/{image.event_id}/{Path(image.s3_key).name}"
    s3_client.upload_file(source, key, _CONTENT_TYPES.get(ext, "application/octet-stream"))
    return key
