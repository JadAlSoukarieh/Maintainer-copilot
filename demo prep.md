# Demo Prep

This file is the plain-English walkthrough for the Week 7 Maintainer's Copilot demo.

## 1. What the app is

Maintainer's Copilot is a local maintainer assistant for Node.js issue triage.

It has four main surfaces:

- The backend API orchestrator in [services/api/maintcopilot_api/main.py](services/api/maintcopilot_api/main.py)
- The model server in [services/model-server/maintcopilot_model_server/main.py](services/model-server/maintcopilot_model_server/main.py)
- The internal Streamlit console in [services/chatbot/app.py](services/chatbot/app.py)
- The public/demo React widget in [services/widget/src/App.tsx](services/widget/src/App.tsx)

## 2. End-to-end app workflow from A to Z

1. A user types a message in Streamlit or in the widget.
2. The UI sends the request to `POST /chat` or `POST /chat/stream`.
3. The API receives the request in [services/api/maintcopilot_api/api/routes/chat.py](services/api/maintcopilot_api/api/routes/chat.py).
4. The router hands the request to [services/api/maintcopilot_api/services/chat_service.py](services/api/maintcopilot_api/services/chat_service.py).
5. The chat service decides whether to use Claude first or deterministic fallback.
6. If `use_llm` is omitted, the chat service defaults to `API_CHAT_LLM_ENABLED`.
7. If LLM mode is on, the API asks [services/api/maintcopilot_api/services/llm_chat_service.py](services/api/maintcopilot_api/services/llm_chat_service.py) to pick one tool.
8. Claude is not answering from memory alone. It is choosing one allowed backend tool such as `classify_issue`, `extract_entities`, `summarize_thread`, `rag_answer`, or `write_memory`.
9. The chosen tool is executed through [services/api/maintcopilot_api/services/tools.py](services/api/maintcopilot_api/services/tools.py).
10. If the tool is classifier, NER, or summarization, the API calls the model server.
11. If the tool is RAG, the API runs local retrieval and answer synthesis.
12. If the tool is memory write, the API only writes long-term memory when the user explicitly asks to remember something.
13. After the tool returns, Claude can produce the final user-facing answer.
14. If Claude is unavailable and fallback is allowed, the system still runs the same tool path and responds in `deterministic_fallback` mode.
15. The response returns with `selected_tool`, `mode`, citations if relevant, and `fallback_reason` if a fallback happened.

## 3. How the model server fits in

The API is the orchestrator. The model server is the inference worker.

Relevant files:

- [services/api/maintcopilot_api/services/tools.py](services/api/maintcopilot_api/services/tools.py)
- [services/api/maintcopilot_api/infra/model_client.py](services/api/maintcopilot_api/infra/model_client.py)
- [services/model-server/maintcopilot_model_server/main.py](services/model-server/maintcopilot_model_server/main.py)

The model server exposes:

- `/classify` for issue labels
- `/ner` for code-shaped entity extraction
- `/summarize` for extractive summaries

## 4. How chat mode works now

The primary runtime rule is simple:

- If `API_CHAT_LLM_ENABLED=true`, Claude tool-calling is the first choice.
- If the request explicitly sends `use_llm=false`, the API skips Claude and uses deterministic routing.
- If Claude fails and fallback is allowed, the API returns `mode="deterministic_fallback"`.
- If fallback is not allowed, the API returns a clean error instead of pretending Claude worked.

Relevant files:

- [services/api/maintcopilot_api/domain/chat.py](services/api/maintcopilot_api/domain/chat.py)
- [services/api/maintcopilot_api/services/chat_service.py](services/api/maintcopilot_api/services/chat_service.py)
- [services/api/maintcopilot_api/services/llm_chat_service.py](services/api/maintcopilot_api/services/llm_chat_service.py)

## 5. RAG from A to Z

RAG means retrieval-augmented generation. In this project it is mostly local retrieval plus grounded answer synthesis.

### Data sources

The corpus is built from:

- Local Node.js docs
- Resolved Node.js issues
- Optional issue-comment samples

Relevant files:

