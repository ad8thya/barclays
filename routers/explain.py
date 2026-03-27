from fastapi import APIRouter
router = APIRouter()

@router.post("/analyze/explain")
async def analyze_explain():
    return {"success": True, "layer": "explanation", "data": {"explanation": "stub"}, "error": None}