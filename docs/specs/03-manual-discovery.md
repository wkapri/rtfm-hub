# Manual Discovery Agent

## Standing rule

**Never downloads a file without the user approving that specific candidate first.**
Not a v1 limitation to relax later — this stays true even once ranking is reliable,
because a wrong or malicious PDF silently ingested into the RAG store is a bad failure
mode, and it's cheap to just ask.

## Flow

1. Triggered when a product is added (or manually re-triggered from the product page
   if the first search found nothing good).
2. Build a search query from the product's brand + model + category, e.g.
   `"Roborock S7 owner's manual filetype:pdf"`. Category helps disambiguate generic
   model numbers.
3. Call Tavily's search API. Filter results to plausible PDF links (either the URL
   ends in `.pdf`, or the result is on a domain that looks like the manufacturer's).
4. Rank candidates — cheap heuristics, no LLM call needed for this part:
   - Manufacturer's own domain (or a known aggregator like manualslib.com) ranks
     above random third-party sites.
   - Model number appearing in the URL or result title ranks above a generic match.
   - Prefer results whose title suggests "owner's manual" / "user guide" over
     "service manual" / "parts list" as the default first candidate — user can still
     see and pick the others.
5. Return top 3 candidates to the frontend: title, source URL, domain, and which
   heuristics matched (so the user can judge confidence themselves, not just trust a
   score).
6. User approves one (or rejects all — no manual found, log it as such rather than
   silently failing).
7. On approval: download the file, verify `Content-Type` is actually a PDF and the
   size is sane (reject 0-byte or suspiciously huge files), then call rtfm-rag's
   `POST /api/documents` to ingest it.
8. Store the resulting `document_id` in `product_documents`.

## What happens when nothing good is found

Don't force a low-confidence auto-selection. Show whatever candidates exist (even
low-confidence ones) with their match reasoning visible, and let the user either pick
one anyway, provide a direct URL themselves, or skip — the product still exists in
inventory without a manual; that's a valid state, not an error state.

## Not built yet / explicitly deferred

- Re-checking for a newer manual revision later (recalls, firmware updates that change
  the manual) — out of scope until there's a reason to need it.
- Scraping manufacturer support sites directly instead of general web search — only
  worth the per-brand engineering effort if Tavily's results prove unreliable for
  specific brands in practice.