- [scripts/build_rag_corpus.py](scripts/build_rag_corpus.py)
- [services/api/maintcopilot_api/services/rag/corpus.py](services/api/maintcopilot_api/services/rag/corpus.py)
- [scripts/fetch_rag_issue_comments.py](scripts/fetch_rag_issue_comments.py)

### Retrieval flow

1. User asks a docs or debugging question.
2. The chat service or `/rag/answer` route forwards it to [services/api/maintcopilot_api/services/rag/rag_service.py](services/api/maintcopilot_api/services/rag/rag_service.py).
3. The query may be rewritten by [services/api/maintcopilot_api/services/rag/query_transform.py](services/api/maintcopilot_api/services/rag/query_transform.py).
4. The retriever is selected in `rag_service`.
5. Retrieval can be sparse, dense, hybrid, or reranked.
6. Metadata boost can adjust scores after retrieval.
7. The service builds an extractive grounded answer from the best evidence chunks.
8. The response returns citations, rewritten query, intent, retriever diagnostics, and fallback information if needed.

### Retrieval modes in plain English

- Sparse: keyword matching with TF-IDF
- Dense: semantic search using MiniLM embeddings
- Hybrid: mixes sparse and dense scores
- Reranked: gets candidates first, then re-sorts them with a cross-encoder

Relevant files:

- [services/api/maintcopilot_api/services/rag/retrieval.py](services/api/maintcopilot_api/services/rag/retrieval.py)
- [services/api/maintcopilot_api/services/rag/rag_service.py](services/api/maintcopilot_api/services/rag/rag_service.py)

## 6. How query rewrite works

Rewrite is deterministic. It does not call Claude.

In plain English:

- It looks for common Node.js patterns like `https.request`, `memory leak`, `stream.pipeline`, `fs.readFile`, `tls`, `dns`, and `ECONNRESET`.
- It expands the query with extra helpful terms.
- It predicts an intent such as `docs`, `debug`, `memory`, or `network`.
- It can suggest whether docs or resolved issues are more likely to help.

Example:

- User asks: "How do I debug a memory leak in https request?"
- Rewrite expands the query with related words like `http`, `https`, `request`, `clientrequest`, `memory`, `heap`, `allocation`, and `gc`.

Relevant file:

- [services/api/maintcopilot_api/services/rag/query_transform.py](services/api/maintcopilot_api/services/rag/query_transform.py)

## 7. How rerank works

Rerank is a second-pass sort, not the first retrieval step.

In plain English:

1. The system first fetches a wider set of candidates with hybrid retrieval.
2. Then it compares the user query against each candidate chunk more carefully with a local cross-encoder.
3. It gives each candidate a better relevance score.
4. It reorders the candidates and keeps the strongest ones at the top.

Why this matters:

- Sparse is good for exact keywords.
- Dense is good for semantic similarity.
- Rerank is good at deciding which of the already-retrieved chunks is actually the best evidence.

Relevant file:

- [services/api/maintcopilot_api/services/rag/retrieval.py](services/api/maintcopilot_api/services/rag/retrieval.py)

## 8. How answer generation works in RAG

This project does not let Claude freely invent answers for the default RAG eval path.

The local RAG answer path:

- retrieves chunks
- extracts the strongest evidence sentences
- writes a grounded summary
- returns citations

Relevant file:

- [services/api/maintcopilot_api/services/rag/rag_service.py](services/api/maintcopilot_api/services/rag/rag_service.py)

That is why the RAG evals stay reproducible and do not depend on the external Claude API.

## 9. How Claude fits into chat

Claude is used as a tool-calling orchestrator.

That means:

- Claude chooses which backend tool should run.
- Claude can write the final natural-language answer after the tool runs.
- Claude does not replace the model server.
- Claude does not replace the local RAG retrieval stack.

Relevant file:

- [services/api/maintcopilot_api/services/llm_chat_service.py](services/api/maintcopilot_api/services/llm_chat_service.py)

## 10. How deterministic fallback works

The deterministic router is a safe backup path.

It uses keyword rules in:

- [services/api/maintcopilot_api/services/tool_router.py](services/api/maintcopilot_api/services/tool_router.py)

