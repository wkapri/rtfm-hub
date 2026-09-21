# Architecture

## Components

```
┌──────────────┐      ┌───────────────────┐      ┌──────────────────┐
│  Frontend     │ HTTP │  FastAPI backend  │      │  Postgres         │
│  (React/TS)   │◄────►│  (hubapp.api)     │◄────►│  (products,       │
└──────────────┘      └─────────┬─────────┘      │   maintenance_log)│
                                 │                 └──────────────────┘
                    ┌────────────┼────────────┐
                    │            │            │
             ┌──────▼─────┐ ┌───▼────┐ ┌─────▼──────┐
             │  Tavily     │ │ Ollama │ │  rtfm-rag  │
             │  (web       │ │ (intent│ │  (RAG API, │
             │  search)    │ │ routing│ │  own        │
             └────────────┘ │ calls) │ │  Postgres) │
                             └────────┘ └────────────┘
```

rtfm-hub and rtfm-rag are separate services with **separate Postgres
databases/instances**, talking over HTTP. See "Why not share rtfm-rag's database"
below for the reasoning.

## Data flow — adding a product

1. User adds a product (nickname, brand, model, category) via the frontend.
2. `POST /api/products` creates the row (`routing`/`discovery` not involved yet).
3. User triggers discovery (either automatically on add, or manually — TBD in
   [03-manual-discovery.md](03-manual-discovery.md)): backend searches Tavily, ranks
   candidates, returns them to the frontend for approval.
4. User approves a candidate. Backend downloads the PDF, verifies it's actually a
   PDF, and calls rtfm-rag's `POST /api/documents` (once that endpoint exists — see
   [05-roadmap.md](05-roadmap.md)) to ingest it.
5. rtfm-rag returns a `document_id`. rtfm-hub stores the link in `product_documents`.

## Data flow — chat

1. User asks a question via the frontend.
2. `POST /api/chat` (rtfm-hub's own endpoint, not rtfm-rag's) runs the query router:
   - Classify intent: manual-content question, inventory-metadata question, or both.
   - If manual-content: infer which product(s) the question is about from the user's
     inventory (see [04-query-routing.md](04-query-routing.md)).
3. Branch:
   - **Manual content, product resolved**: call rtfm-rag's `POST /api/chat` scoped to
     that product's `document_id`(s) (needs rtfm-rag's document-filter addition).
   - **Manual content, product ambiguous/unresolved**: ask a clarifying question
     instead of guessing, or (configurable) fall back to searching across all
     ingested manuals.
   - **Inventory metadata**: answer directly from rtfm-hub's own Postgres — no LLM
     call needed for simple lookups ("when does X's warranty expire"), though a
     summarizing LLM pass may help for open-ended ones ("what maintenance is coming
     up soon").
   - **Both**: run both paths, combine in the response.

## Why not share rtfm-rag's database

Simpler alternative would be one shared Postgres with a `products` table alongside
rtfm-rag's `documents`/`chunks`, giving real foreign keys instead of soft references.
Chose separate databases instead because:

- Matches the chosen service boundary (rtfm-hub calls rtfm-rag's API, not its
  internals) — sharing a database is a much tighter coupling than an HTTP contract,
  and defeats the purpose of keeping rtfm-rag reusable/standalone.
- rtfm-rag may need to change its schema for reasons unrelated to rtfm-hub (e.g. a
  different embedding model with a different vector dimension); a shared DB means
  every rtfm-rag migration is also a rtfm-hub concern.

Tradeoff accepted: `product_documents.document_id` is a **soft reference** (plain
UUID column, not an enforced foreign key) — validity is checked at write time by
calling rtfm-rag's API, not by the database. A document deleted directly in rtfm-rag
(bypassing its own API) could leave a dangling reference; acceptable for a
single-user local setup, revisit if this ever needs to be more robust.

## Key interfaces

- `DiscoveryAgent.search(brand, model) -> list[Candidate]` — Tavily search + ranking,
  no side effects (no downloads).
- `DiscoveryAgent.ingest(candidate, product_id) -> document_id` — the only place that
  downloads a file, and only ever called after explicit user approval of that
  specific candidate.
- `QueryRouter.classify(question, products) -> Intent` — decides manual vs. inventory
  vs. both, and which product(s) if manual-related.

These are the seams to keep stable as ranking heuristics, the search backend, or the
routing model change.
