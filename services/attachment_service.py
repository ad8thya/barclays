# services/attachment_service.py
import io, tempfile, os, re
import PyPDF2
import pytesseract
import pickle
import scipy.sparse as sp
from PIL import Image

from services.extraction_service import extract
from utils.llm import generate_llm_reason
from utils.text import extract_flags, score_from_flags, build_reason
from schemas.attachment import AttachmentData
from services.email_model.email_utils.features import extract_signals, extract_flagged, extract_meta

_model_dir        = os.path.abspath(os.path.join(os.path.dirname(__file__), 'email_model', 'model'))
_email_model      = pickle.load(open(os.path.join(_model_dir, 'xgb_model.pkl'), 'rb'))
_email_vectorizer = pickle.load(open(os.path.join(_model_dir, 'tfidf_vectorizer.pkl'), 'rb'))


def parse_email_fields(text: str) -> dict:
    lines = text.split("\n")
    subject, sender, body_lines = "", "", []
    body_started = False
    for line in lines:
        l = line.strip()
        if re.match(r'^from\s*:', l, re.IGNORECASE):
            sender = re.sub(r'^from\s*:', '', l, flags=re.IGNORECASE).strip()
        elif re.match(r'^subject\s*:', l, re.IGNORECASE):
            subject = re.sub(r'^subject\s*:', '', l, flags=re.IGNORECASE).strip()
        elif re.match(r'^(to|date|cc|bcc)\s*:', l, re.IGNORECASE):
            body_started = False
        elif l == "" and subject:
            body_started = True
        elif body_started:
            body_lines.append(line)
    body = "\n".join(body_lines).strip() or text
    return {"subject": subject, "sender": sender, "body": body}


def run_email_model_on_text(text: str, sender: str = "") -> dict:
    try:
        tfidf = _email_vectorizer.transform([text])
        meta  = extract_meta(text)
        X     = sp.hstack([tfidf, meta])
        pred  = int(_email_model.predict(X)[0])
        prob  = _email_model.predict_proba(X)[0]
        label_map = {0: "Official", 1: "Suspicious", 2: "Phishing"}
        return {
            "label":           label_map[pred],
            "risk_score":      round(float(max(prob)), 3),
            "signals":         extract_signals(text, sender),
            "flagged_phrases": extract_flagged(text),
        }
    except Exception as e:
        return {"label": "Unknown", "risk_score": 0.0, "signals": {}, "flagged_phrases": [], "error": str(e)}


def analyze_attachment(content: bytes, file_type: str) -> AttachmentData:
    if file_type == "unsupported":
        raise ValueError("Unsupported file type")

    suffix = {"pdf": ".pdf", "image": ".png"}.get(file_type, ".bin")
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    text = ""
    page_count = None

    try:
        result     = extract(tmp_path)
        text       = result.all_text()
        page_count = result.metadata.get("pages") if file_type == "pdf" else None
    except Exception:
        if file_type == "pdf":
            try:
                reader     = PyPDF2.PdfReader(io.BytesIO(content))
                text       = " ".join(p.extract_text() or "" for p in reader.pages)
                page_count = len(reader.pages)
            except Exception:
                pass
        elif file_type == "image":
            try:
                img = Image.open(io.BytesIO(content))
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                text = pytesseract.image_to_string(img)
            except Exception:
                pass
    finally:
        os.unlink(tmp_path)

    if not text.strip():
        return AttachmentData(
            extracted_text="",
            file_type=file_type,
            page_count=page_count,
            char_count=0,
            flags=["no_text_extracted"],
            risk_score=0.1,
            reason="No readable text could be extracted from this attachment.",
            email_subject=None, email_sender=None,
            email_risk_score=None, email_label=None,
            email_signals=None, email_flagged=None,
        )

    flags = extract_flags(text)
    score = score_from_flags(flags)

    if score > 0.3:
        try:
            reason = generate_llm_reason(text, flags, score, file_type)
        except Exception:
            reason = build_reason(flags, score, file_type)
    else:
        reason = build_reason(flags, score, file_type)

    # parse email fields and run email model
    email_fields = parse_email_fields(text)
    email_text   = (email_fields["subject"] + " " + email_fields["body"]).strip()
    email_result = run_email_model_on_text(email_text, email_fields["sender"])

    return AttachmentData(
        extracted_text=text[:2000],
        file_type=file_type,
        page_count=page_count,
        char_count=len(text),
        flags=flags,
        risk_score=score,
        reason=reason,
        email_subject=email_fields["subject"] or None,
        email_sender=email_fields["sender"] or None,
        email_risk_score=email_result["risk_score"],
        email_label=email_result["label"],
        email_signals=email_result["signals"],
        email_flagged=email_result["flagged_phrases"],
    )