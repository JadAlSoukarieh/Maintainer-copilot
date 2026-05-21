from __future__ import annotations

import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --mc-bg: #f0f4f9;
          --mc-surface: #ffffff;
          --mc-border: #d2dde9;
          --mc-border-strong: #b8cce0;
          --mc-text: #0c1e33;
          --mc-text-soft: #2a4460;
          --mc-muted: #5a7490;
          --mc-accent: #1a63d8;
          --mc-accent-dark: #1450b0;
          --mc-accent-soft: #e8f0fc;
          --mc-success: #1a7a3c;
          --mc-success-bg: #e6f7ed;
          --mc-warning: #8a4d00;
          --mc-warning-bg: #fff4e0;
          --mc-danger: #a01f17;
          --mc-danger-bg: #fdf0ef;
          --mc-shadow: 0 20px 56px rgba(10,28,54,0.12);
          --mc-shadow-soft: 0 2px 12px rgba(10,28,54,0.07);
          --mc-radius: 14px;
          --mc-radius-sm: 10px;
        }

        html, body, [class*="css"] { color: var(--mc-text); }

        /* ── Page background ───────────────────────── */
        [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(ellipse at 0% 0%, rgba(26,99,216,0.06) 0%, transparent 30%),
            linear-gradient(180deg, #f4f8ff 0%, #edf3fb 55%, #e8f0f9 100%);
        }
        .block-container {
          max-width: 1480px;
          padding-top: 0.75rem;
          padding-bottom: 2rem;
          padding-left: 1.5rem;
          padding-right: 1.5rem;
        }
        .stAppToolbar, header[data-testid="stHeader"] { background: transparent; }

        /* ── Sidebar ───────────────────────────────── */
        [data-testid="stSidebar"] {
          background: linear-gradient(180deg, #091826 0%, #0e2540 55%, #162f52 100%);
          border-right: 1px solid rgba(255,255,255,0.05);
        }
        [data-testid="stSidebar"] * { color: #bdd4ee !important; }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { color: #e2efff !important; font-size: 1rem !important; }
        [data-testid="stSidebar"] .stButton button {
          background: rgba(255,255,255,0.07);
          border: 1px solid rgba(255,255,255,0.13);
          color: #bdd4ee !important;
          border-radius: 9px;
          font-size: 0.85rem;
          transition: all 0.15s;
        }
        [data-testid="stSidebar"] .stButton button:hover {
          background: rgba(255,255,255,0.13);
          border-color: rgba(255,255,255,0.26);
          color: #e2efff !important;
        }
        [data-testid="stSidebar"] .stButton button[kind="primary"] {
          background: var(--mc-accent); border-color: var(--mc-accent); color: #fff !important;
        }
        [data-testid="stSidebar"] [data-testid="stToggle"] label,
        [data-testid="stSidebar"] [data-testid="stToggle"] span { color: #bdd4ee !important; }
        [data-testid="stSidebar"] code {
          background: rgba(255,255,255,0.09) !important;
          color: #90bde0 !important;
          border: 1px solid rgba(255,255,255,0.1) !important;
          border-radius: 6px !important;
          font-size: 0.78rem !important;
        }
        [data-testid="stSidebar"] [data-testid="stCaption"] {
          color: rgba(189,212,238,0.65) !important;
          font-size: 0.78rem !important;
        }

        /* ── st.container(border=True) cards ──────── */
        [data-testid="stBorderContainer"] {
          background: #ffffff !important;
          border: 1px solid var(--mc-border) !important;
          border-radius: var(--mc-radius) !important;
          box-shadow: var(--mc-shadow-soft) !important;
          padding: 1rem 1.1rem !important;
        }
        /* Chat message coloring via :has() */
        [data-testid="stBorderContainer"]:has(.mc-msg-user) {
          border-left: 3px solid #aac4e8 !important;
          background: linear-gradient(160deg, #f8fbff 0%, #f0f6ff 100%) !important;
        }
        [data-testid="stBorderContainer"]:has(.mc-msg-asst) {
          border-left: 3px solid var(--mc-accent) !important;
          background: linear-gradient(160deg, #f0f6ff 0%, #e8f2ff 100%) !important;
        }

        /* ── Tabs ──────────────────────────────────── */
        [data-testid="stTabs"] > div:first-child {
          border-bottom: 2px solid var(--mc-border);
          gap: 0;
          margin-bottom: 0.25rem;
        }
        button[data-baseweb="tab"] {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--mc-muted);
          padding: 0.6rem 1.1rem 0.55rem;
          border-radius: 8px 8px 0 0;
          transition: color 0.15s, background 0.15s;
          border-bottom: 2px solid transparent;
          margin-bottom: -2px;
        }
        button[data-baseweb="tab"]:hover {
          color: var(--mc-text);
          background: rgba(26,99,216,0.05);
        }
        button[data-baseweb="tab"][aria-selected="true"] {
          color: var(--mc-accent) !important;
          font-weight: 760;
          border-bottom-color: var(--mc-accent) !important;
          background: rgba(26,99,216,0.04);
        }

        /* ── Forms ─────────────────────────────────── */
        div[data-testid="stForm"] { border: none; padding: 0; background: transparent; }

        /* ── Banner ────────────────────────────────── */
        .mc-banner {
          background: linear-gradient(135deg, #08192e 0%, #0d2d50 42%, #1250aa 82%, #1a63d8 100%);
          border-radius: var(--mc-radius);
          padding: 1.2rem 1.5rem 1rem;
          margin-bottom: 1rem;
          position: relative;
          overflow: hidden;
        }
        .mc-banner::before {
          content: "";
          position: absolute;
          top: -35%; right: -4%;
          width: 42%; height: 200%;
          background: radial-gradient(ellipse, rgba(255,255,255,0.07) 0%, transparent 60%);
          pointer-events: none;
        }
        .mc-banner-eyebrow {
          font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
          letter-spacing: 0.13em; color: rgba(190,215,255,0.7); margin-bottom: 0.3rem;
        }
        .mc-banner-title {
          font-size: 1.65rem; font-weight: 800; line-height: 1.1;
          color: #fff; margin-bottom: 0.28rem; letter-spacing: -0.01em;
        }
        .mc-banner-subtitle {
          color: rgba(205,225,255,0.8); font-size: 0.92rem;
          line-height: 1.55; max-width: 820px;
        }

        /* ── HTML-only cards (metric, feature, etc.) */
        .mc-card, .mc-command-card {
          background: rgba(255,255,255,0.97);
          border: 1px solid var(--mc-border);
          border-radius: var(--mc-radius);
          box-shadow: var(--mc-shadow-soft);
          padding: 1rem 1.05rem;
          margin-bottom: 0.75rem;
        }
        .mc-login-card {
          background: #fff;
          border: 1px solid var(--mc-border);
          border-radius: var(--mc-radius);
          box-shadow: var(--mc-shadow);
          padding: 1.6rem 1.5rem;
          margin-bottom: 0.75rem;
        }
        .mc-feature-card {
          min-height: 130px;
          background: linear-gradient(180deg, #ffffff 0%, #f6faff 100%);
        }
        .mc-feature-title {
          font-size: 0.98rem; font-weight: 760; margin-bottom: 0.28rem; color: var(--mc-text);
        }
        .mc-section-title {
          font-size: 0.7rem; font-weight: 780; text-transform: uppercase;
          letter-spacing: 0.1em; color: var(--mc-muted); margin-bottom: 0.55rem;
        }
        .mc-card-copy { color: var(--mc-text-soft); line-height: 1.6; font-size: 0.93rem; }
        .mc-card-caption { color: var(--mc-muted); font-size: 0.83rem; margin-top: 0.45rem; }
        .mc-tab-intro {
          color: var(--mc-muted); font-size: 0.91rem; line-height: 1.55; margin-bottom: 0.8rem;
        }
        .mc-section-intro { margin-bottom: 0.9rem; }
        .mc-eyebrow {
          color: var(--mc-accent); font-size: 0.74rem; font-weight: 620;
          letter-spacing: 0.07em; text-transform: uppercase; margin-bottom: 0.28rem;
        }
        .mc-section-description {
          color: var(--mc-muted); font-size: 0.9rem; line-height: 1.5; margin-top: 0.28rem;
        }

        /* ── Metric cards ──────────────────────────── */
        .mc-metric-card {
          min-height: 106px; display: flex; flex-direction: column; justify-content: space-between;
        }
        .mc-metric-accent  { border-color: rgba(26,99,216,0.28); background: linear-gradient(180deg,#fff 0%,#f0f6ff 100%); }
        .mc-metric-success { border-color: rgba(26,122,60,0.22); background: linear-gradient(180deg,#fff 0%,#f2faf5 100%); }
        .mc-metric-warning { border-color: rgba(138,77,0,0.20); }
        .mc-metric-danger  { border-color: rgba(160,31,23,0.20); }
        .mc-metric-label {
          color: var(--mc-muted); font-size: 0.7rem;
          text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.28rem;
        }
        .mc-metric-value {
          font-size: 1.3rem; line-height: 1.15; font-weight: 800;
          color: var(--mc-text); word-break: break-word;
        }
        .mc-metric-caption { margin-top: 0.35rem; color: var(--mc-muted); font-size: 0.79rem; }

        /* ── Badges ────────────────────────────────── */
        .mc-badge {
          display: inline-flex; align-items: center; border-radius: 999px;
          padding: 0.22rem 0.6rem; margin-right: 0.3rem; margin-bottom: 0.3rem;
          font-size: 0.74rem; font-weight: 750; border: 1px solid transparent; white-space: nowrap;
        }
        .mc-badge-success { background: var(--mc-success-bg); color: var(--mc-success); border-color: #aadfc0; }
        .mc-badge-warning { background: var(--mc-warning-bg); color: var(--mc-warning); border-color: #eecf90; }
        .mc-badge-danger  { background: var(--mc-danger-bg);  color: var(--mc-danger);  border-color: #f0c0bc; }
        .mc-badge-muted   { background: #f0f4f8; color: #4d6075; border-color: #d2dce8; }
        .mc-badge-info    { background: var(--mc-accent-soft); color: #1340b0; border-color: #b0ccf8; }

        /* ── Chat messages ─────────────────────────── */
        .mc-message-meta {
          font-size: 0.7rem; font-weight: 780; text-transform: uppercase;
          letter-spacing: 0.1em; margin-bottom: 0.3rem;
        }
        .mc-msg-user { color: #5a7faa; }
        .mc-msg-asst { color: var(--mc-accent); }
        .mc-message-badges { margin-top: 0.45rem; }

        /* ── Source / citation cards ───────────────── */
        .mc-source-card {
          border: 1px solid #d5e4f2; border-radius: 10px;
          background: linear-gradient(180deg,#fff 0%,#f7fbff 100%);
          padding: 0.8rem 0.95rem; margin-bottom: 0.55rem;
        }
        .mc-source-top {
          display: flex; justify-content: space-between;
          align-items: flex-start; gap: 0.7rem; margin-bottom: 0.22rem;
        }
        .mc-source-title { font-size: 0.93rem; font-weight: 740; line-height: 1.3; color: var(--mc-text); }
        .mc-source-meta  { color: var(--mc-muted); font-size: 0.77rem; margin-bottom: 0.32rem; }
        .mc-source-excerpt { color: var(--mc-text-soft); font-size: 0.88rem; line-height: 1.48; margin-bottom: 0.32rem; }
        .mc-source-link a, .mc-small-link a {
          color: var(--mc-accent); text-decoration: none; font-weight: 700;
        }
        .mc-source-link a:hover, .mc-small-link a:hover { text-decoration: underline; }

        /* ── Empty states ──────────────────────────── */
        .mc-empty-state {
          border: 1px dashed var(--mc-border-strong); border-radius: 10px;
          background: linear-gradient(180deg,#fafdff 0%,#f2f8ff 100%);
          padding: 0.95rem 1rem; margin: 0.15rem 0 0.35rem;
        }
        .mc-empty-title { font-size: 0.92rem; font-weight: 740; color: var(--mc-text); margin-bottom: 0.16rem; }
        .mc-empty-copy  { color: var(--mc-muted); font-size: 0.88rem; line-height: 1.5; }

        /* ── Chips ─────────────────────────────────── */
        .mc-chip-row { display: flex; flex-wrap: wrap; gap: 0.38rem; }
        .mc-chip {
          display: inline-flex; align-items: center;
          border: 1px solid #ccdaeb; border-radius: 999px; padding: 0.24rem 0.56rem;
          background: #f5f9ff; color: var(--mc-text-soft); font-size: 0.79rem; font-weight: 640;
        }

        /* ── Key-value grid ────────────────────────── */
        .mc-kv-row {
          display: flex; justify-content: space-between;
          align-items: flex-start; gap: 1rem; padding: 0.4rem 0;
          border-bottom: 1px solid #eaf0f7;
        }
        .mc-kv-row:last-child { border-bottom: none; }
        .mc-kv-label { color: var(--mc-muted); font-size: 0.81rem; flex: 0 0 40%; }
        .mc-kv-value { color: var(--mc-text); font-size: 0.86rem; font-weight: 670; text-align: right; overflow-wrap: anywhere; }

        /* ── Eval progress bars ────────────────────── */
        .mc-eval-row { margin-bottom: 0.6rem; }
        .mc-eval-header {
          display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.18rem;
        }
        .mc-eval-label { font-size: 0.82rem; font-weight: 660; color: var(--mc-text-soft); }
        .mc-eval-value { font-size: 0.87rem; font-weight: 780; color: var(--mc-text); }
        .mc-eval-track { height: 7px; background: #e4edf7; border-radius: 999px; overflow: hidden; }
        .mc-eval-fill {
          height: 100%; border-radius: 999px;
          background: linear-gradient(90deg,#1a63d8 0%,#4a90e2 100%);
          transition: width 0.4s ease;
        }
        .mc-eval-fill-success { background: linear-gradient(90deg,#1a7a3c 0%,#38b06a 100%); }
        .mc-eval-fill-warning { background: linear-gradient(90deg,#c47c10 0%,#e9a530 100%); }

        /* ── Service health grid ───────────────────── */
        .mc-health-row {
          display: flex; align-items: center; gap: 0.48rem; padding: 0.36rem 0;
          border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.82rem;
        }
        .mc-health-row:last-child { border-bottom: none; }
        .mc-health-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
        .mc-health-dot-green  { background: #2ed672; box-shadow: 0 0 5px #2ed672; }
        .mc-health-dot-yellow { background: #f5c541; box-shadow: 0 0 5px #f5c541; }
        .mc-health-dot-red    { background: #ff4f3b; box-shadow: 0 0 5px #ff4f3b; }
        .mc-health-dot-grey   { background: #607a90; }
        .mc-health-name { flex: 1; font-weight: 620; color: #bdd4ee; }
        .mc-health-port { font-size: 0.71rem; color: rgba(189,212,238,0.5); font-family: ui-monospace, monospace; }

        /* ── Sidebar headings ──────────────────────── */
        .mc-sidebar-heading {
          font-size: 0.66rem; font-weight: 760; text-transform: uppercase;
          letter-spacing: 0.12em; color: rgba(189,212,238,0.42) !important;
          padding: 0.7rem 0 0.15rem;
        }
        .mc-small-link { padding: 0.2rem 0; }

        /* ── Login page ────────────────────────────── */
        .mc-login-page { max-width: 1200px; margin: 0 auto; padding-top: 0.75rem; }
        .mc-shell-title {
          font-size: 2rem; line-height: 1.08; font-weight: 800;
          letter-spacing: -0.01em; color: var(--mc-text); margin-bottom: 0.35rem;
        }
        .mc-shell-subtitle, .mc-login-subtitle {
          max-width: 820px; color: var(--mc-muted); font-size: 0.95rem;
          line-height: 1.65; margin-bottom: 0.8rem;
        }

        /* ── Command card ──────────────────────────── */
        .mc-command-card pre, .mc-command-card code { margin: 0; }

        /* ── Streamlit native overrides ────────────── */
        .stButton button, .stDownloadButton button {
          border-radius: 9px; border: 1px solid #c4d4e6;
          background: #fff; color: var(--mc-text);
          min-height: 2.4rem; font-weight: 640; box-shadow: none; transition: all 0.15s;
        }
        .stButton button[kind="primary"], .stFormSubmitButton button[kind="primary"] {
          background: var(--mc-accent); border-color: var(--mc-accent); color: #fff;
        }
        .stButton button:hover { border-color: var(--mc-accent); color: var(--mc-accent); }
        .stButton button[kind="primary"]:hover, .stFormSubmitButton button[kind="primary"]:hover {
          filter: brightness(0.92); color: #fff;
        }
        .stTextInput input, .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
          border-radius: 9px; border-color: #c4d4e6;
          background: #fff; color: var(--mc-text); transition: border-color 0.15s;
        }
        .stTextInput input:focus, .stTextArea textarea:focus {
          border-color: var(--mc-accent) !important;
          box-shadow: 0 0 0 2px rgba(26,99,216,0.14) !important;
        }
        .stTextArea textarea { line-height: 1.55; }
        .stCheckbox label, .stRadio label, .stSelectbox label,
        .stTextInput label, .stTextArea label { color: var(--mc-text); font-weight: 600; }
        .stExpander {
          border: 1px solid var(--mc-border) !important;
          border-radius: 10px !important;
          background: rgba(255,255,255,0.88) !important;
        }
        .stExpander summary { font-size: 0.88rem !important; font-weight: 640 !important; }
        .stDataFrame, [data-testid="stTable"] { border-radius: 10px; overflow: hidden; }
        a { color: var(--mc-accent); text-decoration: none; }
        a:hover { text-decoration: underline; }

        @media (max-width: 1100px) {
          .mc-banner-title { font-size: 1.4rem; }
          .block-container { padding-left: 1rem; padding-right: 1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
