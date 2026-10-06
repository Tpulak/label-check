"""Compare the application with the words read from the label.

A capitalization difference is a match for ordinary fields. A clear disagreement
is a mismatch. Anything uncertain, including a weak photo reading, needs a person
to look.

The government warning is stricter. It must be the official text, the heading
must be GOVERNMENT WARNING in all capitals, and that heading must be bold.
"""

import re

from rapidfuzz import fuzz

from app.models.extraction import ExtractedField, ExtractedLabel
from app.models.verification import FieldResult, FieldStatus

# A reading below this can look right and still be wrong, so a person should check it.
CONFIDENT_READING = 0.8

OFFICIAL_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


def compare_label(application: dict[str, str], extracted: ExtractedLabel) -> list[FieldResult]:
    return [
        _text_result("Brand name", application["brand_name"], extracted.brand_name),
        _text_result("Class / type", application["class_type"], extracted.class_type),
        _alcohol_result(application["alcohol_content"], extracted.alcohol_content),
        _volume_result(application["net_contents"], extracted.net_contents),
        _text_result("Producer name and address", application["producer"], extracted.producer),
        _warning_result(extracted.government_warning),
    ]


def overall_status(fields: list[FieldResult]) -> FieldStatus:
    statuses = {field.status for field in fields}
    if "MISMATCH" in statuses:
        return "MISMATCH"
    if "REVIEW" in statuses:
        return "REVIEW"
    return "MATCH"


def summary_message(fields: list[FieldResult], elapsed_ms: int) -> str:
    mismatch = sum(field.status == "MISMATCH" for field in fields)
    review = sum(field.status == "REVIEW" for field in fields)
    matched = sum(field.status == "MATCH" for field in fields)
    timing = f"Checked in {elapsed_ms / 1000:.1f} seconds."
    if mismatch and review:
        return (
            f"{_count(mismatch, 'field does not match', 'fields do not match')}. "
            f"{_count(review, 'field needs a person to look', 'fields need a person to look')}. "
            f"{timing}"
        )
    if mismatch:
        return f"{_count(mismatch, 'field does not match', 'fields do not match')}. {timing}"
    if review:
        return (
            f"{_count(review, 'field needs a person to look', 'fields need a person to look')}. "
            f"{_count(matched, 'field matches', 'fields match')}. "
            f"{timing}"
        )
    return f"All {_count(matched, 'field matches', 'fields match')}. {timing}"


def _text_result(label: str, application_value: str, extracted: ExtractedField) -> FieldResult:
    status, note = _compare_text(application_value, extracted.value)
    status, note = _apply_confidence(status, note, extracted.confidence)
    return _field(label, application_value, extracted.value, status, note)


def _alcohol_result(application_value: str, extracted: ExtractedField) -> FieldResult:
    status, note = _compare_alcohol(application_value, extracted.value)
    status, note = _apply_confidence(status, note, extracted.confidence)
    return _field("Alcohol content", application_value, extracted.value, status, note)


def _volume_result(application_value: str, extracted: ExtractedField) -> FieldResult:
    status, note = _compare_volume(application_value, extracted.value)
    status, note = _apply_confidence(status, note, extracted.confidence)
    return _field("Net contents", application_value, extracted.value, status, note)


def _warning_result(extracted: ExtractedField) -> FieldResult:
    status, note = _compare_warning(extracted.value, extracted.heading_bold)
    status, note = _apply_confidence(status, note, extracted.confidence)
    return _field("Government warning", "Required on the label", extracted.value, status, note)


def _compare_text(application_value: str, label_value: str | None) -> tuple[FieldStatus, str]:
    if not label_value:
        return "REVIEW", "Could not confidently read this from the photo."
    if not application_value.strip():
        return "REVIEW", "The application field is empty."

    if _normalize(application_value) == _normalize(label_value):
        if application_value.strip() == label_value.strip():
            return "MATCH", "The values match."
        return "MATCH", "Only capitalization or punctuation is different."

    score = _similarity(application_value, label_value)
    if score >= 0.9:
        return "REVIEW", "The values are close. A person should confirm them."
    if score >= 0.7:
        return "REVIEW", "The values are similar. A person should confirm them."
    return (
        "MISMATCH",
        f"The application says {application_value}. The label says {label_value}.",
    )


