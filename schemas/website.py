from pydantic import BaseModel
from typing import List, Optional

class WebsiteRequest(BaseModel):
    url: str


class WebsiteResponse(BaseModel):
    domain: str
    status_code: Optional[int] = None
    reachable: bool

    # 🔹 heuristic
    risk: str
    score: int

    # 🔹 fused output (IMPORTANT)
    final_score: int
    final_risk: str

    # 🔹 reasoning
    reasons: List[str] = []

    # 🔹 AI layers
    ai_analysis: Optional[str] = None
    js_analysis: Optional[str] = None

    # 🔹 meta
    confidence: int
    llm_risk: Optional[str] = None
    disagreement: Optional[bool] = None