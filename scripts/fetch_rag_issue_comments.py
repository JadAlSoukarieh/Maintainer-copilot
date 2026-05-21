#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services/api"))

from maintcopilot_api.services.rag.golden import load_jsonl  # noqa: E402


GITHUB_API = "https://api.github.com"
ISSUE_CHUNK_RE = re.compile(r"^issue-(?P<number>\d+)-")
MAINTAINER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch optional sample issue comments for RAG corpus enrichment.")
    parser.add_argument("--issues-path", default="data/raw/nodejs_node_closed_issue_items_capped_raw.jsonl")
    parser.add_argument("--golden-path", default="data/rag/golden/rag_golden.jsonl")
    parser.add_argument("--out", default="data/rag/raw/issue_comments_sample.jsonl")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--only-golden", action="store_true")
    return parser.parse_args()


def load_jsonl_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl_file(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def golden_issue_numbers(golden_rows: list[dict]) -> set[int]:
    numbers: set[int] = set()
    for row in golden_rows:
        if row.get("source_type") != "resolved_issue":
            continue
        for chunk_id in row.get("ground_truth_chunk_ids", []):
            match = ISSUE_CHUNK_RE.match(str(chunk_id))
            if match:
                numbers.add(int(match.group("number")))
    return numbers


def select_issue_numbers(issue_rows: list[dict], *, limit: int, only_golden: bool, golden_numbers: set[int]) -> list[int]:
    selected: list[int] = []
    for row in issue_rows:
        number = row.get("issue_number")
        if not isinstance(number, int):
            continue
        if only_golden and number not in golden_numbers:
            continue
        selected.append(number)
        if len(selected) >= limit:
            break
    return selected


def main() -> int:
    args = parse_args()
    issue_rows = load_jsonl_file(REPO_ROOT / args.issues_path)
    golden_rows = load_jsonl(REPO_ROOT / args.golden_path) if args.only_golden else []
    issue_numbers = select_issue_numbers(
        issue_rows,
        limit=args.limit,
        only_golden=args.only_golden,
        golden_numbers=golden_issue_numbers(golden_rows),
    )
    if not issue_numbers:
        print("No issue numbers selected.")
        return 0

    token = os.getenv("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "maintainers-copilot-rag-comments"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print("Warning: GITHUB_TOKEN is not set; continuing unauthenticated.")

    rows: list[dict] = []
    with httpx.Client(timeout=10.0, headers=headers) as client:
        for issue_number in issue_numbers:
            url = f"{GITHUB_API}/repos/nodejs/node/issues/{issue_number}/comments"
            try:
                response = client.get(url)
            except Exception as exc:
                print(f"SKIPPED issue #{issue_number}: request failed ({exc})")
                continue
            if response.status_code != 200:
                print(f"SKIPPED issue #{issue_number}: GitHub returned {response.status_code}")
                continue
            for item in response.json():
                association = str(item.get("author_association") or "NONE")
                rows.append(
                    {
                        "repo": "nodejs/node",
                        "issue_number": issue_number,
                        "comment_id": item.get("id"),
                        "author_login": ((item.get("user") or {}).get("login") or ""),
                        "author_association": association,
                        "created_at": item.get("created_at"),
                        "body": item.get("body") or "",
                        "url": item.get("html_url") or "",
                        "is_possible_maintainer": association in MAINTAINER_ASSOCIATIONS,
                    }
                )

    write_jsonl_file(REPO_ROOT / args.out, rows)
    print(f"Wrote {len(rows)} comments to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
