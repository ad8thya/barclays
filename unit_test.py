"""
Unit test — runs WITHOUT the server.
Tests your service and utils functions directly.
Run: python3 unit_test.py
"""
import sys, os, magic
from pypdf import PdfReader

# ── adjust this to point at your project root ──
PROJECT_ROOT = os.path.expanduser("~/BARCLAYS")   # change if folder is named differently
sys.path.insert(0, PROJECT_ROOT)

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def check(label, condition, got=None):
    if condition:
        print(f"{PASS}  {label}")
        results.append(True)
    else:
        print(f"{FAIL}  {label}  →  got: {got}")
        results.append(False)

print("\n── 1. utils/text.py ──────────────────────────────")
try:
    from utils.text import extract_flags, score_from_flags, build_reason

    # Should find keyword flags
    flags = extract_flags("Verify your account immediately or it expires today")
    check("extract_flags finds keyword flags", len(flags) > 0, flags)

    # Should find credential pattern
    flags2 = extract_flags("Please enter your password and OTP to continue")
    check("extract_flags finds credential pattern", "credential_pattern_detected" in flags2, flags2)

    # Should find suspicious URL
    flags3 = extract_flags("Click http://barclays-verify.login.net/auth to confirm")
    check("extract_flags finds suspicious URL", any("suspicious_urls" in f for f in flags3), flags3)

    # Clean text should have no flags
    flags4 = extract_flags("Your statement is ready at barclays.co.uk")
    check("extract_flags is quiet on clean text", len(flags4) == 0, flags4)

    # Score should be 0 for no flags
    score0 = score_from_flags([])
    check("score_from_flags returns 0.0 for empty flags", score0 == 0.0, score0)

    # Score should be high for many flags
    score1 = score_from_flags(["keyword:verify_your_account", "credential_pattern_detected", "suspicious_urls:2"])
    check("score_from_flags returns >0.5 for many flags", score1 > 0.5, score1)

    # Score must never exceed 1.0
    score_max = score_from_flags(["keyword:a"] * 20)
    check("score_from_flags caps at 1.0", score_max <= 1.0, score_max)

    # Reason should mention file type
    reason = build_reason(["credential_pattern_detected"], 0.8, "pdf")
    check("build_reason mentions pdf", "pdf" in reason, reason)

except ImportError as e:
    print(f"\033[91m IMPORT ERROR\033[0m  utils.text — {e}")
    print("  → Check your PROJECT_ROOT path at the top of this file")
    results.extend([False]*8)

print("\n── 2. utils/file.py ──────────────────────────────")
try:
    from utils.file import detect_type_from_filename

    check("pdf detected from filename",   detect_type_from_filename("invoice.pdf")  == "pdf",   detect_type_from_filename("invoice.pdf"))
    check("png detected from filename",   detect_type_from_filename("scan.png")     == "image", detect_type_from_filename("scan.png"))
    check("jpg detected from filename",   detect_type_from_filename("photo.jpg")    == "image", detect_type_from_filename("photo.jpg"))
    check("docx is unsupported",          detect_type_from_filename("doc.docx")     == "unsupported", detect_type_from_filename("doc.docx"))
    check("unknown ext is unsupported",   detect_type_from_filename("file.xyz")     == "unsupported", detect_type_from_filename("file.xyz"))
    check("no extension is unsupported",  detect_type_from_filename("noext")        == "unsupported", detect_type_from_filename("noext"))

except ImportError as e:
    print(f"\033[91m IMPORT ERROR\033[0m  utils.file — {e}")
    results.extend([False]*6)

