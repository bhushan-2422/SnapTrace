"""Event (album) CRUD."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.user import User
from app.repositories.event_repository import EventRepository


class NotEventOwner(Exception):
    """The acting user does not own this event."""


def create_event(db: Session, *, owner_id: int, name: str, description: str | None) -> Event:
    event = Event(name=name.strip(), description=description, owner_id=owner_id)
    EventRepository(db).add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, *, owner_id: int, limit: int, offset: int) -> list[Event]:
    return EventRepository(db).list(owner_id=owner_id, limit=limit, offset=offset)


def get_event(db: Session, event_id: int) -> Event | None:
    return EventRepository(db).get_by_id(event_id)


def require_owner(event: Event, user: User) -> None:
    """Raise NotEventOwner unless `user` created `event`."""
    if event.owner_id != user.id:
        raise NotEventOwner(event.id)


def update_event(
    db: Session,
    event: Event,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Event:
    if name is not None:
        event.name = name.strip()
    if description is not None:
        event.description = description
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event: Event) -> None:
    """Delete the event; images/faces/embeddings cascade away."""
    EventRepository(db).delete(event)
    db.commit()
