import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from services.graph_service import store_incident, find_correlated_incidents, get_graph_score, build_graph
from services.oob_service import build_oob_notification, store_oob_event

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
    website_suspicious: bool = False 

class OOBResponse(BaseModel):
    incident_id: str
    response: str   # "approve" or "deny"

@router.post("/analyze/score")
async def analyze_score(req: ScoreRequest):
    suspicious_domains = req.domains if req.website_suspicious else []
    suspicious_ips = req.ips

    signals = {"domains": suspicious_domains, "ips": suspicious_ips}
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
    conn = sqlite3.connect("fraud_graph.db")
    conn.execute("UPDATE incidents SET final_score=? WHERE incident_id=?",
                 (round(frs, 2), req.incident_id))
    conn.commit()
    conn.close()

    score_breakdown = {
        "email_contribution":      round(0.35 * req.email_score, 3),
        "website_contribution":    round(0.25 * req.website_score, 3),
        "attachment_contribution": round(0.15 * req.attachment_score, 3),
        "audio_contribution":      round(0.15 * req.audio_score, 3),
        "graph_contribution":      round(0.10 * graph_score, 3)
    }

    layer_scores = {
        "email": req.email_score,
        "website": req.website_score,
        "attachment": req.attachment_score,
        "audio": req.audio_score,
    }

    oob_triggered = frs > 0.60
    oob_details = None

    if oob_triggered:
        oob_details = build_oob_notification(
            incident_id=req.incident_id,
            frs=frs,
            layer_scores=layer_scores,
            graph_info=graph_data,
            score_breakdown=score_breakdown,
        )
        store_oob_event(
            incident_id=req.incident_id,
            account_id=req.account_id,
            frs=frs,
            channel=oob_details["channel"],
            reason=oob_details["channel_reason"],
            campaign_summary=oob_details["campaign_summary"],
        )

    return {
        "success": True,
        "incident_id": req.incident_id,
        "layer": "score",
        "data": {
            "final_risk_score": round(frs, 2),
            "verdict": "OOB" if frs > 0.60 else "FLAG" if frs > 0.45 else "CLEAR",
            "threshold_breached": "OOB" if frs > 0.60 else "FLAG" if frs > 0.45 else "CLEAR",
            "oob_triggered": oob_triggered,
            "oob": oob_details,
            "graph": graph_data,
            "score_breakdown": score_breakdown,
        },
        "error": None
    }

@router.post("/oob/respond")
async def oob_respond(req: OOBResponse):
    from services.oob_service import record_oob_response
    result = record_oob_response(req.incident_id, req.response)
    return {"success": True, "data": result, "error": None}

@router.get("/graph/all")
async def graph_all():
    return {"success": True, "data": build_graph(), "error": None}