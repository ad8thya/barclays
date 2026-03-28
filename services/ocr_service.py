import pytesseract
from PIL import Image
import cv2
import numpy as np
from pathlib import Path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Support both Hindi (hin) and English (eng)
TESS_LANG = "hin+eng"

def preprocess_image(image_path: str) -> np.ndarray:
    """Improve OCR accuracy via preprocessing."""
    img = cv2.imread(image_path)
    if img is None:
            raise ValueError("Image not loaded properly")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=30)

    # Adaptive threshold (handles uneven lighting)
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )

    # Upscale if small (OCR needs ~300 DPI minimum)
    h, w = thresh.shape
    if w < 1000:
        thresh = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    return thresh

def extract_text(image_path: str) -> dict:
    """Run OCR with Hindi + English support."""
    processed = preprocess_image(image_path)

    # PSM 6 = assume uniform block of text (good for documents)
    config = r"--oem 3 --psm 6"

    raw_text = pytesseract.image_to_string(
        processed,
        lang=TESS_LANG,
        config=config
    )

    # Also get confidence scores
    data = pytesseract.image_to_data(
        processed,
        lang=TESS_LANG,
        config=config,
        output_type=pytesseract.Output.DICT
    )

    confidences = [int(c) for c in data["conf"] if str(c).isdigit() and int(c) >= 0]
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return {
        "text": raw_text.strip(),
        "confidence": avg_conf,
        "lang": TESS_LANG
    }