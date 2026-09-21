# Roadmap

## Done

- [x] Design docs — overview, architecture, data model, discovery agent, query
  routing. Architecture revised: rtfm-rag consumed as a library (shared process/DB),
  not an HTTP service — see 01-architecture.md's revision note.

## Dependencies on rtfm-rag (library-level, not API endpoints)

Tracked in rtfm-rag's own roadmap, listed here for visibility since Phase 1 needs the
first one:

- [ ] `VectorStore.search()` needs an optional `document_ids` filter — the library
  equivalent of what was previously going to be an HTTP `/api/chat` scoping param.
- [ ] Ingestion logic needs to be cleanly importable (today it's CLI-only, wired
  through `cli.py`'s `ingest()` — needs factoring into a plain function that doesn't
  `raise SystemExit` and isn't argparse-shaped).
- [ ] `LLMClient` needs a pluggable-provider refactor (Ollama today; OpenAI-compatible
  and Anthropic as swappable alternatives) — not blocking Phase 1-3 below, but
  blocking "bring your own LLM" and should happen before too much routing code is
  written against the Ollama-specific client.

## Phase 1 — inventory, no discovery/routing yet

- [ ] Shared Postgres: rtfm-hub's schema (`products`, `product_documents`,
  `maintenance_log`) applied after rtfm-rag's own schema, in the same database.
- [ ] FastAPI CRUD for products + maintenance log.
- [ ] Frontend: product list/detail views, add/edit product, maintenance log entries.
- [ ] Manually link a product to an already-ingested rtfm-rag document (no discovery
  agent yet — proves the `product_documents` FK and calling `ragapp` directly work
  before automating discovery).

## Phase 2 — discovery agent

- [ ] Tavily integration, candidate search + ranking.
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
