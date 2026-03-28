# services/attachment_service.py
import io
import PyPDF2
import pytesseract
from PIL import Image

from utils.text import extract_flags, score_from_flags, build_reason
from schemas.attachment import AttachmentData

# --- PDF extraction ---
def extract_text_from_pdf(content: bytes) -> tuple[str, int]:
    """Returns (extracted_text, page_count)"""
    reader = PyPDF2.PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return " ".join(pages), len(reader.pages)

# --- Image OCR extraction ---
def extract_text_from_image(content: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(content))
        # Convert to RGB if needed (handles RGBA PNGs etc.)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

# --- Main service function ---
def analyze_attachment(content: bytes, file_type: str) -> AttachmentData:
    """
    Pure function — takes bytes, returns AttachmentData.
    Raises ValueError for unsupported types.
    """
    if file_type == "unsupported":
        raise ValueError("Unsupported file type")

    # 1. Extract text
    page_count = None
    if file_type == "pdf":
        text, page_count = extract_text_from_pdf(content)
    elif file_type == "image":
        text = extract_text_from_image(content)
    else:
        text = ""

    # 2. Guard: if extraction yielded nothing
    if not text.strip():
        return AttachmentData(
            extracted_text="",
            file_type=file_type,
            page_count=page_count,
            char_count=0,
            flags=["no_text_extracted"],
            risk_score=0.1,  # slight suspicion — blank PDFs can be evasion
            reason="No readable text could be extracted from this attachment."
        )

    # 3. Score
    flags = extract_flags(text)
    score = score_from_flags(flags)
    reason = build_reason(flags, score, file_type)

    return AttachmentData(
        extracted_text=text[:2000],  # truncate for storage — don't log full docs
        file_type=file_type,
        page_count=page_count,
        char_count=len(text),
        flags=flags,
        risk_score=score,
        reason=reason,
    )