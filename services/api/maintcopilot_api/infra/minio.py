from __future__ import annotations


class MinioClient:
    def __init__(self, *, endpoint: str, access_key: str, secret_key: str, bucket: str) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket

