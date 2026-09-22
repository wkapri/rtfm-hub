# rtfm-hub — Personal Inventory + Manual Assistant

## What this is

A personal inventory tracker that pairs each item you own with its instruction manual,
searchable via chat:
- Track "products" (appliances, vehicles, electronics — anything with a manual):
  brand, model, purchase date, warranty, maintenance history.
- A discovery agent searches the web for the official manual PDF for a product you add,
  and (after you approve the candidate) ingests it via rtfm-rag's retrieval pipeline.
- Chat that routes each question to the right place: manual content ("how do I reset
  wifi on this?") goes through RAG scoped to the right product; inventory questions
  ("when does the Subaru's warranty expire?") are answered directly from this app's own
  database, no RAG involved.
- Ambiguous questions ("how do I reset wifi on my vacuum") get resolved against your
  owned products before retrieval happens, so you don't have to name the exact model
  every time.

Runs two ways: **standalone** (own Docker Compose stack, like rtfm-rag today) or as a
**Home Assistant add-on** (single container under HA's supervisor). Same codebase,
same behavior either way — see "Deployment targets" below for what differs.

## Relationship to rtfm-rag

rtfm-rag stays its **own repo** — independently runnable, independently useful to
someone who just wants local PDF-RAG with no inventory concept. rtfm-hub consumes it
as a **Python library** (`pip install -e ../rtfm-rag/backend`, `import ragapp...`),
not as a network service. One FastAPI process, one Postgres database, real foreign
keys between rtfm-hub's `products` and rtfm-rag's `documents` — see
[01-architecture.md](docs/specs/01-architecture.md) for the reasoning (this replaced
an earlier HTTP-based design once "single-container HA add-on" and "one shared LLM
abstraction" became goals).

This means rtfm-rag needs to be usable as a library, not just a standalone app — its
ingestion/retrieval/llm modules called directly as Python functions rather than
through its FastAPI routes. Tracked as work items in rtfm-rag's own roadmap.

## Stack

| Layer          | Choice                                    | Notes |
|----------------|--------------------------------------------|-------|
| Backend        | Python (FastAPI)                            | products/inventory API, discovery agent, query router, imports rtfm-rag's `ragapp` package directly |
| Frontend       | React + TypeScript (Vite)                   | inventory UI + chat UI |
| Database       | PostgreSQL                                  | one shared database with rtfm-rag's tables (real FKs) — see 01-architecture.md |
| Web search     | Tavily API, with an automatic keyless fallback (DuckDuckGo HTML search) if `TAVILY_API_KEY` isn't set | manual discovery — see 03-manual-discovery.md for why the fallback isn't browser automation |
| LLM            | Pluggable provider (Ollama by default; OpenAI-compatible / Anthropic later) | shared abstraction, lives in `ragapp.llm`, used by both RAG generation and query routing |

## Deployment targets

- **Standalone**: Docker Compose, same pattern as rtfm-rag today — own Postgres
  container, talks to a local (or remote) Ollama.
- **Home Assistant add-on**: single container under HA's supervisor, using HA's
  ingress (reverse-proxied UI, no exposed port needed). Adds one HA-specific
  capability not available standalone: **auto-import devices from HA's device
  registry** as candidate products (HA already has manufacturer/model for most
  integrations — pre-filling `products` from that is a big head start over manual
  entry). Detected via the `SUPERVISOR_TOKEN` env var HA injects into add-ons; the
  app behaves identically otherwise. Not building this yet — see
  [05-roadmap.md](docs/specs/05-roadmap.md) for when.

## Repo layout

```
rtfm-hub/
  backend/
    src/hubapp/
      products/        Inventory CRUD, maintenance log — built
      discovery/        Search backends (Tavily + keyless DuckDuckGo fallback), ranking,
                         download+verify+relevance-check+handoff to ragapp's ingestion — built
      routing/          Intent classification (manual vs. inventory question), product
                         inference — not built yet (Phase 3)
      ha/               HA-add-on-only: device-registry import (SUPERVISOR_TOKEN-gated) —
                         not built yet (Phase 4)
      api/              FastAPI app
  frontend/
    src/               Inventory UI (built: list/detail, forms, maintenance, discovery
                        approval); chat UI not built yet (Phase 3)
  docs/specs/          Design docs — read before making architectural changes
```

## Conventions

Same as rtfm-rag: design docs before code for anything architectural, small testable
functions over notebook-style scripts, config in env vars, never hardcode secrets.

One addition specific to this project: **the discovery agent never downloads a file
without the user approving that specific candidate first.** No "trust mode," no
auto-approval threshold, even for high-confidence matches — this isn't a performance
optimization to relax later, it's a standing rule. Same standard applies to the future
HA device-import feature: importing a device's *metadata* (name/model) needs no
approval, but nothing downloads or gets treated as authoritative until you confirm it.

## Current status

**Phase 1 and Phase 2 done**: product CRUD, maintenance log (UI hidden, data model
kept), PDF upload/link/discovery → ingest (via `ragapp.ingestion.service.ingest_pdf`,
in-process) → link-to-product, plus a full React frontend for all of it. Ingested
manuals' original PDFs are retained and viewable (`GET /api/documents/{id}/file`),
not just chunked into the vector store and discarded.

Product identification (a single free-text description → confirmed brand/model)
and manual discovery are both **real tool-calling agent loops** now, not a single
LLM call each — the model can search again, fetch a page to verify a detail, or
score candidates with the old heuristic ranking, as many times as it needs before
answering via a terminal tool. Identification must be confirmed by the user before
discovery's tools even exist (the two loops share no tool namespace), and
downloading/ingesting stays a plain human-approved action, never a tool either
loop can call. Required a new `complete_with_tools()` method on rtfm-rag's
`LLMProvider`, implemented across all three providers. See
[docs/specs/06-agent-architecture.md](docs/specs/06-agent-architecture.md) for the
loop mechanics (including real small-model reliability quirks found via live
testing) and [docs/specs/03-manual-discovery.md](docs/specs/03-manual-discovery.md)
for the domain-specific pieces (ranking heuristic, content-relevance check).

Every identify/discover/approve request is traced (every model turn + tool call,
with timings), logged server-side and shown in the UI as a "What happened" panel
(`hubapp/observability.py`). No query routing/chat yet. See
[docs/specs/05-roadmap.md](docs/specs/05-roadmap.md).

## Prerequisites

Same machine as rtfm-rag — Python, Node, Docker, Ollama are already installed.
Optional for this project: a [Tavily](https://tavily.com) API key (free tier) for
better manual-discovery search results — works without one (falls back to a keyless
DuckDuckGo search, see 03-manual-discovery.md), just with weaker ranking.
