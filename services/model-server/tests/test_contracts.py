from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintcopilot_model_server.api.routes import classify
from maintcopilot_model_server.domain.errors import ConfigurationError
from maintcopilot_model_server.domain.schemas import ClassifyRequest
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader
from maintcopilot_model_server.services.classifier_service import ClassifierService


ROOT = Path(__file__).resolve().parents[3]
TRANSFORMER_ARTIFACT_DIR = ROOT / "artifacts" / "classifier" / "transformer"
TRANSFORMER_MODEL_DIR = TRANSFORMER_ARTIFACT_DIR / "model"


def test_artifact_hash_computation() -> None:
    computed = ArtifactLoader.compute_sha256(TRANSFORMER_MODEL_DIR / "model.safetensors")
    metrics = json.loads((TRANSFORMER_ARTIFACT_DIR / "metrics.json").read_text(encoding="utf-8"))
    assert computed == metrics["model_sha256"]


def test_missing_artifact_fails_cleanly(tmp_path: Path) -> None:
    loader = ArtifactLoader(str(tmp_path), model_dir=str(tmp_path / "model"))
    with pytest.raises(ConfigurationError, match="Required classifier artifacts are missing"):
        loader.load_classifier_artifacts()


def test_hash_mismatch_fails_cleanly(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "transformer"
    model_dir = artifact_dir / "model"
    model_dir.mkdir(parents=True)
    (model_dir / "model.safetensors").write_bytes(b"not-the-real-model")
    (artifact_dir / "metrics.json").write_text(
        json.dumps(
            {
                "model_sha256": "deadbeef",
                "base_model": "roberta-base",
                "model_type": "fine_tuned_transformer_encoder",
                "label2id": {"bug": 0, "feature": 1, "docs": 2, "question": 3},
                "max_length": 512,
            }
        ),
        encoding="utf-8",
    )
    loader = ArtifactLoader(str(artifact_dir), model_dir=str(model_dir))
    with pytest.raises(ConfigurationError, match="hash mismatch"):
        loader.load_classifier_artifacts()


def test_classify_returns_schema_valid_output() -> None:
    service = ClassifierService(ArtifactLoader(str(TRANSFORMER_ARTIFACT_DIR), model_dir=str(TRANSFORMER_MODEL_DIR)))
    response = classify(
        ClassifyRequest(
            title="dns.lookup blocks filesystem I/O",
            body="On networks with slow DNS response, blocking calls from dns.lookup delay serial and filesystem work.",
        ),
        service,
    )

    assert response.label in {"bug", "feature", "docs", "question"}
    assert isinstance(response.confidence, float)
    assert response.model_name == "roberta-base"
    assert response.model_type == "transformer"
    assert len(response.top_probabilities) == 4
    assert {item.label for item in response.top_probabilities} == {"bug", "feature", "docs", "question"}
