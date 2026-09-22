# Manual Discovery Agent

Both discovery and product identification are now real tool-calling agent loops,
not fixed pipelines with a single LLM call — see
[06-agent-architecture.md](06-agent-architecture.md) for the loop mechanics
(how tools are called, the terminal-tool pattern, small-model reliability
handling). This doc covers the domain-specific pieces: what the ranking
heuristic does (now offered to the agent as a `score_heuristic` tool rather
than always running), the content-relevance safety check, and PDF retention.

## Standing rule

**Never downloads a file without the user approving that specific candidate first.**
Not a v1 limitation to relax later — this stays true even once ranking is reliable,
because a wrong or malicious PDF silently ingested into the RAG store is a bad failure
mode, and it's cheap to just ask.

## Search backend: Tavily, with a keyless fallback

Tavily is the primary backend (built for LLM/agent use — clean results, often direct
PDF links). It needs an API key. Rather than making the whole discovery feature
unusable without one, there's an automatic fallback:

- `TAVILY_API_KEY` set → use Tavily.
- Not set → use **DuckDuckGo's HTML search endpoint**
  (`html.duckduckgo.com/html/`) — no API key, no JavaScript rendering needed (a plain
  HTML response, parseable with a simple request + basic HTML parsing), so no headless
  browser to bundle.

Explicitly **not** doing real browser automation (Playwright/Selenium driving an
actual Chromium instance) for this, even as a fallback: it means bundling a full
browser binary (100s of MB) into what's supposed to be a lightweight, fast-starting
container — a real cost for a Home Assistant add-on — and directly scraping Google
is fragile (CAPTCHAs, ToS, markup that changes without notice). DuckDuckGo's HTML
endpoint is explicitly meant to be machine-parseable and doesn't have those problems.

Both backends implement the same interface — `search(query: str) -> list[RawResult]`
— so the ranking/candidate logic below doesn't know or care which one ran. Selection
is automatic (env var presence), not a user-facing setting, mirroring how
`LLM_PROVIDER` works in rtfm-rag but without the manual choice — this is a fallback,
not a preference.

Result quality from the fallback will likely be worse than Tavily's (less structured,
more irrelevant links to filter) — acceptable degradation, not a bug to fix later.

## Flow

1. Triggered when a product is added (or manually re-triggered from the product page
   if the first search found nothing good). Only ever runs against an
   already-confirmed brand/model — see 06-agent-architecture.md for why that's
   structurally guaranteed, not just convention.
2. The discovery agent (`hubapp/discovery/service.py`, `search_manual`) searches
   the web, can fetch a candidate's actual content to check it before
   recommending it, and can run the ranking heuristic below as a `score_heuristic`
   tool for a second opinion — as many times as it decides it needs, not a fixed
   one-shot search. It ends by calling `propose_candidates` with up to 3 ranked
   candidates and a reason for each, or an empty list if nothing plausible turned
   up (see "What happens when nothing good is found" below).
3. The ranking heuristic itself (`hubapp/discovery/ranking.py`, `rank_candidates`)
   is unchanged cheap string-matching — no LLM call needed for it specifically:
   - Only candidates on the manufacturer's own domain, a known aggregator
     (manualslib.com etc.), or a direct `.pdf` link that actually mentions the
     product's brand or model in its title/URL are considered at all — being a
     `.pdf` link is *not* enough on its own. Found via live testing: searching
     for a Subaru's manual returned completely unrelated PDFs (a solar-charger
     manual, a state DMV handbook) that used to pass this filter purely because
     the URL ended in `.pdf`.
   - A direct `.pdf` link outranks everything else, including an aggregator match —
     an aggregator "manual" page (e.g. ManualsLib) is often an HTML viewer, not a
     download, and fails the approval-time PDF check; a real PDF link just works.
     Found via live testing, not designed in upfront.
   - Manufacturer's own domain (or a known aggregator like manualslib.com) ranks
     above random third-party sites.
   - Model number appearing in the URL or result title ranks above a generic match
     — and when a model *is* specified but doesn't appear anywhere, that's a
     penalty, not just a missed bonus. Also found via live testing: a manufacturer
     domain can rank a PDF for a *different, newer* product above everything else
     on domain authority alone.
   - Prefer results whose title suggests "owner's manual" / "user guide" over
     "service manual" / "parts list" as the default first candidate — user can still
     see and pick the others.
4. The frontend shows the agent's final candidates: title, source URL, domain, and
   its stated reasoning (so the user can judge confidence themselves, not just
   trust a score). Each candidate also links directly to its source URL ("Preview")
   so the user can open and look at the actual page/file before approving
   anything — not just trust the title or the agent's reasoning.
