# Agent Architecture

## What changed

The identify and discover steps used to be a single LLM call each: search once,
hand the results to the model, parse whatever came back. They're now real
tool-calling agent loops — the model can search again with a different query,
fetch a page to confirm a detail, or check a batch of candidates against a
heuristic scorer, as many times as it needs, before answering.

## Two loops, separated by a hard human checkpoint

**Phase A — identification** (`hubapp/discovery/identify.py`). Given a bare
description ("roomba", "2013 subaru xv crosstrek"), the agent searches the web
and can fetch a page to confirm a detail, until it's ready to report a specific
brand/model via its terminal tool, `propose_identification`.

**Phase B — discovery** (`hubapp/discovery/service.py`, `search_manual`). Only
ever runs against an already-**confirmed** brand/model — never a raw
description. It searches for the manual, can fetch a candidate's actual content
to check it's really about this product before recommending it, and can run
the old heuristic ranking as a `score_heuristic` tool for a second opinion. Ends
by calling `propose_candidates`.

The two phases don't share a tool namespace, so there's no path for the agent
to search for a manual before a model has been confirmed. That separation,
not any extra plumbing, is what enforces "confirm the exact model before
looking for its manual" — Phase B's tools simply don't exist while Phase A is
running, and Phase B never starts until the user has confirmed/edited Phase
A's answer in the QuickAddModal UI and a product record exists.

## The loop mechanics (`hubapp/agent.py`)

A ReAct-style loop, built on `ragapp.llm.base.LLMProvider.complete_with_tools()`
(new — the RAG chat path still uses `chat_stream()`, unaffected):

1. Send the running message history + tool schemas to the model.
2. It replies with tool call(s) or plain text.
3. Each non-terminal tool call is executed server-side; the result is fed back
   as a message, and the loop repeats.
4. The loop ends only when the model calls the **terminal tool** — that call's
   arguments (already structured, no more regex JSON-extraction from free
   text) are the loop's result.
5. A hard cap (`max_iterations`, default 6) prevents a runaway loop.

Every turn and every tool call is a step in the `Trace` (see
[03-manual-discovery.md](03-manual-discovery.md)'s Observability section), so
the full reasoning trail — which query, what came back, why it fetched a page —
is visible in the UI's "What happened" panel, not just the final answer.

## What's deliberately never a tool

Downloading and ingesting a manual stays exactly what it was before: a plain
function (`ingest_candidate`) reachable only through the user's explicit
approval click. Neither agent loop can invoke it. `fetch_candidate_preview` (a
tool) can *look* at a candidate's content — that's read-only and nothing is
persisted — but committing it to the vector store is a completely separate
step outside the agent's reach. This is the same standing rule from
03-manual-discovery.md, just drawn as a hard line in the tool surface instead
of a policy comment.

## Model reliability, in practice

Ollama's `llama3.2:3b` (this project's default) does support tool-calling —
confirmed via `curl` against `/api/chat` directly. But it's noticeably less
reliable at the agentic *pattern* than at a single-shot extraction:

- It sometimes gathers what it needs via tools and then **summarizes in plain
  text instead of calling the terminal tool** — it "sounds" done without
  formally finishing. `run_agent_loop` nudges once (an explicit "call
  `{terminal_tool}` now" message) before giving up — this recovers the loop
  in the common case, confirmed via live testing.
- It sometimes deviates from a tool's requested argument shape (e.g. returning
  a bare URL string in `propose_candidates`'s candidates array instead of the
  `{title, url, reasoning}` object asked for). `_coerce_candidates` and
  `_coerce_identification` are defensive about this — skip what doesn't parse
  rather than crash the request.
- If it still doesn't reach the terminal tool after the nudge, both phases
  degrade to their existing empty-result state (no candidates / no
  identification) rather than a 500 — same principle as "don't force a
  low-confidence auto-selection," just applied to agent failures too.

`AGENT_LLM_PROVIDER` (`hubapp/config.py`) lets the agent loops run against a
different, more tool-reliable provider (e.g. `anthropic`, given an
`ANTHROPIC_API_KEY`) while RAG chat and embeddings stay on local Ollama — the
agent loops are occasional and latency-tolerant, a very different workload
from RAG chat's frequent/streaming/local-first default. Not set by default;
this project runs entirely on local Ollama unless you configure otherwise.

## Provider interface (rtfm-rag)

`ragapp.llm.base` adds `ToolSpec`, `ToolCall`, `AssistantTurn`, and a `Message`
type, plus `LLMProvider.complete_with_tools()`. All three providers
(Ollama/OpenAI-compatible/Anthropic) implement it, translating the generic
message format to their own wire shape — the trickiest part, since none of the
three represent "a tool's result" or "a tool call's arguments" the same way
(Ollama's arguments arrive pre-parsed, OpenAI's as a JSON string to
`json.loads`, Anthropic has no `"tool"` role at all — a result becomes a
`tool_result` content block inside a `user` turn). See
`rtfm-rag/backend/tests/test_llm_tools.py` for each provider's translation
tested directly against a canned response, no real network calls.
