from __future__ import annotations

import io
import json
import logging
from typing import Any

try:
    from minio import Minio
    from minio.error import S3Error

    _MINIO_AVAILABLE = True
except ImportError:
    _MINIO_AVAILABLE = False


logger = logging.getLogger("app.minio")


class MinioStorageError(RuntimeError):
    pass


class MinioClient:
    def __init__(self, *, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        if not _MINIO_AVAILABLE:
            raise MinioStorageError("minio package is not installed.")
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False,
            )
        return self._client

    # ------------------------------------------------------------------
    # Bucket management
    # ------------------------------------------------------------------

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not already exist."""
        client = self._get_client()
        try:
            if not client.bucket_exists(self.bucket):
                client.make_bucket(self.bucket)
                logger.info("minio.bucket_created", extra={"event_fields": {"bucket": self.bucket}})
        except S3Error as exc:
            raise MinioStorageError(f"MinIO bucket setup failed: {exc}") from exc

    def check_health(self) -> bool:
        """Return True if MinIO is reachable and the bucket exists or can be created."""
        try:
            self.ensure_bucket()
            return True
        except (MinioStorageError, Exception):
            return False

    # ------------------------------------------------------------------
    # Read / write
    # ------------------------------------------------------------------

    def put_json(self, key: str, data: Any) -> None:
        """Serialise *data* as JSON and store it at *key*."""
        client = self._get_client()
        body = json.dumps(data, default=str).encode("utf-8")
        try:
            client.put_object(
                self.bucket,
                key,
                io.BytesIO(body),
                length=len(body),
                content_type="application/json",
            )
            logger.debug("minio.put_json", extra={"event_fields": {"key": key, "bytes": len(body)}})
        except S3Error as exc:
            raise MinioStorageError(f"MinIO put_json failed for {key!r}: {exc}") from exc

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Store raw bytes at *key*."""
        client = self._get_client()
        try:
            client.put_object(
                self.bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise MinioStorageError(f"MinIO put_bytes failed for {key!r}: {exc}") from exc

    def get_json(self, key: str) -> Any:
        """Fetch the object at *key* and deserialise it as JSON."""
        client = self._get_client()
        try:
            response = client.get_object(self.bucket, key)
            return json.loads(response.read())
        except S3Error as exc:
            raise MinioStorageError(f"MinIO get_json failed for {key!r}: {exc}") from exc

    def list_keys(self, prefix: str = "") -> list[str]:
        """Return all object keys under *prefix*."""
        client = self._get_client()
        try:
            return [obj.object_name for obj in client.list_objects(self.bucket, prefix=prefix, recursive=True)]
        except S3Error as exc:
            raise MinioStorageError(f"MinIO list_keys failed for prefix {prefix!r}: {exc}") from exc