5. User approves one (or rejects all — no manual found, log it as such rather than
   silently failing).
6. On approval: download the file, verify `Content-Type` is actually a PDF and the
   size is sane (reject 0-byte or suspiciously huge files), **then check that the
   product's brand or model actually appears somewhere in the first few pages of
   extracted text** before committing to a full ingest. This step exists because of
   a real failure during testing: a candidate titled "Roborock S7" from a short
   domain resolved to an entirely unrelated PDF (a US Sentencing Commission
   guidelines document) — which passed the content-type and size checks fine, since
   it genuinely was a large, real PDF. The title and source of a search result are
   not proof of what a URL actually resolves to. If the check fails, surface a clear
   error and let the user try another candidate — same "no auto-selection" principle
   as everywhere else in this flow. Note this check accepts brand *or* model, so a
   manual for a different model from the same brand can still pass it — filtering
   already keeps most of these out at step 3, but it's not a full model-match
   guarantee, which is what the "Preview" link is for.
7. If all checks pass, call `ragapp`'s `ingest_pdf()` directly (in-process library
   call, not an HTTP request — see [01-architecture.md](01-architecture.md)) and
   store the resulting `document_id` in `product_documents`. The original PDF bytes
   are also saved to `MANUALS_DIR` (`hubapp/storage.py`), keyed by `document_id` —
   ingestion only stores extracted text/chunks/embeddings, so without this the
   source file would be discarded once the temp directory it was downloaded into is
   cleaned up. `GET /api/documents/{document_id}/file` serves it back, and every
   linked manual in the product detail view has a "View" link to it. Documents
   ingested before this feature existed (or a manually-uploaded PDF from before the
   upload endpoint also started retaining copies) 404 on this endpoint — there's no
   file to serve for those.

## What happens when nothing good is found

Don't force a low-confidence auto-selection. Show whatever candidates exist (even
low-confidence ones) with their match reasoning visible, and let the user either pick
one anyway, provide a direct URL themselves, or skip — the product still exists in
inventory without a manual; that's a valid state, not an error state.

## Product identification ("smart add")

Adding a product starts from a single free-text description ("roomba", "2013 subaru
xv crosstrek") instead of a blank form with every field. The identification agent
(`hubapp/discovery/identify.py`) searches the web and can fetch a page to confirm a
detail, as many times as it needs, before reporting `{brand, model, category, year,
confidence, reasoning}` via its terminal tool. Confidence is explicitly `"low"`
rather than a confident-sounding guess when it can't pin down a specific
brand/model. The user sees this (confidence badge + reasoning, collapsible trace)
with all fields pre-filled but still editable, confirms and saves, and discovery
runs automatically against the new product — no separate "now go find a manual"
step. See [06-agent-architecture.md](06-agent-architecture.md) for the loop
mechanics both agents share, and for the history of what this replaced (a single
LLM call parsing raw JSON out of free text, including a real context-window
truncation bug found via live testing).

This required extending rtfm-rag's `LLMProvider` with `complete_with_tools()` (all
three providers — Ollama/OpenAI-compatible/Anthropic): the existing
`chat_stream()` is plain text-in/text-out with no concept of tool calls, and RAG
chat still uses it unchanged.

## Observability

Every identify/discover/approve request builds a `Trace` (`hubapp/observability.py`)
— a list of named steps with a human-readable detail and duration. For the agent
loops, that's every model turn and every tool call, e.g.:

```
agent_turn          546ms   called web_search
tool:web_search     1733ms  - Smart Thermostat Enhanced | ecobee ...
agent_turn          2348ms  called propose_identification
```

Each step is logged server-side as it completes (so `docker logs` / the uvicorn
console shows the same thing even without opening the UI), and also returned to the
frontend, which renders it as a collapsible "What happened" panel — admin-facing
visibility into which search backend ran, what it found, whether a PDF passed the
content-relevance check, and how long each part took, without needing to tail logs.
Trace steps recorded before a request fails are only visible server-side today (the
error response doesn't carry partial trace data) — the happy-path steps above are
covered, failure-path trace surfacing is a possible follow-up.

## Not built yet / explicitly deferred

- Re-checking for a newer manual revision later (recalls, firmware updates that change
  the manual) — out of scope until there's a reason to need it.
- Scraping manufacturer support sites directly instead of general web search — only
  worth the per-brand engineering effort if both search backends prove unreliable for
  specific brands in practice.
- A third, browser-automation-backed search tier — only worth the weight/fragility
  tradeoff if the DuckDuckGo fallback proves genuinely inadequate in practice, not
  speculatively.