Fallback reasons now include:

- `llm_auth_failed`
- `llm_timeout`
- `llm_missing_key`
- `llm_unavailable`
- `llm_disabled`

This is useful because the user can clearly see whether the app used Claude or had to fall back.

## 11. How key resolution works

The Anthropic key resolution rules are:

- If `API_REQUIRE_VAULT=true`, prefer Vault and fail cleanly if the Vault key is missing or still placeholder.
- If `API_REQUIRE_VAULT=false` and env fallback is allowed, use `ANTHROPIC_API_KEY` from the environment.
- Never silently use an empty key.
- Never print the key value.

Relevant files:

- [services/api/maintcopilot_api/infra/anthropic_client.py](services/api/maintcopilot_api/infra/anthropic_client.py)
- [services/api/maintcopilot_api/infra/vault.py](services/api/maintcopilot_api/infra/vault.py)
- [services/api/maintcopilot_api/infra/config.py](services/api/maintcopilot_api/infra/config.py)
- [scripts/check_anthropic_config.py](scripts/check_anthropic_config.py)

## 12. How memory works

There are two memory layers.

Short-term memory:

- stores recent chat events
- uses Redis normally
- can use in-memory fallback for dev/test only

Long-term memory:

- is explicit-only
- is only written when the user clearly asks to remember something
- is stored in Postgres
- can use pgvector embeddings for semantic search

Relevant files:

- [services/api/maintcopilot_api/services/short_term_memory.py](services/api/maintcopilot_api/services/short_term_memory.py)
- [services/api/maintcopilot_api/services/memory_service.py](services/api/maintcopilot_api/services/memory_service.py)
- [services/api/maintcopilot_api/repositories/memory_repository.py](services/api/maintcopilot_api/repositories/memory_repository.py)
- [services/api/alembic/versions/0003_memory_pgvector.py](services/api/alembic/versions/0003_memory_pgvector.py)
- [services/api/alembic/versions/0005_memory_pgvector_ann_index.py](services/api/alembic/versions/0005_memory_pgvector_ann_index.py)

## 13. How the two UIs are different

Streamlit:

- internal/admin console
- good for demoing many features in one place
- toggles between Claude and deterministic mode

Widget:

- public/demo embedded surface
- fetches widget config from the backend
- now respects backend `default_use_llm`
- shows fallback status if the backend had to drop to deterministic mode

Relevant files:

- [services/chatbot/app.py](services/chatbot/app.py)
- [services/chatbot/session_state.py](services/chatbot/session_state.py)
- [services/widget/src/App.tsx](services/widget/src/App.tsx)
- [services/api/maintcopilot_api/api/routes/widgets.py](services/api/maintcopilot_api/api/routes/widgets.py)
- [services/api/maintcopilot_api/services/widget_service.py](services/api/maintcopilot_api/services/widget_service.py)

## 14. What to say about security

The honest security story is:

- Auth exists and works.
- Vault integration exists and is validated.
- Widget origins are allowlisted.
- Secrets are redacted from logs and reports.
- Rate limiting exists for project scope.
- This is not claiming full production hardening yet.

Relevant files:

- [services/api/maintcopilot_api/api/routes/auth.py](services/api/maintcopilot_api/api/routes/auth.py)
- [services/api/maintcopilot_api/infra/startup.py](services/api/maintcopilot_api/infra/startup.py)
- [services/api/maintcopilot_api/infra/rate_limit.py](services/api/maintcopilot_api/infra/rate_limit.py)
- [services/api/maintcopilot_api/api/routes/widgets.py](services/api/maintcopilot_api/api/routes/widgets.py)

## 15. What to say about observability

Project-scope observability includes:

- request IDs
- trace IDs
- recent event endpoints
- OTEL spans
- Jaeger in Docker

Relevant files:

- [services/api/maintcopilot_api/infra/tracing.py](services/api/maintcopilot_api/infra/tracing.py)
- [services/api/maintcopilot_api/infra/observability.py](services/api/maintcopilot_api/infra/observability.py)
- [services/api/maintcopilot_api/api/routes/observability.py](services/api/maintcopilot_api/api/routes/observability.py)

