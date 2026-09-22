from dataclasses import dataclass

from ragapp.llm.base import ToolSpec
from ragapp.llm.factory import create_llm_client

from hubapp.agent import AgentError, Tool, run_agent_loop
from hubapp.config import settings
from hubapp.discovery.factory import create_search_backend
from hubapp.discovery.fetch import FetchError, fetch_preview
from hubapp.observability import Trace

_SYSTEM_PROMPT = (
    "You identify the exact consumer product a user is describing — the specific "
    "brand and model, confirmed, not just a best guess. You have tools to search "
    "the web and fetch a page's content. Search first. If the results are "
    "ambiguous, too generic, or don't clearly confirm one specific model, search "
    "again with a narrower or different query, or fetch a promising page (a "
    "product listing, spec sheet, review) to confirm a detail — do this as many "
    "times as you need before answering. Once you're confident (or confident you "
    "can't do better with more searching), call propose_identification exactly "
    "once. Set brand/model to null and confidence to \"low\" rather than "
    "guessing — a wrong confident-sounding guess is worse than admitting "
    "uncertainty, and this identification gates everything downstream (a manual "
    "search only starts once the user has confirmed it)."
)

_PROPOSE_IDENTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"], "description": 'e.g. "vacuum"'},
        "year": {"type": ["integer", "null"], "description": "Model year, if apparent."},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reasoning": {"type": "string", "description": "One short phrase explaining the answer."},
    },
    "required": ["brand", "model", "category", "year", "confidence", "reasoning"],
}

_WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "required": ["query"],
}

_FETCH_PAGE_SCHEMA = {
    "type": "object",
    "properties": {"url": {"type": "string"}},
    "required": ["url"],
}

_FETCH_PREVIEW_CHARS = 1200


class IdentifyError(Exception):
    """The identification agent didn't reach a usable answer."""


@dataclass
class Identification:
    brand: str | None
    model: str | None
    category: str | None
    year: int | None
    confidence: str
    reasoning: str


def identify_product(description: str, trace: Trace | None = None) -> Identification:
    """Run the identification agent: given a bare description, it searches the
    web (and can fetch a page to confirm a detail) until it's confident about
    the exact brand/model, then reports a structured answer via its terminal
    tool. This result still isn't trusted outright — the frontend always shows
    it as an editable suggestion for the user to confirm before a product is
    created, and manual discovery (a separate agent) never runs until that
    confirmation happens. See docs/specs/06-agent-architecture.md.
    """
    trace = trace if trace is not None else Trace()
    llm = create_llm_client(settings.agent_llm_provider)

    def _tool_web_search(query: str) -> str:
        backend = create_search_backend()
        results = backend.search(query, max_results=5)
        if not results:
            return "No results found."
        return "\n".join(f"- {r.title}\n  {r.url}\n  {(r.snippet or '')[:300]}".rstrip() for r in results)

    def _tool_fetch_page(url: str) -> str:
        try:
            preview = fetch_preview(url)
        except FetchError as exc:
            return str(exc)
        return f"content-type: {preview.content_type}\n\n{preview.text[:_FETCH_PREVIEW_CHARS]}"

    tools = [
        Tool(
            ToolSpec("web_search", "Search the web for information about a product.", _WEB_SEARCH_SCHEMA),
            _tool_web_search,
        ),
        Tool(
            ToolSpec("fetch_page", "Fetch a URL and return a text preview of its content.", _FETCH_PAGE_SCHEMA),
            _tool_fetch_page,
        ),
        Tool(
            ToolSpec(
                "propose_identification",
                "Report the identified product. Call this exactly once, when done.",
                _PROPOSE_IDENTIFICATION_SCHEMA,
            ),
            lambda **kw: kw,
        ),
    ]

    try:
        result = run_agent_loop(
            llm=llm,
            system_prompt=_SYSTEM_PROMPT,
            user_message=f'Product description: "{description}"',
            tools=tools,
            terminal_tool_name="propose_identification",
            trace=trace,
        )
    except AgentError as exc:
        raise IdentifyError(str(exc)) from exc

    return _coerce_identification(result)


def _coerce_identification(data: dict) -> Identification:
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
