from __future__ import annotations

from pathlib import Path


class ArtifactLoader:
    def __init__(self, artifact_dir: str) -> None:
        self.artifact_dir = Path(artifact_dir)

    def artifacts_present(self) -> bool:
        return self.artifact_dir.exists() and any(self.artifact_dir.iterdir())

    def model_version(self) -> str:
        return "placeholder-classifier-v1"

