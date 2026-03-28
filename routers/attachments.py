# routers/attachments.py
import uuid
from fastapi import APIRouter, UploadFile, File
from schemas.attachment import AttachmentResponse, AttachmentData
from services.attachment_service import analyze_attachment
from utils.file import read_upload, detect_type_from_filename

router = APIRouter(prefix="/api", tags=["attachment"])

@router.post("/analyze/attachment", response_model=AttachmentResponse)
async def analyze_attachment_endpoint(
    file: UploadFile = File(...)
):
    incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"

    # 1. Read and detect type
    content, file_type = await read_upload(file)

    # Fallback to filename extension if magic failed
    if file_type == "unsupported" and file.filename:
        file_type = detect_type_from_filename(file.filename)

    # 2. Call service
    try:
        data: AttachmentData = analyze_attachment(content, file_type)
    except ValueError as e:
        return AttachmentResponse(
            success=False,
            incident_id=incident_id,
            layer="attachment",
            data=None,
            error=str(e)
        )
    except Exception as e:
        return AttachmentResponse(
            success=False,
            incident_id=incident_id,
            layer="attachment",
            data=None,
            error=f"Extraction failed: {str(e)}"
        )

    # 3. Return envelope
    return AttachmentResponse(
        success=True,
        incident_id=incident_id,
        layer="attachment",
        data=data,
        error=None
    )