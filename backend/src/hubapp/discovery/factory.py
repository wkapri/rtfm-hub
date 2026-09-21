from hubapp.config import settings
from hubapp.discovery.base import SearchBackend
from hubapp.discovery.duckduckgo import DuckDuckGoBackend
from hubapp.discovery.tavily import TavilyBackend


def create_search_backend() -> SearchBackend:
    """Tavily if TAVILY_API_KEY is set, otherwise the keyless DuckDuckGo fallback.
    Automatic, not a user-facing setting — this is a fallback, not a preference.
    See docs/specs/03-manual-discovery.md.
    """
    if settings.tavily_api_key:
        return TavilyBackend(api_key=settings.tavily_api_key)
    return DuckDuckGoBackend()
