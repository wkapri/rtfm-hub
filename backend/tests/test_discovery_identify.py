from hubapp.discovery.identify import _coerce_identification


def test_coerces_well_formed_data():
    result = _coerce_identification(
        {"brand": "Roborock", "model": "S7", "category": "vacuum", "year": 2022, "confidence": "high", "reasoning": "Exact match."}
    )

    assert result.brand == "Roborock"
    assert result.model == "S7"
    assert result.category == "vacuum"
    assert result.year == 2022
    assert result.confidence == "high"


def test_invalid_confidence_falls_back_to_low():
    result = _coerce_identification({"brand": "X", "model": "Y", "confidence": "very sure"})

    assert result.confidence == "low"


def test_missing_confidence_falls_back_to_low():
    result = _coerce_identification({"brand": "X", "model": "Y"})

    assert result.confidence == "low"


def test_non_integer_year_becomes_none():
    result = _coerce_identification({"brand": "X", "model": "Y", "year": "unknown"})

    assert result.year is None


def test_missing_fields_become_none_or_empty():
    result = _coerce_identification({})

    assert result.brand is None
    assert result.model is None
    assert result.category is None
    assert result.year is None
    assert result.confidence == "low"
    assert result.reasoning == ""


def test_null_brand_and_model_pass_through():
    result = _coerce_identification({"brand": None, "model": None, "confidence": "low", "reasoning": "Too vague."})

    assert result.brand is None
    assert result.model is None
