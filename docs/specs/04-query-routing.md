# Query Routing

## Two questions to answer per query

1. **Intent**: is this about manual *content* (how do I / why won't it / what does
   this mean), or about *inventory metadata* (when did I buy it / is it still under
   warranty / what maintenance has it had)? Could be both in one question.
2. **Product**: if manual content, which product's manual should be searched?

## Intent classification

A single small LLM call (via the shared Ollama instance) given the question and asked
to classify: `manual_content | inventory_metadata | both`. Cheap, and this is exactly
the kind of short structured-output task a local 3B model handles fine — no need for
anything fancier. Log every classification (question, chosen intent, which product if
resolved) the same way rtfm-rag logs `query_logs`, since this is exactly the kind of
thing that needs eval once there's enough real usage to notice it getting things
wrong.

## Product inference (for manual-content questions)

1. If the question names a product explicitly or unambiguously ("the Subaru", "S7") —
   match directly against `products.nickname`/`brand`/`model`.
2. If vague ("my vacuum") — match against `category` first. If exactly one product in
   that category, resolved. If multiple, ambiguous (see below).
3. If neither matches anything — no product resolved; ask the user which product they
   mean rather than guessing, or (if there's only one product in the entire inventory)
   assume that one.

Implementation-wise this is the same kind of classification call as intent detection
— one LLM call given the question + a list of the user's products (nickname, brand,
model, category), asked to pick the best match or say "none"/"ambiguous". Don't
overbuild this into a separate embedding-based product-matching system unless the
LLM-classification approach proves unreliable in practice.

## Ambiguous product resolution

When multiple products could match (two vacuums), don't guess — ask a clarifying
question in the chat ("Which one — the Roborock S7 or the Shark IQ?") rather than
silently picking one or searching both manuals and hoping the right answer surfaces.
Wrong-product answers that sound confident are worse than a one-extra-turn
clarification.

## Inventory-metadata questions

No RAG involved. Straightforward cases ("when does X's warranty expire") are a direct
Postgres query, no LLM needed at all for the data lookup — an LLM pass may still help
to phrase the answer naturally or handle open-ended versions ("what maintenance is
coming up"), but the underlying question is answered from `products`/
`maintenance_log`, never from a manual.

## Not built yet / explicitly deferred

- Handling a question that spans multiple products ("compare the fuel economy of my
  two cars") — not a v1 case, revisit if it comes up.
- Confidence scores surfaced to the user for product inference — start with binary
  resolved/ambiguous/unresolved; only add graduated confidence if the binary version
  proves too blunt in practice.
