from typing import Any, Optional
from pydantic import BaseModel


class EnvelopeResponse(BaseModel):
    success: bool
    incident_id: str
    layer: str
    data: Optional[Any] = None
    error: Optional[str] = None