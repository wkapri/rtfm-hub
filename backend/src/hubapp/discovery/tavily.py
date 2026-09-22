import httpx

from hubapp.discovery.base import SearchResult


class TavilyBackend:
    """Primary search backend — built for LLM/agent use, returns clean results.
    Needs an API key; see factory.py for the fallback when one isn't configured.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client = httpx.Client(base_url="https://api.tavily.com", timeout=20)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        response = self._client.post(
            "/search",
            json={"api_key": self._api_key, "query": query, "max_results": max_results},
        )
        response.raise_for_status()
        data = response.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r["url"],
                snippet=r.get("content", ""),
                source="tavily",
            )
            for r in data.get("results", [])
        ]
