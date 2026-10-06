import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import UnidentifiedImageError

from app.models.extraction import ExtractedLabel
from app.models.verification import VerificationResponse
from app.services.comparison_service import compare_label, overall_status, summary_message
from app.services.extraction_service import read_label
from app.services.ocr_service import OcrUnavailableError

router = APIRouter()

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")


def _is_image(upload: UploadFile) -> bool:
    if upload.content_type and upload.content_type.startswith("image/"):
        return True
    name = (upload.filename or "").lower()
    return name.endswith(IMAGE_SUFFIXES)


async def _image_bytes(image: UploadFile) -> bytes:
    if not _is_image(image):
        raise HTTPException(
            status_code=400,
            detail="Please choose a photo, such as a JPG or PNG.",
        )
    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail="The photo file was empty.")
    return contents


def _read_or_reject(contents: bytes) -> ExtractedLabel:
    try:
        return read_label(contents)
    except OcrUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="The label reader is not installed on the server.",
        ) from None
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail="Please choose a photo, such as a JPG or PNG.",
        ) from None


@router.post("/extract", response_model=ExtractedLabel)
async def extract_label(image: UploadFile = File(...)) -> ExtractedLabel:
    """Read one label photo and return the fields found on it.

    This does not compare those fields with an application.
    """
    return _read_or_reject(await _image_bytes(image))


@router.post("/verify", response_model=VerificationResponse)
async def verify_label(
    image: UploadFile = File(...),
    brand_name: str = Form(...),
    class_type: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(...),
    producer: str = Form(...),
) -> VerificationResponse:
    """Read the label and compare it with the application."""
    started = time.perf_counter()
    contents = await _image_bytes(image)
    extracted = _read_or_reject(contents)
    fields = compare_label(
        {
            "brand_name": brand_name,
            "class_type": class_type,
            "alcohol_content": alcohol_content,
            "net_contents": net_contents,
            "producer": producer,
        },
        extracted,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return VerificationResponse(
        image_name=image.filename or "label",
        message=summary_message(fields, elapsed_ms),
        overall_status=overall_status(fields),
        processing_ms=elapsed_ms,
        fields=fields,
    )
