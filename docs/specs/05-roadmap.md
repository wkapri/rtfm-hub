# Roadmap

## Done

- [x] Design docs — overview, architecture, data model, discovery agent, query routing.

## Blocking dependency on rtfm-rag

Two additions needed on rtfm-rag's side before rtfm-hub can be fully wired end to end
(track these in rtfm-rag's own roadmap, not duplicated here):

- [ ] `POST /api/documents` — ingest a PDF via API call, not just CLI.
- [ ] Document-scoping filter on `POST /api/chat` (e.g. `document_ids: [...]`) so a
  question can be answered from one product's manual specifically.

Everything else below can be built in parallel against rtfm-rag's *current* API
(unscoped chat) and switched over once those land.

## Phase 1 — inventory, no discovery/routing yet

- [ ] Postgres schema (`products`, `product_documents`, `maintenance_log`).
- [ ] FastAPI CRUD for products + maintenance log.
- [ ] Frontend: product list/detail views, add/edit product, maintenance log entries.
- [ ] Manually link a product to an already-ingested rtfm-rag document (no discovery
  agent yet — proves the product_documents linkage and the "ask rtfm-rag, scoped"
  call path work before automating discovery).

## Phase 2 — discovery agent

- [ ] Tavily integration, candidate search + ranking.
- [ ] Approval UI (show candidates, approve/reject/provide-own-URL).
- [ ] Download + verify + hand off to rtfm-rag's ingest endpoint.

## Phase 3 — query routing + unified chat

- [ ] Intent classifier (manual vs. inventory vs. both).
- [ ] Product inference against owned items, with clarification fallback for
  ambiguous cases.
- [ ] Unified chat endpoint that branches to rtfm-rag (scoped) or direct DB lookup.
- [ ] Log every routing decision (question, intent, resolved product) for eval later,
  same pattern as rtfm-rag's `query_logs`.

## Phase 4 — polish / future

- [ ] Warranty-expiration reminders (needs some notification mechanism — not designed
  yet).
- [ ] Home Assistant integration (the original motivating idea — revisit once the
  core inventory + chat loop actually works day to day).
