from __future__ import annotations

import json
import re
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
QUESTION_MIN_LENGTH = 16
ANSWER_MAX_LENGTH = 280
FINAL_REVIEW_STATUSES = {"approved", "ai_assisted_approved"}
HTML_TAG_RE = re.compile(r"<[^>]+>")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"\[[^\]]+\]:\s+\S+")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
WHITESPACE_RE = re.compile(r"\s+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    errors_by_id: dict[str, list[str]] = {}
    corpus_chunk_ids = {row["chunk_id"] for row in corpus_rows}
    source_distribution: Counter[str] = Counter()
    needing_review = 0
    approved = 0

    if not golden_rows:
        errors.append("Golden file contains no rows.")

    if require_final and len(golden_rows) != 25:
        errors.append(f"Final golden set must contain exactly 25 rows, found {len(golden_rows)}.")

    for index, row in enumerate(golden_rows, start=1):
        row_id = row.get("golden_id", f"row-{index}")
        row_errors: list[str] = []
        question = str(row.get("question", "")).strip()
        ideal_answer = str(row.get("ideal_answer", "")).strip()
        chunk_ids = row.get("ground_truth_chunk_ids")
        source_type = str(row.get("source_type", "unknown"))
        review_status = str(row.get("human_review_status", "")).strip().lower()

        if not str(row.get("golden_id", "")).strip():
            row_errors.append("golden_id is required.")
        if not question:
            row_errors.append("question is required.")
        if not ideal_answer:
            row_errors.append("ideal_answer is required.")
        if not source_type:
            row_errors.append("source_type is required.")
        if not isinstance(chunk_ids, list) or not chunk_ids:
            row_errors.append("ground_truth_chunk_ids must be a non-empty list.")
            chunk_ids = []
        for chunk_id in chunk_ids:
            if chunk_id not in corpus_chunk_ids:
                row_errors.append(f"unknown ground_truth_chunk_id {chunk_id}.")
        if row.get("needs_human_review", False):
            needing_review += 1
        if review_status in FINAL_REVIEW_STATUSES:
            approved += 1
        if require_final and row.get("needs_human_review", False):
            row_errors.append("final golden rows must set needs_human_review=false.")
        if require_final and row.get("human_review_status") is not None and review_status not in FINAL_REVIEW_STATUSES:
            row_errors.append("human_review_status must be 'approved' or 'ai_assisted_approved' in final mode.")
        if require_final and len(question) < QUESTION_MIN_LENGTH:
            row_errors.append("question is too short for final mode.")
        if require_final and _looks_like_broken_answer(ideal_answer):
            row_errors.append("ideal_answer looks like broken markdown or fragmentary text.")
        source_distribution[source_type] += 1
        if row_errors:
            errors.extend(f"{row_id}: {message}" for message in row_errors)
            errors_by_id[row_id] = row_errors

    return {
        "ok": not errors,
        "errors": errors,
        "errors_by_id": errors_by_id,
        "count": len(golden_rows),
        "source_distribution": dict(source_distribution),
        "needs_review_count": needing_review,
        "approved_count": approved,
    }


def build_candidate_question(row: dict[str, Any]) -> str:
    if row["source_type"] == "doc":
        section = str(row["metadata"].get("section") or row["title"])
        section_topic = section.split(" > ")[-1].strip()
        title = row["title"]
        if any(keyword in section_topic.lower() for keyword in ("debug", "diagnostic", "inspect", "memory")):
            return f"Where do the {title} docs explain {section_topic.lower()}?"
        if any(keyword in section_topic.lower() for keyword in ("request", "response", "tls", "dns", "stream", "error")):
            return f"Which Node.js {title} docs cover {section_topic}?"
        return f"Where do the Node.js docs explain {section_topic} in {title}?"
    return f"What resolved Node.js issue discusses {row['title']}?"


def build_candidate_answer(row: dict[str, Any]) -> str:
    content = _extract_body_text(row["text"])
    snippet = _first_sentences(content, limit=ANSWER_MAX_LENGTH)
    if row["source_type"] == "doc":
        return snippet or f"The {row['title']} docs cover {row['metadata'].get('section', row['title'])}."
    return snippet or f"A resolved issue titled {row['title']} discusses that topic."


def create_rag_golden_draft(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    draft_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        draft = dict(row)
        draft["needs_human_review"] = True
        draft["human_review_status"] = "pending"
        draft_rows.append(draft)
    return draft_rows


def build_rag_golden_review_markdown(
    *,
    candidate_rows: list[dict[str, Any]],
    corpus_rows: list[dict[str, Any]],
    max_chunk_chars: int = 1500,
) -> str:
    corpus_by_id = {row["chunk_id"]: row for row in corpus_rows}
    parts = ["# RAG Golden Candidate Review", ""]
    for row in candidate_rows:
        parts.extend(
            [
                f"## {row['golden_id']}",
                "",
                f"- Source type: `{row['source_type']}`",
                f"- Question: {row['question']}",
                f"- Ideal answer: {row['ideal_answer']}",
                f"- Ground truth chunk ids: `{', '.join(row['ground_truth_chunk_ids'])}`",
                f"- Source titles: {', '.join(row.get('source_titles', []))}",
                "",
                "### Referenced chunks",
                "",
            ]
        )
        for chunk_id in row["ground_truth_chunk_ids"]:
            chunk = corpus_by_id.get(chunk_id)
            chunk_text = "(missing chunk)"
            if chunk is not None:
                chunk_text = chunk["text"][:max_chunk_chars]
            parts.extend(
                [
                    f"#### {chunk_id}",
                    "",
                    "```text",
                    chunk_text,
                    "```",
                    "",
                ]
            )
        parts.extend(
            [
                "### Review checklist",
                "",
                "- [ ] Is the question a realistic maintainer/user question?",
                "- [ ] Is the ideal answer grounded in the referenced chunk?",
                "- [ ] Is the chunk ID correct?",
                "- [ ] Does the answer avoid broken raw markdown?",
                "- [ ] Should this row be kept, rewritten, or replaced?",
                "",
            ]
        )
    return "\n".join(parts).rstrip() + "\n"


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
    negative_score = 0 if not _looks_like_broken_answer(content[:ANSWER_MAX_LENGTH]) else -1
    return (quality_score, useful_length, keyword_score + section_score, negative_score, length_score)


def _extract_body_text(text: str) -> str:
    parts = text.split("\n\n", 1)
    if len(parts) == 2:
        body = parts[1]
    else:
        body = text
    cleaned = MARKDOWN_LINK_RE.sub(r"\1", body)
    cleaned = INLINE_CODE_RE.sub(r"\1", cleaned)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = REFERENCE_LINK_RE.sub(" ", cleaned)
    body_lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("Document:", "Section path:", "|", "<tr", "<td", "</tr", "</td", "<table", "</table")):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        if "]: " in stripped:
            continue
        body_lines.append(stripped)
    return WHITESPACE_RE.sub(" ", " ".join(body_lines)).strip()


def _first_sentences(text: str, *, limit: int) -> str:
    if not text:
        return ""
    sentences = [segment.strip(" -") for segment in SENTENCE_RE.split(text) if _is_candidate_friendly(segment)]
    answer = " ".join(sentences[:2]).strip()
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


def _looks_like_broken_answer(text: str) -> bool:
    stripped = WHITESPACE_RE.sub(" ", text).strip()
    if not stripped:
        return True
    if len(stripped) < 12:
        return True
    if stripped.startswith(("<tr", "<td", "|", "```")):
        return True
    alpha_count = sum(1 for char in stripped if char.isalpha())
    if alpha_count < 8:
        return True
    if REFERENCE_LINK_RE.search(stripped):
        return True
    if stripped.count("]:") >= 1:
        return True
    punctuation = sum(1 for char in stripped if not char.isalnum() and not char.isspace())
    if punctuation > alpha_count:
        return True
    return False
