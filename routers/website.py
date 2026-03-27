from fastapi import APIRouter
router = APIRouter()

@router.post("/analyze/website")
async def analyze_website():
    return {"success": True, "layer": "website", "data": {"risk_score": 0.0}, "error": None}