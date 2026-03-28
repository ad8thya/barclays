# routers/website.py
from fastapi import APIRouter
from services.website_service import analyze_website
from schemas.website import WebsiteRequest

router = APIRouter()

@router.post("/analyze/website")
def analyze(data: WebsiteRequest):
    result = analyze_website(data.url)
    return {
        "success": True,
        "layer": "website",
        "data": result,       # ← nested under data now
        "error": None
    }