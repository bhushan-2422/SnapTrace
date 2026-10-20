"""Saving uploaded files to disk and validating them.

Limits are enforced while streaming the file, not after it lands on
disk, so a huge body can never fill the filesystem.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


class UploadTooLarge(Exception):
    """The uploaded file exceeds MAX_UPLOAD_MB."""


class UnsupportedFileType(Exception):
    """The uploaded file is not one of the allowed image extensions."""


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def extension_of(filename: str | None) -> str:
    """Lower-cased extension including the dot, or "" when there is none."""
    if not filename:
        return ""
    return Path(filename).suffix.lower()


def validate_extension(filename: str | None) -> str:
    ext = extension_of(filename)
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise UnsupportedFileType(
            f"allowed extensions: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )
    return ext


def safe_original_name(filename: str | None) -> str:
    """Keep the human-readable name, but strip anything path-like."""
    base = Path(filename or "image").name
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or "image"
    return cleaned[:255]


def unique_key(event_id: int, original_filename: str) -> str:
    """Storage key for one upload - unique, event-scoped, extension kept.

    Also used as the S3 object key, which is why the event id is part of
    it (images.s3_key is UNIQUE across the whole table).
    """
    ext = validate_extension(original_filename)
    return f"events/{event_id}/{uuid.uuid4().hex}{ext}"


async def save_upload(upload: UploadFile, destination: Path) -> int:
    """Stream an upload to `destination`, enforcing MAX_UPLOAD_MB.

    Returns the number of bytes written.  The partial file is removed
    if the size limit is exceeded.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    written = 0

    with destination.open("wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)  # 1 MB at a time
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                out.close()
                destination.unlink(missing_ok=True)
                raise UploadTooLarge(
                    f"{upload.filename!r} is larger than {settings.MAX_UPLOAD_MB} MB"
                )
            out.write(chunk)

    if written == 0:
        destination.unlink(missing_ok=True)
        raise UnsupportedFileType("empty file")

    return written
