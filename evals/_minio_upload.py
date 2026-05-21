"""Upload eval report JSON to MinIO if the endpoint is configured via env vars."""
from __future__ import annotations

import json
import os
from pathlib import Path


def try_upload_report(report_path: Path) -> None:
    """
    Upload *report_path* to MinIO when MINIO_ENDPOINT is set in the environment.
    Silently skips when MinIO is not configured or not reachable.
    """
    endpoint = os.environ.get("MINIO_ENDPOINT") or os.environ.get("API_MINIO_ENDPOINT")
    if not endpoint:
        return
    access_key = os.environ.get("MINIO_ACCESS_KEY") or os.environ.get("API_MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY") or os.environ.get("API_MINIO_SECRET_KEY", "minioadmin")
    bucket = os.environ.get("MINIO_BUCKET") or os.environ.get("API_MINIO_BUCKET", "maintainers-copilot")

    try:
        from minio import Minio
        from minio.error import S3Error
        import io

        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        key = f"reports/{report_path.name}"
        body = report_path.read_bytes()
        client.put_object(bucket, key, io.BytesIO(body), length=len(body), content_type="application/json")
        print(f"MinIO: uploaded report to s3://{bucket}/{key}")
    except ImportError:
        pass  # minio package not installed in this env
    except Exception as exc:
        print(f"MinIO: upload skipped ({exc})")