print("\n── 3. services/attachment_service.py ────────────")
try:
    from services.attachment_service import analyze_attachment
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas as rl_canvas
    from PIL import Image, ImageDraw

    # Build a phishing PDF in memory
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 700, "URGENT: Verify your account immediately")
    c.drawString(72, 675, "Enter your password and OTP at http://verify-login.barclays.fake.net")
    c.save()
    pdf_bytes = buf.getvalue()

    result = analyze_attachment(pdf_bytes, "pdf")
    check("PDF analysis returns AttachmentData",     hasattr(result, "risk_score"), result)
    check("PDF: file_type is 'pdf'",                result.file_type == "pdf",     result.file_type)
    check("PDF: page_count is set",                 result.page_count is not None, result.page_count)
    check("PDF: phishing score > 0.3",              result.risk_score > 0.3,       result.risk_score)
    check("PDF: has flags",                         len(result.flags) > 0,         result.flags)
    check("PDF: reason is a non-empty string",      len(result.reason) > 10,       result.reason)

    # Build a phishing image in memory
    img = Image.new("RGB", (400, 150), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Verify your account immediately!", fill="black")
    draw.text((10, 50), "Enter password and OTP now", fill="black")
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    img_result = analyze_attachment(img_bytes, "image")
    check("Image analysis returns AttachmentData",  hasattr(img_result, "risk_score"), img_result)
    check("Image: file_type is 'image'",            img_result.file_type == "image",   img_result.file_type)
    check("Image: char_count >= 0",                 img_result.char_count >= 0,         img_result.char_count)

    # Unsupported type must raise ValueError
    try:
        analyze_attachment(b"fake", "unsupported")
        check("Unsupported type raises ValueError", False, "no exception raised")
    except ValueError:
        check("Unsupported type raises ValueError", True)

    # Empty PDF (blank page)
    buf2 = io.BytesIO()
    c2 = rl_canvas.Canvas(buf2, pagesize=letter)
    c2.save()
    blank_result = analyze_attachment(buf2.getvalue(), "pdf")
    check("Blank PDF returns low score",            blank_result.risk_score <= 0.3, blank_result.risk_score)
    check("Blank PDF has 'no_text_extracted' flag", "no_text_extracted" in blank_result.flags, blank_result.flags)

except ImportError as e:
    print(f"\033[91m IMPORT ERROR\033[0m  services.attachment_service — {e}")
    results.extend([False]*11)

print("\n── 4. schemas/attachment.py ──────────────────────")
try:
    from schemas.attachment import AttachmentResponse, AttachmentData

    # Valid response
    data = AttachmentData(
        extracted_text="hello",
        file_type="pdf",
        page_count=1,
        char_count=5,
        flags=["test_flag"],
        risk_score=0.5,
        reason="Test reason"
    )
    resp = AttachmentResponse(
        success=True,
        incident_id="INC-TEST01",
        layer="attachment",
        data=data,
        error=None
    )
    check("AttachmentResponse constructs correctly", resp.success == True, resp)
    check("layer is 'attachment'",                  resp.layer == "attachment", resp.layer)
    check("data.risk_score is preserved",           resp.data.risk_score == 0.5, resp.data.risk_score)

    # Error response
    err_resp = AttachmentResponse(
        success=False,
        incident_id="INC-ERR001",
        layer="attachment",
        data=None,
        error="Unsupported file type"
    )
    check("Error response: success=False",          err_resp.success == False, err_resp.success)
    check("Error response: data is None",           err_resp.data is None, err_resp.data)
    check("Error response: error string present",   len(err_resp.error) > 0, err_resp.error)

except ImportError as e:
    print(f"\033[91m IMPORT ERROR\033[0m  schemas.attachment — {e}")
    results.extend([False]*6)

# ── Summary ──────────────────────────────────────────
print("\n" + "─"*50)
passed = sum(results)
total  = len(results)
pct    = int(100 * passed / total) if total else 0
if passed == total:
    print(f"\033[92m✓ All {total} tests passed ({pct}%)\033[0m")
else:
    print(f"\033[91m✗ {passed}/{total} passed ({pct}%)\033[0m")
    print("\nFailed tests indicate exactly which function/file to fix.")
print()