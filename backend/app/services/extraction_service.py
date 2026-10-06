"""Pick the label fields out of the lines Tesseract read.

This file does not compare those fields with the application. It only reports
what it could read, and it leaves a field empty when it is not confident.
"""

import re

from PIL import Image

from app.models.extraction import ExtractedField, ExtractedLabel
from app.services.ocr_service import OcrLine, heading_is_bold, read_lines

# Free text such as a brand name needs a clearer reading than a number,
# because a number also has to match a pattern like "45%" or "750 mL".
TEXT_CONFIDENCE = 0.55
PATTERN_CONFIDENCE = 0.40
WARNING_CONFIDENCE = 0.35

ALCOHOL_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%", re.IGNORECASE)
NET_CONTENTS_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mL|ml|L|oz|fl\.?\s*oz)\b",
    re.IGNORECASE,
)
CLASS_PATTERN = re.compile(
    r"\b(?:whiskey|whisky|bourbon|vodka|gin|rum|tequila|brandy|wine|beer|ale|lager|stout|cognac|mezcal|liqueur|schnapps)\b",
    re.IGNORECASE,
)
WARNING_PATTERN = re.compile(r"government\s+warning", re.IGNORECASE)
STATE_PATTERN = re.compile(
    r"\b(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY)\b"
)
ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def read_label(image_bytes: bytes) -> ExtractedLabel:
    lines, image = read_lines(image_bytes)
    raw_text = "\n".join(line.text for line in lines)
    warning, remaining = _split_warning(lines, image)
    alcohol = _take_match(remaining, ALCOHOL_PATTERN, PATTERN_CONFIDENCE, prefer=r"alc")
    net_contents = _take_match(remaining, NET_CONTENTS_PATTERN, PATTERN_CONFIDENCE)
    class_type = _take_match(remaining, CLASS_PATTERN, TEXT_CONFIDENCE)
    producer_lines = [line for line in remaining if _looks_like_address(line.text)]
    for line in producer_lines:
        remaining.remove(line)
    brand = _take_tallest(remaining, TEXT_CONFIDENCE)
    producer = _join(producer_lines + remaining, TEXT_CONFIDENCE)
    return ExtractedLabel(
        brand_name=brand,
        class_type=class_type,
        alcohol_content=alcohol,
        net_contents=net_contents,
        producer=producer,
        government_warning=warning,
        raw_text=raw_text,
    )


def _split_warning(
    lines: list[OcrLine],
    image: Image.Image,
) -> tuple[ExtractedField, list[OcrLine]]:
    start = None
    for index, line in enumerate(lines):
        if WARNING_PATTERN.search(line.text):
            start = index
            break
        if re.fullmatch(r"government", line.text.strip(), re.IGNORECASE):
            following = lines[index + 1].text if index + 1 < len(lines) else ""
            if re.match(r"warning", following.strip(), re.IGNORECASE):
                start = index
                break
    if start is None:
        return ExtractedField(value=None, confidence=None), list(lines)
    warning_lines = lines[start:]
    warning = _join(warning_lines, WARNING_CONFIDENCE)
    if warning.value is not None:
        warning = warning.model_copy(update={"heading_bold": heading_is_bold(image, warning_lines)})
    return warning, list(lines[:start])


def _take_match(
    lines: list[OcrLine],
    pattern: re.Pattern[str],
    minimum: float,
    prefer: str | None = None,
) -> ExtractedField:
    matches = [line for line in lines if pattern.search(line.text)]
    if not matches:
        return ExtractedField(value=None, confidence=None)
    chosen = matches[0]
    if prefer:
        preferred = next(
            (line for line in matches if re.search(prefer, line.text, re.IGNORECASE)),
            None,
        )
        if preferred is not None:
            chosen = preferred
    lines.remove(chosen)
    return _accept(chosen, minimum)


def _take_tallest(lines: list[OcrLine], minimum: float) -> ExtractedField:
    if not lines:
        return ExtractedField(value=None, confidence=None)
    chosen = max(lines, key=lambda line: line.height)
    lines.remove(chosen)
    return _accept(chosen, minimum)


def _accept(line: OcrLine, minimum: float) -> ExtractedField:
    confidence = round(line.confidence, 2)
    if line.confidence < minimum:
        return ExtractedField(value=None, confidence=confidence)
    return ExtractedField(value=_clean(line.text), confidence=confidence)


def _join(lines: list[OcrLine], minimum: float) -> ExtractedField:
    if not lines:
        return ExtractedField(value=None, confidence=None)
    confidence = sum(line.confidence for line in lines) / len(lines)
    rounded = round(confidence, 2)
    if confidence < minimum:
        return ExtractedField(value=None, confidence=rounded)
    return ExtractedField(
        value=_clean(" ".join(line.text for line in lines)),
        confidence=rounded,
    )


def _looks_like_address(text: str) -> bool:
    has_state = STATE_PATTERN.search(text) is not None
    return ZIP_PATTERN.search(text) is not None or ("," in text and has_state)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
