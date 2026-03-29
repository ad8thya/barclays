from pydantic import BaseModel
from typing import Optional
from schemas.base import EnvelopeResponse

class AttachmentData(BaseModel):
    extracted_text: str
    file_type: str
    page_count: Optional[int] = None
    char_count: int
    flags: list[str]
    risk_score: float
    reason: str
    email_subject:    Optional[str]   = None
    email_sender:     Optional[str]   = None
    email_risk_score: Optional[float] = None
    email_label:      Optional[str]   = None
    email_signals:    Optional[dict]  = None
    email_flagged:    Optional[list]  = None

class AttachmentResponse(EnvelopeResponse):
    layer: str = "attachment"
    data: Optional[AttachmentData] = None