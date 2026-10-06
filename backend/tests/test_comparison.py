from app.models.extraction import ExtractedField, ExtractedLabel
from app.services.comparison_service import compare_label, overall_status


def _label(**overrides: ExtractedField) -> ExtractedLabel:
    fields = {
        "brand_name": ExtractedField(value="OLD TOM DISTILLERY", confidence=0.96),
        "class_type": ExtractedField(
            value="Kentucky Straight Bourbon Whiskey",
            confidence=0.95,
        ),
        "alcohol_content": ExtractedField(value="45% Alc./Vol. (90 Proof)", confidence=0.94),
        "net_contents": ExtractedField(value="750 mL", confidence=0.95),
        "producer": ExtractedField(value="Old Tom Distillery, Louisville, KY", confidence=0.96),
        "government_warning": ExtractedField(
            value=(
                "GOVERNMENT WARNING: (1) According to the Surgeon General, women should "
                "not drink alcoholic beverages during pregnancy because of the risk of "
                "birth defects. (2) Consumption of alcoholic beverages impairs your "
                "ability to drive a car or operate machinery, and may cause health problems."
            ),
            confidence=0.96,
            heading_bold=True,
        ),
    }
    fields.update(overrides)
    return ExtractedLabel(raw_text="", **fields)


def _application(**overrides: str) -> dict[str, str]:
    values = {
        "brand_name": "OLD TOM DISTILLERY",
        "class_type": "Kentucky Straight Bourbon Whiskey",
        "alcohol_content": "45%",
        "net_contents": "750 mL",
        "producer": "Old Tom Distillery, Louisville, KY",
    }
    values.update(overrides)
    return values


def _by_label(fields, label: str):
    return next(field for field in fields if field.label == label)


def test_matching_label_passes() -> None:
    fields = compare_label(_application(), _label())

    assert overall_status(fields) == "MATCH"
    assert all(field.status == "MATCH" for field in fields)


def test_capitalization_is_not_a_mismatch() -> None:
    fields = compare_label(
        _application(brand_name="Stone's Throw"),
        _label(brand_name=ExtractedField(value="STONE'S THROW", confidence=0.97)),
    )
    brand = _by_label(fields, "Brand name")

    assert brand.status == "MATCH"
    assert "capitalization" in brand.note.lower() or "punctuation" in brand.note.lower()


def test_different_brand_is_a_mismatch() -> None:
    fields = compare_label(
        _application(brand_name="STONE'S THROW"),
        _label(),
    )

    assert _by_label(fields, "Brand name").status == "MISMATCH"
    assert overall_status(fields) == "MISMATCH"


def test_alcohol_number_is_compared() -> None:
    match = compare_label(_application(alcohol_content="90 proof"), _label())
    mismatch = compare_label(_application(alcohol_content="40%"), _label())

    assert _by_label(match, "Alcohol content").status == "MATCH"
    assert _by_label(mismatch, "Alcohol content").status == "MISMATCH"
    assert "40%" in _by_label(mismatch, "Alcohol content").note
    assert "45%" in _by_label(mismatch, "Alcohol content").note


def test_volume_ignores_spacing_and_unit_form() -> None:
    fields = compare_label(_application(net_contents="750ml"), _label())

    assert _by_label(fields, "Net contents").status == "MATCH"


def test_different_volume_is_a_mismatch() -> None:
    fields = compare_label(_application(net_contents="1 L"), _label())

    assert _by_label(fields, "Net contents").status == "MISMATCH"


def test_unreadable_field_needs_review() -> None:
    fields = compare_label(
        _application(),
        _label(brand_name=ExtractedField(value=None, confidence=None)),
    )
    brand = _by_label(fields, "Brand name")

    assert brand.status == "REVIEW"
    assert brand.label_value is None
    assert overall_status(fields) == "REVIEW"


def test_uncertain_reading_is_not_treated_as_certain() -> None:
    fields = compare_label(
        _application(),
        _label(brand_name=ExtractedField(value="OLD TOM DISTILLERY", confidence=0.6)),
    )

    assert _by_label(fields, "Brand name").status == "REVIEW"


def test_missing_warning_needs_review() -> None:
    fields = compare_label(
        _application(),
        _label(government_warning=ExtractedField(value=None, confidence=None)),
    )
    warning = _by_label(fields, "Government warning")

    assert warning.status == "REVIEW"
    assert "warning" in warning.note.lower()


def test_warning_heading_must_be_all_caps() -> None:
    warning = _by_label(compare_label(_application(), _label()), "Government warning").label_value
    assert warning is not None
    title_case = "Government Warning:" + warning.split(":", 1)[1]
    fields = compare_label(
        _application(),
        _label(
            government_warning=ExtractedField(value=title_case, confidence=0.96, heading_bold=True)
        ),
    )
    result = _by_label(fields, "Government warning")

    assert result.status == "MISMATCH"
    assert "capital" in result.note.lower()


def test_warning_wording_must_match_exactly() -> None:
    warning = _by_label(compare_label(_application(), _label()), "Government warning").label_value
    assert warning is not None
    changed = warning.replace("health problems", "health issues")
    fields = compare_label(
        _application(),
        _label(government_warning=ExtractedField(value=changed, confidence=0.96, heading_bold=True)),
    )
    result = _by_label(fields, "Government warning")

    assert result.status == "MISMATCH"
    assert "official wording" in result.note.lower()


def test_regular_warning_heading_is_not_a_match() -> None:
    warning = _by_label(compare_label(_application(), _label()), "Government warning").label_value
    fields = compare_label(
        _application(),
        _label(
            government_warning=ExtractedField(value=warning, confidence=0.96, heading_bold=False)
        ),
    )
    result = _by_label(fields, "Government warning")

    assert result.status == "MISMATCH"
    assert "bold" in result.note.lower()


def test_unknown_bold_heading_needs_review() -> None:
    warning = _by_label(compare_label(_application(), _label()), "Government warning").label_value
    fields = compare_label(
        _application(),
        _label(government_warning=ExtractedField(value=warning, confidence=0.96, heading_bold=None)),
    )
    result = _by_label(fields, "Government warning")

    assert result.status == "REVIEW"
    assert "bold" in result.note.lower()
