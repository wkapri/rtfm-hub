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

**Phase 1 is done.**

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

- [ ] `SearchBackend` interface + Tavily implementation + keyless DuckDuckGo HTML
  fallback (auto-selected by `TAVILY_API_KEY` presence — see
  [03-manual-discovery.md](03-manual-discovery.md)), candidate ranking.
- [ ] Approval UI (show candidates, approve/reject/provide-own-URL).
- [ ] Download + verify + hand off to `ragapp`'s ingestion functions directly.

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
