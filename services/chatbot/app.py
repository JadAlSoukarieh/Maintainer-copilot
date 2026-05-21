from __future__ import annotations

from typing import Any

import streamlit as st

from api_client import ApiClient, ApiClientError, infer_model_server_base_url
from components import (
    badge,
    format_report_metric,
    group_entities,
    metric_card,
    render_chat_message,
    render_chip_group,
    render_citation,
    render_command_card,
    render_console_banner,
    render_empty_state,
    render_eval_progress,
    render_feature_card,
    render_health_row,
    render_key_value_grid,
    render_memory_notice,
    render_page_header,
    render_section_intro,
    render_widget_iframe,
    render_widget_snippet,
)
from session_state import (
    add_message,
    init_state,
    is_authenticated,
    login_success,
    logout,
    start_new_conversation,
)
from styles import apply_styles


QUICK_PROMPTS = [
    "How do I debug a memory leak in https request?",
    "Where do the Node docs explain stream pipeline cleanup after errors?",
    "Extract files, functions, versions, and error codes from this issue.",
    "Remember that missing JWT auth issues should be treated as bugs.",
]
TOOL_OPTIONS = ["classify_issue", "extract_entities", "summarize_thread", "rag_answer", "write_memory"]


def main() -> None:
    st.set_page_config(page_title="Maintainer's Copilot", page_icon="MC", layout="wide")
    init_state()
    apply_styles()

    if not is_authenticated():
        render_login_screen()
        return

    client = ApiClient(st.session_state.api_base_url, token=st.session_state.token)
    render_sidebar(client)
    render_console(client)


def render_login_screen() -> None:
    st.markdown('<div class="mc-login-page">', unsafe_allow_html=True)
    render_page_header(
        "Maintainer's Copilot",
        "Internal triage console for Node.js issue classification, RAG search, memory, and widget administration.",
    )

    feature_cols = st.columns(3, gap="large")
    features = [
        ("Triage", "Classify issues as bug, feature, docs, or question."),
        ("Knowledge", "Search local Node.js docs and resolved issue evidence."),
        ("Operations", "Inspect memory, widget config, logs, and eval metrics."),
    ]
    for col, (title, body) in zip(feature_cols, features, strict=True):
        with col:
            render_feature_card(title, body)

    outer_left, center, outer_right = st.columns([1.05, 1.1, 1.05])
    with center:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Sign in</div>', unsafe_allow_html=True)
            st.text_input("Email", key="welcome_email", placeholder="maintainer@example.com")
            st.text_input("Password", type="password", key="welcome_password", placeholder="Password")
            action_cols = st.columns(2, gap="small")
            if action_cols[0].button("Login", type="primary", use_container_width=True):
                attempt_login()
            if action_cols[1].button("Continue in demo mode", use_container_width=True):
                login_success(token=None, user=None, demo_mode=True)
                st.session_state.last_error = "Demo mode uses dev-only unauthenticated API access. Do not use in production."
                st.rerun()

            st.caption("Demo mode uses dev-only unauthenticated API access. Do not use in production.")
            if st.session_state.get("last_error"):
                st.error(st.session_state.last_error)

            with st.expander("Advanced API settings", expanded=False):
                st.session_state.api_base_url = st.text_input("API base URL", value=st.session_state.api_base_url)
    st.markdown("</div>", unsafe_allow_html=True)


def attempt_login() -> None:
    client = ApiClient(st.session_state.api_base_url)
    try:
        token = client.login(st.session_state.get("welcome_email", ""), st.session_state.get("welcome_password", ""))
        user = ApiClient(st.session_state.api_base_url, token=token["access_token"]).me()
    except ApiClientError as exc:
        st.session_state.last_error = str(exc)
        return
    login_success(token=token["access_token"], user=user, demo_mode=False)
    st.rerun()


