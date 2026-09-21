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
(see [rtfm-rag's README](../rtfm-rag/README.md) if starting fresh elsewhere). Optional:
a [Tavily](https://tavily.com) API key for better manual-discovery search results —
works without one, see [03-manual-discovery.md](docs/specs/03-manual-discovery.md).

rtfm-hub imports rtfm-rag's `ragapp` package directly rather than calling it over
HTTP, so **rtfm-rag's own Docker Compose/backend/frontend don't need to be running**
— rtfm-hub has its own Postgres (shared schema with `ragapp`'s tables) and calls
`ragapp`'s Python functions in-process. You do need `ragapp` installed as an editable
package in this project's venv, though — see setup below.
