# utils/file.py
import magic          # pip install python-magic
# On Linux: sudo apt install libmagic1
# On Mac:   brew install libmagic
from fastapi import UploadFile
import io
import os

async def read_upload(file):
    content = await file.read()
    filename = file.filename or ""
    file_type = detect_type_from_filename(filename)
    return content, file_type

def detect_type_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    mapping = {
        ".pdf":  "pdf",
        ".png":  "image",
        ".jpg":  "image",
        ".jpeg": "image",
        ".doc":  "word",
        ".docx": "word",
        ".txt":  "text",
    }
    return mapping.get(ext, "unsupported")
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/webp": "image",
    "image/tiff": "image",
}

async def read_upload(file: UploadFile) -> tuple[bytes, str]:
    """
    Returns (raw_bytes, detected_file_type_string)
    file_type is one of: "pdf", "image", "unsupported"
    """
    content = await file.read()
    mime = magic.from_buffer(content[:2048], mime=True)
    file_type = SUPPORTED_TYPES.get(mime, "unsupported")
    return content, file_type

# fallback if python-magic won't install
def detect_type_from_filename(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {"pdf": "pdf", "png": "image", "jpg": "image",
            "jpeg": "image", "tiff": "image", "webp": "image"}.get(ext, "unsupported")