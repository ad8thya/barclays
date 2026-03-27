from fastapi import APIRouter
router = APIRouter()

@router.post("/analyze/attachment")
async def analyze_attachment():
    return {"success": True, "layer": "attachment", "data": {"risk_score": 0.0}, "error": None}