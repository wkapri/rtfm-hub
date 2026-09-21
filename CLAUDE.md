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
| Web search     | Tavily API                                  | manual discovery — needs an API key (free tier: 1000 searches/mo) |
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

## Repo layout (planned — not built yet)

```
rtfm-hub/
  backend/
    src/hubapp/
      products/        Inventory CRUD, maintenance log
      discovery/        Tavily search, candidate ranking, download+handoff to rtfm-rag's ingestion
      routing/          Intent classification (manual vs. inventory question), product inference
      ha/               HA-add-on-only: device-registry import (SUPERVISOR_TOKEN-gated)
      api/              FastAPI app
  frontend/
    src/               Inventory UI + chat UI (React + TS)
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

Design phase — docs/specs/ only, no code yet. See
[docs/specs/05-roadmap.md](docs/specs/05-roadmap.md).

## Prerequisites

Same machine as rtfm-rag — Python, Node, Docker, Ollama are already installed. New for
this project: a [Tavily](https://tavily.com) API key (free tier).
