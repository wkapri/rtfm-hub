# Data Model

## `products`

One row per item you own.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| nickname | text | user-facing name, e.g. "Kitchen vacuum" — defaults to `"{brand} {model}"` if not given |
| brand | text | e.g. "Roborock" |
| model | text | e.g. "S7" |
| category | text | e.g. "vacuum", "vehicle", "appliance" — free text for now, not an enum; revisit if routing needs it to be structured |
| year | int, nullable | model year, not purchase year (matters for vehicles: "2013 Subaru XV") |
| purchase_date | date, nullable | |
| warranty_expires | date, nullable | |
| notes | text, nullable | freeform |
| created_at | timestamptz | |

## `product_documents`

Many-to-many: a product can have an owner's manual *and* a quick-start guide *and* a
service manual; a document conceptually belongs to one product (a manual isn't shared
across products in practice, but modeling it as many-to-many costs nothing and avoids
a future migration).

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK → products.id | |
| document_id | UUID | **soft reference** to rtfm-rag's `documents.id` — see 01-architecture.md for why this isn't an enforced FK |
| document_kind | text | e.g. "owners_manual", "quick_start", "service_manual" |
| source_url | text | where the discovery agent found it, kept for provenance/re-verification |
| added_at | timestamptz | |

## `maintenance_log`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK → products.id | |
| date | date | |
| description | text | e.g. "Replaced filter", "Oil change" |
| cost | numeric, nullable | |
| created_at | timestamptz | |

## Open questions (resolve when building, not blocking the design)

- Should `category` become a constrained enum once the query router needs to reason
  about categories ("my vacuum" matching category="vacuum")? Leaning yes eventually,
  free text for v1 to avoid guessing the taxonomy upfront.
- Multiple products of the same category (two vacuums) — routing needs a
  disambiguation UX for this case regardless of how `category` is modeled; see
  [04-query-routing.md](04-query-routing.md).
