"""External integrations: S3 object storage and the Redis queue."""

from app.integrations import redis_client, s3_client

__all__ = ["redis_client", "s3_client"]
