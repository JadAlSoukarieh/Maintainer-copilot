from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "maintainers-copilot-model-server"
    log_level: str = "INFO"
    artifact_dir: str = "/app/artifacts/classifier"

    model_config = SettingsConfigDict(env_prefix="MODEL_SERVER_", env_file=".env", extra="ignore")

