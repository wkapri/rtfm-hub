from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from hubapp.discovery.base import SearchResult

# DuckDuckGo blocks the default httpx UA on some setups; a plain browser-ish UA
# avoids that without pretending to be anything more than a script.
_USER_AGENT = "Mozilla/5.0 (compatible; rtfm-hub/0.1; +https://github.com/wkapri/rtfm-hub)"


class DuckDuckGoBackend:
    """Keyless fallback when TAVILY_API_KEY isn't set — see factory.py and
    docs/specs/03-manual-discovery.md for why this and not real browser automation.
    """

    def __init__(self):
        self._client = httpx.Client(
            base_url="https://html.duckduckgo.com",
            timeout=20,
            headers={"User-Agent": _USER_AGENT},
        )

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        response = self._client.get("/html/", params={"q": query})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        results = []
        for link in soup.select("a.result__a")[:max_results]:
            title = link.get_text(strip=True)
            url = _unwrap_redirect(link.get("href", ""))
            if title and url:
                results.append(SearchResult(title=title, url=url, snippet="", source="duckduckgo"))
        return results


def _unwrap_redirect(href: str) -> str:
    """DuckDuckGo's HTML results link through /l/?uddg=<url-encoded target> rather
    than linking directly — unwrap that to get the real URL.
    """
    parsed = urlparse(href)
    if parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        return unquote(target)
    return href
