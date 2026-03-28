from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import scipy.sparse as sp

from utils.features import extract_meta, extract_signals, extract_flagged

app = FastAPI()

# ==========================================
# LOAD MODEL
# ==========================================
model = pickle.load(open("model/xgb_model.pkl", "rb"))
vectorizer = pickle.load(open("model/tfidf_vectorizer.pkl", "rb"))

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
        # Combine input properly
        text = f"{req.subject} {req.body}"

        # TF-IDF features
        tfidf = vectorizer.transform([text])

        # Meta features
        meta = extract_meta(text)

        # Combine
        X = sp.hstack([tfidf, meta])

        # Model prediction (USES WEIGHTS)
        pred = int(model.predict(X)[0])
        prob = model.predict_proba(X)[0]

        # Extract signals + phrases
        signals = extract_signals(text, req.sender)
        flagged = extract_flagged(text)

        # Risk score
        risk_score = float(max(prob))

        # ==========================
        # FINAL CONTRACT RESPONSE
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
                "model_confidence": round(risk_score, 3),
                "model_used": "xgboost_v1"
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