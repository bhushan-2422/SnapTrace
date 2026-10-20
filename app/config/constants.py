"""Named constants shared by more than one module."""

from __future__ import annotations

# Redis queue holding image ids waiting to be processed.
IMAGE_QUEUE = "snaptrace:queue:images"

# Model identification stored on every face_embeddings row.
EMBEDDING_MODEL_NAME = "ArcFace"
EMBEDDING_MODEL_VERSION = "deepface-0.0.102"
