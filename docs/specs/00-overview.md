# Overview

## Goal

You own a bunch of things — a 2013 Subaru XV, a Roborock S7, whatever. Each has a
manual somewhere online that you'll never find again when you actually need it. This
project:

1. Lets you record what you own (nickname, brand, model, purchase date, warranty,
   maintenance history) in one place.
2. Finds the official manual for each item automatically (you approve before anything
   downloads) and makes it searchable via [rtfm-rag](../../rtfm-rag).
3. Gives you one chat interface for everything — ask about how to use/fix/maintain
   anything you own, without needing to remember which manual to search or specify the
   exact model every time.

## Why a separate repo from rtfm-rag (but not a separate service)

rtfm-rag answers "what does this manual say" given a document. It has no concept of
*products*, *ownership*, *warranties*, or *which manual applies to this vague
question*. Those are a different problem — not a RAG problem at all, in the case of
"when does my warranty expire." Keeping the **code** separate means rtfm-rag stays
reusable on its own (it doesn't care whether a document was ingested via its CLI,
found by rtfm-hub's discovery agent, or added some other way) and rtfm-hub stays
focused on ownership + routing rather than reimplementing retrieval.

At **runtime**, though, rtfm-hub imports rtfm-rag's `ragapp` package directly and
they share one process and one database — not two services talking over HTTP. That
changed from the original plan once "package as a single-container Home Assistant
add-on" and "one shared LLM-provider abstraction" became goals; see
[01-architecture.md](01-architecture.md) for the full reasoning.

## Core pieces

1. **Inventory** — CRUD for products + maintenance log. Not RAG-related at all;
   see [02-data-model.md](02-data-model.md).
2. **Discovery agent** — given a product, find and (with your approval) ingest its
   manual via rtfm-rag. See [03-manual-discovery.md](03-manual-discovery.md).
3. **Query router** — given a question, decide (a) is this about manual content or
   inventory metadata, and (b) which product does it concern. See
   [04-query-routing.md](04-query-routing.md).

## Non-goals (for now)

- Multi-user / shared inventories.
- Editing or annotating manuals — read-only reference, same as rtfm-rag.
- Tracking consumables/supplies (filters, batteries) as a separate concept from
  "maintenance" — fold into maintenance log entries for now, revisit if it needs more
  structure later.
- Anything beyond a one-time web search per product for discovery — no continuous
  monitoring for manual updates/recalls (interesting later, not v1).
