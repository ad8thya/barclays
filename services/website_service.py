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
            "dynamic": {},
        }
 
    result["status_code"] = sandbox_data["status_code"]
    result["reachable"] = True
 
    forms        = sandbox_data["num_forms"]
    password_field = sandbox_data["has_password_field"]
    external_scripts = sandbox_data["external_scripts"]
    redirects    = sandbox_data["redirect_count"]
    uses_https   = sandbox_data["uses_https"]
    typo         = sandbox_data.get("typosquatting", {})
    overlays     = sandbox_data.get("overlays", {})
    dynamic      = sandbox_data.get("dynamic", {})
 
    # ── Fetch JS content ──────────────────────────────────────────
    # FIX: use scripts_to_fetch (external + same-origin) not just external
    js_contents = []
    for script_src in sandbox_data.get("scripts_to_fetch", []):
        try:
            full_url = urljoin(url, script_src)
            js_res = requests.get(full_url, timeout=3)
            js_contents.append(js_res.text[:2000])
        except Exception:
            continue
 
    # ── Features for LLM ─────────────────────────────────────────
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
        "typosquatting_verdict": typo.get("verdict", "NO_MATCH"),
        "similar_to": typo.get("closest_legit_domain", ""),
        "cookie_issues": len(sandbox_data["cookies"].get("issues", [])),
        "iframe_count": overlays.get("iframe_count", 0),
        "invisible_elements": overlays.get("invisible_elements", 0),
        "fake_login_overlay": overlays.get("fake_login_overlay", False),
        "inline_js_issues": len(overlays.get("inline_js_issues", [])),
        "dynamic_suspicious_requests": len(dynamic.get("suspicious_requests", [])),
        "dynamic_storage_writes": len(dynamic.get("storage_writes", [])),
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
        reasons.append("Contains @ symbol in URL")
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
 
    # ── Blend enhanced sandbox signals into heuristic ─────────────
    extra_risk = sandbox_data.get("extra_risk_score", 0)
    extra_reasons = sandbox_data.get("extra_risk_reasons", [])
    risk_score = int(risk_score * 0.6 + extra_risk * 0.4)
    reasons.extend(extra_reasons)
 
    # Hard floors for confirmed high-severity patterns
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        risk_score = max(risk_score, 80)
    if overlays.get("fake_login_overlay"):
        risk_score = max(risk_score, 75)
    if dynamic.get("dynamic_risk_score", 0) >= 60:
        risk_score = max(risk_score, 70)
 
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
        al = ai_analysis.lower()
        if "high" in al:
            llm_risk = "HIGH"
        elif "medium" in al:
            llm_risk = "MEDIUM"
        elif "low" in al:
            llm_risk = "LOW"
    except Exception as e:
        print("LLM ERROR:", e)
        # Rule-based fallback when Ollama offline
        if risk_score >= 60 or typo.get("is_suspicious") or overlays.get("fake_login_overlay"):
            llm_risk = "HIGH"
            ai_analysis = (
                f"[Fallback] Score {risk_score}, typosquat verdict: "
                f"{typo.get('verdict','N/A')}, overlay risk: "
                f"{overlays.get('overlay_risk_score', 0)}, "
                f"dynamic risk: {dynamic.get('dynamic_risk_score', 0)}."
            )
        elif risk_score >= 30:
            llm_risk = "MEDIUM"
            ai_analysis = f"[Fallback] Moderate risk indicators. Score: {risk_score}."
        else:
            llm_risk = "LOW"
            ai_analysis = f"[Fallback] Low risk profile. Score: {risk_score}."
 
    # ── JS analysis ───────────────────────────────────────────────
    js_risk = "LOW"
    js_analysis = "No JS content to analyse"
    if js_contents:
        try:
            js_analysis = analyze_js_semantics(js_contents)
            jl = js_analysis.lower()
            if "high" in jl:
                js_risk = "HIGH"
            elif "medium" in jl:
                js_risk = "MEDIUM"
            else:
                js_risk = "LOW"
        except Exception as e:
            print("JS LLM ERROR:", e)
            js_analysis = "JS analysis failed"
    else:
        # No external/same-origin script files, but inline JS was scanned statically
        inline_issues = overlays.get("inline_js_issues", [])
        if inline_issues:
            js_analysis = f"[Static scan] Inline JS issues: {'; '.join(inline_issues)}"
            js_risk = "HIGH" if len(inline_issues) >= 3 else "MEDIUM"
 
    # ── Confidence ────────────────────────────────────────────────
    disagreement = llm_risk != "UNKNOWN" and llm_risk != risk
    confidence = 100
 
    if disagreement:
        confidence -= 20
    if risk_score < 20:
        confidence -= 10
    elif risk_score > 70:
        confidence += 5
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        confidence = min(confidence + 15, 100)
    if overlays.get("fake_login_overlay"):
        confidence = min(confidence + 10, 100)
    if dynamic.get("available") and dynamic.get("dynamic_risk_score", 0) >= 40:
        confidence = min(confidence + 10, 100)
 
    # ── Score fusion ──────────────────────────────────────────────
    llm_score_map = {"LOW": 20, "MEDIUM": 50, "HIGH": 80, "UNKNOWN": 50}
    llm_score = llm_score_map.get(llm_risk, 50)
    js_score  = llm_score_map.get(js_risk, 20)
 
    is_fallback = "[Fallback]" in ai_analysis
 
    if is_fallback:
        # Ollama offline — trust heuristics + JS more
        final_score = int(risk_score * 0.60 + js_score * 0.25 + llm_score * 0.15)
    else:
        # Ollama running — balanced fusion
        final_score = int(risk_score * 0.40 + llm_score * 0.35 + js_score * 0.25)
 
    if confidence < 70:
        final_score += 5
 
    # Hard floor: JS analysis caught clear exfil/obfuscation
    if js_risk == "HIGH":
        final_score = max(final_score, 70)
 
    # Hard floor: dynamic analysis caught runtime exfil
    if dynamic.get("dynamic_risk_score", 0) >= 60:
        final_score = max(final_score, 75)
 
    final_score = min(final_score, 100)
 
    if final_score < 30:
        final_risk = "LOW"
    elif final_score < 60:
        final_risk = "MEDIUM"
    else:
        final_risk = "HIGH"
 
    # ── Build response ────────────────────────────────────────────
    result.update({
        "sandbox": {
            "redirects": sandbox_data["redirect_count"],
            "external_scripts": len(sandbox_data["external_scripts"]),
            "same_origin_scripts": len(sandbox_data.get("same_origin_scripts", [])),
            "forms": sandbox_data["num_forms"],
            "has_password_field": sandbox_data["has_password_field"],
            "uses_https": sandbox_data["uses_https"],
            "external_links": sandbox_data["external_links_count"],
        },
        "typosquatting": typo,
        "cookies":       sandbox_data.get("cookies", {}),
        "overlays":      overlays,
        "dynamic":       dynamic,
 
        "risk":          risk,
        "score":         risk_score,
        "llm_risk":      llm_risk,
        "js_risk":       js_risk,
        "confidence":    confidence,
        "disagreement":  disagreement,
        "final_score":   final_score,
        "final_risk":    final_risk,
        "reasons":       reasons,
        "ai_analysis":   ai_analysis,
        "js_analysis":   js_analysis,
    })
 
    return result
