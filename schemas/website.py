from pydantic import BaseModel
from typing import List, Optional

class WebsiteRequest(BaseModel):
    url: str

class WebsiteResponse(BaseModel):
    domain: str
    status_code: Optional[int] = None
    reachable: bool
    risk: str
    score: int
    reasons: List[str]