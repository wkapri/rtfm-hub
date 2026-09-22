from hubapp.discovery.base import SearchResult
from hubapp.discovery.ranking import rank_candidates


def test_manufacturer_domain_ranks_above_random_site():
    results = [
        SearchResult(
            title="Roborock S7 manual", url="https://randomsite.com/roborock-s7.pdf",
            snippet="", source="tavily",
        ),
        SearchResult(
            title="Roborock S7 Owner's Manual", url="https://www.roborock.com/manuals/s7.pdf",
            snippet="", source="tavily",
        ),
    ]
    candidates = rank_candidates(results, brand="Roborock", model="S7")

    assert candidates[0].domain == "roborock.com"
    assert "manufacturer's own domain" in candidates[0].match_reasons


def test_model_number_in_title_boosts_score():
    results = [
        SearchResult(title="Generic vacuum manual", url="https://manualslib.com/a.pdf", snippet="", source="tavily"),
        SearchResult(title="Roborock S7 manual", url="https://manualslib.com/b.pdf", snippet="", source="tavily"),
    ]
    candidates = rank_candidates(results, brand=None, model="S7")

    assert candidates[0].url.endswith("b.pdf")
    assert "model number in title/URL" in candidates[0].match_reasons


def test_service_manual_title_scores_lower_than_owners_manual():
    results = [
        SearchResult(title="S7 Service Manual", url="https://manualslib.com/a.pdf", snippet="", source="tavily"),
        SearchResult(title="S7 Owner's Manual", url="https://manualslib.com/b.pdf", snippet="", source="tavily"),
    ]
    candidates = rank_candidates(results, brand=None, model="S7")

    assert candidates[0].url.endswith("b.pdf")


def test_non_pdf_non_manufacturer_non_aggregator_is_filtered_out():
    results = [
        SearchResult(title="Some forum post", url="https://randomforum.com/thread/123", snippet="", source="tavily"),
    ]
    candidates = rank_candidates(results, brand="Roborock", model="S7")

    assert candidates == []


def test_pdf_link_on_unrelated_domain_still_passes_filter():
    results = [
        SearchResult(title="S7 manual", url="https://cdn.example.com/files/s7.pdf", snippet="", source="tavily"),
    ]
    candidates = rank_candidates(results, brand="Roborock", model="S7")

    assert len(candidates) == 1


def test_right_model_beats_wrong_model_even_on_better_domain():
    # Real evidence this matters: Tavily returned manufacturer-domain PDFs for
    # *newer* Roborock models (Qrevo, Saros) ranking above everything when
    # searching for the S7 — domain authority shouldn't paper over a model
    # mismatch.
    results = [
        SearchResult(
            title="Roborock Qrevo S Pro User Manual",
            url="https://gl-files.roborock.com/manuals/qrevo-s-pro.pdf",
            snippet="", source="tavily",
        ),
        SearchResult(
            title="Roborock S7 manual",
            url="https://cdn.example.com/files/s7.pdf",
            snippet="", source="tavily",
        ),
    ]
    candidates = rank_candidates(results, brand="Roborock", model="S7")

    assert candidates[0].url.endswith("s7.pdf")


def test_unrelated_pdf_with_no_brand_or_model_mention_is_filtered_out():
    # Real bug found via live testing: searching for a "Subaru XV Crosstrek"
    # manual returned completely unrelated PDFs (a solar-charger manual, a
    # state DMV handbook) that used to pass the filter purely because the URL
    # ended in ".pdf", with no check that they had anything to do with the
    # product at all.
    results = [
        SearchResult(
            title="Manual - SmartShunt IP65",
            url="https://www.victronenergy.com/upload/documents/smartshunt-manual.pdf",
            snippet="", source="tavily",
        ),
        SearchResult(
            title="Subaru XV Crosstrek Owner's Manual",
            url="https://cdn.example.com/files/xv-crosstrek.pdf",
            snippet="", source="tavily",
        ),
    ]
    candidates = rank_candidates(results, brand="Subaru", model="XV Crosstrek")

    assert len(candidates) == 1
    assert candidates[0].url.endswith("xv-crosstrek.pdf")


def test_direct_pdf_link_outranks_aggregator_viewer_page():
    # Real-world case: ManualsLib's individual pages rank well but are HTML
    # viewers, not downloadable PDFs — a direct .pdf link should win even though
    # aggregator status alone would otherwise score higher.
    results = [
        SearchResult(
            title="Roborock S7 User Manual [Page 25] | ManualsLib",
            url="https://www.manualslib.com/manual/2295153/Roborock-S7.html?page=25",
            snippet="", source="tavily",
        ),
        SearchResult(
            title="Roborock S7 manual",
            url="https://cdn.example.com/files/s7.pdf",
            snippet="", source="tavily",
        ),
    ]
    candidates = rank_candidates(results, brand=None, model="S7")

    assert candidates[0].url.endswith(".pdf")
    assert "direct PDF link" in candidates[0].match_reasons
