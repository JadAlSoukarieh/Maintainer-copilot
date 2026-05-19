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
    title: str = Field(min_length=1)
    body: str = Field(default="")


class Entity(BaseModel):
    text: str
    type: str
    start: int
    end: int


class NerResponse(BaseModel):
    entities: list[Entity]


class SummarizeRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(default="")
    max_bullets: int = Field(default=5, ge=1, le=10)


class SummarizeResponse(BaseModel):
    summary: str
    bullets: list[str]
    method: str
