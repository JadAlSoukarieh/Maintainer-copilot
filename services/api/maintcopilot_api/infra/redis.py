from __future__ import annotations


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url

