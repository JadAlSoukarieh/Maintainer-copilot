from __future__ import annotations

from dataclasses import dataclass, field


class EmbeddingUnavailableError(RuntimeError):
    pass


@dataclass(slots=True)
class LocalSentenceTransformerEmbedder:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    local_files_only: bool = True
    _model: object | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._model = None

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingUnavailableError("Cannot embed empty text.")
        model = self._load_model()
        try:
            encoded = model.encode([text], normalize_embeddings=True, convert_to_numpy=True)
        except Exception as exc:  # pragma: no cover - depends on local model cache
            raise EmbeddingUnavailableError("Embedding generation failed.") from exc
        vector = encoded[0].tolist() if getattr(encoded, "ndim", 1) == 2 else encoded.tolist()
        return [float(value) for value in vector]

    def is_available(self) -> bool:
        try:
            self._load_model()
        except EmbeddingUnavailableError:
            return False
        return True

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingUnavailableError("sentence-transformers is not installed.") from exc
        try:
            self._model = SentenceTransformer(self.model_name, local_files_only=self.local_files_only)
        except Exception as exc:  # pragma: no cover - depends on local model cache
            raise EmbeddingUnavailableError("Embedding model is not available locally.") from exc
        return self._model