def _compare_alcohol(application_value: str, label_value: str | None) -> tuple[FieldStatus, str]:
    if not label_value:
        return "REVIEW", "Could not confidently read the alcohol content from the photo."
    application_percent = _alcohol_percent(application_value)
    label_percent = _alcohol_percent(label_value)
    if application_percent is None:
        return "REVIEW", "Enter the alcohol content as a percentage, such as 45%."
    if label_percent is None:
        return "REVIEW", "The alcohol content on the label could not be read as a percentage."
    if abs(application_percent - label_percent) <= 0.1:
        shown = _format_percent(application_percent)
        return "MATCH", f"Both show {shown} alcohol."
    return (
        "MISMATCH",
        f"The application shows {_format_percent(application_percent)} alcohol. "
        f"The label shows {_format_percent(label_percent)} alcohol.",
    )


def _compare_volume(application_value: str, label_value: str | None) -> tuple[FieldStatus, str]:
    if not label_value:
        return "REVIEW", "Could not confidently read the net contents from the photo."
    application_ml = _to_milliliters(application_value)
    label_ml = _to_milliliters(label_value)
    if application_ml is None:
        return "REVIEW", "Enter the net contents with a unit, such as 750 mL."
    if label_ml is None:
        return "REVIEW", "The net contents on the label could not be read."
    if application_ml == 0 or abs(application_ml - label_ml) / application_ml <= 0.03:
        return "MATCH", f"Both show about {_format_ml(application_ml)}."
    return (
        "MISMATCH",
        f"The application says {application_value.strip()}. The label says {label_value.strip()}.",
    )


def _compare_warning(
    label_value: str | None,
    heading_bold: bool | None,
) -> tuple[FieldStatus, str]:
    if not label_value:
        return "REVIEW", "Unable to confidently read the government warning."

    label_text = _collapse(label_value)
    official_text = _collapse(OFFICIAL_WARNING)
    if label_text.casefold() != official_text.casefold():
        return "MISMATCH", "The government warning on the label does not match the official wording."
    if not _heading_is_all_caps(label_text):
        return "MISMATCH", "The heading must be GOVERNMENT WARNING in all capital letters."
    if label_text != official_text:
        return "MISMATCH", "The warning must match the official wording exactly."
    if heading_bold is True:
        return "MATCH", "The warning matches the official wording, and the heading is bold."
    if heading_bold is False:
        return "MISMATCH", "The heading GOVERNMENT WARNING must be bold."
    return "REVIEW", "The wording matches, but it is not clear whether the heading is bold."


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _heading_is_all_caps(value: str) -> bool:
    heading = re.match(r"government\s+warning", value, re.IGNORECASE)
    if heading is None:
        return False
    letters = [character for character in heading.group(0) if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)


def _apply_confidence(
    status: FieldStatus,
    note: str,
    confidence: float | None,
) -> tuple[FieldStatus, str]:
    if status == "REVIEW" or confidence is None or confidence >= CONFIDENT_READING:
        return status, note
    if status == "MATCH":
        return "REVIEW", "The values look the same, but the photo reading is uncertain."
    return "REVIEW", "The values look different, but the photo reading is uncertain."


def _field(
    label: str,
    application_value: str,
    label_value: str | None,
    status: FieldStatus,
    note: str,
) -> FieldResult:
    return FieldResult(
        label=label,
        application_value=application_value,
        label_value=label_value,
        status=status,
        note=note,
    )


def _normalize(value: str) -> str:
    text = value.casefold().replace("’", "'").replace("‘", "'").replace("`", "'")
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _similarity(left: str, right: str) -> float:
    normalized_left = _normalize(left)
    normalized_right = _normalize(right)
    if not normalized_left or not normalized_right:
        return 0
    score = max(
        fuzz.ratio(normalized_left, normalized_right),
        fuzz.token_sort_ratio(normalized_left, normalized_right),
    )
    return score / 100


def _alcohol_percent(value: str) -> float | None:
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    if percent:
        return float(percent.group(1))
    proof = re.search(r"(\d+(?:\.\d+)?)\s*proof", value, re.IGNORECASE)
    if proof:
        return float(proof.group(1)) / 2
    bare = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", value)
    if bare:
        return float(bare.group(1))
    return None


def _to_milliliters(value: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|fl\.?\s*oz|oz)\b", value, re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1))
    unit = re.sub(r"[\s.]", "", match.group(2).lower())
    if unit == "ml":
        return amount
    if unit == "l":
        return amount * 1000
    return amount * 29.5735


def _format_percent(value: float) -> str:
    if value.is_integer():
        return f"{int(value)}%"
    return f"{value:g}%"


def _format_ml(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return f"{round(value)} mL"
    return f"{value:.1f} mL"


def _count(amount: int, singular: str, plural: str) -> str:
    return f"{amount} {singular if amount == 1 else plural}"
