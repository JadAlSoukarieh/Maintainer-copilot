import type { CSSProperties, FormEvent, KeyboardEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./styles.css";

// ── Types ──────────────────────────────────────────────────────────────────────

type WidgetConfig = {
  public_widget_id: string;
  greeting: string;
  theme: { primaryColor: string; position: "bottom-right" | "bottom-left" | "inline" };
  enabled_tools: string[];
  default_use_llm: boolean;
};

type ToolName =
  | "classify_issue"
  | "extract_entities"
  | "summarize_thread"
  | "rag_answer"
  | "write_memory"
  | "none";

type Citation = {
  chunk_id: string;
  title?: string;
  source_type?: string;
  url?: string;
  text_excerpt?: string;
};

type Entity = { text: string; type: string };

type ToolResult = {
  label?: string;
  confidence?: number;
  top_probabilities?: Record<string, number>;
  model_name?: string;
  entities?: Entity[];
  bullets?: string[];
  summary?: string;
  answer?: string;
  citations?: Citation[];
  memory_id?: string;
  error?: { code: string; message?: string };
};

type SSEPhase = "idle" | "thinking" | "streaming" | "done" | "error";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  tool?: ToolName;
  tool_result?: ToolResult;
  mode?: string;
  phase?: SSEPhase;
  statusText?: string;
  timestamp: Date;
};

type IssueContext = { title: string; body: string };

