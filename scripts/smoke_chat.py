#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Maintainer's Copilot API smoke checks.")
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--mode", choices=["fallback", "claude"], default="fallback")
    parser.add_argument("--widget-config", action="store_true")
    parser.add_argument("--chat-rag", action="store_true")
    parser.add_argument("--chat-classify", action="store_true")
    return parser.parse_args()


def build_chat_payload(check: str, *, use_llm: bool = False) -> dict[str, Any]:
    if check == "rag":
        return {
            "use_llm": use_llm,
            "message": "How do I debug a memory leak in https request?",
        }
    if check == "classify":
        return {
            "use_llm": use_llm,
            "message": "Classify this issue",
            "context": {
                "issue_title": "Memory leak in https.request",
                "issue_body": "Repeated requests increase memory usage until the process crashes.",
            },
        }
    raise ValueError(f"Unsupported chat smoke check: {check}")


def summarize_chat_response(payload: dict[str, Any]) -> str:
    message = str(payload.get("message") or "")
    return (
        f"selected_tool={payload.get('selected_tool')} "
        f"mode={payload.get('mode')} "
        f"conversation_id={payload.get('conversation_id')} "
        f"message={message[:300]}"
    )


def main() -> int:
    args = parse_args()
    selected = args.widget_config or args.chat_rag or args.chat_classify
    run_widget_config = args.widget_config or not selected
    run_chat_rag = args.chat_rag or not selected
    run_chat_classify = args.chat_classify or not selected
    use_llm = args.mode == "claude"
    base_url = args.api_base_url.rstrip("/")

    try:
        if run_widget_config:
            config = get_json(f"{base_url}/widgets/demo-widget/config")
            print(f"widget_config public_widget_id={config.get('public_widget_id')} greeting={str(config.get('greeting', ''))[:120]}")
        if run_chat_rag:
            response = post_json(f"{base_url}/chat", build_chat_payload("rag", use_llm=use_llm))
            print(f"chat_rag {summarize_chat_response(response)}")
        if run_chat_classify:
            response = post_json(f"{base_url}/chat", build_chat_payload("classify", use_llm=use_llm))
            print(f"chat_classify {summarize_chat_response(response)}")
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"smoke check failed: {exc}", file=sys.stderr)
        return 1
    return 0


def get_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
