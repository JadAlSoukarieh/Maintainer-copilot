from __future__ import annotations

from maintcopilot_api.services.rag.generation_eval import (
    aggregate_generation_metrics,
    build_generation_report,
    compare_human_labels,
    evaluate_generation_thresholds,
    judge_answer,
)


def test_generation_judge_scores_relevant_grounded_answer() -> None:
    score = judge_answer(
        question="How does stream.pipeline clean up after errors?",
        ideal_answer="stream.pipeline calls stream.destroy(err) on streams after a pipeline error.",
        answer="The stream.pipeline docs say it calls stream.destroy(err) on streams after a pipeline error.",
        citations=[
            {
                "chunk_id": "doc-stream-001",
                "title": "stream",
                "text_excerpt": "stream.pipeline calls stream.destroy(err) on all streams after an error.",
            }
        ],
        ground_truth_chunk_ids=["doc-stream-001"],
    )

    assert score["answer_relevancy"] > 0.45
    assert score["faithfulness"] > 0.50
    assert score["citation_coverage"] is True
    assert score["groundedness_pass"] is True


def test_generation_judge_penalizes_unsupported_answer() -> None:
    score = judge_answer(
        question="How do I debug ECONNRESET?",
        ideal_answer="Use cited HTTP issue evidence.",
        answer="The fix is to rewrite the TLS stack and disable garbage collection.",
        citations=[{"chunk_id": "issue-1", "title": "ECONNRESET issue", "text_excerpt": "HTTP server reports ECONNRESET."}],
        ground_truth_chunk_ids=["issue-1"],
    )

    assert score["faithfulness"] < 0.50
    assert score["groundedness_pass"] is False


def test_generation_threshold_failures_are_reported() -> None:
    details = [
        {
            "answer_relevancy": 0.1,
            "faithfulness": 0.1,
            "citation_coverage": False,
            "groundedness_pass": False,
            "answer_length": 10,
            "refusal_or_empty": True,
        }
    ]
    metrics = aggregate_generation_metrics(details)
    failures = evaluate_generation_thresholds(
        metrics,
        {
            "min_answer_relevancy": 0.45,
            "min_faithfulness": 0.50,
            "min_citation_coverage": 0.60,
            "min_groundedness_pass_rate": 0.60,
            "min_human_judge_agreement": 0.60,
        },
        {"human_labeled_count": 0, "agreement_rate": 0.0},
    )

    assert failures


def test_human_label_agreement_compares_judge_outputs() -> None:
    details = [
        {
            "golden_id": "rag-golden-001",
            "answer_relevancy": 0.8,
            "groundedness_pass": True,
        }
    ]
    labels = {
        "rag-golden-001": {
            "human_faithful": True,
            "human_relevant": True,
            "review_status": "human_spot_checked",
        }
    }

    agreement = compare_human_labels(details, labels)

    assert agreement["human_labeled_count"] == 1
    assert agreement["ai_assisted_labeled_count"] == 0
    assert agreement["agreement_rate"] == 1.0
    assert agreement["review_status"] == ["human_spot_checked"]


def test_ai_assisted_labels_are_not_counted_as_human_review() -> None:
    agreement = compare_human_labels(
        [{"golden_id": "rag-golden-001", "answer_relevancy": 0.8, "groundedness_pass": True}],
        {"rag-golden-001": {"human_faithful": True, "human_relevant": True, "review_status": "ai_assisted_initial"}},
    )

    assert agreement["ai_assisted_labeled_count"] == 1
    assert agreement["human_labeled_count"] == 0


def test_generation_report_includes_expected_fields() -> None:
    report = build_generation_report(
        mode="deterministic",
        details=[
            {
                "golden_id": "rag-golden-001",
                "answer_relevancy": 0.6,
                "faithfulness": 0.7,
                "citation_coverage": True,
                "groundedness_pass": True,
                "answer_length": 120,
                "refusal_or_empty": False,
            }
        ],
        thresholds={
            "min_answer_relevancy": 0.45,
            "min_faithfulness": 0.50,
            "min_citation_coverage": 0.60,
            "min_groundedness_pass_rate": 0.60,
            "min_human_judge_agreement": 0.60,
        },
        agreement={"ai_assisted_labeled_count": 1, "human_labeled_count": 0, "review_status": ["ai_assisted_initial"], "agreement_rate": 0.0, "disagreements": []},
        extra={"successful_claude_calls": 1},
    )

    assert report["mode"] == "deterministic"
    assert report["threshold_gate"] == "PASS"
    assert report["successful_claude_calls"] == 1
