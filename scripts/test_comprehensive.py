"""
CrossShield — Comprehensive E2E Test
Hits every endpoint, prints layer scores, checks OOB + graph.
"""
import requests, json, os, tempfile

BASE = "http://localhost:8000"
passed = 0
failed = 0


def test(name, method, url, **kwargs):
    global passed, failed
    try:
        r = getattr(requests, method)(url, **kwargs, timeout=60)
        data = r.json()
        ok = r.status_code == 200 and data.get("success", False)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {name}  (HTTP {r.status_code})")
        if not ok:
            print(f"       Response: {json.dumps(data, indent=2)[:300]}")
        return data
    except Exception as e:
        failed += 1
        print(f"[FAIL] {name} -- {e}")
        return {}


print("=" * 60)
print("CROSSSHIELD COMPREHENSIVE TEST")
print("=" * 60)

# ---- 1. Email ----
print("\n--- Layer: Email ---")
email_res = test("POST /analyze/email", "post", f"{BASE}/analyze/email", json={
    "incident_id": "TEST-001",
    "subject": "URGENT: Verify your account immediately",
    "body": (
        "Dear customer, your account has been compromised. "
        "Click here to verify: http://barclays-secure-login.tk/verify?id=abc123. "
        "Enter your password and PIN immediately or your account will be locked."
    ),
    "sender": "security@barclays-alerts.tk",
})
email_score = 0.0
if email_res.get("data"):
    d = email_res["data"]
    email_score = d.get("risk_score", d.get("score", 0.0))
    model = d.get("model_used", "unknown")
    print(f"       Email score: {email_score}, model: {model}")

# ---- 2. Website ----
print("\n--- Layer: Website ---")
web_res = test("POST /analyze/website", "post", f"{BASE}/analyze/website", json={
    "incident_id": "TEST-001",
    "url": "http://barclays-secure-login.tk",
})
web_score = 0.0
if web_res.get("data"):
    d = web_res["data"]
    fs = d.get("final_score", d.get("risk_score", 0))
    web_score = fs / 100.0 if fs > 1 else fs
    print(f"       Website score: {web_score}")

# ---- 3. Attachment ----
print("\n--- Layer: Attachment ---")
tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
# Build a minimal valid PDF with phishing text
pdf_content = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 44>>stream\n"
    b"BT /F1 12 Tf 100 700 Td (verify password) Tj ET\n"
    b"endstream\nendobj\n"
    b"xref\n0 5\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"0000000210 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\n"
    b"startxref\n309\n%%EOF\n"
)
tmp.write(pdf_content)
tmp.close()
with open(tmp.name, "rb") as f:
    att_res = test(
        "POST /analyze/attachment", "post", f"{BASE}/analyze/attachment",
        files={"file": ("test.pdf", f, "application/pdf")},
        data={"incident_id": "TEST-001"},
    )
os.unlink(tmp.name)
att_score = 0.0
if att_res.get("data"):
    d = att_res["data"]
    att_score = d.get("risk_score", d.get("score", 0.0))
    print(f"       Attachment score: {att_score}")

# ---- 4. Audio (stub) ----
print("\n--- Layer: Audio ---")
audio_res = test(
    "POST /analyze/audio", "post", f"{BASE}/analyze/audio",
    files={"file": ("test.wav", b"RIFF fake audio", "audio/wav")},
    data={"incident_id": "TEST-001"},
)
audio_score = 0.0
if audio_res.get("data"):
    audio_score = audio_res["data"].get("risk_score", 0.0)
    print(f"       Audio score: {audio_score}")

# ---- 5. Score Fusion ----
print("\n--- Layer: Score Fusion ---")
score_res = test("POST /analyze/score", "post", f"{BASE}/analyze/score", json={
    "incident_id": "TEST-001",
    "account_id": "ACC-9999",
    "email_score": email_score,
    "website_score": web_score,
    "attachment_score": att_score,
    "audio_score": audio_score,
    "domains": ["barclays-secure-login.tk"],
    "ips": ["203.0.113.42"],
})
frs = 0.0
oob_triggered = False
if score_res.get("data"):
    d = score_res["data"]
    frs = d.get("final_risk_score", 0)
    oob_triggered = d.get("oob_triggered", False)
    verdict = d.get("verdict", "N/A")
    print(f"       FRS: {frs}, Verdict: {verdict}, OOB: {oob_triggered}")
    if d.get("score_breakdown"):
        print(f"       Breakdown: {json.dumps(d['score_breakdown'])}")
    if d.get("oob") and d["oob"].get("channel"):
        print(f"       OOB Channel: {d['oob']['channel']}")
        if d["oob"].get("campaign_summary"):
            print(f"       Campaign: {d['oob']['campaign_summary'][:120]}")

# ---- 6. Explain ----
print("\n--- Layer: Explain ---")
score_data = score_res.get("data", {})
explain_payload = {
    "incident_id": "TEST-001",
    "final_risk_score": frs,
    "verdict": score_data.get("verdict", "CLEAR"),
    "oob_triggered": oob_triggered,
    "score_breakdown": score_data.get("score_breakdown", {}),
    "graph": score_data.get("graph", {}),
    "oob": score_data.get("oob"),
}
explain_res = test("POST /analyze/explain", "post", f"{BASE}/analyze/explain", json=explain_payload)
if explain_res.get("data"):
    expl = explain_res["data"].get("explanation", "")
    print(f"       Explanation: {expl[:200]}...")

# ---- 7. OOB Respond (deny) ----
print("\n--- OOB Feedback ---")
oob_res = test("POST /oob/respond (deny)", "post", f"{BASE}/oob/respond", json={
    "incident_id": "TEST-001",
    "response": "deny",
})
if oob_res.get("data"):
    print(f"       OOB result: {json.dumps(oob_res['data'])}")

# ---- 8. Graph ----
print("\n--- Graph ---")
graph_res = test("GET /graph/all", "get", f"{BASE}/graph/all")
if graph_res.get("data"):
    nodes = graph_res["data"].get("nodes", [])
    edges = graph_res["data"].get("edges", [])
    print(f"       Nodes: {len(nodes)}, Edges: {len(edges)}")

# ---- Summary ----
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED — check output above")
print("=" * 60)
