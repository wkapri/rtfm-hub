# Roadmap

## Done

- [x] Design docs — overview, architecture, data model, discovery agent, query
  routing. Architecture revised: rtfm-rag consumed as a library (shared process/DB),
  not an HTTP service — see 01-architecture.md's revision note.
- [x] rtfm-rag's three library-readiness changes (all landed in that repo): a
  `document_ids` filter on `VectorStore.search()`, ingestion factored into an
  importable `ingest_pdf()`, and a pluggable `LLMProvider` interface
  (Ollama/OpenAI-compatible/Anthropic).
- [x] Phase 1 backend: shared Postgres (hubapp's schema applied after ragapp's own),
  FastAPI CRUD for products + maintenance log, PDF upload → `ingest_pdf()` →
  link-to-product. Verified live end to end (see commit history).
- [x] Phase 1 frontend: product list/detail views, add/edit modal, maintenance log,
  document linking (upload new PDF or link an already-ingested one). Verified live —
  created products, uploaded a manual, added a maintenance entry, all through the UI.
- [x] Phase 2 — discovery agent: `SearchBackend` interface (Tavily + keyless
  DuckDuckGo fallback), candidate ranking, approval UI, download→verify→ingest→link.
  Verified live against the real Tavily API and caught (then fixed) two real ranking
  problems plus one real safety gap along the way — see
  [03-manual-discovery.md](03-manual-discovery.md)'s Flow section for the
  content-relevance check this added: a candidate titled "Roborock S7" resolved to
  an entirely unrelated PDF (US Sentencing Commission guidelines), which passed the
  content-type/size checks fine since it genuinely was a large real PDF — the title
  and source of a search result don't prove what the URL actually resolves to.
- [x] Smart "Add product": replaced the blank product form with a single
  description field — the discovery agent searches the web, has the LLM extract
  brand/model/category/year from real results, and the user confirms/edits before
  saving. Discovery auto-runs right after a product is created this way. Required
  extending rtfm-rag's `LLMProvider.chat_stream()` with an optional `system_prompt`
  override (it was hardcoded to the RAG manual-Q&A prompt) — see
  [03-manual-discovery.md](03-manual-discovery.md) for the identify flow and the
  context-window truncation bug this surfaced.
- [x] Observability: every identify/discover/ingest request now records a step-by-step
  trace (which search backend ran, what it found, verification results, timings),
  logged server-side and shown in the UI as a collapsible "What happened" panel —
  see [03-manual-discovery.md](03-manual-discovery.md).

**Phase 1 and Phase 2 are done.**

## Phase 1 — inventory, no discovery/routing yet

- [x] Shared Postgres: rtfm-hub's schema (`products`, `product_documents`,
  `maintenance_log`) applied after rtfm-rag's own schema, in the same database.
- [x] FastAPI CRUD for products + maintenance log.
- [x] Manually link a product to an already-ingested rtfm-rag document — proved via
  the upload endpoint (`POST /products/{id}/documents/upload`), which calls
  `ingest_pdf()` directly and links the result; a separate `POST .../documents`
  endpoint links an already-ingested `document_id` without re-uploading.
- [x] Frontend: product list/detail views, add/edit product, maintenance log entries.

## Phase 2 — discovery agent

- [x] `SearchBackend` interface + Tavily implementation + keyless DuckDuckGo HTML
  fallback (auto-selected by `TAVILY_API_KEY` presence — see
  [03-manual-discovery.md](03-manual-discovery.md)), candidate ranking.
- [x] Approval UI (show candidates with match reasoning, approve one at a time).
  Provide-own-URL isn't separate — `LinkDocumentModal`'s "Upload PDF" already covers
  the "nothing good found" case.
- [x] Download + verify (content-type, size, **and content-relevance** — see
  03-manual-discovery.md) + hand off to `ragapp`'s ingestion functions directly.

## Phase 3 — query routing + unified chat

- [ ] Intent classifier (manual vs. inventory vs. both).
- [ ] Product inference against owned items, with clarification fallback for
  ambiguous cases.
- [ ] Unified `/api/chat` that branches to scoped RAG (via `ragapp`, in-process) or
  direct DB lookup.
- [ ] Log every routing decision (question, intent, resolved product) for eval later,
  same pattern as rtfm-rag's `query_logs`.

## Phase 4 — Home Assistant add-on

- [ ] Package as a single-container HA add-on (HA supervisor config, ingress-aware
  frontend routing — HA serves add-on UIs behind a dynamic path prefix, not root `/`).
- [ ] Device auto-import: call the HA Supervisor API (`SUPERVISOR_TOKEN` auth,
  available automatically in add-on mode) to list the device registry, offer devices
  as candidate products pre-filled with whatever manufacturer/model HA already has.
  Import is metadata-only and needs confirmation before anything's added — same
  standing rule as the manual-discovery approval step, not a relaxation of it.
- [ ] Verify standalone mode still works unchanged (this should require zero
  behavior-affecting code paths — `SUPERVISOR_TOKEN` presence is the only branch).

## Phase 5 — polish / future

- [ ] Warranty-expiration reminders (needs some notification mechanism — not designed
  yet; HA add-on mode could push these as HA notifications instead of building one
  from scratch).
- [ ] Multi-product questions ("compare fuel economy of my two cars").
