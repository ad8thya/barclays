from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import scipy.sparse as sp

from utils.features import extract_meta, extract_signals, extract_flagged

app = FastAPI()

# ==========================================
# LOAD MODEL
# ==========================================
vectorizer = pickle.load(open("model/crossshield_tfidf_updated.pkl", "rb"))
model = pickle.load(open("model/crossshield_xgb_updated.pkl", "rb"))
print(type(model))
print(type(vectorizer))

# ==========================================
# REQUEST SCHEMA
# ==========================================
class EmailRequest(BaseModel):
    incident_id: str
    subject: str
    body: str
    sender: str

# ==========================================
# LABEL MAP
# ==========================================
label_map = {
    0: "Official",
    1: "Suspicious",
    2: "Phishing"
}

# ==========================================
# ENDPOINT
# ==========================================
@app.post("/analyze/email")
async def analyze_email(req: EmailRequest):

    try:
        # ==========================
        # PREP INPUT
        # ==========================
        text = f"{req.subject} {req.body}"

        # TF-IDF features
        tfidf = vectorizer.transform([text])

        # Meta features
        meta = extract_meta(text)

        # Combine features
        X = sp.hstack([tfidf, meta])

        # ==========================
        # MODEL PREDICTION
        # ==========================
        pred = int(model.predict(X)[0])
        prob = model.predict_proba(X)[0]
        print("TFIDF shape:", tfidf.shape)
        print("Meta shape:", meta.shape)

        # ==========================
        # SIGNALS
        # ==========================
        signals = extract_signals(text, req.sender)
        flagged = extract_flagged(text)

        # ==========================
        # 🔥 BALANCED RISK SCORING
        # ==========================

        # 1. MODEL RISK
        model_risk = float(0.7 * prob[2] + 0.3 * prob[1])  # was 0.6/0.4

        # 2. ATTACK SCORE (positive risk)
        attack_score = 0.0

        if signals["credential_request_context"]:
            attack_score += 0.30
        elif signals["credential_request"]:
            attack_score += 0.15

        if signals["sender_domain_mismatch"]:
            attack_score += 0.25

        if signals["urgency_detected"]:
            attack_score += 0.10

        if signals["link_present"]:
            attack_score += 0.10

        # continuous domain similarity contribution
        attack_score += 0.25 * signals["domain_similarity_score"]

        # 3. TRUST SCORE (negative risk)
        # Replace the trust score block with this:
        trust_score = 0.0

        if not signals["sender_domain_mismatch"] and signals["domain_similarity_score"] == 0:
            trust_score += 0.20  # reduced from 0.50

        if not signals["credential_request_context"]:
            trust_score += 0.10  # reduced from 0.15

        if not signals["urgency_detected"]:
            trust_score += 0.05  # reduced from 0.10

        if not signals["link_present"]:
            trust_score += 0.10  # keep — no link is genuinely safe signal

        if signals["generic_greeting"]:
            trust_score -= 0.05

        # ==========================
        # FINAL RISK SCORE
        # ==========================
        risk_score = model_risk + attack_score - trust_score
        risk_score = max(0.0, min(1.0, risk_score))

        # ==========================
        # RESPONSE
        # ==========================
        return {
            "success": True,
            "incident_id": req.incident_id,
            "layer": "email",
            "data": {
                "risk_score": round(risk_score, 2),
                "label": label_map[pred],
                "flagged_phrases": flagged,
                "signals": signals,
                "model_confidence": round(float(max(prob)), 3),
                "model_used": "xgboost_v3_balanced"
            },
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "incident_id": req.incident_id,
            "layer": "email",
            "data": None,
            "error": str(e)
        }