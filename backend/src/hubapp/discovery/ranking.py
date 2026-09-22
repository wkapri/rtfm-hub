from dataclasses import dataclass
from urllib.parse import urlparse

from hubapp.discovery.base import SearchResult

MANUAL_AGGREGATOR_DOMAINS = {"manualslib.com", "manua.ls", "manualsonline.com"}
GOOD_TITLE_KEYWORDS = ["owner", "manual", "user guide", "quick start"]
BAD_TITLE_KEYWORDS = ["service manual", "parts list", "parts catalog"]


@dataclass
class Candidate:
    title: str
    url: str
    domain: str
    source: str
    match_reasons: list[str]
    score: int  # internal sort key only — never shown to the user as a raw number


def rank_candidates(
    results: list[SearchResult], brand: str | None, model: str | None
) -> list[Candidate]:
    """Filter to plausible manual links and rank by cheap heuristics — no LLM call.
    See docs/specs/03-manual-discovery.md for the reasoning behind each heuristic.
    """
    candidates = []
    for r in results:
        domain = urlparse(r.url).netloc.lower().removeprefix("www.")
        if not _is_plausible(r.url, domain, brand):
            continue
        candidates.append(_score(r, domain, brand, model))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def _is_plausible(url: str, domain: str, brand: str | None) -> bool:
    if urlparse(url).path.lower().endswith(".pdf"):
        return True
    if brand and brand.lower() in domain:
        return True
    return domain in MANUAL_AGGREGATOR_DOMAINS


def _score(result: SearchResult, domain: str, brand: str | None, model: str | None) -> Candidate:
    reasons = []
    score = 0

    # A literal .pdf link just works when approved; an aggregator page (e.g.
    # ManualsLib) is often a viewer, not a download, and fails the PDF check at
    # approval time. Real evidence for this: Tavily's top results for "Roborock
    # S7 owner's manual filetype:pdf" were ManualsLib HTML pages, not PDFs.
    if urlparse(result.url).path.lower().endswith(".pdf"):
        reasons.append("direct PDF link")
        score += 3  # deliberately > the aggregator bonus below, so a real PDF
        # always outranks an aggregator viewer page even when both also match
        # on model/title — a viewer page fails the approval-time PDF check.

    if brand and brand.lower() in domain:
        reasons.append("manufacturer's own domain")
        score += 3
    elif domain in MANUAL_AGGREGATOR_DOMAINS:
        reasons.append("known manual aggregator")
        score += 2

    haystack = f"{result.title} {result.url}".lower()
    if model:
        if model.lower() in haystack:
            reasons.append("model number in title/URL")
            score += 2
        else:
            # Real evidence this matters: a manufacturer's own domain can rank a
            # PDF for a *different* product (e.g. a newer model) above everything
            # else on domain authority alone, even though it's the wrong manual.
            # No visible reason string for this — it's an absence, not a signal
            # to show — but it keeps a right-model result from a lesser domain
            # from being buried under a wrong-model one from a great domain.
            score -= 2

    title_lower = result.title.lower()
    if any(kw in title_lower for kw in GOOD_TITLE_KEYWORDS):
        reasons.append("looks like an owner's manual")
        score += 1
    if any(kw in title_lower for kw in BAD_TITLE_KEYWORDS):
        score -= 1

    return Candidate(
        title=result.title,
        url=result.url,
        domain=domain,
        source=result.source,
        match_reasons=reasons,
        score=score,
    )
