from pydantic import BaseModel


class ExtractedField(BaseModel):
    value: str | None
    confidence: float | None
    # Only the government-warning heading uses this. True means the heading
    # letters are bold, False means they are regular, and None means the photo
    # does not show which.
    heading_bold: bool | None = None


class ExtractedLabel(BaseModel):
    brand_name: ExtractedField
    class_type: ExtractedField
    alcohol_content: ExtractedField
    net_contents: ExtractedField
    producer: ExtractedField
    government_warning: ExtractedField
    raw_text: str