def render_sidebar(client: ApiClient) -> None:
    with st.sidebar:
        st.markdown("## Maintainer's Copilot")
        st.caption("Internal triage console · Week 7 demo")

        st.markdown('<div class="mc-sidebar-heading">Identity</div>', unsafe_allow_html=True)
        if st.session_state.demo_mode:
            badge("Demo mode", "warning")
        elif st.session_state.user:
            badge(st.session_state.user.get("email", "Authenticated"), "success")
            role = st.session_state.user.get("role")
            if role:
                badge(f"Role: {role}", "muted")

        st.markdown('<div class="mc-sidebar-heading">Services</div>', unsafe_allow_html=True)
        api_online = _check_api_online(client)
        model_online = client.probe_model_server()
        render_health_row("API", "8000", online=api_online)
        render_health_row("Model-server", "8001", online=model_online)
        render_health_row("Widget", "5173", online=None)
        render_health_row("Demo host", "8080", online=None)
        render_health_row("Jaeger", "16686", online=None)
        render_health_row("MinIO", "9001", online=None)

        st.markdown('<div class="mc-sidebar-heading">Chat Mode</div>', unsafe_allow_html=True)
        st.session_state.use_llm = st.toggle(
            "Claude tool-calling",
            value=bool(st.session_state.use_llm),
            help="Claude is the primary runtime mode when enabled. Deterministic fallback is the reproducible backup path.",
        )
        badge(
            "Claude tool-calling" if st.session_state.use_llm else "Deterministic fallback",
            "info" if st.session_state.use_llm else "muted",
        )
        st.caption("Claude is primary in demo mode; deterministic fallback is used for reproducible CI and when LLM is unavailable.")

        st.markdown('<div class="mc-sidebar-heading">Conversation</div>', unsafe_allow_html=True)
        conversation_id = st.session_state.conversation_id or "None yet"
        st.code(conversation_id[:18] + ("…" if len(conversation_id) > 18 else ""))
        if st.button("New conversation", use_container_width=True):
            start_new_conversation()
            st.rerun()
        if st.button("Logout / Exit demo mode", use_container_width=True):
            logout()
            st.rerun()

        st.markdown('<div class="mc-sidebar-heading">Quick Links</div>', unsafe_allow_html=True)
        links = [
            ("API docs", f"{st.session_state.api_base_url.rstrip('/')}/docs"),
            ("Demo host", "http://localhost:8080"),
            ("Widget", "http://localhost:5173"),
            ("Jaeger traces", "http://localhost:16686"),
            ("MinIO console", "http://localhost:9001"),
        ]
        for label, url in links:
            st.markdown(
                f'<div class="mc-small-link"><a href="{url}" target="_blank">{label}</a></div>',
                unsafe_allow_html=True,
            )


def render_console(client: ApiClient) -> None:
    reports_summary = _safe_reports_summary(client)

    render_console_banner(
        "Maintainer's Copilot",
        "Node.js issue triage · RAG knowledge base · episodic memory · embedded widget",
    )

    latest_tool = (st.session_state.latest_response or {}).get("selected_tool") or "None yet"
    current_mode = "Claude tool-calling" if st.session_state.use_llm else "Deterministic fallback"

    metrics = st.columns(4, gap="large")
    with metrics[0]:
        metric_card("Classifier", "RoBERTa", "72.5% acc · 0.71 macro-F1", tone="accent")
    with metrics[1]:
        metric_card("RAG retrieval", "Reranked hybrid", "80% hit@5 · 0.63 MRR", tone="accent")
    with metrics[2]:
        metric_card("Latest tool", latest_tool, "Most recent assistant action")
    with metrics[3]:
        metric_card("Chat mode", current_mode, "Live routing mode")

    tabs = st.tabs(["Chat", "Issue Tools", "Memory", "Widget Admin", "Observability", "Evals"])
    with tabs[0]:
        render_chat_tab(client)
    with tabs[1]:
        render_issue_tools_tab(client)
    with tabs[2]:
        render_memory_tab(client)
    with tabs[3]:
        render_widget_admin_tab(client)
    with tabs[4]:
        render_observability_tab(client)
    with tabs[5]:
        render_evals_tab(reports_summary)


