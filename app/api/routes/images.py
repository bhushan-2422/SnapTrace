"""Photo upload, listing, inspection and deletion."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    PageParams,
    get_current_user,
    get_db,
    get_owned_event,
    get_page_params,
    get_searchable_event,
)
from app.controllers import image_controller
from app.models.event import Event
from app.models.image import Image, ImageStatus
from app.models.user import User
from app.schemas.image import ImageResponse, ImageUploadResponse
from app.schemas.processing import FaceRecord
from app.services import image_service
from app.utils import file_utils

router = APIRouter(tags=["images"])

ImageStatusFilter = Literal["uploaded", "processing", "completed", "failed"]


def _image_or_404(db: Session, image_id: int) -> Image:
    image = image_service.get_image(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


def _event_of(db: Session, image: Image) -> Event:
    event = db.get(Event, image.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post(
    "/events/{event_id}/images",
    response_model=ImageUploadResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def upload_photos(
    files: list[UploadFile] = File(..., description="Photos to add to the album"),
    db: Session = Depends(get_db),
    event: Event = Depends(get_owned_event),
):
    """Store photos in public/upload/<event_id>/, mark them `uploaded`
    and push their ids onto the Redis queue for background processing."""
    try:
        return await image_controller.upload(db, event, files)
    except file_utils.UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except file_utils.UploadTooLarge as exc:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        )
    except image_service.TooManyFiles as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except image_service.QueueUnavailable:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Images were saved but the processing queue is unavailable; try again later.",
        )


@router.get("/events/{event_id}/images", response_model=list[ImageResponse])
def list_photos(
    image_status: ImageStatusFilter | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    event: Event = Depends(get_searchable_event),
    page: PageParams = Depends(get_page_params),
):
    """Newest first; filter with ?status=uploaded|processing|completed|failed."""
    status_enum = ImageStatus(image_status) if image_status else None
    return image_controller.list_by_event(
        db, event, status=status_enum, limit=page.limit, offset=page.offset
    )


@router.get("/images/{image_id}", response_model=ImageResponse)
def read_photo(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    image = _image_or_404(db, image_id)
    _event_of(db, image)  # the image must still belong to a live event
    return image_controller.detail(image)


@router.get("/images/{image_id}/faces", response_model=list[FaceRecord])
def read_photo_faces(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Detected faces (bbox, confidence, quality) for one photo."""
    image = _image_or_404(db, image_id)
    _event_of(db, image)
    return image_controller.faces(db, image)


@router.delete("/images/{image_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_photo(
    image_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Only the album owner may delete a photo; faces/embeddings follow."""
    image = _image_or_404(db, image_id)
    event = _event_of(db, image)
    if event.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You do not own this event")
    image_controller.delete(db, image)
