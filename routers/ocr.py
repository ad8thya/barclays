from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil, uuid, os

from services.ocr_service import extract_text
from services.score_service import analyze_text   # ✅ correct import
from schemas.ocr import OCRResponse, OCRData

router = APIRouter(prefix="/ocr", tags=["OCR"])

UPLOAD_DIR = "tmp/ocr_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/extract", response_model=OCRResponse)
async def ocr_extract(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}{suffix}"

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        result = extract_text(temp_path)

        score_result = analyze_text(result["text"])   # ✅ correct

        return OCRResponse(
            success=True,
            incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
            layer="ocr",
            data=OCRData(
                text=result["text"],
                confidence=result["confidence"],
                lang=result["lang"],
                risk_score=score_result["risk_score"],
                reason=score_result["reason"]
            ),
            error=None
        )

    except Exception as e:
        return OCRResponse(
            success=False,
            incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
            layer="ocr",
            data=None,
            error=str(e)
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)