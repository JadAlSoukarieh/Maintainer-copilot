#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "services" / "api"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from maintcopilot_api.services.rag.generation_eval import (  # noqa: E402
    build_generation_report,
    compare_human_labels,
    judge_answer,
    load_generation_thresholds,
    load_human_labels,
    run_rag_generation_eval,
)
from maintcopilot_api.services.rag.golden import load_jsonl, validate_rag_golden  # noqa: E402
from maintcopilot_api.services.rag.retrieval import load_corpus_rows  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic RAG answer generation.")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--corpus-path", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--thresholds-path", default="evals/eval_thresholds.yaml")
    parser.add_argument("--report-path", default="reports/rag_generation_eval_report.json")
    parser.add_argument("--output")
    parser.add_argument("--embedding-index-dir", default="artifacts/rag/embeddings")
    parser.add_argument("--reranker-model-path", default="artifacts/rag/reranker_model")
    parser.add_argument("--human-labels-path", default="data/rag/golden/rag_generation_human_labels.jsonl")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mode", choices=["deterministic", "claude"], default="deterministic")
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--require-claude-success", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path_arg = args.output or args.report_path
    if args.mode == "claude":
        return run_claude_eval(args, report_path_arg=report_path_arg)
    exit_code, report = run_rag_generation_eval(
        golden_path=(ROOT / args.golden_path).resolve(),
        corpus_path=(ROOT / args.corpus_path).resolve(),
        thresholds_path=(ROOT / args.thresholds_path).resolve(),
        report_path=(ROOT / report_path_arg).resolve(),
        embedding_index_dir=(ROOT / args.embedding_index_dir).resolve(),
        reranker_model_path=(ROOT / args.reranker_model_path).resolve(),
        human_labels_path=(ROOT / args.human_labels_path).resolve(),
        limit=args.limit,
    )
    if not report.get("ok", True) and "message" in report:
        print(report["message"])
        return exit_code
    print("RAG generation eval")
    print(f"Judge: {report['judge_version']}")
    print(f"Examples: {report['example_count']}")
    print(f"Answer relevancy: {report['answer_relevancy_avg']:.4f}")
    print(f"Faithfulness: {report['faithfulness_avg']:.4f}")
    print(f"Citation coverage: {report['citation_coverage']:.4f}")
    print(f"Groundedness pass rate: {report['groundedness_pass_rate']:.4f}")
    print(f"AI-assisted labels: {report['ai_assisted_labeled_count']} ({', '.join(report['human_label_review_status'])})")
    print(f"Human spot-checked labels: {report['human_labeled_count']}")
    print(f"Judge/human agreement: {report['judge_human_agreement']:.4f}")
    print(f"Threshold gate: {report['threshold_gate']}")
    print(f"Report: {report_path_arg}")
    from evals._minio_upload import try_upload_report  # noqa: PLC0415
    try_upload_report((ROOT / report_path_arg).resolve())
    return exit_code


