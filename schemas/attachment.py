# schemas/attachment.py
from pydantic import BaseModel
from typing import Optional
from schemas.base import EnvelopeResponse  # import whatever base.py exports

class AttachmentData(BaseModel):
    extracted_text: str
    file_type: str          # "pdf", "image", "unsupported"
    page_count: Optional[int] = None   # PDFs only
    char_count: int
    flags: list[str]
    risk_score: float       # 0.0 to 1.0
    reason: str

class AttachmentResponse(EnvelopeResponse):
    layer: str = "attachment"
    data: Optional[AttachmentData] = None