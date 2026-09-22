# Manual Discovery Agent

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
   if the first search found nothing good).
2. Build a search query from the product's brand + model + category, e.g.
   `"Roborock S7 owner's manual filetype:pdf"`. Category helps disambiguate generic
   model numbers.
3. Call the active search backend (Tavily or the DuckDuckGo fallback). Filter results
   to plausible PDF links (either the URL ends in `.pdf`, or the result is on a
   domain that looks like the manufacturer's).
4. Rank candidates — cheap heuristics, no LLM call needed for this part:
   - A direct `.pdf` link outranks everything else, including an aggregator match —
     an aggregator "manual" page (e.g. ManualsLib) is often an HTML viewer, not a
     download, and fails step 7's PDF check; a real PDF link just works. Found via
     live testing, not designed in upfront.
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
5. Return top 3 candidates to the frontend: title, source URL, domain, and which
   heuristics matched (so the user can judge confidence themselves, not just trust a
   score).
6. User approves one (or rejects all — no manual found, log it as such rather than
   silently failing).
7. On approval: download the file, verify `Content-Type` is actually a PDF and the
   size is sane (reject 0-byte or suspiciously huge files), **then check that the
   product's brand or model actually appears somewhere in the first few pages of
   extracted text** before committing to a full ingest. This step exists because of
   a real failure during testing: a candidate titled "Roborock S7" from a short
   domain resolved to an entirely unrelated PDF (a US Sentencing Commission
   guidelines document) — which passed the content-type and size checks fine, since
   it genuinely was a large, real PDF. The title and source of a search result are
   not proof of what a URL actually resolves to. If the check fails, surface a clear
   error and let the user try another candidate — same "no auto-selection" principle
   as everywhere else in this flow.
8. If all checks pass, call `ragapp`'s `ingest_pdf()` directly (in-process library
   call, not an HTTP request — see [01-architecture.md](01-architecture.md)) and
   store the resulting `document_id` in `product_documents`.

## What happens when nothing good is found

Don't force a low-confidence auto-selection. Show whatever candidates exist (even
low-confidence ones) with their match reasoning visible, and let the user either pick
one anyway, provide a direct URL themselves, or skip — the product still exists in
inventory without a manual; that's a valid state, not an error state.

## Product identification ("smart add")

Adding a product starts from a single free-text description ("roomba", "2013 subaru
xv crosstrek") instead of a blank form with every field. Flow:

1. Web search for `"{description} product specifications"` via the same
   `SearchBackend` used for manual discovery (Tavily/DuckDuckGo).
2. The LLM (via `ragapp`'s pluggable `LLMProvider`, using its `system_prompt`
   override — see below) extracts structured `{brand, model, category, year,
   confidence, reasoning}` from the search results. Confidence is explicitly
   `"low"` rather than a confident-sounding guess when the results don't clearly
   identify a specific brand/model.
3. The user sees the identification (confidence badge + reasoning) with all fields
   pre-filled but still editable, then confirms and saves. If identification fails
   outright, the description becomes the nickname and every field is blank/editable
   — same manual-entry fallback, just without a wasted round trip.
4. On save, discovery (the flow above) runs automatically against the new product —
   no separate "now go find a manual" step.

This required extending rtfm-rag's `LLMProvider.chat_stream()` with an optional
`system_prompt` parameter: it was hardcoded to the RAG manual-Q&A prompt, which made
it unusable for a non-RAG extraction task despite rtfm-hub's own docs already
describing the interface as shared "by both RAG generation and query routing." All
three providers (Ollama/OpenAI-compatible/Anthropic) default to the existing prompt,
so RAG callers are unaffected.

**Context-window truncation bug** (found via live testing, twice): Ollama's chat
`num_ctx` is tuned for RAG chat (2048 tokens, sized for shorter retrieval contexts).
Search-result snippets for identification can be much longer (full articles/reviews),
and once combined with the system prompt they left too little budget for the model's
own JSON output — responses were cut off mid-sentence with no closing brace. Fixed
with two layers: (1) truncate each snippet to 350 chars and keep the "reasoning"
field short by instruction (under 15 words), and (2) if the response still comes back
unparsable, retry once with titles-only context (no snippets) — a much smaller
footprint that's usually still enough to identify a well-known brand/model.

## Observability

Every identify/discover/approve request builds a `Trace` (`hubapp/observability.py`)
— a list of named steps with a human-readable detail and duration, e.g.:

```
web_search        1708ms   TavilyBackend: 5 result(s) for '2021 tesla model 3'
llm_identify      1099ms   Tesla Model 3 (high)
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
