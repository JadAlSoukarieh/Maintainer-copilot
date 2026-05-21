from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from maintcopilot_api.domain.rag import RagAnswerRequest
from maintcopilot_api.services.rag.golden import load_jsonl, validate_rag_golden
from maintcopilot_api.services.rag.rag_service import RagService
from maintcopilot_api.services.rag.retrieval import load_corpus_rows

JUDGE_VERSION = "frozen-rag-judge-v1"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "use",
    "with",
}
GENERIC_ANSWER_TOKENS = {
    "answer",
    "based",
    "below",
    "cited",
    "citations",
    "closest",
    "compare",
    "context",
    "debugging",
    "docs",
    "evidence",
    "guaranteed",
    "handling",
    "issue",
    "issues",
    "knowledge",
    "lifecycle",
    "local",
    "node",
    "node.js",
    "points",
    "project",
    "relevant",
    "related",
    "reports",
    "reproduction",
    "retrieved",
    "sections",
    "show",
    "similar",
    "socket",
    "source",
    "starting",
    "steps",
    "supporting",
    "symptoms",
    "treat",
    "truth",
}
REFUSAL_MARKERS = ("could not find enough", "insufficient context", "no grounded context")


def run_rag_generation_eval(
    *,
    golden_path: Path,
    corpus_path: Path,
    thresholds_path: Path,
    report_path: Path,
    embedding_index_dir: Path,
    reranker_model_path: Path,
    human_labels_path: Path,
    limit: int | None = None,
) -> tuple[int, dict[str, Any]]:
    corpus_rows = load_corpus_rows(corpus_path)
    golden_rows = load_jsonl(golden_path)
    if limit is not None:
        golden_rows = golden_rows[:limit]
    validation = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows, require_final=(limit is None))
    if not validation["ok"]:
        return 1, {"ok": False, "message": "RAG golden set failed validation.", "validation": validation}

    service = RagService(
        corpus_path=corpus_path,
        embedding_index_dir=embedding_index_dir,
        reranker_model_path=reranker_model_path,
        rerank_top_n=20,
    )
    details = []
    for row in golden_rows:
        response = service.answer_rag_question(RagAnswerRequest(question=str(row["question"]), top_k=5))
        score = judge_answer(
            question=str(row["question"]),
            ideal_answer=str(row["ideal_answer"]),
            answer=response.answer,
            citations=[citation.model_dump() for citation in response.citations],
            ground_truth_chunk_ids=[str(item) for item in row["ground_truth_chunk_ids"]],
        )
        details.append(
            {
                "golden_id": row["golden_id"],
                "question": row["question"],
                "ideal_answer": row["ideal_answer"],
                "generated_answer": response.answer,
                "answer": response.answer,
                "citations": [citation.model_dump() for citation in response.citations],
                "citation_chunk_ids": [citation.chunk_id for citation in response.citations],
                "retriever": response.retriever,
                **score,
            }
        )

    metrics = aggregate_generation_metrics(details)
    thresholds = load_generation_thresholds(thresholds_path)
    human_labels = load_human_labels(human_labels_path)
    agreement = compare_human_labels(details, human_labels)
    failures = evaluate_generation_thresholds(metrics, thresholds, agreement)
    report = {
        "judge_version": JUDGE_VERSION,
        "mode": "deterministic",
        "example_count": len(details),
        "answer_relevancy_avg": metrics["answer_relevancy_avg"],
        "faithfulness_avg": metrics["faithfulness_avg"],
        "citation_coverage": metrics["citation_coverage"],
        "groundedness_pass_rate": metrics["groundedness_pass_rate"],
        "average_answer_length": metrics["average_answer_length"],
        "refusal_or_empty_rate": metrics["refusal_or_empty_rate"],
        "ai_assisted_labeled_count": agreement["ai_assisted_labeled_count"],
        "human_labeled_count": agreement["human_labeled_count"],
        "human_label_review_status": agreement["review_status"],
        "judge_human_agreement": agreement["agreement_rate"],
        "disagreements": agreement["disagreements"],
        "thresholds": thresholds,
        "threshold_gate": "PASS" if not failures else "FAIL",
        "passed": not failures,
        "failures": failures,
        "details": details,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return (0 if not failures else 1), report


def build_generation_report(
    *,
    mode: str,
    details: list[dict[str, Any]],
    thresholds: dict[str, float],
    agreement: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = aggregate_generation_metrics(details)
    failures = evaluate_generation_thresholds(metrics, thresholds, agreement)
    report = {
        "judge_version": JUDGE_VERSION,
        "mode": mode,
        "example_count": len(details),
        "answer_relevancy_avg": metrics["answer_relevancy_avg"],
        "faithfulness_avg": metrics["faithfulness_avg"],
        "citation_coverage": metrics["citation_coverage"],
        "groundedness_pass_rate": metrics["groundedness_pass_rate"],
        "average_answer_length": metrics["average_answer_length"],
        "refusal_or_empty_rate": metrics["refusal_or_empty_rate"],
        "ai_assisted_labeled_count": agreement["ai_assisted_labeled_count"],
        "human_labeled_count": agreement["human_labeled_count"],
        "human_label_review_status": agreement["review_status"],
        "judge_human_agreement": agreement["agreement_rate"],
        "disagreements": agreement["disagreements"],
        "thresholds": thresholds,
        "threshold_gate": "PASS" if not failures else "FAIL",
        "passed": not failures,
        "failures": failures,
        "details": details,
    }
    if extra:
        report.update(extra)
    return report


def judge_answer(
    *,
    question: str,
    ideal_answer: str,
    answer: str,
    citations: list[dict[str, Any]],
    ground_truth_chunk_ids: list[str],
) -> dict[str, Any]:
    answer_tokens = _tokens(answer)
    expected_tokens = _tokens(f"{question} {ideal_answer}")
    citation_text = " ".join(f"{item.get('title', '')} {item.get('text_excerpt', '')}" for item in citations)
    citation_tokens = _tokens(citation_text)

    answer_text_relevance = max(_overlap_score(answer_tokens, expected_tokens), _overlap_score(expected_tokens, answer_tokens))
    citation_relevance = max(_overlap_score(citation_tokens, expected_tokens), _overlap_score(expected_tokens, citation_tokens))
    answer_relevancy = min(1.0, (0.45 * answer_text_relevance) + (0.55 * citation_relevance))
    faithfulness_tokens = answer_tokens - GENERIC_ANSWER_TOKENS
    faithfulness = _overlap_score(faithfulness_tokens, citation_tokens)
    cited_ids = {str(item.get("chunk_id")) for item in citations}
    truth_ids = set(ground_truth_chunk_ids)
    citation_coverage = bool(cited_ids & truth_ids)
    refusal_or_empty = not answer.strip() or any(marker in answer.lower() for marker in REFUSAL_MARKERS)
    groundedness_pass = bool(citations) and faithfulness >= 0.5 and not refusal_or_empty
    return {
        "answer_relevancy": answer_relevancy,
        "faithfulness": faithfulness,
        "citation_coverage": citation_coverage,
        "groundedness_pass": groundedness_pass,
        "answer_length": len(answer),
        "refusal_or_empty": refusal_or_empty,
    }


def aggregate_generation_metrics(details: list[dict[str, Any]]) -> dict[str, float]:
    total = len(details)
    if total == 0:
        raise ValueError("At least one generation eval detail is required.")
    return {
        "answer_relevancy_avg": sum(item["answer_relevancy"] for item in details) / total,
        "faithfulness_avg": sum(item["faithfulness"] for item in details) / total,
        "citation_coverage": sum(1 for item in details if item["citation_coverage"]) / total,
        "groundedness_pass_rate": sum(1 for item in details if item["groundedness_pass"]) / total,
        "average_answer_length": sum(item["answer_length"] for item in details) / total,
        "refusal_or_empty_rate": sum(1 for item in details if item["refusal_or_empty"]) / total,
    }


def load_generation_thresholds(path: Path) -> dict[str, float]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    section = payload.get("rag_generation")
    if not isinstance(section, dict):
        raise ValueError("Threshold file is missing a rag_generation section.")
    return {
        "min_answer_relevancy": float(section.get("min_answer_relevancy", 0.45)),
        "min_faithfulness": float(section.get("min_faithfulness", 0.50)),
        "min_citation_coverage": float(section.get("min_citation_coverage", 0.60)),
        "min_groundedness_pass_rate": float(section.get("min_groundedness_pass_rate", 0.60)),
        "min_human_judge_agreement": float(section.get("min_human_judge_agreement", 0.60)),
    }


def evaluate_generation_thresholds(
    metrics: dict[str, float],
    thresholds: dict[str, float],
    agreement: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    checks = [
        ("answer_relevancy_avg", "min_answer_relevancy"),
        ("faithfulness_avg", "min_faithfulness"),
        ("citation_coverage", "min_citation_coverage"),
        ("groundedness_pass_rate", "min_groundedness_pass_rate"),
    ]
    for metric_key, threshold_key in checks:
        if metrics[metric_key] < thresholds[threshold_key]:
            failures.append(f"{metric_key} {metrics[metric_key]:.4f} < {thresholds[threshold_key]:.4f}")
    if agreement["human_labeled_count"] and agreement["agreement_rate"] < thresholds["min_human_judge_agreement"]:
        failures.append(
            f"judge_human_agreement {agreement['agreement_rate']:.4f} < {thresholds['min_human_judge_agreement']:.4f}"
        )
    return failures


def load_human_labels(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {
        str(row["golden_id"]): row
        for row in load_jsonl(path)
        if isinstance(row, dict) and row.get("golden_id")
    }


def compare_human_labels(details: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(item["golden_id"]): item for item in details}
    compared = 0
    agreements = 0
    statuses: set[str] = set()
    disagreements: list[dict[str, Any]] = []
    ai_assisted_count = 0
    for golden_id, label in labels.items():
        detail = by_id.get(golden_id)
        if detail is None:
            continue
        review_status = str(label.get("review_status") or "unknown")
        statuses.add(review_status)
        if review_status != "human_spot_checked":
            if review_status == "ai_assisted_initial":
                ai_assisted_count += 1
            continue
        faithful_match = bool(label.get("human_faithful")) == bool(detail["groundedness_pass"])
        relevant_match = bool(label.get("human_relevant")) == (detail["answer_relevancy"] >= 0.45)
        compared += 2
        agreements += int(faithful_match) + int(relevant_match)
        if not faithful_match or not relevant_match:
            disagreements.append(
                {
                    "golden_id": golden_id,
                    "human_faithful": label.get("human_faithful"),
                    "judge_groundedness_pass": detail["groundedness_pass"],
                    "human_relevant": label.get("human_relevant"),
                    "judge_relevant": detail["answer_relevancy"] >= 0.45,
                }
            )
    return {
        "ai_assisted_labeled_count": ai_assisted_count,
        "human_labeled_count": compared // 2,
        "review_status": sorted(statuses),
        "agreement_rate": agreements / compared if compared else 0.0,
        "disagreements": disagreements,
    }


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 2 and token.lower() not in STOPWORDS
    }


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left:
        return 0.0
    if not right:
        return 0.0
    return len(left & right) / len(left)
