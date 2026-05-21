# Maintainer's Copilot Streamlit UI Style Guide

This guide is for the internal Streamlit console only. It does not change backend behavior, and it should not be used to justify API or data-model churn.

## Intent

The internal app should feel like a premium AI operations console for maintainers:

- technical
- composed
- evidence-first
- internally trustworthy

It is not a marketing page and it is not a generic Streamlit dashboard. The UI should signal that this is where maintainers triage issues, inspect grounded evidence, manage widget configuration, and review eval health.

## Audience

- internal maintainers
- admins
- demo reviewers

These users are comfortable with structured information, but they still need hierarchy, spacing, and strong visual grouping.

## Aesthetic direction

Use a single coherent direction:

- light slate / blue-tinted workspace background
- white elevated surfaces
- deep navy primary text
- one strong accent: `#1f6feb`
- restrained status colors:
  - success: green
  - warning: amber
  - danger: red
- monospace styling only for technical identifiers, commands, and chunk/request IDs

The signature gesture is a controlled "operations console" feel:

- strong top header
- compact metric cards
- clean card stacks
- minimal chrome
- no floating toy-like pills

## Layout model

The app has exactly two shells:

1. Login / welcome shell
2. Authenticated internal console

Do not render the console behind the login form.

### Login shell

- centered hero
- short subtitle
- three feature cards
- one contained login card
- advanced API settings hidden in an expander
- no sidebar
- no tabs

### Console shell

- compact sidebar for identity, health, mode, conversation, and links
- top header with title + subtitle
- one row of four equal status cards
- six tabs in this order:
  1. Chat
  2. Issue Tools
  3. Memory
  4. Widget Admin
  5. Observability
  6. Evals

## Spacing and sizing

Use a consistent compact spacing scale:

- `8px` micro gaps
- `12px` inner control rhythm
- `16px` card padding minimum
- `20px` to `24px` between major sections

Avoid:

- giant blank vertical gaps
- overly tall empty cards
- clipped section headers
- stacked expanders as the main layout

## Core CSS classes

These classes should remain the design vocabulary for future passes:

- `.mc-shell`
- `.mc-login-page`
- `.mc-hero`
- `.mc-login-card`
- `.mc-feature-grid`
- `.mc-feature-card`
- `.mc-card`
- `.mc-dashboard-grid`
- `.mc-metric-card`
- `.mc-badge`
- `.mc-badge-success`
- `.mc-badge-warning`
- `.mc-badge-danger`
- `.mc-badge-muted`
- `.mc-message-user`
- `.mc-message-assistant`
- `.mc-source-card`
- `.mc-empty-state`
- `.mc-command-card`

## Content rules

### Chat

- answer text first
- tool/mode as compact badges underneath
- citations in a dedicated "Sources" section
- request IDs and trace IDs inside technical details
- never default to raw JSON

### Issue Tools

- one issue input surface at the top
- four action surfaces in one row
- structured result rendering below
- classification should read like a decision surface, not raw payload

### Memory

- explicit memory policy notice first
- show redacted text clearly
- label text/vector fallback honestly
- empty states should explain why nothing is present

### Widget Admin

- split list, form, and snippet into separate surfaces
- keep embed code copy-friendly
- allowed origins must stay readable

### Observability

- clearly say this is lightweight recent events, not full distributed tracing
- render commands and request IDs cleanly
- metadata must be readable without turning into a wall of JSON

### Evals

- show selected systems and gates prominently
- make the selected classifier and selected RAG pipeline obvious
- tables should support a demo conversation without needing explanation

## Accessibility

- keep contrast solid on badges and metadata
- do not use tiny grey text for primary information
- preserve clear labels for forms
- do not rely on color alone for meaning

## Screenshot-driven TODOs for future UI passes

- tighten the Chat composer and history rhythm after backend work stabilizes
- improve table styling if Streamlit offers better native theming hooks later
- consider a stronger dark/light contrast treatment for the sidebar if it remains visually flat
- verify the console at `1440px`, `1280px`, and `1024px`
- verify that long chunk IDs and request IDs wrap cleanly without breaking cards
