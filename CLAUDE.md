# rtfm-hub — Personal Inventory + Manual Assistant

## What this is

A personal inventory tracker that pairs each item you own with its instruction manual,
searchable via chat:
- Track "products" (appliances, vehicles, electronics — anything with a manual):
  brand, model, purchase date, warranty, maintenance history.
- A discovery agent searches the web for the official manual PDF for a product you add,
  and (after you approve the candidate) hands it to [rtfm-rag](../rtfm-rag) for ingestion.
- Chat that routes each question to the right place: manual content ("how do I reset
  wifi on this?") goes through rtfm-rag's RAG pipeline scoped to the right product;
  inventory questions ("when does the Subaru's warranty expire?") are answered directly
  from this app's own database, no RAG involved.
- Ambiguous questions ("how do I reset wifi on my vacuum") get resolved against your
  owned products before retrieval happens, so you don't have to name the exact model
  every time.

## Relationship to rtfm-rag

This is a **separate service that calls rtfm-rag**, not a fork or an extension of it.
rtfm-rag stays a focused, reusable local RAG engine; rtfm-hub owns everything about
*which* products you have and *which* manual/question a query is about, then delegates
the actual retrieval+generation to rtfm-rag's API.

rtfm-rag needs two additions to support this (tracked in its own roadmap, not here):
- `POST /api/documents` — upload + ingest a PDF via API (today it's CLI-only).
- A document-scoping filter on `POST /api/chat` (today it always searches everything).

Until those land, rtfm-hub's discovery-agent and routing pieces can be designed and
partially built, but the last mile (actually scoping a chat answer to one product's
manual) is blocked on rtfm-rag's side.

## Stack

Same as rtfm-rag, for consistency and to reuse the same local Ollama/Postgres setup:

| Layer          | Choice                                    | Notes |
|----------------|--------------------------------------------|-------|
| Backend        | Python (FastAPI)                            | products/inventory API, discovery agent, query router |
| Frontend       | React + TypeScript (Vite)                   | inventory UI + chat UI |
| Database       | PostgreSQL                                  | own instance/database, separate from rtfm-rag's — see 01-architecture.md for why |
| Web search     | Tavily API                                  | manual discovery — needs an API key (free tier: 1000 searches/mo) |
| LLM            | Ollama (shared with rtfm-rag)               | query-intent classification + product inference |
| RAG            | rtfm-rag, called over HTTP                  | not embedded — see "Relationship to rtfm-rag" above |

## Repo layout (planned — not built yet)

```
rtfm-hub/
  backend/
    src/hubapp/
      products/        Inventory CRUD, maintenance log
      discovery/        Tavily search, candidate ranking, download+handoff to rtfm-rag
      routing/          Intent classification (manual vs. inventory question), product inference
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
optimization to relax later, it's a standing rule.

## Current status

Design phase — docs/specs/ only, no code yet. See
[docs/specs/05-roadmap.md](docs/specs/05-roadmap.md).

## Prerequisites

Same machine as rtfm-rag — Python, Node, Docker, Ollama are already installed. New for
this project: a [Tavily](https://tavily.com) API key (free tier).
