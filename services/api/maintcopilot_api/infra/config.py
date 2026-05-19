from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "maintainers-copilot-api"
    env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+pysqlite:///:memory:"
    require_vault: bool = True
    vault_addr: str = "http://vault:8200"
    vault_token: str = "dev-root-token"
    redis_url: str = "redis://redis:6379/0"
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "maintainers-copilot"
    model_server_url: str = "http://model-server:8001"
    jwt_secret: str | None = None
    jwt_exp_minutes: int = 60
    invite_exp_hours: int = 72
    anthropic_model_name: str = "claude-haiku-4-5-20251001"
    anthropic_api_key_secret_path: str | None = None
    require_llm_key: bool = False

    model_config = SettingsConfigDict(env_prefix="API_", env_file=".env", extra="ignore")
