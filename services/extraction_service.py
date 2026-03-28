"""
extraction_service.py  —  Drop into services/
Handles: .eml, .msg, HTTP URLs, JPEG/JPG, PDF, HTML, .zip, .rar, .7z
Requires (pip install):
    python-magic-bin    # Windows mime detection
    extract-msg         # .msg files
    beautifulsoup4      # HTML parsing
    requests            # HTTP fetching
    pytesseract         # OCR
    Pillow              # image handling
    opencv-python-headless
    pdfplumber          # PDF text extraction
    pdf2image           # PDF → image fallback
    patool              # .rar / .7z / .zip unified extract
    rarfile             # .rar support
    py7zr               # .7z support

System requirements:
    - Tesseract OCR  (with eng + hin tessdata)
    - Poppler        (for pdf2image)
    - UnRAR binary   (for rarfile on Windows: https://www.rarlab.com/rar_add.htm)
"""

from __future__ import annotations

import email
import io
import logging
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import cv2
import numpy as np
import pdfplumber
import pytesseract
import requests
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from PIL import Image

# ── Windows: point to Tesseract executable ──────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TESS_LANG   = "hin+eng"
TESS_CONFIG = r"--oem 3 --psm 6"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("extraction_service")


# ════════════════════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ════════════════════════════════════════════════════════════════════════════

class ExtractionResult:
    """Structured result returned by every extractor."""

    def __init__(
        self,
        source: str,
        source_type: str,
        text: str = "",
        metadata: dict | None = None,
        attachments: list["ExtractionResult"] | None = None,
        confidence: float | None = None,
        error: str | None = None,
    ):
        self.source      = source
        self.source_type = source_type
        self.text        = text.strip()
        self.metadata    = metadata or {}
        self.attachments = attachments or []
        self.confidence  = confidence
        self.error       = error

    def to_dict(self) -> dict[str, Any]:
        return {
            "source":      self.source,
            "source_type": self.source_type,
            "text":        self.text,
            "metadata":    self.metadata,
            "confidence":  self.confidence,
            "error":       self.error,
            "attachments": [a.to_dict() for a in self.attachments],
        }

    def all_text(self) -> str:
        """Recursively collect all text (self + attachments)."""
        parts = [self.text]
        for att in self.attachments:
            parts.append(att.all_text())
        return "\n\n".join(filter(None, parts))


# ════════════════════════════════════════════════════════════════════════════
#  IMAGE PRE-PROCESSING  (shared by image + PDF image fallback)
# ════════════════════════════════════════════════════════════════════════════

def _preprocess_for_ocr(pil_image: Image.Image) -> np.ndarray:
    """
    Grayscale → denoise → adaptive threshold → upscale if needed.
    Returns a numpy array ready for pytesseract.
    """
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # Deskew (straighten slightly rotated scans)
    coords = np.column_stack(np.where(denoised < 200))
    if len(coords) > 50:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            (h, w) = denoised.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            denoised = cv2.warpAffine(denoised, M, (w, h),
                                      flags=cv2.INTER_CUBIC,
                                      borderMode=cv2.BORDER_REPLICATE)

    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2,
    )

    # Upscale small images (OCR needs ~300 DPI)
    h, w = thresh.shape
    if w < 1000:
        thresh = cv2.resize(thresh, None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC)

    return thresh


def _ocr_image_array(arr: np.ndarray) -> tuple[str, float]:
    """Run Tesseract on a numpy array; return (text, avg_confidence)."""
    text = pytesseract.image_to_string(arr, lang=TESS_LANG, config=TESS_CONFIG)
    data = pytesseract.image_to_data(
        arr, lang=TESS_LANG, config=TESS_CONFIG,
        output_type=pytesseract.Output.DICT,
    )
    confs = [int(c) for c in data["conf"] if str(c).isdigit() and int(c) >= 0]
    avg   = round(sum(confs) / len(confs), 2) if confs else 0.0
    return text, avg


# ════════════════════════════════════════════════════════════════════════════
#  INDIVIDUAL EXTRACTORS
# ════════════════════════════════════════════════════════════════════════════

