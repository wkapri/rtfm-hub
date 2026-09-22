from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str  # "tavily" or "duckduckgo" — which backend produced this


class SearchBackend(Protocol):
    """Common interface for manual-discovery search backends. Ranking logic
    (ranking.py) depends only on this, never on Tavily's or DuckDuckGo's actual
    response shape.
    """

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...
