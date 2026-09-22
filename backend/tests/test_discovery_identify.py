import pytest

from hubapp.discovery.identify import IdentifyError, _parse_response


def test_parses_well_formed_json():
    raw = """{
        "brand": "Roborock", "model": "S7", "category": "vacuum",
        "year": 2022, "confidence": "high", "reasoning": "Exact match in results."
    }"""
    result = _parse_response(raw)

    assert result.brand == "Roborock"
    assert result.model == "S7"
    assert result.category == "vacuum"
    assert result.year == 2022
    assert result.confidence == "high"


def test_extracts_json_even_with_surrounding_text():
    raw = 'Sure, here is the identification:\n{"brand": "iRobot", "model": "Roomba j7", "category": null, "year": null, "confidence": "medium", "reasoning": "x"}\nHope that helps!'
    result = _parse_response(raw)

    assert result.brand == "iRobot"
    assert result.model == "Roomba j7"
    assert result.confidence == "medium"


def test_invalid_confidence_falls_back_to_low():
    raw = '{"brand": "X", "model": "Y", "category": null, "year": null, "confidence": "very sure", "reasoning": "x"}'
    result = _parse_response(raw)

    assert result.confidence == "low"


def test_non_integer_year_becomes_none():
    raw = '{"brand": "X", "model": "Y", "category": null, "year": "unknown", "confidence": "low", "reasoning": "x"}'
    result = _parse_response(raw)

    assert result.year is None


def test_no_json_raises_identify_error():
    with pytest.raises(IdentifyError):
        _parse_response("I'm not sure, sorry, no JSON here.")


def test_malformed_json_raises_identify_error():
    with pytest.raises(IdentifyError):
        _parse_response("{brand: Roborock, not valid json}")
