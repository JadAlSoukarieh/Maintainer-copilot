from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from maintcopilot_api.services.rag.corpus import (
    build_doc_corpus_rows,
    build_issue_comment_corpus_rows,
    build_issue_corpus_rows,
    discover_doc_paths,
    load_jsonl_records,
    write_jsonl_records,
)
from maintcopilot_api.services.rag.retrieval import SparseRetriever


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Week 7 RAG corpus foundation.")
    parser.add_argument(
        "--issues-path",
        default="data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl",
        help="Raw issues path used for provenance in the manifest.",
    )
    parser.add_argument("--val-path", default="data/processed/val.jsonl")
    parser.add_argument("--test-path", default="data/processed/test.jsonl")
    parser.add_argument("--excluded-path", default="data/processed/excluded_issues.jsonl")
    parser.add_argument("--issue-comments-path", default="data/rag/raw/issue_comments_sample.jsonl")
    parser.add_argument("--docs-dir", default="data/rag/raw/node_docs")
    parser.add_argument("--out", default="data/rag/processed/rag_corpus.jsonl")
    parser.add_argument("--manifest-path", default="artifacts/rag/corpus_manifest.json")
    parser.add_argument("--report-path", default="artifacts/rag/retrieval_baseline_report.json")
    parser.add_argument("--max-chars", type=int, default=1400)
    parser.add_argument("--overlap-chars", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--smoke-query", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    val_records = load_jsonl_records(ROOT / args.val_path)
    test_records = load_jsonl_records(ROOT / args.test_path)
    excluded_records = load_jsonl_records(ROOT / args.excluded_path)
    issue_comment_records = load_jsonl_records(ROOT / args.issue_comments_path)
    docs_dir = ROOT / args.docs_dir
    doc_paths = discover_doc_paths(docs_dir)

    issue_rows = []
    issue_rows.extend(
        build_issue_corpus_rows(
            val_records,
            source_split="val",
            max_chars=args.max_chars,
            overlap_chars=args.overlap_chars,
        )
    )
    issue_rows.extend(
        build_issue_corpus_rows(
            test_records,
            source_split="test",
            max_chars=args.max_chars,
            overlap_chars=args.overlap_chars,
        )
    )
    issue_rows.extend(
        build_issue_corpus_rows(
            excluded_records,
            source_split="excluded",
            max_chars=args.max_chars,
            overlap_chars=args.overlap_chars,
        )
    )
    issue_comment_rows = build_issue_comment_corpus_rows(
        issue_comment_records,
        source_split="issue_comments",
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )

    doc_rows = build_doc_corpus_rows(
        docs_dir,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )

    rows = issue_rows + issue_comment_rows + doc_rows
    output_path = ROOT / args.out
    write_jsonl_records(output_path, rows)

    manifest = build_manifest(
        args,
        rows,
        len(val_records),
        len(test_records),
        len(excluded_records),
        len(issue_rows),
        len(issue_comment_rows),
        len(doc_rows),
        [path.relative_to(docs_dir).as_posix() for path in doc_paths],
    )
    write_json(ROOT / args.manifest_path, manifest)

    report = build_retrieval_report(rows, args.smoke_query, top_k=args.top_k)
    write_json(ROOT / args.report_path, report)

    print(f"Built RAG corpus: {len(rows)} chunks")
    print(f"- resolved_issue chunks: {len(issue_rows)}")
    print(f"- issue_comment chunks: {len(issue_comment_rows)}")
    print(f"- doc chunks: {len(doc_rows)}")
    print(f"Corpus written to: {output_path}")
    if args.smoke_query:
        print(f"Smoke query: {args.smoke_query}")
        for rank, item in enumerate(report["results"], start=1):
            print(f"{rank}. {item['chunk_id']} score={item['score']:.4f} title={item['title']}")
    return 0


def build_manifest(
    args: argparse.Namespace,
    rows: list[dict],
    val_count: int,
    test_count: int,
    excluded_count: int,
    issue_chunk_count: int,
    issue_comment_chunk_count: int,
    doc_chunk_count: int,
    doc_source_paths: list[str],
) -> dict:
    by_source_type = Counter(row["source_type"] for row in rows)
    by_source_split = Counter(row["metadata"]["source_split"] for row in rows)
    return {
        "built_at_utc": datetime.now(UTC).isoformat(),
        "repo": "nodejs/node",
        "sources": {
            "raw_issues_path": args.issues_path,
            "val_path": args.val_path,
            "test_path": args.test_path,
            "excluded_path": args.excluded_path,
            "issue_comments_path": args.issue_comments_path,
            "docs_dir": args.docs_dir,
        },
        "chunking": {
            "strategy": "section-aware markdown chunking for docs; structured issue records for resolved issues",
            "max_chars": args.max_chars,
            "overlap_chars": args.overlap_chars,
        },
        "limitations": [
            "Resolved issue corpus currently uses issue title/body only until comments are fetched.",
            "Dense embeddings, hybrid retrieval, reranking, and query rewriting are not implemented yet.",
        ],
        "counts": {
            "total_chunks": len(rows),
            "by_source_type": dict(by_source_type),
            "by_source_split": dict(by_source_split),
            "issue_chunks": issue_chunk_count,
            "issue_comment_chunks": issue_comment_chunk_count,
            "doc_chunks": doc_chunk_count,
            "input_issue_records": {
                "val": val_count,
                "test": test_count,
                "excluded": excluded_count,
            },
            "doc_source_files": len(doc_source_paths),
        },
        "doc_source_paths": doc_source_paths,
    }


def build_retrieval_report(rows: list[dict], query: str, top_k: int) -> dict:
    report = {
        "built_at_utc": datetime.now(UTC).isoformat(),
        "baseline": "sparse_tfidf",
        "smoke_query": query,
        "top_k": top_k,
        "result_count": 0,
        "results": [],
        "top_k_source_type_hits": {
            "doc": 0,
            "resolved_issue": 0,
        },
        "notes": [
            "Baseline uses local sparse TF-IDF retrieval only.",
            "Dense embeddings, hybrid retrieval, reranking, and generation eval are still missing.",
        ],
    }
    if not query or not rows:
        return report

    retriever = SparseRetriever(rows)
    results = retriever.query(query, top_k=top_k)
    report["results"] = [
        {
            "chunk_id": item["chunk_id"],
            "score": round(item["score"], 6),
            "source_type": item["source_type"],
            "title": item["title"],
            "url": item["url"],
            "metadata": item["metadata"],
            "text_preview": item["text"][:240],
        }
        for item in results
    ]
    report["result_count"] = len(results)
    report["top_k_source_type_hits"] = {
        "doc": sum(1 for item in results if item["source_type"] == "doc"),
        "resolved_issue": sum(1 for item in results if item["source_type"] == "resolved_issue"),
    }
    return report


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
