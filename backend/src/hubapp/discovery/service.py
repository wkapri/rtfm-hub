import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from ragapp.ingestion.service import IngestionError, ingest_pdf
from ragapp.llm.base import ToolSpec
from ragapp.llm.factory import create_llm_client

from hubapp.agent import AgentError, Tool, run_agent_loop
from hubapp.config import settings
from hubapp.discovery.base import SearchResult
from hubapp.discovery.factory import create_search_backend
from hubapp.discovery.fetch import FetchError, extract_pdf_text, fetch_preview
from hubapp.discovery.ranking import Candidate, rank_candidates
from hubapp.models import ProductDocument
from hubapp.observability import Trace
from hubapp.products.store import ProductStore
from hubapp.storage import save_manual

_USER_AGENT = "Mozilla/5.0 (compatible; rtfm-hub/0.1; +https://github.com/wkapri/rtfm-hub)"
_MIN_PDF_BYTES = 1024  # reject suspiciously tiny "PDFs" (broken links, error pages)
_RELEVANCE_CHECK_PAGES = 5  # only the first few pages — cheap, and enough to catch a wrong file
_MAX_TOOL_SEARCH_RESULTS = 8
_FETCH_PREVIEW_CHARS = 800  # keep tool results small — several may accumulate in one loop


class DiscoveryError(Exception):
    """A candidate couldn't be downloaded, verified, or ingested."""


_DISCOVER_SYSTEM_PROMPT = (
    "You find the official owner's manual PDF for a specific, already-confirmed "
    "product. You have tools to search the web, fetch a candidate URL's actual "
    "content to check it before recommending it, and run a cheap heuristic "
    "scorer over a batch of candidates. Search first. If a result looks "
    "promising but you're not sure it's really about this exact model (not a "
    "different model from the same brand, not an unrelated document that "
    "happens to match on title), fetch it and check — this matters: a wrong "
    "PDF silently approved by the user because it looked right from the title "
    "alone is the exact failure mode this tool exists to avoid. When you've "
    "identified up to 3 good candidates, call propose_candidates with your "
    "final list and a short reason for each. If nothing plausible turns up "
    "after a reasonable search, call propose_candidates with an empty list — "
    "don't force a weak match just to have an answer."
)

_PROPOSE_CANDIDATES_SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "reasoning": {"type": "string", "description": "Why this looks like the right manual."},
                },
                "required": ["title", "url", "reasoning"],
            },
        }
    },
    "required": ["candidates"],
}


def search_manual(
    brand: str | None,
    model: str | None,
    category: str | None,
    max_results: int = 3,
    trace: Trace | None = None,
) -> list[Candidate]:
    """Agentic manual search: an LLM with search/fetch/score tools looks for
    the product's owner's manual, optionally fetching a candidate's actual
    content to verify it before recommending it — something the old fixed
    heuristic-only pipeline couldn't do (see docs/specs/03-manual-discovery.md
    for the Qrevo/S7 case this is meant to catch). No downloads are persisted
    or ingested here regardless of what the agent does — fetch_candidate_preview
    is read-only, and the only function with real side effects, ingest_candidate,
    isn't a tool at all; it's only ever called after explicit user approval.
    """
    trace = trace if trace is not None else Trace()
    llm = create_llm_client(settings.agent_llm_provider)

    def _tool_web_search(query: str) -> str:
        backend = create_search_backend()
        results = backend.search(query, max_results=_MAX_TOOL_SEARCH_RESULTS)
        if not results:
            return "No results found."
        return "\n".join(f"- {r.title}\n  {r.url}" for r in results)

    def _tool_fetch_candidate_preview(url: str) -> str:
        try:
            preview = fetch_preview(url)
        except FetchError as exc:
            return str(exc)
        return f"content-type: {preview.content_type}, {preview.size_bytes} bytes\n\n{preview.text[:_FETCH_PREVIEW_CHARS]}"

    def _tool_score_heuristic(candidates: list[dict]) -> str:
        results = [SearchResult(title=c["title"], url=c["url"], snippet="", source="agent") for c in candidates]
        ranked = rank_candidates(results, brand, model)
        if not ranked:
            return "None passed the plausibility filter (no brand/model match, not a manufacturer/aggregator domain)."
        return "\n".join(f"- {c.title}\n  {c.url}\n  score={c.score}, reasons={c.match_reasons}" for c in ranked)

    tools = [
        Tool(ToolSpec("web_search", "Search the web.", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}), _tool_web_search),
        Tool(
            ToolSpec(
                "fetch_candidate_preview",
                "Download a candidate URL and return its content-type, size, and a text preview — to verify it's actually about this product before recommending it. Read-only, nothing is saved.",
                {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            ),
            _tool_fetch_candidate_preview,
        ),
        Tool(
            ToolSpec(
                "score_heuristic",
                "Score a batch of candidate {title, url} objects against the product's brand/model using cheap heuristics (domain, model-in-title, aggregator match). Optional — use it as a sanity check if you want a second opinion alongside your own judgment.",
                {
                    "type": "object",
                    "properties": {
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"title": {"type": "string"}, "url": {"type": "string"}},
                                "required": ["title", "url"],
                            },
                        }
                    },
                    "required": ["candidates"],
                },
            ),
            _tool_score_heuristic,
        ),
        Tool(
            ToolSpec("propose_candidates", "Report your final ranked list of manual candidates. Call this exactly once, when done.", _PROPOSE_CANDIDATES_SCHEMA),
            lambda **kw: kw,
        ),
    ]

    query_hint = " ".join(p for p in (brand, model, category) if p)
    user_message = (
        f"Find the owner's manual for: brand={brand!r}, model={model!r}, category={category!r}. "
        f'A reasonable starting search query might be "{query_hint} owner\'s manual filetype:pdf", '
        "but adjust it if that doesn't turn up good results."
    )

    try:
        result = run_agent_loop(
            llm=llm,
            system_prompt=_DISCOVER_SYSTEM_PROMPT,
            user_message=user_message,
            tools=tools,
            terminal_tool_name="propose_candidates",
            trace=trace,
        )
    except AgentError as exc:
        raise DiscoveryError(str(exc)) from exc

    return _coerce_candidates(result, max_results)


