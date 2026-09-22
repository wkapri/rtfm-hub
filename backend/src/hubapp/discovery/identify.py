import json
import re
from dataclasses import dataclass

from ragapp.llm.factory import create_llm_client

from hubapp.discovery.base import SearchResult
from hubapp.discovery.factory import create_search_backend
from hubapp.observability import Trace

SYSTEM_PROMPT = (
    "You identify consumer products from a short user description and web search "
    'results. Respond with ONLY a JSON object, no other text, with these exact '
    'keys: "brand" (string or null), "model" (string or null), "category" '
    '(string or null, e.g. "vacuum"), "year" (integer or null, model year if '
    'apparent), "confidence" ("high", "medium", or "low"), "reasoning" (under 15 '
    'words explaining your answer — a phrase, not a paragraph). If the description '
    "and search results don't clearly identify a specific brand/model, set "
    'brand/model to null and confidence to "low" rather than guessing — a wrong '
    "confident-sounding guess is worse than admitting uncertainty."
)


class IdentifyError(Exception):
    """The LLM's response couldn't be parsed as a valid identification."""


@dataclass
class Identification:
    brand: str | None
    model: str | None
    category: str | None
    year: int | None
    confidence: str
    reasoning: str


_MAX_RESULTS = 5
_MAX_SNIPPET_CHARS = 350  # some search results are full news articles, not short
# snippets — without a cap, 5 of those can eat most of the 2048-token context
# budget (tuned for RAG chat's shorter context) before the model even starts
# answering, truncating its JSON output mid-response. Found via live testing:
# a real query returned a response cut off with no closing brace. That first
# pass still wasn't enough headroom on some queries (verbose review-style
# snippets, or the model rambling in "reasoning"), so on a truncated/unparsable
# response we retry once with titles only — much smaller footprint, usually
# still enough to identify a well-known brand/model.


def identify_product(description: str, trace: Trace | None = None) -> Identification:
    """Search the web for the description, then have the LLM extract brand/model
    from real search results — more accurate for new/obscure products than
    relying on the LLM's own (dated) training knowledge alone.
    """
    trace = trace if trace is not None else Trace()
    backend = create_search_backend()

    with trace.step("web_search") as s:
        results = backend.search(f"{description} product specifications", max_results=_MAX_RESULTS)
        s.detail = f"{type(backend).__name__}: {len(results)} result(s) for {description!r}"

    user_message = f'Product description: "{description}"'
    llm = create_llm_client()

    with trace.step("llm_identify") as s:
        context = _build_context(results, include_snippets=True)
        raw = "".join(llm.chat_stream(user_message, context, system_prompt=SYSTEM_PROMPT))
        try:
            identification = _parse_response(raw)
            s.detail = f"{identification.brand} {identification.model} ({identification.confidence})"
            return identification
        except IdentifyError:
            s.detail = "response truncated/unparsable, retrying with titles only"

    with trace.step("llm_identify_retry") as s:
        context = _build_context(results, include_snippets=False)
        raw = "".join(llm.chat_stream(user_message, context, system_prompt=SYSTEM_PROMPT))
        identification = _parse_response(raw)
        s.detail = f"{identification.brand} {identification.model} ({identification.confidence})"
        return identification


def _build_context(results: list[SearchResult], include_snippets: bool) -> str:
    if include_snippets:
        parts = [
            f"{r.title}\n{(r.snippet or '')[:_MAX_SNIPPET_CHARS]}".strip()
            for r in results
            if r.title or r.snippet
        ]
    else:
        parts = [r.title for r in results if r.title]
    return "\n\n".join(parts) or "(no search results found)"


def _parse_response(raw: str) -> Identification:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise IdentifyError(f"Model response wasn't valid JSON: {raw[:200]!r}")

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise IdentifyError(f"Model response wasn't valid JSON: {raw[:200]!r}") from exc

    confidence = data.get("confidence") or "low"
    if confidence not in ("high", "medium", "low"):
        confidence = "low"

    year = data.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None

    return Identification(
        brand=data.get("brand") or None,
        model=data.get("model") or None,
        category=data.get("category") or None,
        year=year,
        confidence=confidence,
        reasoning=data.get("reasoning") or "",
    )
