from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    artifact_dir: str
    artifacts_present: bool


class ClassifyRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(default="")


class ProbabilityScore(BaseModel):
    label: str
    probability: float


class ClassifyResponse(BaseModel):
    label: str
    confidence: float
    top_probabilities: list[ProbabilityScore]
    model_name: str
    model_type: str
    model_hash: str
    artifact_dir: str


class NerRequest(BaseModel):
    text: str = Field(min_length=1)


class Entity(BaseModel):
    text: str
    label: str
    start: int
    end: int


class NerResponse(BaseModel):
    entities: list[Entity]
    model_version: str


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1)
    max_sentences: int = Field(default=2, ge=1, le=10)


class SummarizeResponse(BaseModel):
    summary: str
    sentences_used: int
    metadata: dict[str, Any] = Field(default_factory=dict)
