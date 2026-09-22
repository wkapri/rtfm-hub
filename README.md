# rtfm-hub

Personal inventory + manual assistant. Track what you own, auto-discover the official
manual for each item, and ask questions about any of it through one chat interface —
routed automatically to the right product and to either the manual (via
[rtfm-rag](../rtfm-rag)) or your own inventory data, whichever the question needs.

See [CLAUDE.md](CLAUDE.md) for the stack/architecture summary and
[docs/specs/](docs/specs/) for the full design — start with
[00-overview.md](docs/specs/00-overview.md). [MIT licensed](LICENSE).

## Status

**Phase 1 and Phase 2 done, verified end to end**: product CRUD, maintenance log
(UI hidden, data kept), PDF upload/link/discovery → ingest (via `ragapp`,
in-process) → link-to-product with the original PDF retained and viewable, and a
full React frontend for all of it.

Adding a product and finding its manual are both **real tool-calling agent
loops** — search, fetch-and-verify, and (for discovery) heuristic-score are
callable tools; each loop ends by calling a terminal tool with a structured
result, not by parsing free text. Identification must be confirmed by the user
before discovery even starts (the two loops share no tools), and
downloading/ingesting a manual stays a plain human-approved action neither loop
can trigger itself. See [06-agent-architecture.md](docs/specs/06-agent-architecture.md)
for the design (including real small-model reliability quirks found via live
testing) and [03-manual-discovery.md](docs/specs/03-manual-discovery.md) for the
ranking heuristic and content-relevance safety check. Every identify/discover/
approve request is traced (every model turn + tool call, with timings) and shown
in the UI as a "What happened" panel. No query routing/chat yet — see
[docs/specs/05-roadmap.md](docs/specs/05-roadmap.md) for what's next.

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

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5174 (5173 is rtfm-rag's own frontend — different port so both
can run at once).
