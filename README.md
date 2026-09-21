# rtfm-hub

Personal inventory + manual assistant. Track what you own, auto-discover the official
manual for each item, and ask questions about any of it through one chat interface —
routed automatically to the right product and to either the manual (via
[rtfm-rag](../rtfm-rag)) or your own inventory data, whichever the question needs.

See [CLAUDE.md](CLAUDE.md) for the stack/architecture summary and
[docs/specs/](docs/specs/) for the full design — start with
[00-overview.md](docs/specs/00-overview.md). [MIT licensed](LICENSE).

## Status

**Phase 1 backend done, verified end to end**: product CRUD, maintenance log, and
PDF upload → ingest (via `ragapp`, in-process) → link-to-product all work against
the shared Postgres database. No frontend yet, no discovery agent, no query
routing/chat — see [docs/specs/05-roadmap.md](docs/specs/05-roadmap.md) for what's
next.

## Prerequisites

Same machine as rtfm-rag — Python, Node, Docker, and Ollama are already installed
(see [rtfm-rag's README](../rtfm-rag/README.md) if starting fresh elsewhere). Optional:
a [Tavily](https://tavily.com) API key for better manual-discovery search results —
works without one, see [03-manual-discovery.md](docs/specs/03-manual-discovery.md).

rtfm-hub imports rtfm-rag's `ragapp` package directly rather than calling it over
HTTP, so **rtfm-rag's own Docker Compose/backend/frontend don't need to be running**
— rtfm-hub has its own Postgres (shared schema with `ragapp`'s tables) and calls
`ragapp`'s Python functions in-process. You do need `ragapp` installed as an editable
package in this project's venv, though.

## Setup

```powershell
# 1. Start this project's own Postgres (separate from rtfm-rag's own standalone one)
docker compose up -d

# 2. Backend — ragapp (rtfm-rag) installed as an editable sibling dependency
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ..\..\rtfm-rag\backend
pip install -e ".[dev]"
copy ..\.env.example ..\.env
uvicorn hubapp.api.main:app --reload --port 8001
```

Frontend setup isn't written yet — no frontend exists as of Phase 1.