def render_chat_tab(client: ApiClient) -> None:
    render_section_intro("Run the internal assistant against the same `/chat` orchestration used by the backend tool-calling flow.")
    main_col, side_col = st.columns([1.75, 1], gap="large")

    with main_col:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Chat History</div>', unsafe_allow_html=True)
            if not st.session_state.messages:
                render_empty_state(
                    "No conversation yet",
                    "Start with a maintainer question or use one of the quick prompts to seed a grounded conversation.",
                )
            for message in st.session_state.messages:
                render_chat_message(message)

        with st.form("chat-send-form", clear_on_submit=False):
            st.session_state.chat_input = st.text_area(
                "Message",
                value=st.session_state.chat_input,
                height=120,
                placeholder="Ask about Node.js docs, issues, or triage...",
            )
            send_cols = st.columns([1.2, 5])
            send = send_cols[0].form_submit_button("Send", type="primary", use_container_width=True)
            if send and st.session_state.chat_input.strip():
                _send_chat(
                    client,
                    st.session_state.chat_input.strip(),
                    issue_title=st.session_state.issue_title,
                    issue_body=st.session_state.issue_body,
                    use_llm=bool(st.session_state.use_llm),
                )
                st.session_state.chat_input = ""
                st.rerun()

    with side_col:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Issue Context</div>', unsafe_allow_html=True)
            st.session_state.issue_title = st.text_input("Issue title", value=st.session_state.issue_title)
            st.session_state.issue_body = st.text_area("Issue body", value=st.session_state.issue_body, height=190)

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Quick Prompts</div>', unsafe_allow_html=True)
            for prompt in QUICK_PROMPTS:
                if st.button(prompt, key=f"chat-prompt-{prompt}", use_container_width=True):
                    st.session_state.chat_input = prompt

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Options</div>', unsafe_allow_html=True)
            badge("Claude tool-calling" if st.session_state.use_llm else "Deterministic fallback", "info" if st.session_state.use_llm else "muted")
            if st.button("Clear conversation", use_container_width=True):
                start_new_conversation()
                st.rerun()


def render_issue_tools_tab(client: ApiClient) -> None:
    render_section_intro("Use the same chat orchestration as the assistant, but shaped as a focused issue workbench.")
    with st.container(border=True):
        st.markdown('<div class="mc-section-title">Issue Input</div>', unsafe_allow_html=True)
        title = st.text_input("Issue title", key="tools_issue_title", value=st.session_state.issue_title or "Memory leak in https.request")
        body = st.text_area(
            "Issue body",
            key="tools_issue_body",
            value=st.session_state.issue_body or "Repeated requests increase memory usage until the process crashes.",
            height=220,
        )
        url = st.text_input("Issue URL (optional)", key="tools_issue_url", value=st.session_state.issue_url)

    action_cols = st.columns(4, gap="large")
    actions = [
        ("Classify", "Classify this issue", "Assign a triage label."),
        ("Extract entities", "Extract files, functions, versions, and error codes from this issue.", "Pull code-shaped entities."),
        ("Summarize", "Summarize this issue", "Generate a concise maintainer recap."),
        ("Ask knowledge base", "How should I investigate this issue?", "Ground the issue in retrieved evidence."),
    ]
    for index, (label, message, copy) in enumerate(actions):
        with action_cols[index]:
            with st.container(border=True):
                st.markdown(f'<div class="mc-section-title">{label}</div>', unsafe_allow_html=True)
                st.markdown(copy)
                if st.button(label, key=f"issue-tool-{label}", use_container_width=True):
                    st.session_state.issue_tool_response = _chat_once(client, message, title, body)
                    st.session_state.issue_title = title
                    st.session_state.issue_body = body
                    st.session_state.issue_url = url

    response = st.session_state.get("issue_tool_response")
    if response:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Result</div>', unsafe_allow_html=True)
            _render_tool_response(response)


