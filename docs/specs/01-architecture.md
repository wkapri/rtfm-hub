# Architecture

## Revision note

This replaces an earlier design where rtfm-hub called rtfm-rag over HTTP with its own
separate Postgres database. Changed because of two new requirements: packaging as a
single-container Home Assistant add-on (which strongly favors one process, not an
orchestrated pair of services), and wanting a pluggable LLM provider (Ollama today,
OpenAI-compatible/Anthropic later) shared between RAG generation and query routing —
easier to build once and share than to build twice across a network boundary.

## Components

```
┌──────────────┐      ┌─────────────────────────────┐      ┌──────────────────┐
│  Frontend     │ HTTP │  FastAPI backend (hubapp)    │      │  Postgres         │
│  (React/TS)   │◄────►│                               │◄────►│  (shared:         │
└──────────────┘      │  imports ragapp directly:     │      │  products,        │
                       │   ragapp.ingestion             │      │  product_documents,│
                       │   ragapp.retrieval              │      │  maintenance_log,  │
                       │   ragapp.llm (provider-agnostic)│      │  documents, chunks,│
                       └───────────┬───────────────────┘      │  query_logs)       │
                                   │                            └──────────────────┘
                     ┌─────────────┼─────────────┐
                     │             │             │
              ┌──────▼─────┐ ┌────▼─────┐  ┌────▼─────────┐
              │  Tavily     │ │ LLM       │  │  HA Supervisor│
              │  (web       │ │ provider  │  │  API (add-on  │
              │  search)    │ │ (Ollama / │  │  mode only —   │
              └────────────┘ │ OpenAI /  │  │  device import)│
                              │ Anthropic)│  └───────────────┘
                              └──────────┘
```

rtfm-rag remains its own repo/package (`ragapp`) — independently installable, runnable,
and testable on its own. rtfm-hub depends on it as a library, not a network service.
One FastAPI process, one Postgres database, one deployable unit.

## Why a shared process/database (not separate services)

- **HA add-on packaging**: HA's standard add-on model is one container, one process.
  Two services (each with their own Postgres) means either two add-ons a user has to
  install and wire together, or a non-standard multi-container add-on — both are
  worse UX than "install one add-on."
- **One LLM provider abstraction**: both RAG answer-generation and query routing
  (intent classification, product inference) need to call an LLM. Building the
  pluggable-provider interface once in `ragapp.llm` and having rtfm-hub use the same
  code directly is simpler and more consistent than duplicating it or calling through
  an API boundary.
- **Real foreign keys**: `product_documents.document_id` can reference
  `documents.id` directly — no soft-reference validation dance.

**What this costs, honestly**: rtfm-hub's schema now depends on rtfm-rag's schema
existing first (ordering dependency at startup — `ragapp.retrieval.store.init_schema()`
must run before hubapp's own schema, which adds the FK). And rtfm-rag's internal
functions become part of a de facto public API that rtfm-hub depends on, even though
they were originally written just for its own CLI/FastAPI routes — some of them
(notably ingestion) need a small refactor to be cleanly importable rather than
CLI-only. Both are tracked in rtfm-rag's own roadmap.

## Data flow — adding a product

1. User adds a product (nickname, brand, model, category) via the frontend, or (HA
   add-on mode only) picks one from an auto-imported list of HA devices.
2. `POST /api/products` creates the row.
3. Discovery: backend calls the active search backend (Tavily, or a keyless
   DuckDuckGo fallback if no `TAVILY_API_KEY` is set), ranks candidates, returns them
   to the frontend for approval (see
   [03-manual-discovery.md](03-manual-discovery.md)).
4. On approval: backend downloads the PDF, verifies it, and calls `ragapp`'s ingestion
   functions directly (in-process — no HTTP call) to chunk/embed/store it.
5. The resulting `document_id` (rtfm-rag's own UUID) is stored in
   `product_documents.document_id`, now a real FK into rtfm-rag's `documents` table.

## Data flow — chat

1. User asks a question via the frontend, hits rtfm-hub's own `POST /api/chat` (not
   rtfm-rag's — this endpoint doesn't exist in the standalone-service sense anymore;
   rtfm-hub's chat handler calls `ragapp` functions directly where needed).
2. Query router classifies intent (manual-content / inventory-metadata / both) and, if
   manual-content, infers which product — see
   [04-query-routing.md](04-query-routing.md).
3. Branch:
   - **Manual content, product resolved**: call `ragapp.retrieval.Retriever` /
     `ragapp.llm.LLMClient` directly, scoped to that product's `document_id`(s) — this
     needs `VectorStore.search()` to accept an optional `document_ids` filter, which
     doesn't exist in `ragapp` yet (library-level equivalent of what was previously
     scoped as an HTTP API filter).
   - **Manual content, ambiguous/unresolved product**: ask a clarifying question, or
     (configurable) search across all ingested documents.
   - **Inventory metadata**: answer directly from rtfm-hub's own tables
     (`products`, `maintenance_log`) — no RAG, no LLM call for simple lookups.
   - **Both**: run both paths, combine in the response.

## Deployment targets

Same application, two ways to run it:

- **Standalone**: `docker compose up` — Postgres + the app, talks to a local (or
  remote, via `OLLAMA_HOST`) Ollama instance. Same shape as rtfm-rag's current setup.
- **HA add-on**: single container under HA's supervisor, served via HA's ingress
  (reverse-proxied — no exposed port, path-prefixed routing the frontend needs to
  handle). Gains one extra capability not available standalone: calling the HA
  Supervisor API (auth via the `SUPERVISOR_TOKEN` env var HA injects automatically)
  to list the device registry and offer devices as candidate products, pre-filled
  with whatever manufacturer/model HA already knows. Everything else behaves
  identically to standalone mode. Detecting which mode you're in is just "is
  `SUPERVISOR_TOKEN` set" — no separate config flag needed.

Not building HA-add-on packaging or device import yet — see
[05-roadmap.md](05-roadmap.md) for sequencing. Designing the shared-process
architecture now specifically so this doesn't require a rewrite later.

## Key interfaces

- `DiscoveryAgent.search(brand, model) -> list[Candidate]` — search (via whichever
  `SearchBackend` is active) + ranking, no side effects.
- `DiscoveryAgent.ingest(candidate, product_id) -> document_id` — the only place that
  downloads a file, only ever called after explicit approval of that candidate. Calls
  `ragapp`'s ingestion functions directly.
- `QueryRouter.classify(question, products) -> Intent` — manual vs. inventory vs.
  both, and which product(s) if manual-related.
- From `ragapp` (rtfm-rag's package, consumed as a library): `Embedder.embed`,
  `VectorStore.search` (needs a `document_ids` filter param added), `LLMClient`
  (needs the pluggable-provider refactor). These are rtfm-rag's responsibility to
  build/stabilize; rtfm-hub just consumes them.
