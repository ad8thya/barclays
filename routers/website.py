from fastapi import APIRouter
from services.website_service import analyze_website
from schemas.website import WebsiteRequest, WebsiteResponse

router = APIRouter()

@router.post("/analyze", response_model=WebsiteResponse)
def analyze(data: WebsiteRequest):
    return analyze_website(data.url)