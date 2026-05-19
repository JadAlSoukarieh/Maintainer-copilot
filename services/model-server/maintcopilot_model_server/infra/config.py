from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "maintainers-copilot-model-server"
    log_level: str = "INFO"
    artifact_dir: str = "artifacts/classifier"
    classifier_artifact_dir: str = "artifacts/classifier/transformer"
    classifier_model_dir: str = "artifacts/classifier/transformer/model"
    classifier_require_artifacts: bool = True
    classifier_max_length: int = 512

    model_config = SettingsConfigDict(env_prefix="MODEL_SERVER_", env_file=".env", extra="ignore")
