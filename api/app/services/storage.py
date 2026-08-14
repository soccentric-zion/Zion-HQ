"""Signed-URL issuance for device log/backup uploads (agent-gateway) and
the REST API's log/backup downloads. S3-compatible (real S3 or local MinIO)
per ARCHITECTURE.md §2 -- large blobs never touch the gRPC stream or
Postgres. Single source of truth shared by both services (same reasoning
as app/services/credentials.py).
"""

import uuid
from functools import lru_cache

import boto3

from app.config import get_settings


@lru_cache
def _client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def object_key(kind: str, device_id: str, object_id: str) -> str:
    return f"{kind}/{device_id}/{object_id}"


def presigned_upload_url(key: str, expires_in: int = 900) -> str:
    settings = get_settings()
    return _client().generate_presigned_url(
        "put_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires_in
    )


def presigned_download_url(key: str, expires_in: int = 300) -> str:
    settings = get_settings()
    return _client().generate_presigned_url(
        "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires_in
    )


def new_object_id() -> uuid.UUID:
    return uuid.uuid4()