type ChatResponse = {
  conversation_id: string;
  message: string;
  mode: string;
  selected_tool: ToolName;
  tool_result: ToolResult;
  fallback_reason?: string | null;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: WidgetConfig = {
  public_widget_id: "demo-widget",
  greeting: "Ask me anything about Node.js — docs, issues, or triage help.",
  theme: { primaryColor: "#1f6feb", position: "bottom-right" },
  enabled_tools: ["classify_issue", "extract_entities", "summarize_thread", "rag_answer"],
  default_use_llm: true,
};

const TOOL_META: Record<ToolName, { label: string; icon: string; color: string }> = {
  classify_issue:   { label: "Classify",     icon: "🏷",  color: "#cf222e" },
  extract_entities: { label: "Entities",     icon: "🔍", color: "#953800" },
  summarize_thread: { label: "Summarize",    icon: "📝", color: "#8250df" },
  rag_answer:       { label: "Docs Search",  icon: "📚", color: "#1a7f37" },
  write_memory:     { label: "Memory",       icon: "💾", color: "#0969da" },
  none:             { label: "Processing",   icon: "⚙️",  color: "#6e7781" },
};

const LABEL_COLORS: Record<string, string> = {
  bug: "#cf222e",
  question: "#0969da",
  enhancement: "#1a7f37",
  documentation: "#8250df",
  other: "#6e7781",
};

const ENTITY_COLORS: Record<string, string> = {
  VERSION: "#0550ae",
  FILE_PATH: "#1a7f37",
  URL: "#8250df",
  FLAG: "#953800",
  FUNCTION: "#0969da",
  MODULE: "#6e7781",
  ERROR_CODE: "#cf222e",
};

const SUGGESTED_PROMPTS = [
  "Classify this Node.js issue",
  "How do I debug a memory leak in https.request?",
  "Summarize this thread",
  "Extract entities from this issue text",
];

// ── SSE Client ────────────────────────────────────────────────────────────────

async function streamChat(
  apiBase: string,
  payload: object,
  onStatus: (s: { type: string; tool?: string; text: string }) => void,
  onToken: (text: string) => void,
  onDone: (r: ChatResponse) => void,
  onError: (msg: string) => void,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${apiBase}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    onError("Couldn't reach the API — check it's running.");
    return;
  }

  if (!res.ok) {
    onError(`API returned ${res.status}.`);
    return;
  }

  const reader = res.body!.getReader();
  const dec = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });

    const parts = buf.split("\n\n");
    buf = parts.pop() ?? "";

    for (const part of parts) {
      const lines = part.split("\n");
      let evt = "message";
      let dat = "";
      for (const l of lines) {
        if (l.startsWith("event: ")) evt = l.slice(7).trim();
        if (l.startsWith("data: ")) dat = l.slice(6).trim();
      }
      if (!dat) continue;
      try {
        const parsed = JSON.parse(dat);
        if (evt === "status") onStatus(parsed);
        else if (evt === "token") onToken(parsed.text as string);
        else if (evt === "done") onDone(parsed as ChatResponse);
        else if (evt === "error") onError((parsed as { message: string }).message || "Stream error");
      } catch {
        // ignore parse errors on partial chunks
      }
    }
  }
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function IconChat() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M8 10h8M8 14h5M5 3h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-4l-4 4-4-4H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconClose({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" aria-hidden>
      <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function IconSend() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden>
      <path d="M16 9H2M9 2l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconBot() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="3" y="9" width="18" height="12" rx="3" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="9" cy="15" r="1.5" fill="currentColor" />
      <circle cx="15" cy="15" r="1.5" fill="currentColor" />
      <path d="M12 3v6M9 3h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function IconContext() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function IconWarn() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden style={{ flexShrink: 0 }}>
      <path d="M12 9v4M12 17h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
        stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconCopy() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

// ── Tool Result Cards ─────────────────────────────────────────────────────────

function ClassifyCard({ result }: { result: ToolResult }) {
  const label = result.label || "unknown";
  const conf = result.confidence ?? 0;
  const color = LABEL_COLORS[label.toLowerCase()] ?? "#6e7781";
  const probs = result.top_probabilities ?? {};
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]);

  return (
    <div className="mcw-card mcw-card-classify">
      <div className="mcw-classify-header">
        <span className="mcw-label-badge" style={{ background: color + "18", color, borderColor: color + "40" }}>
          {label.charAt(0).toUpperCase() + label.slice(1)}
        </span>
        <span className="mcw-classify-conf">{(conf * 100).toFixed(1)}% confidence</span>
      </div>
      {sorted.length > 1 && (
        <div className="mcw-classify-bars">
          {sorted.map(([lbl, prob]) => (
            <div key={lbl} className="mcw-bar-row">
              <span className="mcw-bar-label">{lbl}</span>
              <div className="mcw-bar-track">
                <div
                  className="mcw-bar-fill"
                  style={{
                    width: `${(prob * 100).toFixed(1)}%`,
                    background: LABEL_COLORS[lbl.toLowerCase()] ?? "#6e7781",
                  }}
                />
              </div>
              <span className="mcw-bar-pct">{(prob * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}
      {result.model_name && (
        <div className="mcw-card-meta">Model: {result.model_name}</div>
      )}
    </div>
  );
}

function EntitiesCard({ result }: { result: ToolResult }) {
  const entities = result.entities ?? [];
  if (entities.length === 0) return null;
  return (
    <div className="mcw-card mcw-card-entities">
      <div className="mcw-entities-title">Extracted entities</div>
      <div className="mcw-entity-chips">
        {entities.map((e, i) => {
          const color = ENTITY_COLORS[e.type] ?? "#6e7781";
          return (
            <span
              key={i}
              className="mcw-entity-chip"
              style={{ background: color + "12", color, borderColor: color + "35" }}
              title={e.type}
            >
              {e.text}
              <span className="mcw-entity-type">{e.type}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

function SummaryCard({ result }: { result: ToolResult }) {
  const bullets = result.bullets ?? [];
  if (bullets.length === 0) return null;
  return (
    <div className="mcw-card mcw-card-summary">
      <div className="mcw-summary-title">Summary</div>
      <ul className="mcw-bullets">
        {bullets.map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>
    </div>
  );
}

function CitationsCard({ citations }: { citations: Citation[] }) {
  const visible = citations.slice(0, 3);
  const extra = citations.length - 3;
  return (
    <div className="mcw-citations">
      <div className="mcw-citations-label">Sources</div>
      {visible.map((c) => (
        <div key={c.chunk_id} className="mcw-citation-card">
          <div className="mcw-citation-head">
            <span className={`mcw-source-pill mcw-source-${c.source_type === "resolved_issue" ? "issue" : "doc"}`}>
              {c.source_type === "resolved_issue" ? "Issue" : "Docs"}
            </span>
            <div className="mcw-citation-title">
              {c.url
                ? <a href={c.url} target="_blank" rel="noreferrer">{c.title || c.chunk_id}</a>
                : <span>{c.title || c.chunk_id}</span>}
            </div>
          </div>
          {c.text_excerpt && (
            <div className="mcw-citation-excerpt">{c.text_excerpt}</div>
          )}
        </div>
      ))}
      {extra > 0 && <div className="mcw-citation-more">+{extra} more sources</div>}
    </div>
  );
}

function ToolResultCard({ tool, result }: { tool: ToolName; result?: ToolResult }) {
  if (!result) return null;
  if (result.error) return null;
  if (tool === "classify_issue" && result.label) return <ClassifyCard result={result} />;
  if (tool === "extract_entities" && result.entities?.length) return <EntitiesCard result={result} />;
  if (tool === "summarize_thread" && result.bullets?.length) return <SummaryCard result={result} />;
  if (tool === "rag_answer" && result.citations?.length) return <CitationsCard citations={result.citations} />;
  return null;
}

// ── CopyButton ────────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <button className="mcw-copy-btn" onClick={copy} aria-label="Copy message">
      {copied ? <IconCheck /> : <IconCopy />}
    </button>
  );
}

// ── TypingIndicator ───────────────────────────────────────────────────────────

function TypingIndicator({ text }: { text: string }) {
  return (
    <div className="mcw-row mcw-row-asst">
      <div className="mcw-avatar" aria-hidden>MC</div>
      <div className="mcw-typing-wrap">
        <div className="mcw-typing" aria-label="Thinking…">
          <span className="mcw-dot" />
          <span className="mcw-dot" />
          <span className="mcw-dot" />
        </div>
        <span className="mcw-typing-status">{text}</span>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const widgetId = params.get("widget_id") || "demo-widget";
  const apiBaseUrl = (params.get("api_base_url") || "http://localhost:8000").replace(/\/$/, "");
  const autoOpen = params.get("auto_open") === "true" || params.get("auto_open") === "1";

  const [config, setConfig] = useState<WidgetConfig>(DEFAULT_CONFIG);
  const [expanded, setExpanded] = useState(autoOpen);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [issueCtx, setIssueCtx] = useState<IssueContext>({ title: "", body: "" });
  const [postMsgText, setPostMsgText] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiBaseUrl}/widgets/${encodeURIComponent(widgetId)}/config`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((p: WidgetConfig) => { if (active) setConfig(p); })
      .catch(() => {});
    return () => { active = false; };
  }, [apiBaseUrl, widgetId]);

  useEffect(() => {
    window.parent.postMessage(
      { type: "maintcopilot:resize", expanded, height: expanded ? 660 : 76 },
      "*",
    );
  }, [expanded]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming, streamStatus]);

  useEffect(() => {
    function handle(e: MessageEvent) {
      if (!e.data || typeof e.data !== "object") return;
      const d = e.data as { type?: string; text?: string };
      if (d.type === "maintcopilot:open") setExpanded(true);
      if (d.type === "maintcopilot:send" && typeof d.text === "string") {
        setExpanded(true);
        setPostMsgText(d.text);
      }
    }
    window.addEventListener("message", handle);
    return () => window.removeEventListener("message", handle);
  }, []);

  useEffect(() => {
    if (postMsgText === null) return;
    const text = postMsgText;
    setPostMsgText(null);
    sendMessage(null, text);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postMsgText]);

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  }, []);

  async function sendMessage(event: FormEvent | null, overrideText?: string) {
    event?.preventDefault();
    const message = (overrideText ?? input).trim();
    if (!message || streaming) return;
    if (!overrideText) {
      setInput("");
      if (textareaRef.current) textareaRef.current.style.height = "auto";
    }
    setError(null);
    setStreaming(true);
    setStreamStatus("Analyzing your message…");

    const userMsgId = uid();
    const asstMsgId = uid();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", text: message, timestamp: new Date() },
    ]);

    const context = issueCtx.title || issueCtx.body
      ? { issue_title: issueCtx.title || undefined, issue_body: issueCtx.body || undefined }
      : undefined;

    const payload = {
      conversation_id: conversationId,
      message,
      use_llm: config.default_use_llm,
      ...(context ? { context } : {}),
    };

    setMessages((prev) => [
      ...prev,
      {
        id: asstMsgId,
        role: "assistant",
        text: "",
        phase: "thinking" as SSEPhase,
        timestamp: new Date(),
      },
    ]);

    await streamChat(
      apiBaseUrl,
      payload,
      (status) => {
        setStreamStatus(status.text);
        if (status.type === "tool") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstMsgId
                ? { ...m, tool: status.tool as ToolName, phase: "streaming" }
                : m,
            ),
          );
        }
      },
      (token) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId ? { ...m, text: m.text + token, phase: "streaming" } : m,
          ),
        );
      },
      (result) => {
        setConversationId(result.conversation_id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? {
                  ...m,
                  text: result.message,
                  tool: result.selected_tool,
                  tool_result: result.tool_result,
                  mode: result.mode,
                  statusText: result.fallback_reason ?? undefined,
                  phase: "done",
                }
              : m,
          ),
        );
        setStreaming(false);
        setStreamStatus("");
      },
      (errMsg) => {
        setMessages((prev) => prev.filter((m) => m.id !== asstMsgId));
        setError(errMsg);
        setStreaming(false);
        setStreamStatus("");
      },
    );
  }

  function handleSuggestedPrompt(text: string) {
    sendMessage(null, text);
  }

  function clearConversation() {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setIssueCtx({ title: "", body: "" });
    setShowContext(false);
  }

  const pos = config.theme.position === "bottom-left" ? "mcw-left" : "mcw-right";
  const cssVars = { "--mcw-primary": config.theme.primaryColor } as CSSProperties;
  const visibleTools = config.enabled_tools.slice(0, 4).map((t) => TOOL_META[t as ToolName]?.label || t);

  // ── Collapsed bubble ──────────────────────────────────────────────────────

  if (!expanded) {
    return (
      <button
        className={`mcw-bubble ${pos}`}
        style={cssVars}
        onClick={() => setExpanded(true)}
        aria-label="Open Maintainer's Copilot"
      >
        <IconChat />
        <span className="mcw-bubble-ring" />
      </button>
    );
  }

  // ── Expanded panel ────────────────────────────────────────────────────────

  const hasContext = issueCtx.title.trim() || issueCtx.body.trim();

  return (
    <section className={`mcw-panel ${pos}`} style={cssVars} role="dialog" aria-label="Maintainer's Copilot chat">

      {/* Header */}
      <header className="mcw-header">
        <div className="mcw-header-avatar"><IconBot /></div>
        <div className="mcw-header-info">
          <div className="mcw-header-name">Maintainer's Copilot</div>
          <div className="mcw-header-status">
            <span className="mcw-status-dot" aria-hidden />
            Online · Node.js assistant
          </div>
        </div>
        <div className="mcw-header-actions">
          {messages.length > 0 && (
            <button className="mcw-hdr-btn" onClick={clearConversation} aria-label="Clear conversation" title="Clear conversation">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden>
                <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          )}
          <button className="mcw-hdr-btn mcw-hdr-close" onClick={() => setExpanded(false)} aria-label="Close chat">
            <IconClose size={12} />
          </button>
        </div>
      </header>

      {/* Empty state */}
      {messages.length === 0 && (
        <div className="mcw-empty">
          <div className="mcw-empty-icon" aria-hidden>🤖</div>
          <p className="mcw-empty-greeting">{config.greeting}</p>
          {visibleTools.length > 0 && (
            <div className="mcw-caps">
              {visibleTools.map((label) => (
                <span key={label} className="mcw-cap">{label}</span>
              ))}
            </div>
          )}
          <div className="mcw-suggestions">
            {SUGGESTED_PROMPTS.map((p) => (
              <button key={p} className="mcw-suggestion" onClick={() => handleSuggestedPrompt(p)}>
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="mcw-messages" role="log" aria-live="polite">
        {messages.map((msg) => (
          <div key={msg.id} className={`mcw-row mcw-row-${msg.role}`}>
            {msg.role === "assistant" && (
              <div className="mcw-avatar" aria-hidden>MC</div>
            )}
            <div className="mcw-bubble-wrap">
              {msg.role === "assistant" && msg.tool && msg.tool !== "none" && (
                <div
                  className="mcw-tool-badge"
                  style={{
                    color: TOOL_META[msg.tool]?.color ?? "#6e7781",
                    background: (TOOL_META[msg.tool]?.color ?? "#6e7781") + "12",
                    borderColor: (TOOL_META[msg.tool]?.color ?? "#6e7781") + "30",
                  }}
                >
                  <span>{TOOL_META[msg.tool]?.icon}</span>
                  <span>{TOOL_META[msg.tool]?.label}</span>
                </div>
              )}
              {msg.role === "assistant" && msg.mode === "deterministic_fallback" && (
                <div className="mcw-tool-badge mcw-fallback-badge">
                  <span>Fallback</span>
                  <span>Deterministic fallback</span>
                </div>
              )}
              <div className="mcw-msg-bubble">
                {msg.role === "assistant" && msg.phase === "thinking" && (
                  <div className="mcw-inline-thinking">
                    <span className="mcw-dot" /><span className="mcw-dot" /><span className="mcw-dot" />
                  </div>
                )}
                {msg.text && (
                  <p>
                    {msg.text}
                    {msg.phase === "streaming" && <span className="mcw-cursor" aria-hidden />}
                  </p>
                )}
                {msg.phase === "done" && msg.tool && msg.tool_result && (
                  <ToolResultCard tool={msg.tool} result={msg.tool_result} />
                )}
                {msg.role === "assistant" && msg.statusText && (
                  <div className="mcw-card-meta">Fallback reason: {msg.statusText}</div>
                )}
              </div>
              <div className="mcw-msg-footer">
                <span className="mcw-msg-time">{fmtTime(msg.timestamp)}</span>
                {msg.role === "assistant" && msg.phase === "done" && msg.text && (
                  <CopyButton text={msg.text} />
                )}
              </div>
            </div>
          </div>
        ))}

        {streaming && streamStatus && messages[messages.length - 1]?.phase === "thinking" && (
          <div className="mcw-stream-status">{streamStatus}</div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error bar */}
      {error && (
        <div className="mcw-error-bar" role="alert">
          <IconWarn />
          <span>{error}</span>
          <button className="mcw-error-dismiss" onClick={() => setError(null)} aria-label="Dismiss error">
            <IconClose size={10} />
          </button>
        </div>
      )}

      {/* Issue context panel */}
      {showContext && (
        <div className="mcw-context-panel">
          <div className="mcw-context-header">
            <span>Issue context</span>
            {hasContext && <span className="mcw-context-active-dot" title="Context attached" />}
          </div>
          <input
            className="mcw-context-input"
            placeholder="Issue title"
            value={issueCtx.title}
            onChange={(e) => setIssueCtx((c) => ({ ...c, title: e.target.value }))}
          />
          <textarea
            className="mcw-context-textarea"
            placeholder="Issue body (paste here)"
            value={issueCtx.body}
            rows={4}
            onChange={(e) => setIssueCtx((c) => ({ ...c, body: e.target.value }))}
          />
          {hasContext && (
            <button
              className="mcw-context-clear"
              onClick={() => setIssueCtx({ title: "", body: "" })}
            >
              Clear context
            </button>
          )}
        </div>
      )}

      {/* Input form */}
      <form className="mcw-form" onSubmit={sendMessage}>
        <button
          type="button"
          className={`mcw-ctx-toggle ${showContext ? "mcw-ctx-toggle--active" : ""} ${hasContext ? "mcw-ctx-toggle--has-ctx" : ""}`}
          onClick={() => setShowContext((v) => !v)}
          aria-label="Toggle issue context"
          title="Attach issue context"
        >
          <IconContext />
          {hasContext && <span className="mcw-ctx-dot" />}
        </button>
        <div className="mcw-textarea-wrap">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Node.js…"
            disabled={streaming}
            rows={1}
            aria-label="Message input"
          />
        </div>
        <button
          className="mcw-send-btn"
          type="submit"
          disabled={streaming || !input.trim()}
          aria-label="Send"
        >
          {streaming
            ? <span className="mcw-send-spinner" aria-hidden />
            : <IconSend />}
        </button>
      </form>
    </section>
  );
}
