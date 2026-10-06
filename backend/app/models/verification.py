from typing import Literal

from pydantic import BaseModel

FieldStatus = Literal["MATCH", "MISMATCH", "REVIEW"]


class FieldResult(BaseModel):
    label: str
    application_value: str
    label_value: str | None
    status: FieldStatus
    note: str


class VerificationResponse(BaseModel):
    image_name: str
    message: str
    overall_status: FieldStatus
    processing_ms: int
    fields: list[FieldResult]
