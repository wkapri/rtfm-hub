import re
import tempfile
from pathlib import Path

import httpx
from pypdf import PdfReader
from ragapp.ingestion.service import IngestionError, ingest_pdf

from hubapp.discovery.factory import create_search_backend
from hubapp.discovery.ranking import Candidate, rank_candidates
from hubapp.models import ProductDocument
from hubapp.observability import Trace
from hubapp.products.store import ProductStore

_USER_AGENT = "Mozilla/5.0 (compatible; rtfm-hub/0.1; +https://github.com/wkapri/rtfm-hub)"
_MIN_PDF_BYTES = 1024  # reject suspiciously tiny "PDFs" (broken links, error pages)
_RELEVANCE_CHECK_PAGES = 5  # only the first few pages — cheap, and enough to catch a wrong file


class DiscoveryError(Exception):
    """A candidate couldn't be downloaded, verified, or ingested."""


def search_manual(
    brand: str | None,
    model: str | None,
    category: str | None,
    max_results: int = 3,
    trace: Trace | None = None,
) -> list[Candidate]:
    """Search + rank only — no downloads, no side effects. Safe to call as often
    as the user wants without the approval rule coming into play.
    """
    trace = trace if trace is not None else Trace()
    query = " ".join(p for p in (brand, model, category) if p) + " owner's manual filetype:pdf"
    backend = create_search_backend()

    with trace.step("web_search") as s:
        results = backend.search(query, max_results=10)
        s.detail = f"{type(backend).__name__}: {len(results)} result(s) for {query!r}"

    with trace.step("rank_candidates") as s:
        ranked = rank_candidates(results, brand, model)[:max_results]
        s.detail = f"{len(ranked)} candidate(s) kept: " + ", ".join(c.domain for c in ranked)

    return ranked


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
                preview_text = _extract_preview_text(tmp_path)
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

    return products.link_document(product_id, document_id, document_kind, source_url=candidate_url)


def _extract_preview_text(path: Path, max_pages: int = _RELEVANCE_CHECK_PAGES) -> str:
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:max_pages])


def _mentions_product(text: str, brand: str | None, model: str | None) -> bool:
    text_lower = text.lower()
    if brand and brand.lower() in text_lower:
        return True
    return bool(model and model.lower() in text_lower)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\- ]", "", name).strip()
    return cleaned[:80] or "manual"
