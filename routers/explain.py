from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import requests

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"

class ExplainRequest(BaseModel):
    incident_id: str
    final_risk_score: float
    verdict: Optional[str] = "CLEAR"
    oob_triggered: Optional[bool] = False
    score_breakdown: Optional[dict] = {}
    graph: Optional[dict] = {}
    oob: Optional[dict] = None

@router.post("/analyze/explain")
async def analyze_explain(req: ExplainRequest):
    breakdown = req.score_breakdown or {}
    graph = req.graph or {}
    oob = req.oob or {}

    # Build a structured prompt for the LLM
    prompt = f"""You are a fraud analyst AI at Barclays bank. Write a concise 3-5 sentence 
intelligence brief explaining why this incident was scored the way it was.

Incident: {req.incident_id}
Final Risk Score: {req.final_risk_score} (out of 1.0)
Verdict: {req.verdict}
OOB Triggered: {req.oob_triggered}

Score Breakdown:
- Email contribution: {breakdown.get('email_contribution', 0)}
- Website contribution: {breakdown.get('website_contribution', 0)}
- Attachment contribution: {breakdown.get('attachment_contribution', 0)}
- Audio contribution: {breakdown.get('audio_contribution', 0)}
- Graph contribution: {breakdown.get('graph_contribution', 0)}

Campaign Intelligence:
- Campaign detected: {graph.get('campaign_detected', False)}
- Linked incidents: {graph.get('linked_incidents', [])}
- Shared signals: {graph.get('shared_signals', [])}
- Victim count: {graph.get('victim_count', 1)}

{"OOB Channel: " + oob.get('channel', '') + " — " + oob.get('channel_reason', '') if oob else "No OOB triggered."}

Write the brief as a single paragraph. Be specific about which layers contributed most 
and why. If a campaign was detected, explain the infrastructure reuse. If OOB was triggered, 
explain the channel selection. Do not use bullet points. Do not use markdown."""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "llama3.2:latest",
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        explanation = response.json().get("response", "Explanation generation failed.")
    except Exception as e:
        # Fallback: generate a rule-based explanation
        explanation = generate_fallback_explanation(req, breakdown, graph, oob)

    return {
        "success": True,
        "incident_id": req.incident_id,
        "layer": "explanation",
        "data": {"explanation": explanation},
        "error": None
    }


def generate_fallback_explanation(req, breakdown, graph, oob):
    """Rule-based explanation when LLM is unavailable."""
    parts = []

    # Top contributor
    if breakdown:
        top = max(breakdown.items(), key=lambda x: x[1])
        layer_name = top[0].replace("_contribution", "")
        parts.append(
            f"Incident {req.incident_id} received a fused risk score of "
            f"{req.final_risk_score:.2f}, primarily driven by the {layer_name} "
            f"layer (contributing {top[1]:.3f} to the weighted score)."
        )

    # Campaign info
    if graph.get("campaign_detected"):
        shared = graph.get("shared_signals", [])
        parts.append(
            f"Graph analysis identified a coordinated campaign across "
            f"{graph.get('victim_count', 1)} victims sharing infrastructure: "
            f"{', '.join(shared[:3]) if shared else 'correlated signals'}."
        )

    # Verdict
    if req.oob_triggered and oob:
        channel = oob.get("channel", "push_notification").replace("_", " ")
        parts.append(
            f"The score exceeded the 0.60 OOB threshold, triggering "
            f"out-of-band verification via {channel}."
        )
    elif req.final_risk_score > 0.45:
        parts.append("The score exceeded the 0.45 flag threshold — event flagged for review.")
    else:
        parts.append("The score is below intervention thresholds — event logged.")

    return " ".join(parts) if parts else "Analysis complete."