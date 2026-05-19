from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maintcopilot_model_server.domain.errors import ConfigurationError


@dataclass(slots=True)
class ClassifierArtifacts:
    artifact_dir: Path
    model_dir: Path
    metrics_path: Path
    model_hash: str
    model_name: str
    model_type: str
    label2id: dict[str, int]
    max_length: int


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "artifacts").exists() and (parent / "services").exists():
            return parent
    raise RuntimeError("Could not resolve repository root.")


class ArtifactLoader:
    def __init__(
        self,
        artifact_dir: str,
        *,
        model_dir: str | None = None,
        require_artifacts: bool = True,
        max_length: int = 512,
    ) -> None:
        self.artifact_dir = self._resolve_path(artifact_dir)
        self.model_dir = self._resolve_path(model_dir) if model_dir is not None else self.artifact_dir / "model"
        self.require_artifacts = require_artifacts
        self.max_length = max_length
        self.metrics_path = self.artifact_dir / "metrics.json"
        self.model_card_path = self.artifact_dir / "model_card.md"
        self.model_weights_path = self.model_dir / "model.safetensors"

    def artifacts_present(self) -> bool:
        return self.artifact_dir.exists() and self.model_dir.exists() and self.metrics_path.exists() and self.model_weights_path.exists()

    def load_classifier_artifacts(self) -> ClassifierArtifacts:
        if not self.artifacts_present():
            raise ConfigurationError("Required classifier artifacts are missing.")
        try:
            metrics = json.loads(self.metrics_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError("Classifier metrics artifact is missing.") from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError("Classifier metrics artifact is not valid JSON.") from exc

        expected_hash = metrics.get("model_sha256")
        if not isinstance(expected_hash, str) or not expected_hash:
            raise ConfigurationError("Classifier metrics artifact is missing model_sha256.")

        actual_hash = self.compute_sha256(self.model_weights_path)
        if actual_hash != expected_hash:
            raise ConfigurationError("Classifier artifact hash mismatch.")

        label2id = metrics.get("label2id")
        if not isinstance(label2id, dict) or not label2id:
            raise ConfigurationError("Classifier metrics artifact is missing label2id.")

        base_model = metrics.get("base_model")
        if not isinstance(base_model, str) or not base_model:
            raise ConfigurationError("Classifier metrics artifact is missing base_model.")

        model_type = metrics.get("model_type")
        if not isinstance(model_type, str) or not model_type:
            raise ConfigurationError("Classifier metrics artifact is missing model_type.")

        metric_max_length = metrics.get("max_length")
        effective_max_length = int(metric_max_length) if isinstance(metric_max_length, int) and metric_max_length > 0 else self.max_length

        return ClassifierArtifacts(
            artifact_dir=self.artifact_dir,
            model_dir=self.model_dir,
            metrics_path=self.metrics_path,
            model_hash=actual_hash,
            model_name=base_model,
            model_type=model_type,
            label2id={str(key): int(value) for key, value in label2id.items()},
            max_length=effective_max_length,
        )

    @staticmethod
    def compute_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _resolve_path(path_value: str | None) -> Path:
        if path_value is None:
            return repo_root()
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate
        return repo_root() / candidate
