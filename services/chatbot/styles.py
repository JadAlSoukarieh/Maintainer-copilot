from __future__ import annotations

import streamlit as st


def apply_styles() -> None:
    st.html("""
    <style>
    /* ══════════════════════════════════════════════════════════
       MAINTAINER'S COPILOT — ADMIN CONSOLE
       Streamlit 1.57 compatible — uses st.html() injection
    ══════════════════════════════════════════════════════════ */

    :root {
      --c-accent:    #1a5fd4;
      --c-accent-2:  #1048a8;
      --c-accent-bg: #e6effc;
      --c-surface:   #ffffff;
      --c-bg:        #edf3fc;
      --c-border:    rgba(0,0,0,.08);
      --c-text:      #0b1c33;
      --c-text-2:    #2c4a68;
      --c-text-3:    #567090;
      --c-shadow-2:  0 1px 3px rgba(0,0,0,.05), 0 4px 16px rgba(8,20,48,.08);
      --c-shadow-3:  0 2px 6px rgba(0,0,0,.07), 0 8px 28px rgba(8,20,48,.12);
      --r:           14px;
    }

    /* ── Page background (all three cover Streamlit version variants) ── */
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewContainer"] {
      background: linear-gradient(175deg, #edf3fc 0%, #e4edf7 100%) !important;
      min-height: 100vh;
    }
    .block-container {
      max-width: 1520px !important;
      padding: 0.4rem 1.5rem 2.5rem !important;
    }
    header[data-testid="stHeader"],
    .stAppToolbar { background: transparent !important; }

    /* ── Sidebar (CLI --theme.secondaryBackgroundColor sets the base,
         this gradient adds polish) ── */
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #06101e 0%, #0b1e38 45%, #112444 100%) !important;
      border-right: 1px solid rgba(255,255,255,.05) !important;
    }
    [data-testid="stSidebar"] * { color: #aec8e4 !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
      color: #d8ecff !important;
      font-size: 0.98rem !important;
      font-weight: 750 !important;
    }
    [data-testid="stSidebar"] .stButton button {
      background: rgba(255,255,255,.07) !important;
      border: 1px solid rgba(255,255,255,.13) !important;
      color: #aec8e4 !important;
      border-radius: 8px !important;
      font-size: 0.83rem !important;
      transition: all .14s !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
      background: rgba(255,255,255,.14) !important;
      color: #d8ecff !important;
    }
    [data-testid="stSidebar"] code {
      background: rgba(255,255,255,.09) !important;
      color: #6aaada !important;
      border: 1px solid rgba(255,255,255,.10) !important;
      border-radius: 5px !important;
      font-size: 0.76rem !important;
      padding: 0.12rem 0.35rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaption"] {
      color: rgba(174,200,228,.55) !important;
      font-size: 0.76rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stToggle"] label span {
      color: #aec8e4 !important;
    }

    /* ── Cards (st.container border=True) ── */
    [data-testid="stBorderContainer"] {
      background: #ffffff !important;
      border-radius: 14px !important;
      border: 1px solid rgba(0,0,0,.08) !important;
      box-shadow: 0 1px 3px rgba(0,0,0,.05), 0 4px 16px rgba(8,20,48,.08) !important;
      padding: 1.2rem 1.4rem 1.1rem !important;
      transition: box-shadow .18s, border-color .18s !important;
    }
    [data-testid="stBorderContainer"]:hover {
      box-shadow: 0 2px 6px rgba(0,0,0,.07), 0 8px 28px rgba(8,20,48,.12) !important;
      border-color: rgba(26,95,212,.18) !important;
    }

    /* ── Primary buttons ── */
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"],
    .stFormSubmitButton button[kind="primaryFormSubmit"],
    .stFormSubmitButton button {
      background: #1a5fd4 !important;
      color: #ffffff !important;
      border: none !important;
      box-shadow: 0 1px 4px rgba(26,95,212,.30) !important;
      border-radius: 9px !important;
      font-weight: 650 !important;
    }
    button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
    .stFormSubmitButton button:hover {
      background: #1048a8 !important;
    }
    button[data-testid="stBaseButton-secondary"],
    button[data-testid="stBaseButton-secondaryFormSubmit"] {
      border-radius: 9px !important;
    }

    /* ── Inputs ── */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input {
      border-radius: 9px !important;
      border: 1px solid #c4d4e6 !important;
      transition: border-color .14s, box-shadow .14s !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
      border-color: #1a5fd4 !important;
      box-shadow: 0 0 0 3px rgba(26,95,212,.15) !important;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [role="tablist"] {
      border-bottom: 1px solid rgba(0,0,0,.10) !important;
      gap: 0 !important;
    }
    [data-testid="stTabs"] button[role="tab"] {
      background: transparent !important;
      border: none !important;
      border-bottom: 2px solid transparent !important;
      color: #567090 !important;
      font-size: 0.88rem !important;
      font-weight: 580 !important;
      padding: 0.65rem 1.1rem !important;
      border-radius: 0 !important;
      transition: color .14s, border-color .14s !important;
    }
    [data-testid="stTabs"] button[role="tab"]:hover {
      color: #1a5fd4 !important;
      background: rgba(26,95,212,.04) !important;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
      color: #1a5fd4 !important;
      border-bottom-color: #1a5fd4 !important;
      font-weight: 700 !important;
    }

    /* ── Native st.metric() ── */
    [data-testid="stMetric"] {
      background: #ffffff !important;
      border-radius: 14px !important;
      padding: 1.1rem 1.3rem !important;
      border: 1px solid rgba(0,0,0,.07) !important;
      box-shadow: 0 1px 3px rgba(0,0,0,.05), 0 4px 16px rgba(8,20,48,.07) !important;
    }
    [data-testid="stMetricLabel"] {
      font-size: 0.70rem !important;
      font-weight: 700 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.08em !important;
      color: #567090 !important;
    }
    [data-testid="stMetricValue"] {
      font-size: 1.45rem !important;
      font-weight: 800 !important;
      color: #0b1c33 !important;
    }
    [data-testid="stMetricDelta"] {
      font-size: 0.78rem !important;
      color: #567090 !important;
    }

    /* ── Chat message coloring (via :has()) ── */
    [data-testid="stBorderContainer"]:has(.mc-msg-user) {
      border-left: 4px solid rgba(94,155,226,.5) !important;
      background: linear-gradient(155deg, #f6f9ff, #ecf4ff) !important;
    }
    [data-testid="stBorderContainer"]:has(.mc-msg-asst) {
      border-left: 4px solid #1a5fd4 !important;
      background: linear-gradient(155deg, #edf4ff, #e4effe) !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
      border-radius: 10px !important;
      overflow: hidden !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(26,95,212,.25); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(26,95,212,.45); }

    /* ════════════════════════════════════════════════════════════
       CUSTOM mc-* COMPONENT CLASSES
       These style HTML we emit via st.html() — fully controlled.
    ════════════════════════════════════════════════════════════ */

    /* Sidebar helpers */
    .mc-sidebar-heading {
      font-size: 0.62rem;
      font-weight: 780;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: rgba(174,200,228,.42) !important;
      padding: 0.85rem 0 0.18rem;
      border-top: 1px solid rgba(255,255,255,.06);
      margin-top: 0.3rem;
    }
    .mc-small-link { padding: 0.12rem 0; }
    .mc-small-link a {
      color: rgba(174,200,228,.70) !important;
      font-size: 0.82rem;
      text-decoration: none;
      transition: color .12s;
    }
    .mc-small-link a:hover { color: #d8ecff !important; }

    /* Service health rows */
    .mc-health-row {
      display: flex; align-items: center; gap: 0.42rem;
      padding: 0.26rem 0; font-size: 0.81rem;
      flex-wrap: nowrap; overflow: hidden;
    }
    .mc-health-dot {
      width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    }
    .mc-health-dot-green  { background: #22d46a; box-shadow: 0 0 7px rgba(34,212,106,.65); }
    .mc-health-dot-yellow { background: #f0c030; box-shadow: 0 0 5px rgba(240,192,48,.5); }
    .mc-health-dot-red    { background: #f03c3c; box-shadow: 0 0 5px rgba(240,60,60,.55); }
    .mc-health-dot-grey   { background: rgba(120,158,200,.38); }
    .mc-health-name {
      flex: 1; font-weight: 640; color: #aec8e4;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .mc-health-port {
      font-size: 0.74rem; color: rgba(174,200,228,.42);
      font-family: ui-monospace, "SF Mono", monospace;
    }

    /* Console banner (gradient header bar) */
    .mc-banner {
      background: linear-gradient(130deg, #050e1c 0%, #0a1f3e 30%, #0c308a 68%, #1a5fd4 100%);
      border-radius: 14px;
      padding: 1.5rem 1.8rem 1.4rem;
      margin-bottom: 1.2rem;
      box-shadow: 0 6px 24px rgba(8,28,72,.22), inset 0 1px 0 rgba(255,255,255,.07);
    }
    .mc-banner-eyebrow {
      font-size: 0.63rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.17em; color: rgba(255,255,255,.52);
      margin-bottom: 0.3rem;
    }
    .mc-banner-title {
      font-size: 1.55rem; font-weight: 800; color: #ffffff;
      letter-spacing: -0.03em; line-height: 1.15;
    }
    .mc-banner-subtitle {
      font-size: 0.84rem; color: rgba(255,255,255,.63);
      margin-top: 0.35rem; line-height: 1.5;
    }

    /* Section title inside cards */
    .mc-section-title {
      font-size: 0.70rem;
      font-weight: 770;
      text-transform: uppercase;
      letter-spacing: 0.10em;
      color: #1a5fd4;
      padding-left: 0.55rem;
      border-left: 2.5px solid #1a5fd4;
      margin-bottom: 0.65rem;
      line-height: 1.4;
    }

    /* Tab intro text */
    .mc-tab-intro {
      font-size: 0.88rem; color: #567090;
      margin-bottom: 1.1rem; line-height: 1.6;
    }
    .mc-section-intro { margin-bottom: 0.5rem; }
    .mc-eyebrow {
      font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.14em; color: #1a5fd4; margin-bottom: 0.2rem;
    }
    .mc-section-description {
      font-size: 0.84rem; color: #567090; margin: 0.2rem 0 0;
    }

    /* Badges */
    .mc-badge {
      display: inline-block;
      font-size: 0.72rem; font-weight: 650;
      border-radius: 20px;
      padding: 0.20rem 0.65rem;
      letter-spacing: 0.01em; line-height: 1.5;
      margin: 0.1rem 0.12rem 0.1rem 0;
    }
    .mc-badge-success { background: #e2f5ec; color: #0f7a3a; }
    .mc-badge-warning { background: #fff3dc; color: #8c4b00; }
    .mc-badge-danger  { background: #fde8e7; color: #981c14; }
    .mc-badge-muted   { background: #eef2f7; color: #567090; }
    .mc-badge-info    { background: #e6effc; color: #1a5fd4; }

    /* Custom HTML metric card (used in eval tab for tone variants) */
    .mc-card {
      background: #ffffff;
      border-radius: 14px;
      padding: 1.1rem 1.3rem;
      border: 1px solid rgba(0,0,0,.08);
      box-shadow: 0 1px 3px rgba(0,0,0,.04), 0 4px 16px rgba(8,20,48,.07);
      margin-bottom: 0.6rem;
    }
    .mc-card-copy { font-size: 0.86rem; color: #567090; line-height: 1.55; }
    .mc-card-caption { font-size: 0.76rem; color: #8aa5c2; margin-top: 0.3rem; }
    .mc-metric-card { min-height: 98px; }
    .mc-metric-label {
      font-size: 0.70rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; color: #567090; margin-bottom: 0.35rem;
    }
    .mc-metric-value {
      font-size: 1.45rem; font-weight: 800; color: #0b1c33;
      letter-spacing: -0.02em; line-height: 1.2;
    }
    .mc-metric-caption { font-size: 0.75rem; color: #8aa5c2; margin-top: 0.2rem; }
    .mc-metric-accent .mc-metric-value  { color: #1a5fd4; }
    .mc-metric-success .mc-metric-value { color: #0f7a3a; }
    .mc-metric-warning .mc-metric-value { color: #8c4b00; }

    /* Feature cards (login page) */
    .mc-feature-card {
      background: #ffffff;
      border-radius: 14px;
      padding: 1.5rem 1.4rem 1.3rem;
      border: 1px solid rgba(0,0,0,.07);
      border-top: 3px solid #1a5fd4;
      box-shadow: 0 2px 6px rgba(0,0,0,.05), 0 8px 24px rgba(8,20,48,.08);
      height: 100%;
    }
    .mc-feature-icon {
      font-size: 1.8rem; margin-bottom: 0.7rem; display: block; line-height: 1;
    }
    .mc-feature-title {
      font-size: 0.94rem; font-weight: 760; color: #0b1c33;
      margin-bottom: 0.4rem; letter-spacing: -0.01em;
    }

    /* KV data grid */
    .mc-kv-grid { margin: 0.2rem 0; }
    .mc-kv-row {
      display: flex; align-items: baseline; gap: 0.5rem;
      padding: 0.38rem 0;
      border-bottom: 1px solid rgba(0,0,0,.05);
      font-size: 0.84rem;
    }
    .mc-kv-row:last-child { border-bottom: none; }
    .mc-kv-label {
      width: 38%; flex-shrink: 0;
      font-weight: 650; color: #567090;
      font-size: 0.77rem; text-transform: uppercase; letter-spacing: 0.03em;
    }
    .mc-kv-value {
      flex: 1; color: #0b1c33;
      font-family: ui-monospace, "SF Mono", Consolas, monospace;
      font-size: 0.80rem; word-break: break-all;
    }

    /* Eval progress bars */
    .mc-eval-row { margin-bottom: 0.65rem; }
    .mc-eval-header {
      display: flex; justify-content: space-between; margin-bottom: 0.3rem;
    }
    .mc-eval-label { font-size: 0.80rem; font-weight: 650; color: #2c4a68; }
    .mc-eval-value { font-size: 0.80rem; font-weight: 750; color: #0b1c33; }
    .mc-eval-track {
      height: 10px; background: #e8f0fa; border-radius: 6px; overflow: hidden;
    }
    .mc-eval-fill {
      height: 100%;
      background: linear-gradient(90deg, #1a5fd4, #5a9cf4);
      border-radius: 6px; transition: width .5s ease;
    }
    .mc-eval-fill-success { background: linear-gradient(90deg, #0f7a3a, #2cc36b); }
    .mc-eval-fill-warning { background: linear-gradient(90deg, #8c4b00, #f0a030); }

    /* Chip groups */
    .mc-chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
    .mc-chip {
      background: #e6effc; color: #1a5fd4;
      font-size: 0.75rem; font-weight: 650;
      border-radius: 20px; padding: 0.22rem 0.7rem;
    }

    /* Chat messages */
    .mc-message-meta {
      font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; margin-bottom: 0.4rem;
    }
    .mc-msg-user { color: #2c5fa8; }
    .mc-msg-asst { color: #1a5fd4; }
    .mc-message-badges { margin-top: 0.5rem; }

    /* Citation cards */
    .mc-source-card {
      background: #f8faff;
      border-radius: 10px;
      padding: 0.85rem 1rem;
      border: 1px solid rgba(26,95,212,.12);
      margin-bottom: 0.55rem;
    }
    .mc-source-top {
      display: flex; justify-content: space-between; align-items: flex-start; gap: 0.5rem;
    }
    .mc-source-title { font-size: 0.84rem; font-weight: 700; color: #0b1c33; flex: 1; }
    .mc-source-meta { font-size: 0.73rem; color: #8aa5c2; margin: 0.25rem 0; }
    .mc-source-excerpt {
      font-size: 0.81rem; color: #2c4a68; line-height: 1.55; margin: 0.35rem 0;
    }
    .mc-source-link a { font-size: 0.78rem; color: #1a5fd4; text-decoration: none; }
    .mc-source-link a:hover { text-decoration: underline; }

    /* Empty states */
    .mc-empty-state {
      text-align: center; padding: 2rem 1rem;
      border: 1.5px dashed rgba(26,95,212,.22);
      border-radius: 12px; background: rgba(26,95,212,.02);
    }
    .mc-empty-title {
      font-size: 0.9rem; font-weight: 700; color: #2c4a68; margin-bottom: 0.4rem;
    }
    .mc-empty-copy { font-size: 0.82rem; color: #8aa5c2; line-height: 1.55; }

    /* Login hero (full-width inline banner) */
    .mc-login-hero {
      background: linear-gradient(135deg, #050e1c 0%, #0a1f3e 35%, #0c308a 70%, #1a5fd4 100%);
      border-radius: 16px;
      padding: 3.2rem 2rem 3rem;
      margin-bottom: 1.8rem;
      text-align: center;
      box-shadow: 0 8px 32px rgba(8,28,80,.28), inset 0 1px 0 rgba(255,255,255,.08);
    }
    .mc-login-eyebrow {
      font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.18em; color: rgba(255,255,255,.5);
      margin-bottom: 0.8rem;
    }
    .mc-login-title {
      font-size: 3rem; font-weight: 900; color: #ffffff;
      letter-spacing: -0.05em; line-height: 1.05;
      margin-bottom: 0.7rem;
    }
    .mc-login-subtitle {
      font-size: 1.0rem; color: rgba(255,255,255,.68); line-height: 1.55;
      max-width: 560px; margin: 0 auto;
    }

    </style>
    """)
