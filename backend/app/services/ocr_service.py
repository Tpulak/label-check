"""Turn a label photo into lines of text.

Tesseract is a separate program installed on the computer. This file prepares
the photo, then asks Tesseract to read it. It does not decide whether the
label matches the application.
"""

import io
import os
import re

import pytesseract
from PIL import Image, ImageFilter, ImageOps

WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class OcrUnavailableError(Exception):
    """Raised when the Tesseract program is not installed."""


class OcrWord:
    def __init__(self, text: str, left: int, top: int, width: int, height: int) -> None:
        self.text = text
        self.left = left
        self.top = top
        self.width = width
        self.height = height


class OcrLine:
    def __init__(self, text: str, confidence: float, height: int, words: list[OcrWord]) -> None:
        self.text = text
        self.confidence = confidence
        self.height = height
        self.words = words


def _configure_tesseract() -> None:
    configured = os.environ.get("TESSERACT_CMD")
    if configured:
        pytesseract.pytesseract.tesseract_cmd = configured
        return
    if os.path.exists(WINDOWS_TESSERACT):
        pytesseract.pytesseract.tesseract_cmd = WINDOWS_TESSERACT


_configure_tesseract()


def prepare_image(image_bytes: bytes) -> Image.Image:
    """Make the photo easier to read without changing the words."""
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)))
    image = image.convert("L")
    short_side = min(image.size)
    if short_side < 1000:
        scale = 1000 / short_side
        image = image.resize(
            (int(image.width * scale), int(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.SHARPEN)
    return _deskew(image)


def read_lines(image_bytes: bytes) -> tuple[list[OcrLine], Image.Image]:
    """Read the photo. Also return the prepared image, so later checks can look at the letters."""
    image = prepare_image(image_bytes)
    lines = _read_prepared(image)
    if _word_count(lines) >= 8:
        return lines, image

    rotated = _rotate_upright(image)
    if rotated is None:
        return lines, image
    rotated_lines = _read_prepared(rotated)
    if _word_count(rotated_lines) > _word_count(lines):
        return rotated_lines, rotated
    return lines, image


def _read_prepared(image: Image.Image) -> list[OcrLine]:
    try:
        raw = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
            config="--oem 1 --psm 4",
            timeout=8,
        )
    except pytesseract.TesseractNotFoundError as error:
        raise OcrUnavailableError from error
    except (pytesseract.TesseractError, RuntimeError):
        return []

    grouped: dict[tuple[int, int, int], list[tuple[OcrWord, float]]] = {}
    order: list[tuple[int, int, int]] = []
    for index, word in enumerate(raw["text"]):
        text = (word or "").strip()
        if not text:
            continue
        try:
            confidence = float(raw["conf"][index])
        except (TypeError, ValueError):
            continue
        if confidence < 0:
            continue
        key = (
            int(raw["block_num"][index]),
            int(raw["par_num"][index]),
            int(raw["line_num"][index]),
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(
            (
                OcrWord(
                    text,
                    int(raw["left"][index]),
                    int(raw["top"][index]),
                    int(raw["width"][index]),
                    int(raw["height"][index]),
                ),
                confidence,
            )
        )

    lines: list[OcrLine] = []
    for key in order:
        words = grouped[key]
        lines.append(
            OcrLine(
                text=" ".join(word.text for word, _ in words),
                confidence=sum(confidence for _, confidence in words) / len(words) / 100,
                height=max(word.height for word, _ in words),
                words=[word for word, _ in words],
            )
        )
    return lines


def _word_count(lines: list[OcrLine]) -> int:
    return sum(len(line.text.split()) for line in lines)


# Measured on Arial headings. Bold "GOVERNMENT WARNING" fills about half of its
# letter area. Regular type stays under 0.40. The gap in between is too close to call.
CONFIRMED_BOLD_DENSITY = 0.45
CONFIRMED_REGULAR_DENSITY = 0.40


def heading_is_bold(image: Image.Image, lines: list[OcrLine]) -> bool | None:
    """Look at the ink in GOVERNMENT WARNING. None means the photo does not show the weight."""
    words = _heading_words(lines)
    if len(words) != 2:
        return None
    density = _ink_density(image, words)
    if density is None:
        return None
    if density >= CONFIRMED_BOLD_DENSITY:
        return True
    if density <= CONFIRMED_REGULAR_DENSITY:
        return False
    return None


def _heading_words(lines: list[OcrLine]) -> list[OcrWord]:
    found: list[OcrWord] = []
    expected = ("GOVERNMENT", "WARNING")
    started = False
    for line in lines:
        for word in line.words:
            letters = re.sub(r"[^A-Za-z]", "", word.text).upper()
            if len(found) < len(expected) and letters == expected[len(found)]:
                found.append(word)
                started = True
                if len(found) == len(expected):
                    return found
            elif started:
                return found
    return found


def _ink_density(image: Image.Image, words: list[OcrWord]) -> float | None:
    import numpy as np

    left = max(0, min(word.left for word in words))
    top = max(0, min(word.top for word in words))
    right = min(image.width, max(word.left + word.width for word in words))
    bottom = min(image.height, max(word.top + word.height for word in words))
    if right - left < 8 or bottom - top < 8:
        return None
    crop = np.array(image.crop((left, top, right, bottom)))
    ink = crop < 180
    rows, columns = np.where(ink)
    if len(columns) < 30:
        return None
    tight = ink[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]
    return float(tight.mean())


def _rotate_upright(image: Image.Image) -> Image.Image | None:
    """Turn a sideways photo upright. Small tilts are handled by deskew."""
    try:
        report = pytesseract.image_to_osd(image, timeout=5)
    except Exception:
        return None
    match = re.search(r"Rotate:\s+(\d+)", report)
    if not match:
        return None
    angle = int(match.group(1))
    if angle not in (90, 180, 270):
        return None
    return image.rotate(angle, expand=True, fillcolor=255)


def _deskew(image: Image.Image) -> Image.Image:
    """Straighten a slight tilt. Leave the photo alone when the angle is unclear."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return image

    pixels = np.array(image)
    ys, xs = np.where(pixels < 200)
    ink = np.column_stack((xs, ys)).astype("float32")
    if len(ink) < 100:
        return image

    angle = cv2.minAreaRect(ink)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5 or abs(angle) > 12:
        return image

    center = (image.width / 2, image.height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        pixels,
        matrix,
        (image.width, image.height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return Image.fromarray(rotated)
