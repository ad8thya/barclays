from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
import os
import pickle
import scipy.sparse as sp

# Load email model utils under renamed folder to avoid conflict with barclays/utils/
_model_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'services', 'email_model')
)
sys.path.insert(0, _model_dir)

from email_utils.features import extract_meta, extract_signals, extract_flagged

router = APIRouter()

_pkl_dir    = os.path.join(_model_dir, 'model')
_model      = pickle.load(open(os.path.join(_pkl_dir, 'xgb_model.pkl'), 'rb'))
_vectorizer = pickle.load(open(os.path.join(_pkl_dir, 'tfidf_vectorizer.pkl'), 'rb'))

LABEL_MAP = {0: "Official", 1: "Suspicious", 2: "Phishing"}

class EmailRequest(BaseModel):
    incident_id: str
    subject: str
    body: str
    sender: Optional[str] = ""

@router.post("/analyze/email")
async def analyze_email(req: EmailRequest):
    try:
        print("working right")
        text  = f"{req.subject} {req.body}"
        tfidf = _vectorizer.transform([text])
        meta  = extract_meta(text)
        X     = sp.hstack([tfidf, meta])

        pred  = int(_model.predict(X)[0])
        prob  = _model.predict_proba(X)[0]

        risk_score = float(max(prob))
        signals    = extract_signals(text, req.sender)
        flagged    = extract_flagged(text)

        return {
            "success":     True,
            "incident_id": req.incident_id,
            "layer":       "email",
            "data": {
                "risk_score":       round(risk_score, 2),
                "label":            LABEL_MAP[pred],
                "flagged_phrases":  flagged,
                "signals":          signals,
                "model_confidence": round(risk_score, 3),
                "model_used":       "xgboost_v1",
            },
            "error": None
        }

    except Exception as e:
        return _fallback(req, str(e))


def _fallback(req, error_msg):
    score, signals, flagged = 0.0, {}, []
    text = (req.subject + " " + req.body).lower()
    print("debug check")
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
        "success":     True,
        "incident_id": req.incident_id,
        "layer":       "email",
        "data": {
            "risk_score":       round(min(1.0, score), 2),
            "label":            "Suspicious" if score > 0.4 else "Official",
            "flagged_phrases":  flagged,
            "signals":          signals,
            "model_confidence": round(min(1.0, score), 3),
            "model_used":       "rule_based_fallback",
        },
        "error": f"Model unavailable: {error_msg}"
    }