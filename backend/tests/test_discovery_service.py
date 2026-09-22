from hubapp.discovery.service import _coerce_candidates, _mentions_product, _safe_filename


def test_strips_unsafe_characters():
    assert _safe_filename("Roborock S7 Owner's Manual: 2022/Rev-A") == "Roborock S7 Owners Manual 2022Rev-A"


def test_falls_back_to_manual_when_empty():
    assert _safe_filename("***") == "manual"


def test_truncates_long_names():
    assert len(_safe_filename("x" * 200)) == 80


def test_mentions_product_matches_brand_case_insensitively():
    assert _mentions_product("This is the ROBOROCK vacuum guide", brand="Roborock", model=None)


def test_mentions_product_matches_model():
    assert _mentions_product("Setup instructions for model S7", brand=None, model="S7")


def test_mentions_product_false_for_unrelated_text():
    # The real-world case this guards against: a candidate titled "Roborock S7"
    # that actually resolved to an unrelated US Sentencing Commission PDF.
    text = "United States Sentencing Commission Guidelines Manual 2025"
    assert not _mentions_product(text, brand="Roborock", model="S7")


def test_mentions_product_false_when_neither_given():
    assert not _mentions_product("anything at all", brand=None, model=None)


def test_coerce_candidates_builds_candidate_objects():
    data = {"candidates": [{"title": "S7 Manual", "url": "https://roborock.com/s7.pdf", "reasoning": "Direct PDF."}]}

    candidates = _coerce_candidates(data, max_results=3)

    assert len(candidates) == 1
    assert candidates[0].url == "https://roborock.com/s7.pdf"
    assert candidates[0].domain == "roborock.com"
    assert candidates[0].match_reasons == ["Direct PDF."]


def test_coerce_candidates_skips_non_dict_entries():
    # Real bug found via live testing: the model returned a bare URL string
    # instead of the {title, url, reasoning} object it was asked for.
    data = {"candidates": ["https://roborock.com/s7.pdf", {"title": "OK", "url": "https://x.com/a.pdf"}]}

    candidates = _coerce_candidates(data, max_results=3)

    assert len(candidates) == 1
    assert candidates[0].url == "https://x.com/a.pdf"


def test_coerce_candidates_skips_entries_missing_url():
    data = {"candidates": [{"title": "No URL here"}]}

    assert _coerce_candidates(data, max_results=3) == []


def test_coerce_candidates_handles_missing_or_empty_list():
    assert _coerce_candidates({}, max_results=3) == []
    assert _coerce_candidates({"candidates": []}, max_results=3) == []
