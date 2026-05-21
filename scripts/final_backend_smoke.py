#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ant-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)[=:]\s*[^,\s}]+"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run final backend smoke checks against a running stack.")
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument("--model-server-base-url", default="http://localhost:8001")
    parser.add_argument("--mode", choices=["fallback", "claude", "both"], default="fallback")
    parser.add_argument("--output", default="reports/final_backend_smoke_report.json")
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--allow-claude-fallback", action="store_true")
    parser.add_argument("--require-claude-success", action="store_true")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_base_url = args.api_base_url.rstrip("/")
    model_server_base_url = args.model_server_base_url.rstrip("/")
    checks: list[dict[str, Any]] = []

    checks.append(check_get("api_health", f"{api_base_url}/health", timeout=args.timeout))
    checks.append(check_get("model_server_health", f"{model_server_base_url}/health", timeout=args.timeout))
    checks.append(check_widget_config(api_base_url, timeout=args.timeout))
    checks.append(check_widget_blocked_origin(api_base_url, timeout=args.timeout))
    checks.append(check_widget_js_csp(api_base_url, timeout=args.timeout))
    checks.append(check_chat_rag(api_base_url, use_llm=False, name="deterministic_rag_chat", timeout=args.timeout))
    checks.append(check_chat_classify(api_base_url, timeout=args.timeout))
    checks.append(check_memory_write(api_base_url, timeout=args.timeout))
    checks.append(check_memory_search(api_base_url, timeout=args.timeout))
    checks.append(check_get_reports(api_base_url, timeout=args.timeout))
    checks.append(check_observability(api_base_url, timeout=args.timeout))

    should_run_claude = args.mode in {"claude", "both"} and not args.skip_claude
    if should_run_claude:
        checks.append(check_chat_rag(api_base_url, use_llm=True, name="claude_rag_chat", timeout=args.timeout))

    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "api_base_url": api_base_url,
        "model_server_base_url": model_server_base_url,
        "checks": checks,
        "summary": summarize(checks),
    }
    safe_report = redact(report)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(safe_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Final backend smoke report: {output_path}")
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{status} {check['name']}: {check.get('summary', '')}")

    fallback_failed = any(not check["passed"] and check.get("required", True) for check in checks if not check["name"].startswith("claude_"))
    claude_checks = [check for check in checks if check["name"].startswith("claude_")]
    claude_failed = any(not check["passed"] for check in claude_checks)
    claude_fell_back = any(check.get("mode") == "deterministic_fallback" for check in claude_checks)

    if fallback_failed:
        return 1
    if args.require_claude_success and (not claude_checks or claude_failed or claude_fell_back):
        return 1
    if args.mode == "claude" and claude_failed and not args.allow_claude_fallback:
        return 1
    if args.mode == "claude" and claude_fell_back and not args.allow_claude_fallback:
        return 1
    return 0


def check_get(name: str, url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json("GET", url, timeout=timeout)
    return result(
        name,
        0 < response["status"] < 400,
        status_code=response["status"],
        summary=f"status={response['status']}",
        response=response.get("json"),
        error=response.get("text") if response["status"] == 0 else None,
    )


def check_widget_config(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json(
        "GET",
        f"{api_base_url}/widgets/demo-widget/config",
        headers={"Origin": "http://localhost:8080"},
        timeout=timeout,
    )
    payload = response.get("json") if isinstance(response.get("json"), dict) else {}
    passed = response["status"] == 200 and payload.get("public_widget_id") == "demo-widget"
    return result(
        "widget_config_allowed_origin",
        passed,
        status_code=response["status"],
        summary=f"status={response['status']} widget={payload.get('public_widget_id')}",
        response=payload,
    )


def check_widget_blocked_origin(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json(
        "GET",
        f"{api_base_url}/widgets/demo-widget/config",
        headers={"Origin": "http://evil.localhost"},
        timeout=timeout,
    )
    passed = response["status"] == 403
    return result(
        "widget_config_blocked_origin",
        passed,
        status_code=response["status"],
        summary=f"status={response['status']}",
        response=response.get("json") or response.get("text"),
    )


def check_widget_js_csp(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json(
        "GET",
        f"{api_base_url}/widget.js?public_widget_id=demo-widget",
        headers={"Origin": "http://localhost:8080"},
        timeout=timeout,
        parse_json=False,
    )
    csp = _header(response["headers"], "Content-Security-Policy")
    passed = response["status"] == 200 and "frame-ancestors" in csp
    return result(
        "widget_js_csp",
        passed,
        status_code=response["status"],
        summary=f"status={response['status']} csp={'present' if csp else 'missing'}",
        csp=csp,
    )


def check_chat_rag(api_base_url: str, *, use_llm: bool, name: str, timeout: float) -> dict[str, Any]:
    payload = {"use_llm": use_llm, "message": "How do I debug a memory leak in https request?"}
    response = request_json("POST", f"{api_base_url}/chat", payload=payload, timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    citations = _citations(body)
    answer = str(body.get("message") or "")
    if use_llm:
        passed = (
            response["status"] == 200
            and body.get("selected_tool") == "rag_answer"
            and body.get("mode") in {"llm_tool_calling", "deterministic_fallback"}
            and bool(answer)
            and len(citations) > 0
        )
    else:
        passed = (
            response["status"] == 200
            and body.get("selected_tool") == "rag_answer"
            and body.get("mode") == "deterministic_fallback"
            and len(citations) > 0
            and "corpus" not in answer.lower()
        )
    return result(
        name,
        passed,
        status_code=response["status"],
        selected_tool=body.get("selected_tool"),
        mode=body.get("mode"),
        fallback_reason=body.get("fallback_reason"),
        citations_count=len(citations),
        summary=f"status={response['status']} tool={body.get('selected_tool')} mode={body.get('mode')} citations={len(citations)}",
        response=_compact_chat(body),
    )


def check_chat_classify(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    payload = {
        "use_llm": False,
        "message": "Classify this issue",
        "context": {
            "issue_title": "Memory leak in https.request",
            "issue_body": "Repeated requests increase memory usage until the process crashes.",
        },
    }
    response = request_json("POST", f"{api_base_url}/chat", payload=payload, timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    passed = response["status"] == 200 and body.get("selected_tool") == "classify_issue"
    return result(
        "deterministic_classify_chat",
        passed,
        status_code=response["status"],
        selected_tool=body.get("selected_tool"),
        mode=body.get("mode"),
        summary=f"status={response['status']} tool={body.get('selected_tool')} mode={body.get('mode')}",
        response=_compact_chat(body),
    )


def check_memory_write(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    payload = {"use_llm": False, "message": "Remember that missing JWT auth issues should be treated as bugs."}
    response = request_json("POST", f"{api_base_url}/chat", payload=payload, timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    memory = body.get("memory") if isinstance(body.get("memory"), dict) else {}
    writes = memory.get("memory_writes") if isinstance(memory.get("memory_writes"), list) else []
    passed = response["status"] == 200 and body.get("selected_tool") == "write_memory" and len(writes) >= 1
    if response["status"] == 200 and body.get("selected_tool") == "write_memory" and not writes:
        passed = "degraded" in str(body).lower() or "fallback" in str(body).lower()
    return result(
        "explicit_memory_write",
        passed,
        status_code=response["status"],
        selected_tool=body.get("selected_tool"),
        mode=body.get("mode"),
        memory_writes=len(writes),
        summary=f"status={response['status']} tool={body.get('selected_tool')} writes={len(writes)}",
        response=_compact_chat(body),
    )


def check_memory_search(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    payload = {"query": "missing JWT auth issues", "top_k": 5, "mode": "hybrid"}
    response = request_json("POST", f"{api_base_url}/memory/search", payload=payload, timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    passed = response["status"] == 200 and "items" in body
    return result(
        "memory_search",
        passed,
        status_code=response["status"],
        requested_mode=body.get("requested_mode"),
        effective_mode=body.get("effective_mode"),
        fallback_reason=body.get("fallback_reason"),
        summary=f"status={response['status']} effective_mode={body.get('effective_mode')}",
        response=_limit_items(body),
    )


def check_get_reports(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json("GET", f"{api_base_url}/reports/summary", timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    passed = (
        response["status"] == 200
        and bool(body.get("classifier"))
        and bool(body.get("rag_retrieval"))
        and bool(body.get("rag_generation"))
    )
    return result(
        "reports_summary",
        passed,
        status_code=response["status"],
        summary=f"status={response['status']} classifier={'present' if body.get('classifier') else 'missing'}",
        response=body,
    )


def check_observability(api_base_url: str, *, timeout: float) -> dict[str, Any]:
    response = request_json("GET", f"{api_base_url}/observability/recent?limit=20", timeout=timeout)
    body = response.get("json") if isinstance(response.get("json"), dict) else {}
    events = body.get("events") if isinstance(body.get("events"), list) else []
    safe_text = json.dumps(redact(body), ensure_ascii=False)
    passed = response["status"] == 200 and "sk-" not in safe_text and "ANTHROPIC_API_KEY" not in safe_text
    return result(
        "observability_recent",
        passed,
        status_code=response["status"],
        events_count=len(events),
        summary=f"status={response['status']} events={len(events)}",
        response={"events": events[:5], "count": len(events)},
    )


def request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
    parse_json: bool = True,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "json": json.loads(raw) if parse_json and raw else None,
                "text": None if parse_json else raw[:1000],
            }
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: Any = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
        return {"status": exc.code, "headers": dict(exc.headers.items()), "json": parsed, "text": raw[:1000]}
    except (URLError, TimeoutError) as exc:
        return {"status": 0, "headers": {}, "json": None, "text": str(exc)}


def result(name: str, passed: bool, **fields: Any) -> dict[str, Any]:
    return {"name": name, "passed": passed, "required": True, **redact(fields)}


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "passed": sum(1 for check in checks if check["passed"]),
        "failed": sum(1 for check in checks if not check["passed"]),
        "total": len(checks),
    }


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        safe = value
        for pattern in SECRET_PATTERNS:
            safe = pattern.sub("[REDACTED]", safe)
        return safe
    return value


def _citations(chat_response: dict[str, Any]) -> list[dict[str, Any]]:
    tool_result = chat_response.get("tool_result")
    if not isinstance(tool_result, dict):
        return []
    citations = tool_result.get("citations")
    return citations if isinstance(citations, list) else []


def _compact_chat(chat_response: dict[str, Any]) -> dict[str, Any]:
    return {
        "conversation_id": chat_response.get("conversation_id"),
        "message": str(chat_response.get("message") or "")[:500],
        "mode": chat_response.get("mode"),
        "selected_tool": chat_response.get("selected_tool"),
        "fallback_reason": chat_response.get("fallback_reason"),
        "request_id": chat_response.get("request_id"),
        "trace_id": chat_response.get("trace_id"),
        "citations_count": len(_citations(chat_response)),
    }


def _limit_items(payload: dict[str, Any]) -> dict[str, Any]:
    compact = dict(payload)
    if isinstance(compact.get("items"), list):
        compact["items"] = compact["items"][:3]
        compact["items_count_returned"] = len(payload.get("items", []))
    return compact


def _header(headers: dict[str, str], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
