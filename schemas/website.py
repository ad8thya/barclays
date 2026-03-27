from pydantic import BaseModel, Field
from typing import List, Optional


class WebsiteRequest(BaseModel):
    url: str


class SandboxData(BaseModel):
    redirects: int
    external_scripts: int
    forms: int
    has_password_field: bool
    uses_https: bool
    external_links: int


class WebsiteResponse(BaseModel):
    domain: str
    status_code: Optional[int] = None
    reachable: bool

    # heuristic
    risk: str
    score: int

    # fused
    final_score: int
    final_risk: str

    # sandbox 🔥
    sandbox: SandboxData

    # reasoning
    reasons: List[str] = Field(default_factory=list)

    # AI
    ai_analysis: Optional[str] = None
    js_analysis: Optional[str] = None

    # meta
    confidence: int = 100
    llm_risk: Optional[str] = "UNKNOWN"
    disagreement: Optional[bool] = False