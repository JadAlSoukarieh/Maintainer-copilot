import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import "./styles.css";

type WidgetConfig = {
  public_widget_id: string;
  greeting: string;
  theme: {
    primaryColor: string;
    position: "bottom-right" | "bottom-left" | "inline";
  };
  enabled_tools: string[];
};

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  selectedTool?: string;
  mode?: string;
  citations?: Citation[];
};

type Citation = {
  chunk_id: string;
  title?: string;
  source_type?: string;
  url?: string;
  text_excerpt?: string;
};

type ChatResponse = {
  conversation_id: string;
  message: string;
  mode: "llm_tool_calling" | "deterministic_fallback";
  selected_tool: string;
  tool_result?: {
    citations?: Citation[];
    [key: string]: unknown;
  };
};

const DEFAULT_CONFIG: WidgetConfig = {
  public_widget_id: "demo-widget",
  greeting: "Ask Maintainer's Copilot about this project.",
  theme: {
    primaryColor: "#1f6feb",
    position: "bottom-right",
  },
  enabled_tools: ["classify_issue", "extract_entities", "summarize_thread", "rag_answer", "write_memory"],
};

export default function App() {
  const params = useMemo(() => new URLSearchParams(window.location.search), []);
  const widgetId = params.get("widget_id") || "demo-widget";
  const apiBaseUrl = (params.get("api_base_url") || "http://localhost:8000").replace(/\/$/, "");
  const [config, setConfig] = useState<WidgetConfig>(DEFAULT_CONFIG);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`${apiBaseUrl}/widgets/${encodeURIComponent(widgetId)}/config`)
      .then((response) => {
        if (!response.ok) throw new Error("Widget config could not be loaded.");
        return response.json();
      })
      .then((payload: WidgetConfig) => {
        if (active) setConfig(payload);
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message);
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, widgetId]);

  useEffect(() => {
    const height = expanded ? Math.ceil(panelRef.current?.getBoundingClientRect().height || 620) : 92;
    window.parent.postMessage({ type: "maintcopilot:resize", expanded, height }, "*");
  }, [expanded, messages.length, loading, error]);

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;
    setInput("");
    setError(null);
    setLoading(true);
    setMessages((items) => [...items, { role: "user", text: message }]);

    try {
      const response = await fetch(`${apiBaseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          message,
          use_llm: false,
        }),
      });
      if (!response.ok) throw new Error(`Chat request failed (${response.status}).`);
      const payload = (await response.json()) as ChatResponse;
      setConversationId(payload.conversation_id);
      setMessages((items) => [
        ...items,
        {
          role: "assistant",
          text: payload.message,
          selectedTool: payload.selected_tool,
          mode: payload.mode,
          citations: payload.tool_result?.citations || [],
        },
      ]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Chat request failed.");
    } finally {
      setLoading(false);
    }
  }

  const positionClass = config.theme.position === "bottom-left" ? "mcw-left" : "mcw-right";

  if (!expanded) {
    return (
      <button
        className={`mcw-bubble ${positionClass}`}
        style={{ background: config.theme.primaryColor }}
        onClick={() => setExpanded(true)}
        aria-label="Open Maintainer's Copilot"
      >
        MC
      </button>
    );
  }

  return (
    <section className={`mcw-panel ${positionClass}`} ref={panelRef} style={{ "--mcw-primary": config.theme.primaryColor } as CSSProperties}>
      <header className="mcw-header">
        <div>
          <strong>Maintainer&apos;s Copilot</strong>
          <span>{config.public_widget_id}</span>
        </div>
        <button onClick={() => setExpanded(false)} aria-label="Collapse chat">
          -
        </button>
      </header>

      <div className="mcw-greeting">{config.greeting}</div>
      {config.enabled_tools.length > 0 && <div className="mcw-tools">{config.enabled_tools.join(" / ")}</div>}

      <div className="mcw-messages" aria-live="polite">
        {messages.map((message, index) => (
          <article key={`${message.role}-${index}`} className={`mcw-message mcw-${message.role}`}>
            <p>{message.text}</p>
            {message.selectedTool && (
              <small>
                {message.selectedTool} · {message.mode}
              </small>
            )}
            {message.citations && message.citations.length > 0 && (
              <ul>
                {message.citations.slice(0, 3).map((citation) => (
                  <li key={citation.chunk_id}>{citation.title || citation.chunk_id}</li>
                ))}
              </ul>
            )}
          </article>
        ))}
        {loading && <div className="mcw-loading">Thinking...</div>}
        {error && <div className="mcw-error">{error}</div>}
      </div>

      <form className="mcw-form" onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Ask about docs, issues, or triage"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