## 16. Suggested live demo flow

1. Show the Docker stack is up.
2. Open Streamlit.
3. Show that chat mode says Claude tool-calling.
4. Ask a RAG question.
5. Point out the selected tool and citations.
6. Ask a classify question with issue context.
7. Show the model server is used for real inference.
8. Ask an explicit memory write request.
9. Show memory search.
10. Open the widget demo host.
11. Send one question through the widget.
12. Show the backend health/docs pages if needed.

## 17. Twenty likely questions and plain-English answers

1. What is this app doing at a high level?
It helps a maintainer triage issues, search project knowledge, extract entities, summarize threads, and save explicit memories.

2. Is Claude answering everything directly?
No. Claude is mainly the tool-calling orchestrator. The actual work is done by backend tools like the model server and the local RAG service.

3. What happens if Claude fails?
The app falls back to deterministic routing and reports that clearly with `mode="deterministic_fallback"` and a fallback reason.

4. How do you stop fake success when Claude fails?
The backend maps provider failures to explicit reasons like `llm_auth_failed` and does not label fallback as Claude success.

5. Does CI call Claude?
No. CI and unit tests stay deterministic and never depend on live Anthropic calls.

6. What is the real classifier here?
The selected production classifier is the local RoBERTa artifact served by the model server.

7. Why keep the classical baseline?
It is a comparison baseline and a cheap fallback reference, but not the selected primary classifier.

8. Why not use Claude as the primary classifier?
Because RoBERTa wins on the selected quality and cost tradeoff for this task, and Claude adds latency and API cost.

9. What makes the RAG grounded?
The answer is built from retrieved local docs and issue chunks, and the response returns citations.

10. Does rewrite use an LLM?
No. Rewrite is deterministic and local.

11. What does metadata boost mean?
It gives a small ranking bump to chunks that match useful metadata like likely source type or module hints.

12. What does rerank mean in simple terms?
It is a second-pass relevance sort over already-retrieved candidates.

13. Why use hybrid retrieval instead of only dense?
Sparse helps exact terms, dense helps semantics, and hybrid usually gives better recall than either one alone.

14. How do you avoid saving random memory?
Long-term memory is explicit-only. The user has to clearly ask to remember or save something.

15. Where is short-term memory stored?
Redis by default, with an in-memory dev/test fallback when allowed.

16. Where is long-term memory stored?
Postgres, with pgvector support for embedding-based search when available.

17. How do you protect secrets?
`.env.local` is ignored, Vault is supported, and logs/reports redact secret-like values.

18. Why are there two UIs?
Streamlit is for internal/admin workflows. The React widget is the embedded public/demo surface.

19. What is the primary runtime chat mode now?
Claude tool-calling when enabled. Deterministic mode is the backup and the reproducible CI path.

20. What are the honest remaining gaps?
Auth migration cleanup, deeper Vault policy/rotation, full observability operations, broader issue-comment ingestion, widget production delivery polish, and real traffic rate-limit tuning.

## 18. Last-minute file references to keep open during the demo

- [services/api/maintcopilot_api/services/chat_service.py](services/api/maintcopilot_api/services/chat_service.py)
- [services/api/maintcopilot_api/services/llm_chat_service.py](services/api/maintcopilot_api/services/llm_chat_service.py)
- [services/api/maintcopilot_api/infra/anthropic_client.py](services/api/maintcopilot_api/infra/anthropic_client.py)
- [services/api/maintcopilot_api/services/rag/rag_service.py](services/api/maintcopilot_api/services/rag/rag_service.py)
- [services/api/maintcopilot_api/services/rag/query_transform.py](services/api/maintcopilot_api/services/rag/query_transform.py)
- [services/api/maintcopilot_api/services/rag/retrieval.py](services/api/maintcopilot_api/services/rag/retrieval.py)
- [services/chatbot/app.py](services/chatbot/app.py)
- [services/widget/src/App.tsx](services/widget/src/App.tsx)
- [scripts/final_backend_smoke.py](scripts/final_backend_smoke.py)
- [scripts/check_anthropic_config.py](scripts/check_anthropic_config.py)