def _coerce_candidates(data: dict, max_results: int) -> list[Candidate]:
    out = []
    for c in (data.get("candidates") or [])[:max_results]:
        # A smaller model can deviate from the requested schema (e.g. a bare
        # URL string instead of the {title, url, reasoning} object asked for)
        # — skip anything that isn't shaped as expected rather than crashing
        # the whole request over one malformed entry.
        if not isinstance(c, dict):
            continue
        url = c.get("url") or ""
        if not url:
            continue
        domain = urlparse(url).netloc.lower().removeprefix("www.")
        reasoning = c.get("reasoning") or ""
        out.append(
            Candidate(
                title=c.get("title") or url,
                url=url,
                domain=domain,
                source="agent",
                match_reasons=[reasoning] if reasoning else [],
                score=0,
            )
        )
    return out


def ingest_candidate(
    candidate_url: str,
    candidate_title: str,
    product_id: str,
    document_kind: str,
    products: ProductStore,
    trace: Trace | None = None,
) -> ProductDocument:
    """Download, verify, ingest, and link ONE specific candidate. Only ever called
    after the user has approved that exact candidate — see the standing rule in
    docs/specs/03-manual-discovery.md. This is the only function in this module
    with real side effects.

    Approving a candidate is a judgment call on its *title and source* — the user
    has no way to see whether the URL actually resolves to what its title claims
    (search results can be wrong, and short/redirecting URLs especially so; this
    surfaced for real during testing: a candidate titled "Roborock S7" from a
    short domain actually resolved to an unrelated US Sentencing Commission PDF,
    which passed the content-type/size checks fine since it genuinely was a
    large, real PDF). So this also does a cheap content-relevance check — does
    the product's brand or model appear anywhere in the first few pages — before
    committing to a full ingest.
    """
    trace = trace if trace is not None else Trace()
    product = products.get(product_id)

    with trace.step("download") as s:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": _USER_AGENT}) as client:
            try:
                response = client.get(candidate_url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                s.detail = f"failed: {exc}"
                raise DiscoveryError(f"Couldn't download that URL: {exc}") from exc

        content_type = response.headers.get("content-type", "").lower()
        s.detail = f"{len(response.content)} bytes, content-type={content_type or 'unknown'}"

        if "pdf" not in content_type and not candidate_url.lower().endswith(".pdf"):
            raise DiscoveryError(f"That link doesn't look like a PDF (content-type: {content_type or 'unknown'}).")
        if len(response.content) < _MIN_PDF_BYTES:
            raise DiscoveryError("Downloaded file is suspiciously small — probably not a real manual.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / f"{_safe_filename(candidate_title)}.pdf"
        tmp_path.write_bytes(response.content)

        if product and (product.brand or product.model):
            with trace.step("content_relevance_check") as s:
                preview_text = extract_pdf_text(tmp_path.read_bytes(), max_pages=_RELEVANCE_CHECK_PAGES)
                mentioned = _mentions_product(preview_text, product.brand, product.model)
                wanted = " ".join(p for p in (product.brand, product.model) if p)
                s.detail = f'"{wanted}" {"found" if mentioned else "NOT found"} in first {_RELEVANCE_CHECK_PAGES} pages'
                if not mentioned:
                    raise DiscoveryError(
                        f'This PDF doesn\'t mention "{wanted}" anywhere in its first '
                        f"{_RELEVANCE_CHECK_PAGES} pages — probably the wrong document "
                        "(the title/source can be misleading). Try another candidate, or "
                        "link/upload the correct one directly."
                    )

        with trace.step("ingest") as s:
            try:
                document_id, chunk_count = ingest_pdf(tmp_path, title=candidate_title)
                s.detail = f"{chunk_count} chunk(s) embedded"
            except IngestionError as exc:
                s.detail = f"failed: {exc}"
                raise DiscoveryError(str(exc)) from exc

        save_manual(document_id, response.content)

    return products.link_document(product_id, document_id, document_kind, source_url=candidate_url)


def _mentions_product(text: str, brand: str | None, model: str | None) -> bool:
    text_lower = text.lower()
    if brand and brand.lower() in text_lower:
        return True
    return bool(model and model.lower() in text_lower)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\- ]", "", name).strip()
    return cleaned[:80] or "manual"
