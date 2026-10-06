import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.extraction_service import read_label

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = ROOT / "test-data" / "valid-label.png"
WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(rf"C:\Windows\Fonts\{name}", size)


def make_valid_label() -> bytes:
    image = Image.new("RGB", (1200, 1700), "white")
    draw = ImageDraw.Draw(image)
    brand = _font("arialbd.ttf", 64)
    body = _font("arial.ttf", 40)
    small = _font("arial.ttf", 28)
    y = 90
    draw.text((80, y), "OLD TOM DISTILLERY", font=brand, fill="black")
    y += 130
    for line in (
        "Kentucky Straight Bourbon Whiskey",
        "45% Alc./Vol. (90 Proof)",
        "750 mL",
        "Old Tom Distillery, Louisville, KY",
    ):
        draw.text((80, y), line, font=body, fill="black")
        y += 80
    y += 30
    _draw_wrapped(draw, WARNING, small, 80, y, 1040)
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(SAMPLE_PATH, format="PNG")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    max_width: int,
) -> None:
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) > max_width and line:
            draw.text((x, y), line, font=font, fill="black")
            y += font.size + 10
            line = word
        else:
            line = trial
    if line:
        draw.text((x, y), line, font=font, fill="black")


def test_clear_label_fields_are_read() -> None:
    extracted = read_label(make_valid_label())

    assert extracted.brand_name.value is not None
    assert "OLD TOM" in extracted.brand_name.value.upper()
    assert extracted.class_type.value is not None
    assert "BOURBON" in extracted.class_type.value.upper()
    assert extracted.alcohol_content.value is not None
    assert "45" in extracted.alcohol_content.value
    assert extracted.net_contents.value is not None
    assert "750" in extracted.net_contents.value
    assert extracted.producer.value is not None
    assert "LOUISVILLE" in extracted.producer.value.upper()
    assert extracted.government_warning.value is not None
    warning = extracted.government_warning.value.upper()
    assert "GOVERNMENT WARNING" in warning
    assert "SURGEON" in warning
    assert extracted.government_warning.heading_bold is False


def test_bold_warning_heading_is_recognized() -> None:
    image = Image.new("RGB", (1200, 900), "white")
    draw = ImageDraw.Draw(image)
    bold = _font("arialbd.ttf", 32)
    body = _font("arial.ttf", 28)
    y = 80
    draw.text((80, y), "GOVERNMENT WARNING:", font=bold, fill="black")
    y += 70
    _draw_wrapped(
        draw,
        "(1) According to the Surgeon General, women should not drink alcoholic "
        "beverages during pregnancy because of the risk of birth defects. "
        "(2) Consumption of alcoholic beverages impairs your ability to drive a car "
        "or operate machinery, and may cause health problems.",
        body,
        80,
        y,
        1040,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    extracted = read_label(buffer.getvalue())

    assert extracted.government_warning.heading_bold is True


def test_blank_image_is_not_invented() -> None:
    image = Image.new("RGB", (800, 800), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    extracted = read_label(buffer.getvalue())

    assert extracted.brand_name.value is None
    assert extracted.alcohol_content.value is None
    assert extracted.government_warning.value is None