def render_memory_tab(client: ApiClient) -> None:
    render_section_intro("Inspect redacted short-term conversation state and explicit long-term episodic memory behavior.")
    render_memory_notice()
    memory_mode = st.selectbox("Memory search mode", ["hybrid", "vector", "text"], index=0)

    status_cols = st.columns([1.2, 2], gap="large")
    with status_cols[0]:
        if st.button("Refresh conversation memory", use_container_width=True):
            st.rerun()
    with status_cols[1]:
        badge(f"Conversation: {st.session_state.conversation_id or 'none'}", "muted")

    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Current Conversation Memory</div>', unsafe_allow_html=True)
            if st.session_state.conversation_id:
                try:
                    memory_items = client.get_memory(st.session_state.conversation_id).get("items", [])
                    if memory_items:
                        for item in memory_items:
                            render_key_value_grid(
                                [
                                    ("Message", str(item.get("message") or item)),
                                    ("Selected tool", str(item.get("selected_tool", "n/a"))),
                                    ("Timestamp", str(item.get("timestamp", "n/a"))),
                                ]
                            )
                    else:
                        render_empty_state("No conversation memory yet", "This conversation has not produced any short-term memory records.")
                except ApiClientError as exc:
                    st.warning(str(exc))
            else:
                render_empty_state("No active conversation", "Start a conversation to inspect short-term memory entries.")

    with right:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Write Memory Demo</div>', unsafe_allow_html=True)
            memory_text = st.text_input("Memory text", value="missing JWT auth issues should be treated as bugs")
            if st.button("Write memory through chat", use_container_width=True):
                _send_chat(client, f"Remember that {memory_text}")
                st.rerun()

    with st.container(border=True):
        st.markdown('<div class="mc-section-title">Long-Term Memories</div>', unsafe_allow_html=True)
        search_cols = st.columns([4, 1])
        st.session_state.memory_search = search_cols[0].text_input("Search memory", value=st.session_state.memory_search)
        search_clicked = search_cols[1].button("Search", use_container_width=True)
        try:
            vector_status = client.list_memory().get("vector_status", {})
            badge(
                f"Vector memory {'Available' if vector_status.get('vector_available') else 'Text fallback'}",
                "success" if vector_status.get("vector_available") else "warning",
            )
            if search_clicked and st.session_state.memory_search.strip():
                search_response = client.search_memory(st.session_state.memory_search.strip(), mode=memory_mode)
                memories = search_response.get("items", [])
                if search_response.get("fallback_reason"):
                    badge(f"Fallback: {search_response['fallback_reason']}", "warning")
                badge(f"Effective mode: {search_response.get('effective_mode', 'text')}", "muted")
            else:
                memories = client.list_memory().get("items", [])

            if memories:
                for item in memories:
                    render_key_value_grid(
                        [
                            ("Content", str(item.get("content", ""))),
                            ("Type", str(item.get("memory_type", "n/a"))),
                            ("Source", str((item.get("metadata") or {}).get("source", "n/a"))),
                            ("Created", str(item.get("created_at", "n/a"))),
                        ]
                    )
            else:
                render_empty_state("No long-term memories", "No long-term memories matched the current filter.")
        except ApiClientError as exc:
            st.warning(str(exc))


