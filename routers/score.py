from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from services.graph_service import store_incident, find_correlated_incidents, get_graph_score, build_graph

router = APIRouter()

class ScoreRequest(BaseModel):
    incident_id: str
    account_id: str
    email_score: float
    website_score: float
    attachment_score: float
    audio_score: float
    domains: List[str] = []
    ips: List[str] = []

@router.post("/analyze/score")
async def analyze_score(req: ScoreRequest):

    # Step 1 - store signals first so graph can see them
    signals = {"domains": req.domains, "ips": req.ips}
    scores = {
        "email": req.email_score,
        "website": req.website_score,
        "attachment": req.attachment_score,
        "audio": req.audio_score,
        "final": 0.0  # placeholder, updated below
    }
    store_incident(req.incident_id, req.account_id, scores, signals)

    # Step 2 - now graph can correlate including this incident
    graph_score = get_graph_score(req.incident_id)
    graph_data = find_correlated_incidents(req.incident_id)

    # Step 3 - calculate frs with real graph score
    frs = (0.35 * req.email_score + 0.25 * req.website_score +
           0.15 * req.attachment_score + 0.15 * req.audio_score +
           0.10 * graph_score)

    # Step 4 - update final score in DB
    import sqlite3
    conn = sqlite3.connect("fraud_graph.db")
    conn.execute("UPDATE incidents SET final_score=? WHERE incident_id=?",
                 (round(frs, 2), req.incident_id))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "incident_id": req.incident_id,
        "layer": "score",
        "data": {
            "final_risk_score": round(frs, 2),
            "threshold_breached": "OOB" if frs > 0.8 else "FLAG" if frs > 0.7 else "CLEAR",
            "oob_triggered": frs > 0.8,
            "graph": graph_data,
            "score_breakdown": {
                "email_contribution":      round(0.35 * req.email_score, 3),
                "website_contribution":    round(0.25 * req.website_score, 3),
                "attachment_contribution": round(0.15 * req.attachment_score, 3),
                "audio_contribution":      round(0.15 * req.audio_score, 3),
                "graph_contribution":      round(0.10 * graph_score, 3)
            }
        },
        "error": None
    }
@router.get("/graph/all")
async def graph_all():
    return {"success": True, "data": build_graph(), "error": None}