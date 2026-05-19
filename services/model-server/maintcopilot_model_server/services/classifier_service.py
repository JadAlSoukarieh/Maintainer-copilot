from __future__ import annotations

from dataclasses import dataclass

from maintcopilot_model_server.domain.errors import ConfigurationError
from maintcopilot_model_server.domain.schemas import ClassifyRequest, ClassifyResponse
from maintcopilot_model_server.domain.schemas import ProbabilityScore
from maintcopilot_model_server.infra.artifact_loader import ArtifactLoader, ClassifierArtifacts


@dataclass(slots=True)
class LoadedClassifier:
    tokenizer: object
    model: object
    device: str
    artifacts: ClassifierArtifacts


class ClassifierService:
    def __init__(self, loader: ArtifactLoader) -> None:
        self._loader = loader
        self._loaded: LoadedClassifier | None = None

    def classify(self, payload: ClassifyRequest) -> ClassifyResponse:
        loaded = self._ensure_loaded()
        text = self._format_text(payload.title, payload.body)
        torch = self._torch()
        with torch.no_grad():
            encoded = loaded.tokenizer(
                text,
                truncation=True,
                max_length=loaded.artifacts.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(loaded.device) for key, value in encoded.items()}
            outputs = loaded.model(**encoded)
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]

        id_to_label = {index: label for label, index in loaded.artifacts.label2id.items()}
        top_probabilities: list[ProbabilityScore] = []
        for index, probability in enumerate(probabilities.tolist()):
            label = id_to_label[index]
            top_probabilities.append(ProbabilityScore(label=label, probability=float(probability)))
        top_probabilities.sort(key=lambda item: item.probability, reverse=True)
        best = top_probabilities[0]
        return ClassifyResponse(
            label=best.label,
            confidence=best.probability,
            top_probabilities=top_probabilities,
            model_name=loaded.artifacts.model_name,
            model_type="transformer",
            model_hash=loaded.artifacts.model_hash,
            artifact_dir=str(loaded.artifacts.artifact_dir),
        )

    def _ensure_loaded(self) -> LoadedClassifier:
        if self._loaded is None:
            self._loaded = self._load()
        return self._loaded

    def _load(self) -> LoadedClassifier:
        artifacts = self._loader.load_classifier_artifacts()
        try:
            torch = self._torch()
            transformers = self._transformers()
        except ModuleNotFoundError as exc:
            raise ConfigurationError("Model server dependencies for transformer inference are not installed.") from exc

        tokenizer = transformers.AutoTokenizer.from_pretrained(str(artifacts.model_dir), local_files_only=True)
        model = transformers.AutoModelForSequenceClassification.from_pretrained(str(artifacts.model_dir), local_files_only=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        return LoadedClassifier(tokenizer=tokenizer, model=model, device=device, artifacts=artifacts)

    @staticmethod
    def _format_text(title: str, body: str) -> str:
        return f"TITLE: {title.strip()}\n\nBODY:\n{body.strip()}"

    @staticmethod
    def _torch():
        import torch

        return torch

    @staticmethod
    def _transformers():
        import transformers

        return transformers
