from __future__ import annotations

import re
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`])")
WHITESPACE_RE = re.compile(r"\s+")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n?", re.DOTALL)


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def split_long_text(text: str, max_chars: int = 1400, overlap_chars: int = 200) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    if len(paragraphs) <= 1:
        return _split_dense_text(normalized, max_chars=max_chars, overlap_chars=overlap_chars)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current_parts:
                chunks.append("\n\n".join(current_parts).strip())
                current_parts = []
                current_length = 0
            chunks.extend(_split_dense_text(paragraph, max_chars=max_chars, overlap_chars=overlap_chars))
            continue

        projected = current_length + len(paragraph) + (2 if current_parts else 0)
        if current_parts and projected > max_chars:
            chunks.append("\n\n".join(current_parts).strip())
            current_parts = [paragraph]
            current_length = len(paragraph)
        else:
            current_parts.append(paragraph)
            current_length = projected

    if current_parts:
        chunks.append("\n\n".join(current_parts).strip())

    return chunks


def chunk_markdown_document(
    *,
    title: str,
    text: str,
    path: str,
    max_chars: int = 1400,
    overlap_chars: int = 200,
) -> list[dict]:
    cleaned_text = _clean_markdown_text(text)
    lines = cleaned_text.splitlines()
    heading_stack: list[str] = [title]
    current_heading = title
    current_level = 1
    current_body: list[str] = []
    sections: list[tuple[str, str]] = []

    for line in lines:
        heading_match = HEADING_RE.match(line)
        if heading_match:
            body_text = _clean_section_body("\n".join(current_body))
            if body_text:
                sections.append((current_heading, body_text))
            current_level = len(heading_match.group(1))
            heading_value = heading_match.group(2).strip()
            heading_stack = heading_stack[:current_level]
            if len(heading_stack) < current_level:
                heading_stack.extend([""] * (current_level - len(heading_stack)))
            if current_level == 1:
                heading_stack = [heading_value]
            else:
                heading_stack[current_level - 1] = heading_value
            current_heading = " > ".join(part for part in heading_stack if part)
            current_body = []
            continue
        current_body.append(line)

    final_body = _clean_section_body("\n".join(current_body))
    if final_body:
        sections.append((current_heading, final_body))
    elif not sections:
        fallback = normalize_text(cleaned_text)
        if fallback:
            sections.append((title, fallback))

    chunks: list[dict] = []
    for heading, body in sections:
        section_body = body or heading
        section_text = f"Document: {title}\nSection path: {heading}\n\n{section_body}".strip()
        for index, piece in enumerate(split_long_text(section_text, max_chars=max_chars, overlap_chars=overlap_chars), start=1):
            chunks.append(
                {
                    "title": title,
                    "text": piece,
                    "metadata": {
                        "path": path,
                        "section": heading,
                        "chunk_index": index,
                    },
                }
            )
    return chunks


def chunk_issue_record(
    record: dict,
    *,
    source_split: str,
    max_chars: int = 1400,
    overlap_chars: int = 200,
) -> list[dict]:
    title = (record.get("title") or "").strip()
    body = (record.get("body") or "").strip()
    resolution_note = (
        "Resolved issue corpus currently uses issue title/body only until comments are fetched."
    )
    structured = "\n\n".join(
        part
        for part in [
            f"Issue: {title}" if title else "",
            f"Problem:\n{body}" if body else "",
            f"Resolution note:\n{resolution_note}",
        ]
        if part
    )
    pieces = split_long_text(structured, max_chars=max_chars, overlap_chars=overlap_chars)
    return [
        {
            "title": title or f"nodejs/node issue {record.get('issue_number', 'unknown')}",
            "text": piece,
            "metadata": {
                "source_split": source_split,
                "label": record.get("label"),
                "issue_number": record.get("issue_number"),
                "created_at": record.get("created_at"),
                "closed_at": record.get("closed_at"),
                "section": "issue_record",
                "chunk_index": index,
            },
        }
        for index, piece in enumerate(pieces, start=1)
    ]


def _split_dense_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    sentences = [segment.strip() for segment in SENTENCE_SPLIT_RE.split(text) if segment.strip()]
    if len(sentences) <= 1:
        return _split_hard(text, max_chars=max_chars, overlap_chars=overlap_chars)

    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current_parts:
                chunks.append(" ".join(current_parts).strip())
                current_parts = []
                current_length = 0
            chunks.extend(_split_hard(sentence, max_chars=max_chars, overlap_chars=overlap_chars))
            continue

        projected = current_length + len(sentence) + (1 if current_parts else 0)
        if current_parts and projected > max_chars:
            chunks.append(" ".join(current_parts).strip())
            current_parts = [sentence]
            current_length = len(sentence)
        else:
            current_parts.append(sentence)
            current_length = projected

    if current_parts:
        chunks.append(" ".join(current_parts).strip())
    return chunks


def _split_hard(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    step = max(1, max_chars - overlap_chars)
    while start < len(text):
        end = min(len(text), start + max_chars)
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start += step
    return [piece for piece in pieces if piece]


def _clean_markdown_text(text: str) -> str:
    cleaned = FRONT_MATTER_RE.sub("", text.lstrip())
    cleaned = HTML_COMMENT_RE.sub("", cleaned)
    lines = [line.rstrip() for line in cleaned.splitlines()]
    return "\n".join(lines).strip()


def _clean_section_body(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    cleaned_lines = [
        line
        for line in lines
        if line
        and line not in {"---", "***"}
        and not line.startswith("<!--")
        and line.lower() not in {"stability: 0", "stability: 1", "stability: 2", "stability: 3"}
    ]
    return "\n".join(cleaned_lines).strip()
