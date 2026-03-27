from fastapi import APIRouter
router = APIRouter()

@router.post("/analyze/email")
async def analyze_email():
    return {"success": True, "layer": "email", "data": {"risk_score": 0.0}, "error": None}