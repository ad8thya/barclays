# utils/file.py
# Extension-based type detection — NO python-magic (broken on Windows)
import os


async def read_upload(file):
    content = await file.read()
    file_type = detect_type_from_filename(file.filename or "")
    return content, file_type


def detect_type_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[-1].lower()
    return {
        ".pdf":  "pdf",
        ".png":  "image",
        ".jpg":  "image",
        ".jpeg": "image",
        ".doc":  "word",
        ".docx": "word",
        ".txt":  "text",
        ".tiff": "image",
        ".webp": "image",
    }.get(ext, "unsupported")