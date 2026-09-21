# rtfm-hub

Personal inventory + manual assistant. Track what you own, auto-discover the official
manual for each item, and ask questions about any of it through one chat interface —
routed automatically to the right product and to either the manual (via
[rtfm-rag](../rtfm-rag)) or your own inventory data, whichever the question needs.

See [CLAUDE.md](CLAUDE.md) for the stack/architecture summary and
[docs/specs/](docs/specs/) for the full design — start with
[00-overview.md](docs/specs/00-overview.md). [MIT licensed](LICENSE).

## Status

**Design phase — no code yet.** The specs are written; implementation follows the
phases in [docs/specs/05-roadmap.md](docs/specs/05-roadmap.md), starting with plain
inventory CRUD (no discovery agent or routing yet) so the data model and the
rtfm-rag integration point get proven out before adding the harder pieces.

## Prerequisites

Same machine as rtfm-rag — Python, Node, Docker, and Ollama are already installed
(see [rtfm-rag's README](../rtfm-rag/README.md) if starting fresh elsewhere). New for
this project: a [Tavily](https://tavily.com) API key (free tier is enough to start).

rtfm-rag itself needs to be running (`docker compose up -d` + backend + frontend in
that repo) since rtfm-hub calls its API rather than duplicating retrieval.