# ── 1. IMAGE (JPEG / JPG / PNG / TIFF / BMP / WEBP) ────────────────────────

def extract_image(path: str) -> ExtractionResult:
    try:
        pil = Image.open(path).convert("RGB")
        arr = _preprocess_for_ocr(pil)
        text, conf = _ocr_image_array(arr)
        return ExtractionResult(
            source=path, source_type="image",
            text=text, confidence=conf,
            metadata={"size": pil.size, "format": pil.format},
        )
    except Exception as exc:
        log.exception("Image extraction failed")
        return ExtractionResult(source=path, source_type="image", error=str(exc))


# ── 2. PDF ───────────────────────────────────────────────────────────────────

def extract_pdf(path: str) -> ExtractionResult:
    """
    Strategy:
      1. pdfplumber  →  native text (fast, accurate for digital PDFs)
      2. If yield < 50 chars per page  →  OCR each page image as fallback
    """
    try:
        text_parts: list[str] = []
        total_pages = 0

        with pdfplumber.open(path) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)

        native_text = "\n\n".join(text_parts)
        avg_chars   = len(native_text) / max(total_pages, 1)

        # Fallback to OCR if scanned / image-based PDF
        if avg_chars < 50:
            log.info("PDF has little native text — switching to OCR fallback")
            images = convert_from_path(path, dpi=300)
            ocr_parts: list[str] = []
            confs: list[float]   = []
            for pil in images:
                arr  = _preprocess_for_ocr(pil)
                t, c = _ocr_image_array(arr)
                ocr_parts.append(t)
                confs.append(c)
            return ExtractionResult(
                source=path, source_type="pdf",
                text="\n\n".join(ocr_parts),
                confidence=round(sum(confs) / len(confs), 2) if confs else 0.0,
                metadata={"pages": total_pages, "method": "ocr"},
            )

        return ExtractionResult(
            source=path, source_type="pdf",
            text=native_text,
            metadata={"pages": total_pages, "method": "native"},
        )

    except Exception as exc:
        log.exception("PDF extraction failed")
        return ExtractionResult(source=path, source_type="pdf", error=str(exc))


# ── 3. HTML ──────────────────────────────────────────────────────────────────

def extract_html(path_or_content: str, is_content: bool = False) -> ExtractionResult:
    """
    Accepts either a file path or raw HTML string.
    Strips scripts/styles; collapses whitespace.
    """
    try:
        if is_content:
            html = path_or_content
            src  = "<raw html>"
        else:
            with open(path_or_content, encoding="utf-8", errors="replace") as f:
                html = f.read()
            src = path_or_content

        soup  = BeautifulSoup(html, "html.parser")

        # Remove noise tags
        for tag in soup(["script", "style", "noscript", "head",
                          "meta", "link", "iframe"]):
            tag.decompose()

        text  = soup.get_text(separator="\n")
        text  = re.sub(r"\n{3,}", "\n\n", text)   # collapse blank lines
        title = soup.title.string.strip() if soup.title else ""

        # Extract all hrefs (useful for phishing URL detection)
        links = [a.get("href", "") for a in soup.find_all("a", href=True)]

        return ExtractionResult(
            source=src, source_type="html",
            text=text,
            metadata={"title": title, "links": links},
        )
    except Exception as exc:
        log.exception("HTML extraction failed")
        return ExtractionResult(source=path_or_content, source_type="html", error=str(exc))


# ── 4. HTTP URL ───────────────────────────────────────────────────────────────

