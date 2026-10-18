"""`events` table: a named photo collection (fest, wedding, trip, ...)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, utcnow


class Event(Base):
    __tablename__ = "events"
    # Most listings are "events owned by me" -> index the FK column.
    __table_args__ = (Index("ix_events_owner_id", "owner_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ondelete="CASCADE": deleting a user removes their events (safety net for
    # raw SQL; the ORM relationship cascades as well).
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="events")
    # Deleting an event removes its image rows (and, transitively, faces).
    images: Mapped[list["Image"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Event id={self.id} name={self.name!r}>"