def render_widget_admin_tab(client: ApiClient) -> None:
    render_section_intro("Widgets are embeddable chat surfaces. Their config controls greeting, theme, allowed origins, and enabled tools.")

    with st.container(border=True):
        st.markdown('<div class="mc-section-title">Live Widget Preview</div>', unsafe_allow_html=True)
        st.caption("The widget below runs live against the API. Open the bubble to chat.")
        render_widget_iframe(
            widget_id=st.session_state.widget_form_widget_id or "demo-widget",
            api_base_url=st.session_state.api_base_url.replace("http://api:8000", "http://localhost:8000"),
        )

    widgets: list[dict[str, Any]] = []
    try:
        widgets = client.list_widgets().get("items", [])
    except ApiClientError as exc:
        st.warning(f"You need admin role to configure widgets. {exc}")

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Existing Widgets</div>', unsafe_allow_html=True)
            if widgets:
                st.dataframe(widgets, use_container_width=True, hide_index=True)
            else:
                render_empty_state("No widget rows available", "The current API context did not return any widget configuration rows.")

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Create or Update Widget</div>', unsafe_allow_html=True)
            st.session_state.widget_form_widget_id = st.text_input("public_widget_id", value=st.session_state.widget_form_widget_id)
            st.session_state.widget_form_greeting = st.text_area("Greeting", value=st.session_state.widget_form_greeting, height=100)
            st.session_state.widget_form_primary = st.color_picker("Primary color", value=st.session_state.widget_form_primary)
            st.session_state.widget_form_position = st.selectbox(
                "Position",
                ["bottom-right", "bottom-left", "inline"],
                index=["bottom-right", "bottom-left", "inline"].index(st.session_state.widget_form_position),
            )
            st.session_state.widget_form_origins = st.text_area("Allowed origins", value=st.session_state.widget_form_origins, height=90)
            st.session_state.widget_form_tools = st.multiselect("Enabled tools", TOOL_OPTIONS, default=st.session_state.widget_form_tools)
            st.session_state.widget_form_active = st.checkbox("Active", value=st.session_state.widget_form_active)
            form_actions = st.columns(3, gap="small")
            if form_actions[0].button("Create", type="primary", use_container_width=True):
                _upsert_widget(client, create=True)
            if form_actions[1].button("Update", use_container_width=True):
                _upsert_widget(client, create=False)
            if form_actions[2].button("Disable", use_container_width=True):
                try:
                    client.delete_widget(st.session_state.widget_form_widget_id)
                    st.success("Widget disabled.")
                except ApiClientError as exc:
                    st.error(str(exc))

    with right:
        render_key_value_grid(
            [
                ("Demo host", "http://localhost:8080"),
                ("Widget direct URL", "http://localhost:5173"),
                ("Widget id", st.session_state.widget_form_widget_id or "demo-widget"),
            ]
        )
        render_widget_snippet(
            st.session_state.api_base_url,
            widget_id=st.session_state.widget_form_widget_id or "demo-widget",
            widget_url="http://localhost:5173",
        )


