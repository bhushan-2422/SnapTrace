"""Small OpenCV helpers shared by the worker and the search endpoint."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def read_bgr(path: str | Path) -> np.ndarray | None:
    """Read an image the same way the detection stage does (BGR).

    Returns None when the file is missing or not a readable image -
    callers turn that into a failed image rather than a 500.
    """
    img = cv2.imread(str(path))
    return img if img is not None and img.size else None


def sharpness_score(img: np.ndarray) -> float:
    """Laplacian variance - the basic "is this face sharp enough?" metric.

    Stored in `faces.quality_score` so we can later decide at search time
    whether a blurry embedding should rank lower.  No threshold is applied
    here; collecting the numbers comes first.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