def extract_url(url: str, timeout: int = 15) -> ExtractionResult:
    """
    Fetches a URL, auto-detects content type, and delegates:
      image/* → OCR
      application/pdf → extract_pdf (downloads first)
      text/html or default → extract_html
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ExtractionBot/1.0)"}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").lower()

        # Image URL
        if "image/" in ct:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            try:
                result = extract_image(tmp_path)
                result.source = url
                return result
            finally:
                os.unlink(tmp_path)

        # PDF URL
        if "pdf" in ct:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            try:
                result = extract_pdf(tmp_path)
                result.source = url
                return result
            finally:
                os.unlink(tmp_path)

        # Default: treat as HTML
        return extract_html(resp.text, is_content=True)

    except Exception as exc:
        log.exception("URL extraction failed")
        return ExtractionResult(source=url, source_type="url", error=str(exc))


# ── 5. EML (raw email) ────────────────────────────────────────────────────────

def extract_eml(path: str) -> ExtractionResult:
    """
    Parses .eml files:
    - Extracts headers (From, To, Subject, Date)
    - Extracts plain text + HTML body
    - Recursively extracts all attachments
    """
    try:
        with open(path, "rb") as f:
            msg = email.message_from_bytes(f.read())

        metadata = {
            "from":    msg.get("From", ""),
            "to":      msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date":    msg.get("Date", ""),
        }

        body_parts: list[str] = []
        attachments: list[ExtractionResult] = []

        for part in msg.walk():
            ct   = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))

            # Body text
            if ct == "text/plain" and "attachment" not in disp:
                body_parts.append(part.get_payload(decode=True).decode("utf-8", errors="replace"))

            elif ct == "text/html" and "attachment" not in disp:
                html = part.get_payload(decode=True).decode("utf-8", errors="replace")
                r    = extract_html(html, is_content=True)
                body_parts.append(r.text)

            # Attachments
            elif "attachment" in disp or part.get_filename():
                filename = part.get_filename() or f"attachment_{uuid.uuid4()}"
                payload  = part.get_payload(decode=True)
                if payload:
                    with tempfile.NamedTemporaryFile(
                        suffix=Path(filename).suffix, delete=False
                    ) as tmp:
                        tmp.write(payload)
                        tmp_path = tmp.name
                    try:
                        att = extract(tmp_path)
                        att.source = filename
                        attachments.append(att)
                    finally:
                        os.unlink(tmp_path)

        return ExtractionResult(
            source=path, source_type="eml",
            text="\n\n".join(body_parts),
            metadata=metadata,
            attachments=attachments,
        )
    except Exception as exc:
        log.exception("EML extraction failed")
        return ExtractionResult(source=path, source_type="eml", error=str(exc))


# ── 6. MSG (Outlook) ─────────────────────────────────────────────────────────

def extract_msg(path: str) -> ExtractionResult:
    """
    Parses Outlook .msg files using extract-msg library.
    Recursively processes all attachments.
    """
    try:
        import extract_msg as _extract_msg  # lazy import

        msg = _extract_msg.Message(path)
        metadata = {
            "from":    msg.sender or "",
            "to":      msg.to or "",
            "subject": msg.subject or "",
            "date":    str(msg.date) if msg.date else "",
        }

        body = msg.body or ""

        # Also grab HTML body if plain is empty
        if not body.strip() and msg.htmlBody:
            html = msg.htmlBody.decode("utf-8", errors="replace") \
                   if isinstance(msg.htmlBody, bytes) else msg.htmlBody
            r    = extract_html(html, is_content=True)
            body = r.text

        attachments: list[ExtractionResult] = []
        for att in msg.attachments:
            try:
                data = att.data
                name = att.longFilename or att.shortFilename or f"att_{uuid.uuid4()}"
                if data:
                    with tempfile.NamedTemporaryFile(
                        suffix=Path(name).suffix, delete=False
                    ) as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name
                    try:
                        result = extract(tmp_path)
                        result.source = name
                        attachments.append(result)
                    finally:
                        os.unlink(tmp_path)
            except Exception as att_exc:
                attachments.append(ExtractionResult(
                    source=str(att), source_type="unknown", error=str(att_exc)
                ))

        msg.close()
        return ExtractionResult(
            source=path, source_type="msg",
            text=body,
            metadata=metadata,
            attachments=attachments,
        )
    except Exception as exc:
        log.exception("MSG extraction failed")
        return ExtractionResult(source=path, source_type="msg", error=str(exc))


# ── 7. ZIP ────────────────────────────────────────────────────────────────────

def extract_zip(path: str, max_files: int = 50) -> ExtractionResult:
    """
    Extracts ZIP contents to a temp dir and recursively processes each file.
    Skips files > 50 MB to avoid zip-bomb issues.
    """
    MAX_BYTES = 50 * 1024 * 1024  # 50 MB per file
    results: list[ExtractionResult] = []

    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()[:max_files]
            with tempfile.TemporaryDirectory() as tmpdir:
                for name in names:
                    info = zf.getinfo(name)
                    if info.file_size > MAX_BYTES:
                        results.append(ExtractionResult(
                            source=name, source_type="skipped",
                            error="File too large (>50 MB)",
                        ))
                        continue
                    extracted = zf.extract(name, tmpdir)
                    if os.path.isfile(extracted):
                        r = extract(extracted)
                        r.source = name
                        results.append(r)

        combined = "\n\n".join(r.text for r in results if r.text)
        return ExtractionResult(
            source=path, source_type="zip",
            text=combined,
            attachments=results,
            metadata={"file_count": len(results)},
        )
    except Exception as exc:
        log.exception("ZIP extraction failed")
        return ExtractionResult(source=path, source_type="zip", error=str(exc))


# ── 8. RAR / 7Z ──────────────────────────────────────────────────────────────

def extract_archive(path: str, max_files: int = 50) -> ExtractionResult:
    """
    Handles .rar and .7z using py7zr (7z) or rarfile (rar).
    Falls back to patool for anything else.
    """
    suffix = Path(path).suffix.lower()
    results: list[ExtractionResult] = []

    try:
        with tempfile.TemporaryDirectory() as tmpdir:

            if suffix == ".7z":
                import py7zr
                with py7zr.SevenZipFile(path, mode="r") as archive:
                    archive.extractall(path=tmpdir)

            elif suffix == ".rar":
                import rarfile
                with rarfile.RarFile(path) as archive:
                    archive.extractall(path=tmpdir)

            else:
                # Generic fallback (patool)
                import patool
                patool.extract_archive(path, outdir=tmpdir)

            # Walk extracted files
            count = 0
            for root, _, files in os.walk(tmpdir):
                for fname in files:
                    if count >= max_files:
                        break
                    fpath = os.path.join(root, fname)
                    r = extract(fpath)
                    r.source = fname
                    results.append(r)
                    count += 1

        combined = "\n\n".join(r.text for r in results if r.text)
        return ExtractionResult(
            source=path, source_type=suffix.lstrip("."),
            text=combined,
            attachments=results,
            metadata={"file_count": len(results)},
        )
    except Exception as exc:
        log.exception("Archive extraction failed")
        return ExtractionResult(source=path, source_type="archive", error=str(exc))


# ════════════════════════════════════════════════════════════════════════════
#  UNIFIED DISPATCHER
# ════════════════════════════════════════════════════════════════════════════

_IMAGE_EXTS   = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"}
_ARCHIVE_EXTS = {".rar", ".7z", ".tar", ".gz", ".bz2"}


def extract(path_or_url: str) -> ExtractionResult:
    """
    Single entry point.  Pass a file path or HTTP/HTTPS URL.
    Auto-detects format and dispatches to the right extractor.
    """
    s = path_or_url.strip()

    # HTTP / HTTPS URL
    if s.startswith("http://") or s.startswith("https://"):
        return extract_url(s)

    p      = Path(s)
    suffix = p.suffix.lower()

    if suffix in _IMAGE_EXTS:
        return extract_image(s)
    elif suffix == ".pdf":
        return extract_pdf(s)
    elif suffix in {".html", ".htm"}:
        return extract_html(s)
    elif suffix == ".eml":
        return extract_eml(s)
    elif suffix == ".msg":
        return extract_msg(s)
    elif suffix == ".zip":
        return extract_zip(s)
    elif suffix in _ARCHIVE_EXTS:
        return extract_archive(s)
    else:
        # Unknown type: try to sniff with python-magic, else return error
        try:
            import magic
            mime = magic.from_file(s, mime=True)
            if "image" in mime:
                return extract_image(s)
            elif "pdf" in mime:
                return extract_pdf(s)
            elif "html" in mime:
                return extract_html(s)
            elif "zip" in mime:
                return extract_zip(s)
        except Exception:
            pass

        return ExtractionResult(
            source=s, source_type="unknown",
            error=f"Unsupported file type: '{suffix}'",
        )