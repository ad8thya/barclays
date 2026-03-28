from urllib.parse import urljoin, urlparse
from services.js_analysis_service import analyze_js_semantics
from services.llm_service import analyze_with_llm
from services.sandbox_service import run_sandbox
import requests


def analyze_website(url: str):
    result = {}

    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    result["domain"] = domain

    # ── Run enhanced sandbox ──────────────────────────────────────
    sandbox_data = run_sandbox(url)

    if not sandbox_data.get("reachable"):
        return {
            "domain": domain,
            "status_code": None,
            "reachable": False,
            "risk": "HIGH",
            "score": 90,
            "final_score": 90,
            "final_risk": "HIGH",
            "confidence": 80,
            "reasons": ["Website not reachable"],
            "ai_analysis": "Site unreachable",
            "js_analysis": "No JS analysis",
            "typosquatting": {},
            "cookies": {},
            "overlays": {},
        }

    result["status_code"] = sandbox_data["status_code"]
    result["reachable"] = True

    forms = sandbox_data["num_forms"]
    password_field = sandbox_data["has_password_field"]
    external_scripts = sandbox_data["external_scripts"]
    redirects = sandbox_data["redirect_count"]
    uses_https = sandbox_data["uses_https"]

    # ── Fetch JS content (light) ──────────────────────────────────
    js_contents = []
    for script in external_scripts[:2]:
        try:
            full_url = urljoin(url, script)
            js_res = requests.get(full_url, timeout=3)
            js_contents.append(js_res.text[:1000])
        except Exception:
            continue

    # ── Features dict for LLM ─────────────────────────────────────
    features = {
        "url": url,
        "domain": domain,
        "has_password_field": password_field,
        "num_forms": forms,
        "external_scripts": len(external_scripts),
        "uses_https": uses_https,
        "url_length": len(url),
        "has_suspicious_keywords": any(
            word in url.lower() for word in ["login", "verify", "secure", "account"]
        ),
        "redirects": redirects,
        # new signals surfaced to LLM
        "typosquatting_verdict": sandbox_data["typosquatting"].get("verdict", "NO_MATCH"),
        "similar_to": sandbox_data["typosquatting"].get("closest_legit_domain", ""),
        "cookie_issues": len(sandbox_data["cookies"].get("issues", [])),
        "iframe_count": sandbox_data["overlays"].get("iframe_count", 0),
        "invisible_elements": sandbox_data["overlays"].get("invisible_elements", 0),
        "fake_login_overlay": sandbox_data["overlays"].get("fake_login_overlay", False),
    }

    # ── Heuristic scoring ─────────────────────────────────────────
    risk_score = 0
    reasons = []

    if features["has_suspicious_keywords"]:
        risk_score += 25
        reasons.append("Suspicious keywords in URL")

    if domain.count(".") > 3:
        risk_score += 15
        reasons.append("Too many subdomains")

    if len(url) > 75:
        risk_score += 10
        reasons.append("URL too long")

    if "@" in url:
        risk_score += 30
        reasons.append("Contains @ symbol")

    if not uses_https:
        risk_score += 15
        reasons.append("Not using HTTPS")

    if forms > 0:
        risk_score += 15
        reasons.append("Contains form (possible login page)")

    if password_field:
        risk_score += 20
        reasons.append("Password field detected")

    if len(external_scripts) > 3:
        risk_score += 10
        reasons.append("Multiple external scripts")

    if redirects > 2:
        risk_score += 10
        reasons.append("Multiple redirects")

    # ── NEW: inject enhanced sandbox signals into heuristic ───────
    extra_risk = sandbox_data.get("extra_risk_score", 0)
    extra_reasons = sandbox_data.get("extra_risk_reasons", [])

    # Blend extra risk into main score (weighted 60% heuristic, 40% new signals)
    risk_score = int(risk_score * 0.6 + extra_risk * 0.4)
    reasons.extend(extra_reasons)

    # Hard boosts for severe signals (override blending)
    typo = sandbox_data.get("typosquatting", {})
    overlays = sandbox_data.get("overlays", {})

    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        risk_score = max(risk_score, 80)   # floor at 80 for confirmed spoof
    if overlays.get("fake_login_overlay"):
        risk_score = max(risk_score, 75)   # floor at 75 for overlay login injection

    # Base classification
    if risk_score < 30:
        risk = "LOW"
    elif risk_score < 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    # ── LLM analysis ─────────────────────────────────────────────
    llm_risk = "UNKNOWN"
    ai_analysis = "LLM analysis skipped"
    try:
        ai_analysis = analyze_with_llm(features)
        analysis_lower = ai_analysis.lower()
        if "high" in analysis_lower:
            llm_risk = "HIGH"
        elif "medium" in analysis_lower:
            llm_risk = "MEDIUM"
        elif "low" in analysis_lower:
            llm_risk = "LOW"
    except Exception as e:
        print("LLM ERROR:", e)
        # ── Fallback: rule-based LLM-equivalent risk ──────────────
        # When Ollama is offline, derive llm_risk from heuristics
        if risk_score >= 60 or typo.get("is_suspicious") or overlays.get("fake_login_overlay"):
            llm_risk = "HIGH"
            ai_analysis = (
                f"[Fallback] Heuristic analysis: domain similarity "
                f"{typo.get('verdict','N/A')}, overlay risk "
                f"{overlays.get('overlay_risk_score', 0)}, "
                f"base score {risk_score}."
            )
        elif risk_score >= 30:
            llm_risk = "MEDIUM"
            ai_analysis = f"[Fallback] Moderate risk indicators. Score: {risk_score}."
        else:
            llm_risk = "LOW"
            ai_analysis = f"[Fallback] Low risk profile. Score: {risk_score}."

    # ── JS analysis ───────────────────────────────────────────────
    js_risk = "LOW"
    js_analysis = "No JS content"
    try:
        js_analysis = analyze_js_semantics(js_contents)
        js_lower = js_analysis.lower()
        if "high" in js_lower:
            js_risk = "HIGH"
        elif "medium" in js_lower:
            js_risk = "MEDIUM"
        else:
            js_risk = "LOW"
    except Exception as e:
        print("JS LLM ERROR:", e)
        js_analysis = "JS analysis failed"

    # ── Disagreement & confidence ─────────────────────────────────
    disagreement = llm_risk != "UNKNOWN" and llm_risk != risk
    confidence = 100

    if disagreement:
        confidence -= 20   # reduced penalty since fallback is rule-based
    if risk_score < 20:
        confidence -= 10
    elif risk_score > 70:
        confidence += 5

    # Boost confidence when enhanced signals are high-certainty
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        confidence = min(confidence + 15, 100)
    if overlays.get("fake_login_overlay"):
        confidence = min(confidence + 10, 100)

    llm_score_map = {"LOW": 20, "MEDIUM": 50, "HIGH": 80, "UNKNOWN": 50}
    llm_score = llm_score_map.get(llm_risk, 50)
    js_score = llm_score_map.get(js_risk, 20)

    # JS gets its own weight — if JS says HIGH it overrides a clean metadata score
    if "[Fallback]" in ai_analysis:
        final_score = int(risk_score * 0.60 + llm_score * 0.15 + js_score * 0.25)
    else:
        final_score = int(risk_score * 0.40 + llm_score * 0.35 + js_score * 0.25)

    # When LLM unavailable (fallback), trust heuristics more
    if "[Fallback]" in ai_analysis:
        final_score = int(risk_score * 0.75 + llm_score * 0.25)
    else:
        final_score = int(risk_score * 0.5 + llm_score * 0.5)

    if confidence < 70:
        final_score += 5

    # Clamp
    final_score = min(final_score, 100)

    if final_score < 30:
        final_risk = "LOW"
    elif final_score < 60:
        final_risk = "MEDIUM"
    else:
        final_risk = "HIGH"
    

    # If JS explicitly caught exfiltration/eval/stealData patterns, floor the score
    if js_risk == "HIGH":
        final_score = max(final_score, 70)

    # ── Build response ────────────────────────────────────────────
    result.update({
        "sandbox": {
            "redirects": sandbox_data["redirect_count"],
            "external_scripts": len(sandbox_data["external_scripts"]),
            "forms": sandbox_data["num_forms"],
            "has_password_field": sandbox_data["has_password_field"],
            "uses_https": sandbox_data["uses_https"],
            "external_links": sandbox_data["external_links_count"],
        },

        # ── New enhanced sections ──────────────────────────────────
        "typosquatting": sandbox_data.get("typosquatting", {}),
        "cookies": sandbox_data.get("cookies", {}),
        "overlays": sandbox_data.get("overlays", {}),

        "risk": risk,
        "score": risk_score,

        "llm_risk": llm_risk,
        "confidence": confidence,
        "disagreement": disagreement,

        "final_score": final_score,
        "final_risk": final_risk,

        "reasons": reasons,
        "ai_analysis": ai_analysis,
        "js_analysis": js_analysis,
    })

    return result
