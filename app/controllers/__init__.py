"""Controllers: thin per-request orchestration between routes and services."""

from app.controllers import (
    auth_controller,
    event_controller,
    image_controller,
    search_controller,
    user_controller,
)

__all__ = [
    "auth_controller",
    "event_controller",
    "image_controller",
    "search_controller",
    "user_controller",
]
