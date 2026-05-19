from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


DOC_TARGET = 12
ISSUE_TARGET = 13
REVIEW_NOTE = "Generated candidate. Human should verify question, answer, and chunk ids before final eval."
KEYWORDS = (
    "memory",
    "debug",
    "http",
    "https",
    "tls",
    "dns",
    "crypto",
    "stream",
    "module",
    "error",
    "request",
    "buffer",
    "fs",
    "net",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def generate_rag_golden_candidates(corpus_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_chunk_ids = {row["chunk_id"] for row in corpus_rows}
    doc_rows = [row for row in corpus_rows if row["source_type"] == "doc"]
    issue_rows = [row for row in corpus_rows if row["source_type"] == "resolved_issue"]

    selected_doc_rows = _select_rows(doc_rows, DOC_TARGET, source_type="doc")
    selected_issue_rows = _select_rows(issue_rows, ISSUE_TARGET, source_type="resolved_issue")
    selected_rows = selected_doc_rows + selected_issue_rows

    candidates: list[dict[str, Any]] = []
    for index, row in enumerate(selected_rows, start=1):
        source_type = row["source_type"]
        question = build_candidate_question(row)
        ideal_answer = build_candidate_answer(row)
        candidate = {
            "golden_id": f"rag-golden-{index:03d}",
            "question": question,
            "ideal_answer": ideal_answer,
            "ground_truth_chunk_ids": [row["chunk_id"]],
            "source_type": source_type,
            "source_titles": [row["title"]],
            "needs_human_review": True,
            "review_notes": REVIEW_NOTE,
        }
        if row["chunk_id"] not in existing_chunk_ids:
            raise ValueError(f"Candidate references unknown chunk id: {row['chunk_id']}")
        candidates.append(candidate)
    return candidates


def validate_rag_golden(
    *,
    golden_rows: list[dict[str, Any]],
    corpus_rows: list[dict[str, Any]],
    require_final: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    corpus_chunk_ids = {row["chunk_id"] for row in corpus_rows}
    source_distribution: Counter[str] = Counter()

    if not golden_rows:
        errors.append("Golden file contains no rows.")

    if require_final and len(golden_rows) != 25:
        errors.append(f"Final golden set must contain exactly 25 rows, found {len(golden_rows)}.")

    for index, row in enumerate(golden_rows, start=1):
        row_id = row.get("golden_id", f"row-{index}")
        question = str(row.get("question", "")).strip()
        ideal_answer = str(row.get("ideal_answer", "")).strip()
        chunk_ids = row.get("ground_truth_chunk_ids")
        source_type = str(row.get("source_type", "unknown"))

        if not question:
            errors.append(f"{row_id}: question is required.")
        if not ideal_answer:
            errors.append(f"{row_id}: ideal_answer is required.")
        if not isinstance(chunk_ids, list) or not chunk_ids:
            errors.append(f"{row_id}: ground_truth_chunk_ids must be a non-empty list.")
            chunk_ids = []
        for chunk_id in chunk_ids:
            if chunk_id not in corpus_chunk_ids:
                errors.append(f"{row_id}: unknown ground_truth_chunk_id {chunk_id}.")
        if require_final and row.get("needs_human_review", False):
            errors.append(f"{row_id}: final golden rows must set needs_human_review=false.")
        source_distribution[source_type] += 1

    return {
        "ok": not errors,
        "errors": errors,
        "count": len(golden_rows),
        "source_distribution": dict(source_distribution),
    }


def build_candidate_question(row: dict[str, Any]) -> str:
    if row["source_type"] == "doc":
        section = str(row["metadata"].get("section") or row["title"])
        section_topic = section.split(" > ")[-1].strip()
        title = row["title"]
        return f"What do the {title} docs say about {section_topic}?"
    return f"What resolved Node.js issue discusses {row['title']}?"


def build_candidate_answer(row: dict[str, Any]) -> str:
    content = _extract_body_text(row["text"])
    snippet = _first_sentences(content, limit=220)
    if row["source_type"] == "doc":
        return snippet or f"The {row['title']} docs cover {row['metadata'].get('section', row['title'])}."
    return snippet or f"A resolved issue titled {row['title']} discusses that topic."


def _select_rows(rows: list[dict[str, Any]], target_count: int, *, source_type: str) -> list[dict[str, Any]]:
    scored_rows = sorted(rows, key=lambda row: (_score_row(row, source_type=source_type), row["chunk_id"]), reverse=True)
    selected: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for row in scored_rows:
        signature = _row_signature(row)
        if signature in seen_signatures:
            continue
        if not build_candidate_answer(row):
            continue
        selected.append(row)
        seen_signatures.add(signature)
        if len(selected) == target_count:
            break
    if len(selected) < target_count:
        raise ValueError(f"Unable to generate {target_count} {source_type} golden candidates.")
    return list(reversed(selected))


def _row_signature(row: dict[str, Any]) -> str:
    if row["source_type"] == "doc":
        return str(row["metadata"].get("path"))
    return str(row["source_id"])


def _score_row(row: dict[str, Any], *, source_type: str) -> tuple[int, int, int]:
    content = _extract_body_text(row["text"])
    lower = content.lower()
    keyword_score = sum(1 for keyword in KEYWORDS if keyword in lower or keyword in row["title"].lower())
    length_score = min(len(content), 1200)
    section_score = 1 if source_type == "doc" and str(row["metadata"].get("section", "")).count(">") >= 1 else 0
    useful_length = 1 if len(content) >= 80 else 0
    quality_score = 1 if _is_candidate_friendly(content) else 0
    return (quality_score, useful_length, keyword_score + section_score, length_score)


def _extract_body_text(text: str) -> str:
    parts = text.split("\n\n", 1)
    if len(parts) == 2:
        body = parts[1]
    else:
        body = text
    body_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip()
        and not line.startswith("Document:")
        and not line.startswith("Section path:")
        and not line.startswith("[")
        and "]: " not in line
    ]
    return " ".join(body_lines).strip()


def _first_sentences(text: str, *, limit: int) -> str:
    if not text:
        return ""
    sentences = [segment.strip() for segment in text.replace("\n", " ").split(".") if _is_candidate_friendly(segment)]
    answer = ". ".join(sentences[:2]).strip()
    if answer and not answer.endswith("."):
        answer += "."
    return answer[:limit].strip()


def _is_candidate_friendly(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 40:
        return False
    alpha_count = sum(1 for char in stripped if char.isalpha())
    non_space_count = sum(1 for char in stripped if not char.isspace())
    if non_space_count == 0:
        return False
    if alpha_count / non_space_count < 0.45:
        return False
    if stripped.count("[") + stripped.count("]") > max(4, len(stripped) // 20):
        return False
    return True
