from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from maintcopilot_api.services.rag.chunking import chunk_issue_record, chunk_markdown_document


def load_jsonl_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_jsonl_records(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def build_issue_corpus_rows(
    records: list[dict],
    *,
    source_split: str,
    max_chars: int = 1400,
    overlap_chars: int = 200,
) -> list[dict]:
    rows: list[dict] = []
    for record in records:
        issue_number = record.get("issue_number") or record.get("number") or "unknown"
        url = record.get("url") or record.get("html_url") or ""
        repo = record.get("repo") or "nodejs/node"
        for chunk in chunk_issue_record(
            record,
            source_split=source_split,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
        ):
            chunk_index = chunk["metadata"].pop("chunk_index")
            row = {
                "chunk_id": f"issue-{issue_number}-{source_split}-{chunk_index:03d}",
                "source_type": "resolved_issue",
                "source_id": str(issue_number),
                "title": chunk["title"],
                "url": url,
                "text": chunk["text"],
                "metadata": {
                    "repo": repo,
                    "source_split": source_split,
                    "label": record.get("label"),
                    "issue_number": issue_number,
                    "created_at": record.get("created_at"),
                    "closed_at": record.get("closed_at"),
                    "path": None,
                    "section": chunk["metadata"].get("section"),
                },
            }
            validate_corpus_row(row)
            rows.append(row)
    return rows


def build_doc_corpus_rows(
    docs_dir: Path,
    *,
    repo: str = "nodejs/node",
    max_chars: int = 1400,
    overlap_chars: int = 200,
) -> list[dict]:
    if not docs_dir.exists():
        return []

    rows: list[dict] = []
    for path in discover_doc_paths(docs_dir):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name
        for chunk_index, chunk in enumerate(
            chunk_markdown_document(
                title=title,
                text=text,
                path=str(path),
                max_chars=max_chars,
                overlap_chars=overlap_chars,
            ),
            start=1,
        ):
            relative_path = path.relative_to(docs_dir).as_posix()
            section = chunk["metadata"].get("section") or title
            section_slug = slugify(section)
            source_id = f"{relative_path}#{section_slug}:{chunk_index:03d}"
            row = {
                "chunk_id": f"doc-{slugify(relative_path)}-{section_slug}-{chunk_index:03d}",
                "source_type": "doc",
                "source_id": source_id,
                "title": chunk["title"],
                "url": "",
                "text": chunk["text"],
                "metadata": {
                    "repo": repo,
                    "source_split": "docs",
                    "label": None,
                    "issue_number": None,
                    "created_at": None,
                    "closed_at": None,
                    "path": relative_path,
                    "section": chunk["metadata"].get("section"),
                },
            }
            validate_corpus_row(row)
            rows.append(row)
    return rows


def validate_corpus_row(row: dict) -> None:
    required_top = ["chunk_id", "source_type", "source_id", "title", "url", "text", "metadata"]
    for key in required_top:
        if key not in row:
            raise ValueError(f"Corpus row is missing required field: {key}")
    if row["source_type"] not in {"doc", "resolved_issue"}:
        raise ValueError(f"Unsupported source_type: {row['source_type']}")

    metadata = row["metadata"]
    required_metadata = [
        "repo",
        "source_split",
        "label",
        "issue_number",
        "created_at",
        "closed_at",
        "path",
        "section",
    ]
    for key in required_metadata:
        if key not in metadata:
            raise ValueError(f"Corpus row metadata is missing required field: {key}")


def discover_doc_paths(docs_dir: Path) -> list[Path]:
    if not docs_dir.exists():
        return []
    candidates = [
        path
        for path in sorted(docs_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in {".md", ".mdx", ".txt"}
    ]
    by_relative_path = {path.relative_to(docs_dir).as_posix(): path for path in candidates}
    selected: list[Path] = []
    for path in candidates:
        relative_path = path.relative_to(docs_dir).as_posix()
        collapsed_relative_path = collapse_redundant_leading_segment(relative_path)
        if (
            collapsed_relative_path != relative_path
            and collapsed_relative_path in by_relative_path
            and _same_file_contents(path, by_relative_path[collapsed_relative_path])
        ):
            continue
        selected.append(path)
    return selected


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "root"


def collapse_redundant_leading_segment(relative_path: str) -> str:
    parts = Path(relative_path).parts
    while len(parts) >= 2 and parts[0] == parts[1]:
        parts = parts[1:]
    return Path(*parts).as_posix()


def _same_file_contents(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    return _sha256(left) == _sha256(right)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
