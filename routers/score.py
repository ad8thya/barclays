import sqlite3
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.graph_service import store_incident, find_correlated_incidents, get_graph_score, build_graph
from services.oob_service import build_oob_notification, store_oob_event

router = APIRouter()

class ScoreRequest(BaseModel):
    incident_id: str
    account_id: str
    email_score: Optional[float] = None
    website_score: Optional[float] = None
    attachment_score: Optional[float] = None
    audio_score: Optional[float] = None
    domains: List[str] = []
    ips: List[str] = []
    website_suspicious: bool = False

class OOBResponse(BaseModel):
    incident_id: str
    response: str


def calculate_frs(email, website, attachment, audio, graph) -> tuple[float, dict]:
    """
    Equal weights across all provided layers.
    Graph always gets 10%. Remaining 90% split equally among provided layers.
    """
    provided = {}
    if email      is not None: provided["email"]      = email
    if website    is not None: provided["website"]    = website
    if attachment is not None: provided["attachment"] = attachment
    if audio      is not None: provided["audio"]      = audio

    if not provided:
        return 0.0, {}

    # 90% split equally, graph always 10%
    each = round(0.90 / len(provided), 4)

    frs = sum(score * each for score in provided.values())
    frs += graph * 0.10
    frs = round(min(1.0, frs), 4)

    breakdown = {
        f"{layer}_contribution": round(score * each, 3)
        for layer, score in provided.items()
    }
    breakdown["graph_contribution"] = round(graph * 0.10, 3)

    return frs, breakdown

@router.post("/analyze/score")
async def analyze_score(req: ScoreRequest):

    # ── Step 1 — store signals (only suspicious domains) ──
    suspicious_domains = req.domains if req.website_suspicious else []
    signals = {"domains": suspicious_domains, "ips": req.ips}

    scores = {
        "email":      req.email_score      or 0,
        "website":    req.website_score    or 0,
        "attachment": req.attachment_score or 0,
        "audio":      req.audio_score      or 0,
        "final":      0.0
    }
    store_incident(req.incident_id, req.account_id, scores, signals)

    # ── Step 2 — graph correlation ──
    graph_score = get_graph_score(req.incident_id)
    graph_data  = find_correlated_incidents(req.incident_id)

    # ── Step 3 — dynamic FRS ──
    frs, score_breakdown = calculate_frs(
        email      = req.email_score,
        website    = req.website_score,
        attachment = req.attachment_score,
        audio      = req.audio_score,
        graph      = graph_score,
    )

    # ── Step 4 — persist final score ──
    conn = sqlite3.connect("fraud_graph.db")
    conn.execute("UPDATE incidents SET final_score=? WHERE incident_id=?",
                 (round(frs, 2), req.incident_id))
    conn.commit()
    conn.close()

    # ── Step 5 — OOB ──
    layer_scores = {
        "email":      req.email_score      or 0,
        "website":    req.website_score    or 0,
        "attachment": req.attachment_score or 0,
        "audio":      req.audio_score      or 0,
    }

    oob_triggered = frs > 0.40
    oob_details   = None

    if oob_triggered:
        oob_details = build_oob_notification(
            incident_id    = req.incident_id,
            frs            = frs,
            layer_scores   = layer_scores,
            graph_info     = graph_data,
            score_breakdown= score_breakdown,
        )
        store_oob_event(
            incident_id      = req.incident_id,
            account_id       = req.account_id,
            frs              = frs,
            channel          = oob_details["channel"],
            reason           = oob_details["channel_reason"],
            campaign_summary = oob_details["campaign_summary"],
        )

    verdict = "OOB" if frs > 0.40 else "FLAG" if frs < 0.39 else "CLEAR"

    return {
        "success":     True,
        "incident_id": req.incident_id,
        "layer":       "score",
        "data": {
            "final_risk_score":  round(frs, 2),
            "verdict":           verdict,
            "threshold_breached":verdict,
            "oob_triggered":     oob_triggered,
            "oob":               oob_details,
            "graph":             graph_data,
            "score_breakdown":   score_breakdown,
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

    