from dataclasses import dataclass
from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

USER_AGENT = "Mozilla/5.0 (compatible; rtfm-hub/0.1; +https://github.com/wkapri/rtfm-hub)"
_PREVIEW_CHARS = 2000
_PDF_PREVIEW_PAGES = 5


class FetchError(Exception):
    """A URL couldn't be downloaded or read."""


@dataclass
class PagePreview:
    content_type: str
    size_bytes: int
    text: str


def fetch_preview(url: str) -> PagePreview:
    """Download a URL and return a short text preview plus basic metadata —
    read-only, nothing persisted or ingested. Used by both agent phases'
    fetch tools so they can inspect a page or PDF before deciding anything,
    without that inspection itself being (or requiring) a full ingest — that
    stays a separate, human-approved step (see docs/specs/03-manual-discovery.md).
    """
    with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        try:
            response = client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"Couldn't fetch {url}: {exc}") from exc

    content_type = response.headers.get("content-type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        text = extract_pdf_text(response.content)
    else:
        text = _extract_html_text(response.text)

    return PagePreview(
        content_type=content_type or "unknown",
        size_bytes=len(response.content),
        text=text[:_PREVIEW_CHARS] or "(no extractable text)",
    )


def extract_pdf_text(content: bytes, max_pages: int = _PDF_PREVIEW_PAGES) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:max_pages])


def _extract_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())
