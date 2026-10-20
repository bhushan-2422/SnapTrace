"""Configuration package.

    from app.config import settings, constants   # modules
    from app.config import PUBLIC_DIR             # common path shortcuts
"""

from app.config import constants, settings
from app.config.settings import PUBLIC_DIR, SEARCH_DIR, TEMP_DIR, UPLOAD_DIR

__all__ = [
    "PUBLIC_DIR",
    "SEARCH_DIR",
    "TEMP_DIR",
    "UPLOAD_DIR",
    "constants",
    "settings",
]