def run_claude_eval(args: argparse.Namespace, *, report_path_arg: str) -> int:
    golden_path = (ROOT / args.golden_path).resolve()
    corpus_path = (ROOT / args.corpus_path).resolve()
    thresholds_path = (ROOT / args.thresholds_path).resolve()
    human_labels_path = (ROOT / args.human_labels_path).resolve()
    report_path = (ROOT / report_path_arg).resolve()

    corpus_rows = load_corpus_rows(corpus_path)
    golden_rows = load_jsonl(golden_path)
    if args.limit is not None:
        golden_rows = golden_rows[: args.limit]
    validation = validate_rag_golden(golden_rows=golden_rows, corpus_rows=corpus_rows, require_final=(args.limit is None))
    if not validation["ok"]:
        print("RAG golden set failed validation.")
        return 1

    details: list[dict[str, Any]] = []
    skipped = 0
    failed = 0
    for row in golden_rows:
        result = _call_chat(
            api_base_url=args.api_base_url,
            question=str(row["question"]),
            timeout=args.timeout,
        )
        if not result["ok"]:
            failed += 1
            if args.require_claude_success:
                break
            continue
        body = result["body"]
        citations = _extract_citations(body)
        answer = str(body.get("message") or body.get("tool_result", {}).get("answer") or "").strip()
        if not answer:
            skipped += 1
            continue
        score = judge_answer(
            question=str(row["question"]),
            ideal_answer=str(row["ideal_answer"]),
            answer=answer,
            citations=citations,
            ground_truth_chunk_ids=[str(item) for item in row["ground_truth_chunk_ids"]],
        )
        details.append(
            {
                "golden_id": row["golden_id"],
                "question": row["question"],
                "ideal_answer": row["ideal_answer"],
                "generated_answer": answer,
                "answer": answer,
                "citations": citations,
                "citation_chunk_ids": [str(item.get("chunk_id") or "") for item in citations],
                "retriever": body.get("tool_result", {}).get("retriever"),
                "selected_tool": body.get("selected_tool"),
                "mode": body.get("mode"),
                **score,
            }
        )

    thresholds = load_generation_thresholds(thresholds_path)
    human_labels = load_human_labels(human_labels_path)
    agreement = compare_human_labels(details, human_labels)
    if not details:
        report = {
            "judge_version": "frozen-rag-judge-v1",
            "mode": "claude",
            "example_count": 0,
            "threshold_gate": "SKIPPED",
            "passed": False,
            "successful_claude_calls": 0,
            "skipped_or_empty": skipped,
            "failed_calls": failed,
            "estimated_cost": "not measured",
            "details": [],
            "unavailable": True,
        }
    else:
        report = build_generation_report(
            mode="claude",
            details=details,
            thresholds=thresholds,
            agreement=agreement,
            extra={
                "successful_claude_calls": len(details),
                "skipped_or_empty": skipped,
                "failed_calls": failed,
                "estimated_cost": "not measured",
            },
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("RAG generation eval")
    print(f"Judge: {report['judge_version']}")
    print(f"Mode: claude")
    print(f"Examples: {report.get('example_count', 0)}")
    if report.get("details"):
        print(f"Answer relevancy: {report['answer_relevancy_avg']:.4f}")
        print(f"Faithfulness: {report['faithfulness_avg']:.4f}")
        print(f"Citation coverage: {report['citation_coverage']:.4f}")
        print(f"Groundedness pass rate: {report['groundedness_pass_rate']:.4f}")
    print(f"Successful Claude calls: {report.get('successful_claude_calls', 0)}")
    print(f"Skipped/empty: {report.get('skipped_or_empty', 0)}")
    print(f"Failed calls: {report.get('failed_calls', 0)}")
    print(f"Estimated cost: {report.get('estimated_cost', 'not measured')}")
    print(f"Threshold gate: {report['threshold_gate']}")
    print(f"Report: {report_path_arg}")

    if args.require_claude_success and (failed or skipped or not details or report.get("threshold_gate") != "PASS"):
        return 1
    if not details:
        return 0
    return 0 if report.get("threshold_gate") == "PASS" else 1


def _call_chat(*, api_base_url: str, question: str, timeout: float) -> dict[str, Any]:
    payload = json.dumps({"use_llm": True, "message": question}).encode("utf-8")
    request = Request(
        f"{api_base_url.rstrip('/')}/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "body": json.loads(body)}
    except HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": f"http_{exc.code}"}
    except URLError:
        return {"ok": False, "status": 0, "error": "unavailable"}


def _extract_citations(body: dict[str, Any]) -> list[dict[str, Any]]:
    tool_result = body.get("tool_result")
    if not isinstance(tool_result, dict):
        return []
    citations = tool_result.get("citations")
    if not isinstance(citations, list):
        return []
    return [item for item in citations if isinstance(item, dict)]


if __name__ == "__main__":
    raise SystemExit(main())
