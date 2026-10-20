"""Event albums: create, list, view, update, delete, processing status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    PageParams,
    get_db,
    get_current_user,
    get_owned_event,
    get_page_params,
    get_searchable_event,
)
from app.controllers import event_controller
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventCreate, EventResponse, EventUpdate
from app.schemas.processing import EventProcessingStatusResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return event_controller.create(db, user, payload)


@router.get("", response_model=list[EventResponse])
def list_my_events(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: PageParams = Depends(get_page_params),
):
    return event_controller.list_mine(db, user, limit=page.limit, offset=page.offset)


@router.get("/{event_id}", response_model=EventResponse)
def read_event(event: Event = Depends(get_searchable_event)):
    return event_controller.get(event)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    payload: EventUpdate,
    db: Session = Depends(get_db),
    event: Event = Depends(get_owned_event),
):
    return event_controller.update(db, event, payload)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(db: Session = Depends(get_db), event: Event = Depends(get_owned_event)):
    event_controller.delete(db, event)


@router.get("/{event_id}/status", response_model=EventProcessingStatusResponse)
def processing_status(
    db: Session = Depends(get_db),
    event: Event = Depends(get_owned_event),
):
    """Organizer view: how many photos are uploaded/processing/done/failed."""
    return event_controller.processing_status(db, event)