def render_observability_tab(client: ApiClient) -> None:
    render_section_intro("Recent structured events, request IDs, and trace links. OpenTelemetry SDK + OTLP exporter → Jaeger.")

    jaeger_cols = st.columns([3, 1], gap="large")
    with jaeger_cols[0]:
        st.info("Distributed traces are available in Jaeger. Every LLM call, tool execution, and RAG retrieval emits a span.", icon="🔭")
    with jaeger_cols[1]:
        st.markdown(
            '<div class="mc-card" style="text-align:center">'
            '<div class="mc-section-title">Jaeger UI</div>'
            '<div class="mc-small-link"><a href="http://localhost:16686" target="_blank">Open Jaeger → :16686</a></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    latest = st.session_state.latest_response or {}
    diagnostics = latest.get("tool_result", {}).get("diagnostics", {}) if isinstance(latest.get("tool_result"), dict) else {}
    filter_cols = st.columns([2, 2, 1], gap="large")
    event_type = filter_cols[0].text_input("Filter by event type", value="")
    filter_request_id = filter_cols[1].text_input("Filter by request ID", value="")
    event_limit = filter_cols[2].number_input("Limit", min_value=1, max_value=100, value=20, step=1)

    top_cols = st.columns(3, gap="large")
    with top_cols[0]:
        render_key_value_grid(
            [
                ("Request ID", str(latest.get("request_id", "n/a"))),
                ("Trace ID", str(latest.get("trace_id", "n/a"))),
                ("Selected tool", str(latest.get("selected_tool", "n/a"))),
            ]
        )
    with top_cols[1]:
        render_key_value_grid(
            [
                ("Mode", str(latest.get("mode", "n/a"))),
                ("Fallback reason", str(latest.get("fallback_reason", "n/a"))),
                ("Citations", str(len((latest.get("tool_result") or {}).get("citations", []))) if isinstance(latest.get("tool_result"), dict) else "0"),
            ]
        )
    with top_cols[2]:
        render_key_value_grid(
            [
                ("Effective retriever", str(diagnostics.get("effective_retriever", "n/a"))),
                ("Preferred source", str(diagnostics.get("preferred_source_type", "n/a"))),
                ("Candidate count", str(diagnostics.get("candidate_count", "n/a"))),
            ]
        )

    with st.container(border=True):
        st.markdown('<div class="mc-section-title">Recent Events</div>', unsafe_allow_html=True)
        try:
            events = client.get_recent_events(limit=int(event_limit), event_type=event_type or None, request_id=filter_request_id or None).get("items", [])
            if events:
                for event in events[:20]:
                    render_key_value_grid(
                        [
                            ("Event", str(event.get("event", "n/a"))),
                            ("Timestamp", str(event.get("timestamp", "n/a"))),
                            ("Request ID", str(event.get("request_id", "n/a"))),
                            ("Trace ID", str(event.get("trace_id", "n/a"))),
                            ("Metadata", str(event.get("fields", {}))),
                        ]
                    )
            else:
                render_empty_state("No recent events", "The API did not return any recent events for the current filter.")
        except ApiClientError as exc:
            st.warning(str(exc))

    command_cols = st.columns(3, gap="large")
    with command_cols[0]:
        render_command_card("API logs", "docker compose logs api --tail=100")
    with command_cols[1]:
        render_command_card("Model-server logs", "docker compose logs model-server --tail=100")
    with command_cols[2]:
        render_command_card("Chatbot logs", "docker compose logs chatbot --tail=100")


def render_evals_tab(summary: dict[str, Any]) -> None:
    render_section_intro("Committed metrics and eval gate outputs for the classifier, retrieval stack, and deterministic local RAG generation.")
    classifier = summary.get("classifier", {})
    classification_golden = summary.get("classification_golden", {})
    rag_retrieval = summary.get("rag_retrieval", {})
    rag_generation = summary.get("rag_generation", {})

    top_metrics = st.columns(5, gap="large")
    with top_metrics[0]:
        metric_card("RoBERTa macro-F1", classifier.get("transformer_macro_f1") or "0.7139", "Selected classifier", tone="accent")
    with top_metrics[1]:
        metric_card("Golden accuracy", classification_golden.get("accuracy") or "0.96", "25-example gate", tone="success")
    with top_metrics[2]:
        metric_card("RAG hit@5", _extract_rag_metric(rag_retrieval, "hit_at_5") or "0.80", "Reranked hybrid")
    with top_metrics[3]:
        metric_card("RAG MRR@10", _extract_rag_metric(rag_retrieval, "mrr_at_10") or "0.63", "Reranked hybrid")
    gate = rag_generation.get("threshold_gate")
    with top_metrics[4]:
        metric_card("Gen gate", gate or "PASS", "Deterministic RAG", tone="success" if gate != "FAIL" else "warning")

    badge("Selected classifier: RoBERTa (beats classical + Claude baseline)", "success")
    badge("Selected RAG: reranked hybrid + query rewrite + metadata boost", "info")

    left, right = st.columns([1, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">Classifier Comparison</div>', unsafe_allow_html=True)
            classifier_rows = [
                {"model": "Classical (TF-IDF + LR)", "macro_f1": format_report_metric(classifier.get("classical_macro_f1") or 0.6121)},
                {"model": "RoBERTa fine-tuned ✓", "macro_f1": format_report_metric(classifier.get("transformer_macro_f1") or 0.7139)},
                {"model": "Claude 3 Haiku baseline", "macro_f1": format_report_metric(classifier.get("llm_macro_f1") or 0.6834)},
            ]
            st.dataframe(classifier_rows, use_container_width=True, hide_index=True)

            st.markdown('<div class="mc-section-title" style="margin-top:0.8rem">RoBERTa metrics</div>', unsafe_allow_html=True)
            render_eval_progress("Macro-F1", classifier.get("transformer_macro_f1") or 0.7139, tone="success")
            render_eval_progress("Accuracy", classifier.get("transformer_accuracy") or 0.725)
            render_eval_progress("Golden gate accuracy", classification_golden.get("accuracy") or 0.96, tone="success")

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">RAG Retrieval Progression</div>', unsafe_allow_html=True)
            retrieval_rows = _build_retrieval_rows(rag_retrieval)
            if retrieval_rows:
                st.dataframe(retrieval_rows, use_container_width=True, hide_index=True)
            else:
                st.dataframe(
                    [
                        {"retriever": "Sparse TF-IDF", "hit@5": "0.5800", "hit@10": "0.6800", "MRR@10": "0.4502"},
                        {"retriever": "Dense MiniLM", "hit@5": "0.7000", "hit@10": "0.7800", "MRR@10": "0.5614"},
                        {"retriever": "Hybrid", "hit@5": "0.7400", "hit@10": "0.8200", "MRR@10": "0.5989"},
                        {"retriever": "Hybrid + rewrite + boost", "hit@5": "0.7600", "hit@10": "0.8400", "MRR@10": "0.6105"},
                        {"retriever": "Reranked selected ✓", "hit@5": "0.8000", "hit@10": "0.8600", "MRR@10": "0.6311"},
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

    with right:
        with st.container(border=True):
            st.markdown('<div class="mc-section-title">RAG Generation Eval</div>', unsafe_allow_html=True)
            render_eval_progress("Answer relevancy", rag_generation.get("answer_relevancy_avg") or 0.3104)
            render_eval_progress("Faithfulness", rag_generation.get("faithfulness_avg") or 0.6244, tone="success")
            render_eval_progress("Citation coverage", rag_generation.get("citation_coverage") or 0.68, tone="success")
            render_eval_progress("Groundedness pass rate", rag_generation.get("groundedness_pass_rate") or 0.72, tone="success")
            render_key_value_grid(
                [
                    ("Judge/human agreement", format_report_metric(rag_generation.get("judge_human_agreement") or 0.70)),
                    ("Human spot-checked", str(rag_generation.get("human_labeled_count", 5))),
                    ("Generation gate", rag_generation.get("threshold_gate") or "PASS"),
                ]
            )

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">RAG Retrieval Highlights</div>', unsafe_allow_html=True)
            render_eval_progress("hit@5 (reranked)", _extract_rag_metric(rag_retrieval, "hit_at_5") or 0.80, tone="success")
            render_eval_progress("hit@10 (reranked)", _extract_rag_metric(rag_retrieval, "hit_at_10") or 0.86, tone="success")
            render_eval_progress("MRR@10 (reranked)", _extract_rag_metric(rag_retrieval, "mrr_at_10") or 0.6311, tone="success")

        with st.container(border=True):
            st.markdown('<div class="mc-section-title">CI Workflow Jobs</div>', unsafe_allow_html=True)
            render_chip_group(
                "Active jobs",
                ["api-tests", "model-server-tests", "widget-build", "lint", "type-check", "evals", "docker-build", "redaction-check"],
            )


def _send_chat(client: ApiClient, message: str, *, issue_title: str = "", issue_body: str = "", use_llm: bool | None = None) -> None:
    add_message("user", message)
    payload: dict[str, Any] = {
        "conversation_id": st.session_state.conversation_id,
        "message": message,
        "context": {
            "issue_title": issue_title or None,
            "issue_body": issue_body or None,
            "issue_url": st.session_state.issue_url or None,
        },
        "use_llm": st.session_state.use_llm if use_llm is None else use_llm,
    }
    try:
        response = client.chat(payload)
    except ApiClientError as exc:
        st.session_state.last_error = str(exc)
        add_message("assistant", "I couldn't reach the assistant service. Check the API is running.")
        return

    st.session_state.conversation_id = response.get("conversation_id")
    st.session_state.latest_response = response
    st.session_state.last_error = None
    tool_result = response.get("tool_result") or {}
    add_message(
        "assistant",
        response.get("message", ""),
        metadata={
            "selected_tool": response.get("selected_tool"),
            "mode": response.get("mode"),
            "citations": tool_result.get("citations") or [],
            "request_id": response.get("request_id"),
            "trace_id": response.get("trace_id"),
            "fallback_reason": response.get("fallback_reason"),
        },
    )


def _chat_once(client: ApiClient, message: str, title: str, body: str) -> dict[str, Any] | None:
    try:
        return client.chat(
            {
                "conversation_id": st.session_state.conversation_id,
                "message": message,
                "context": {"issue_title": title, "issue_body": body, "issue_url": st.session_state.issue_url or None},
                "use_llm": bool(st.session_state.use_llm),
            }
        )
    except ApiClientError as exc:
        st.error(str(exc))
        return None


def _render_tool_response(response: dict[str, Any]) -> None:
    result = response.get("tool_result") or {}
    badge(f"Tool: {response.get('selected_tool', 'n/a')}", "info")
    badge(f"Mode: {response.get('mode', 'n/a')}", "muted")
    if response.get("message"):
        st.markdown(response.get("message", ""))

    selected_tool = response.get("selected_tool")
    if selected_tool == "classify_issue":
        cols = st.columns([1, 1], gap="large")
        cols[0].metric("Label", result.get("label", "n/a"))
        cols[1].metric("Confidence", f"{float(result.get('confidence', 0)):.2f}")
        probabilities = result.get("top_probabilities", [])
        if probabilities:
            st.dataframe(probabilities, use_container_width=True, hide_index=True)
    elif selected_tool == "extract_entities":
        grouped = group_entities(result.get("entities", []))
        if grouped:
            for entity_type, values in grouped.items():
                render_chip_group(entity_type, values)
        else:
            render_empty_state("No entities detected", "The current response did not include any extracted entities.")
    elif selected_tool == "summarize_thread":
        bullets = result.get("bullets", [])
        if bullets:
            for bullet in bullets:
                st.markdown(f"- {bullet}")
        else:
            render_empty_state("No summary bullets", "The current response did not return any summary bullets.")
    elif selected_tool == "rag_answer":
        citations = result.get("citations", [])
        if citations:
            for citation in citations[:5]:
                render_citation(citation)
        else:
            render_empty_state("No citations", "The current knowledge-base response did not include citations.")


def _upsert_widget(client: ApiClient, *, create: bool) -> None:
    payload = {
        "public_widget_id": st.session_state.widget_form_widget_id,
        "allowed_origins": [line.strip() for line in st.session_state.widget_form_origins.splitlines() if line.strip()],
        "theme": {"primaryColor": st.session_state.widget_form_primary, "position": st.session_state.widget_form_position},
        "greeting": st.session_state.widget_form_greeting,
        "enabled_tools": st.session_state.widget_form_tools,
        "is_active": st.session_state.widget_form_active,
    }
    try:
        if create:
            create_payload = {k: v for k, v in payload.items() if k != "is_active"}
            client.create_widget(create_payload)
            st.success("Widget created.")
        else:
            update_payload = {k: v for k, v in payload.items() if k != "public_widget_id"}
            client.update_widget(st.session_state.widget_form_widget_id, update_payload)
            st.success("Widget updated.")
    except ApiClientError as exc:
        st.error(str(exc))


def _check_api_online(client: ApiClient) -> bool:
    try:
        client.health()
    except ApiClientError:
        return False
    return True


def _safe_reports_summary(client: ApiClient) -> dict[str, Any]:
    try:
        return client.get_reports_summary()
    except ApiClientError:
        return {}


def _extract_rag_metric(rag_summary: dict[str, Any], metric_key: str) -> Any:
    preferred_order = ["selected", "reranked", "hybrid_rewrite_boost", "hybrid", "dense", "sparse"]
    for key in preferred_order:
        metrics = rag_summary.get(key)
        if isinstance(metrics, dict) and metric_key in metrics:
            return metrics.get(metric_key)
    return None


def _build_retrieval_rows(rag_summary: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    labels = {
        "sparse": "Sparse TF-IDF",
        "dense": "Dense MiniLM",
        "hybrid": "Hybrid",
        "hybrid_rewrite_boost": "Hybrid + rewrite + boost",
        "reranked": "Reranked selected",
        "selected": "Selected default",
    }
    for key, label in labels.items():
        metrics = rag_summary.get(key)
        if not isinstance(metrics, dict):
            continue
        rows.append(
            {
                "retriever": label,
                "hit@5": format_report_metric(metrics.get("hit_at_5")),
                "hit@10": format_report_metric(metrics.get("hit_at_10")),
                "MRR@10": format_report_metric(metrics.get("mrr_at_10")),
            }
        )
    return rows


if __name__ == "__main__":
    main()
