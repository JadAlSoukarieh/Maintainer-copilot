from __future__ import annotations

import html
from typing import Any

import streamlit as st

from api_client import build_widget_snippet


def badge_html(label: str, tone: str = "muted") -> str:
    safe_label = html.escape(label)
    tone_class = {
        "success": "mc-badge-success",
        "warning": "mc-badge-warning",
        "danger": "mc-badge-danger",
        "muted": "mc-badge-muted",
        "info": "mc-badge-info",
    }.get(tone, "mc-badge-muted")
    return f'<span class="mc-badge {tone_class}">{safe_label}</span>'


def badge(label: str, tone: str = "muted") -> None:
    st.markdown(badge_html(label, tone), unsafe_allow_html=True)


def card(title: str, body: str, *, caption: str = "") -> None:
    caption_html = f'<div class="mc-card-caption">{html.escape(caption)}</div>' if caption else ""
    st.markdown(
        f"""
        <div class="mc-card">
          <div class="mc-section-title">{html.escape(title)}</div>
          <div class="mc-card-copy">{html.escape(body)}</div>
          {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_intro(text: str) -> None:
    st.markdown(f'<div class="mc-tab-intro">{html.escape(text)}</div>', unsafe_allow_html=True)


def render_section_intro(title: str, description: str | None = None, eyebrow: str | None = None) -> None:
    eyebrow_html = f'<div class="mc-eyebrow">{html.escape(eyebrow)}</div>' if eyebrow else ""
    description_html = f'<p class="mc-section-description">{html.escape(description)}</p>' if description else ""
    st.markdown(
        f'<div class="mc-section-intro">{eyebrow_html}<div class="mc-tab-intro">{html.escape(title)}</div>{description_html}</div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, caption: str = "", *, tone: str = "neutral") -> None:
    rendered = "n/a" if value is None else (f"{value:.4f}" if isinstance(value, float) else str(value))
    tone_class = {
        "neutral": "",
        "accent": " mc-metric-accent",
        "success": " mc-metric-success",
        "warning": " mc-metric-warning",
        "danger": " mc-metric-danger",
    }.get(tone, "")
    st.markdown(
        f"""
        <div class="mc-card mc-metric-card{tone_class}">
          <div class="mc-metric-label">{html.escape(label)}</div>
          <div class="mc-metric-value">{html.escape(rendered)}</div>
          <div class="mc-metric-caption">{html.escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="mc-hero mc-shell">
          <div class="mc-shell-title">{html.escape(title)}</div>
          <div class="mc-shell-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_console_banner(title: str, subtitle: str, eyebrow: str = "Internal Admin Console") -> None:
    st.markdown(
        f"""
        <div class="mc-banner">
          <div class="mc-banner-eyebrow">{html.escape(eyebrow)}</div>
          <div class="mc-banner-title">{html.escape(title)}</div>
          <div class="mc-banner-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_eval_progress(label: str, value: float | None, *, tone: str = "default") -> None:
    if value is None:
        display = "n/a"
        pct = 0.0
    else:
        display = f"{value:.4f}"
        pct = min(max(float(value), 0.0), 1.0) * 100

    fill_class = {
        "success": "mc-eval-fill mc-eval-fill-success",
        "warning": "mc-eval-fill mc-eval-fill-warning",
    }.get(tone, "mc-eval-fill")

    st.markdown(
        f"""
        <div class="mc-eval-row">
          <div class="mc-eval-header">
            <span class="mc-eval-label">{html.escape(label)}</span>
            <span class="mc-eval-value">{html.escape(display)}</span>
          </div>
          <div class="mc-eval-track">
            <div class="{fill_class}" style="width:{pct:.1f}%"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_row(name: str, port: str, *, online: bool | None = None) -> None:
    if online is True:
        dot = "mc-health-dot-green"
    elif online is False:
        dot = "mc-health-dot-red"
    else:
        dot = "mc-health-dot-grey"
    st.markdown(
        f"""
        <div class="mc-health-row">
          <div class="mc-health-dot {dot}"></div>
          <span class="mc-health-name">{html.escape(name)}</span>
          <span class="mc-health-port">:{port}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_widget_iframe(widget_id: str = "demo-widget", api_base_url: str = "http://localhost:8000") -> None:
    import streamlit.components.v1 as components
    src = f"http://localhost:5173?widget_id={widget_id}&api_base_url={api_base_url}&auto_open=true"
    components.iframe(src, height=580, scrolling=False)


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="mc-empty-state">
          <div class="mc-empty-title">{html.escape(title)}</div>
          <div class="mc-empty-copy">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feature_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="mc-card mc-feature-card">
          <div class="mc-feature-title">{html.escape(title)}</div>
          <div class="mc-card-copy">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_message(message: dict[str, Any]) -> None:
    role = message.get("role", "assistant")
    label = "Maintainer" if role == "user" else "Assistant"
    role_class = "mc-msg-user" if role == "user" else "mc-msg-asst"

    with st.container(border=True):
        st.markdown(
            f'<div class="mc-message-meta {role_class}">{html.escape(label)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(str(message.get("content") or ""))
        if role == "assistant":
            tool = message.get("selected_tool")
            mode = message.get("mode")
            metadata = []
            if tool:
                metadata.append(badge_html(f"Tool: {tool}", "info"))
            if mode:
                metadata.append(badge_html(f"Mode: {_friendly_mode(mode)}", "muted"))
            if metadata:
                st.markdown(f'<div class="mc-message-badges">{"".join(metadata)}</div>', unsafe_allow_html=True)

            citations = dedupe_citations(message.get("citations") or [])
            if citations:
                with st.expander("Sources", expanded=False):
                    for citation in citations[:5]:
                        render_citation(citation)

            request_id = message.get("request_id")
            trace_id = message.get("trace_id")
            fallback_reason = message.get("fallback_reason")
            diagnostics = {
                k: v
                for k, v in {
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "fallback_reason": fallback_reason,
                }.items()
                if v
            }
            if diagnostics:
                with st.expander("Technical details", expanded=False):
                    for key, value in diagnostics.items():
                        st.caption(f"{key}: {value}")


def render_citation(citation: dict[str, Any]) -> None:
    formatted = format_citation(citation)
    link_html = ""
    if formatted["url"]:
        link_html = (
            f'<div class="mc-source-link"><a href="{html.escape(formatted["url"])}" target="_blank">'
            "Open source</a></div>"
        )
    st.markdown(
        f"""
        <div class="mc-source-card">
          <div class="mc-source-top">
            <div class="mc-source-title">{html.escape(formatted["title"])}</div>
            <div>{badge_html(formatted["source_type"], "muted")}</div>
          </div>
          <div class="mc-source-meta"><code>{html.escape(formatted["chunk_id"])}</code></div>
          <div class="mc-source-excerpt">{html.escape(formatted["excerpt"])}</div>
          {link_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_widget_snippet(api_base_url: str, widget_id: str, widget_url: str) -> None:
    snippet = build_widget_snippet(api_base_url=api_base_url, widget_id=widget_id, widget_url=widget_url)
    with st.container(border=True):
        st.markdown('<div class="mc-section-title">Embed snippet</div>', unsafe_allow_html=True)
        st.code(snippet, language="html")
        st.text_area("Copy snippet", value=snippet, height=150, label_visibility="collapsed")


def render_memory_notice() -> None:
    st.markdown(
        """
        <div class="mc-card">
          <div class="mc-section-title">Memory policy</div>
          <div class="mc-card-copy">
            Memory is explicit. The assistant only writes long-term memory when the user asks it to
            remember, save, or note something.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_key_value_grid(items: list[tuple[str, str]]) -> None:
    rows_html = "".join(
        f'<div class="mc-kv-row"><span class="mc-kv-label">{html.escape(label)}</span>'
        f'<span class="mc-kv-value">{html.escape(value)}</span></div>'
        for label, value in items
    )
    st.markdown(f'<div class="mc-card">{rows_html}</div>', unsafe_allow_html=True)


def render_chip_group(title: str, values: list[str]) -> None:
    chip_html = "".join(f'<span class="mc-chip">{html.escape(value)}</span>' for value in values)
    st.markdown(
        f"""
        <div class="mc-card">
          <div class="mc-section-title">{html.escape(title)}</div>
          <div class="mc-chip-row">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_command_card(title: str, command: str) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="mc-section-title">{html.escape(title)}</div>', unsafe_allow_html=True)
        st.code(command, language="bash")


def format_citation(citation: dict[str, Any]) -> dict[str, str]:
    excerpt = " ".join(str(citation.get("text_excerpt") or "").split())[:300]
    return {
        "title": str(citation.get("title") or citation.get("chunk_id") or "Untitled source"),
        "source_type": _friendly_source(citation.get("source_type")),
        "chunk_id": str(citation.get("chunk_id") or ""),
        "excerpt": excerpt,
        "url": str(citation.get("url") or ""),
    }


def format_report_metric(value: Any, *, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def dedupe_citations(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for citation in citations:
        key = (
            str(citation.get("chunk_id") or "").strip().lower(),
            str(citation.get("title") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(citation)
    return output


def group_entities(entities: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for entity in entities:
        entity_type = str(entity.get("type") or "unknown")
        entity_text = str(entity.get("text") or "").strip()
        if not entity_text:
            continue
        grouped.setdefault(entity_type, [])
        if entity_text not in grouped[entity_type]:
            grouped[entity_type].append(entity_text)
    return grouped


def _friendly_mode(mode: str) -> str:
    return {
        "deterministic_fallback": "Deterministic fallback",
        "llm_tool_calling": "Claude tool-calling",
    }.get(mode, mode)


def _friendly_source(source_type: str | None) -> str:
    return {"doc": "Docs", "resolved_issue": "Resolved issue"}.get(str(source_type), "Source")
