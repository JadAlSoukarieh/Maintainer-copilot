from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RagRetriever = Literal["sparse", "dense", "hybrid", "reranked"]
RagSourceType = Literal["doc", "resolved_issue"]
RagIntent = Literal["docs", "issue", "debug", "api", "memory", "network", "crypto", "stream", "fs", "dns", "unknown"]


class QueryRewriteResult(BaseModel):
    original_query: str
    rewritten_query: str
    added_terms: list[str] = Field(default_factory=list)
    intent: RagIntent = "unknown"
    preferred_source_type: RagSourceType | None = None


class RagAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    retriever: RagRetriever = "reranked"
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)
    query_rewrite: bool = True
    metadata_boost: bool = True
    source_type: RagSourceType | None = None


class RagCitation(BaseModel):
    chunk_id: str
    title: str
    source_type: RagSourceType
    url: str
    score: float
    text_excerpt: str


class RagAnswerDiagnostics(BaseModel):
    query_rewrite_enabled: bool
    metadata_boost_enabled: bool
    preferred_source_type: RagSourceType | None = None
    candidate_count: int
    requested_retriever: RagRetriever
    effective_retriever: RagRetriever
    fallback_reason: str | None = None


class RagAnswerResponse(BaseModel):
    answer: str
    method: Literal["extractive_rag"] = "extractive_rag"
    question: str
    rewritten_query: str
    intent: RagIntent
    retriever: RagRetriever
    alpha: float
    citations: list[RagCitation] = Field(default_factory=list)
    diagnostics: RagAnswerDiagnostics
