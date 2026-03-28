from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import httpx

router = APIRouter()

EMAIL_MODEL_URL = "http://localhost:8001/analyze/email"

class EmailRequest(BaseModel):
    incident_id: str
    subject: str
    body: str
    sender: Optional[str] = ""

@router.post("/analyze/email")
async def analyze_email(req: EmailRequest):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(EMAIL_MODEL_URL, json={
                "incident_id": req.incident_id,
                "subject":     req.subject,
                "body":        req.body,
                "sender":      req.sender,
            })
            return res.json()

    except Exception as e:
        # Model service down — rule-based fallback so app never breaks
        return _rule_based_fallback(req, str(e))


def _rule_based_fallback(req, error_msg):
    score, signals, flagged = 0.0, {}, []
    text = (req.subject + " " + req.body).lower()

    urgency = ["urgent", "immediately", "verify", "suspended",
               "click here", "confirm your", "unusual activity", "account locked"]
    found = [p for p in urgency if p in text]
    if found:
        score += min(0.4, len(found) * 0.1)
        flagged.extend(found)
        signals["urgency_phrases"] = True

    if req.sender:
        if any(l in req.sender.lower() for l in ["barcl4ys", "barclays-", "secure-barclays"]):
            score += 0.3
            signals["lookalike_domain"] = True
        if any(t in req.sender for t in [".xyz", ".tk", ".top", ".click"]):
            score += 0.2
            signals["suspicious_tld"] = True

    if "http" in req.body.lower():
        score += 0.15
        signals["contains_link"] = True

    if any(w in text for w in ["password", "pin", "otp", "cvv"]):
        score += 0.2
        signals["credential_request"] = True

    return {
        "success": True,
        "incident_id": req.incident_id,
        "layer": "email",
        "data": {
            "risk_score":        round(min(1.0, score), 2),
            "label":             "Suspicious" if score > 0.4 else "Official",
            "flagged_phrases":   flagged,
            "signals":           signals,
            "model_confidence":  round(min(1.0, score), 3),
            "model_used":        "rule_based_fallback",
        },
        "error": f"Model service unavailable: {error_msg}"
    }