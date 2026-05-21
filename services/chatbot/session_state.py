from __future__ import annotations

import os
from typing import Any

import streamlit as st


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


DEFAULTS: dict[str, Any] = {
    "api_base_url": "http://api:8000",
    "token": None,
    "user": None,
    "demo_mode": False,
    "conversation_id": None,
    "messages": [],
    "latest_response": None,
    "last_error": None,
    "use_llm": _env_flag("API_CHAT_LLM_ENABLED", True),
    "issue_title": "",
    "issue_body": "",
    "issue_url": "",
    "chat_input": "",
    "memory_search": "",
    "widget_form_widget_id": "demo-widget",
    "widget_form_greeting": "Ask Maintainer's Copilot about this project.",
    "widget_form_primary": "#1f6feb",
    "widget_form_position": "bottom-right",
    "widget_form_origins": "http://localhost:8080\nhttp://localhost:5173",
    "widget_form_tools": [
        "classify_issue",
        "extract_entities",
        "summarize_thread",
        "rag_answer",
        "write_memory",
    ],
    "widget_form_active": True,
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)


def is_authenticated() -> bool:
    return bool(st.session_state.get("token") or st.session_state.get("demo_mode"))


def login_success(*, token: str | None, user: dict[str, Any] | None, demo_mode: bool) -> None:
    st.session_state.token = token
    st.session_state.user = user
    st.session_state.demo_mode = demo_mode
    st.session_state.last_error = None


def logout() -> None:
    preserved_api_base_url = st.session_state.get("api_base_url", DEFAULTS["api_base_url"])
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()
    st.session_state.api_base_url = preserved_api_base_url


def start_new_conversation() -> None:
    st.session_state.conversation_id = None
    st.session_state.messages = []
    st.session_state.latest_response = None
    st.session_state.last_error = None


def add_message(role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
    message = {"role": role, "content": content}
    if metadata:
        message.update(metadata)
    st.session_state.messages.append(message)
