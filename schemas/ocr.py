from pydantic import BaseModel
from typing import Optional
from schemas.base import EnvelopeResponse

class OCRData(BaseModel):
    text: str
    confidence: float   # OCR confidence
    lang: str
    risk_score: float   # 🔥 scam probability
    reason: str         # explanation

class OCRResponse(EnvelopeResponse):
    layer: str = "ocr"
    data: Optional[OCRData] = None