# ============================================================
# services/website_service.py  — FULL FILE, COPY-PASTE READY
# ============================================================

from urllib.parse import urljoin, urlparse
import requests

from services.js_analysis_service import analyze_js_semantics
from services.llm_service import analyze_with_llm, parse_llm_risk
from services.sandbox_service import run_sandbox


def _parse_risk_label(text: str, default: str = "LOW") -> str:
    """Extract RISK: label from LLM output — only reads the RISK: line."""
    for line in text.upper().splitlines():
        line = line.strip()
        if line.startswith("RISK:"):
            val = line.replace("RISK:", "").strip().split()[0]
            if val in ("HIGH", "MEDIUM", "LOW"):
                return val
    return default


def analyze_website(url: str) -> dict:
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    sandbox = run_sandbox(url)

    if not sandbox.get("reachable"):
        return {
            "domain": domain, "status_code": None, "reachable": False,
            "risk": "HIGH", "score": 85, "final_score": 85, "final_risk": "HIGH",
            "confidence": 70, "reasons": ["Website not reachable"],
            "ai_analysis": "Site unreachable", "js_analysis": "N/A",
            "sandbox": {}, "typosquatting": {}, "cookies": {}, "overlays": {}, "dynamic": {},
        }

    typo        = sandbox.get("typosquatting", {})
    overlays    = sandbox.get("overlays", {})
    dynamic     = sandbox.get("dynamic", {})
    domain_age  = sandbox.get("domain_age", {})
    dns         = sandbox.get("dns", {})
    headers     = sandbox.get("security_headers", {})
    injection   = sandbox.get("prompt_injection", {})
    extra_risk  = sandbox.get("extra_risk_score", 0)

    uses_https     = sandbox["uses_https"]
    password_field = sandbox["has_password_field"]
    redirects      = sandbox["redirect_count"]
    forms          = sandbox["num_forms"]
    ext_scripts    = sandbox["external_scripts"]

    # ── Heuristic score ───────────────────────────────────────────
    # Only signals that are genuinely discriminative.
    # A legitimate site should stay well below 35.
    h_score = 0
    h_reasons = []

    if "@" in url:
        h_score += 35; h_reasons.append("@ symbol in URL")
    if not uses_https:
        h_score += 20; h_reasons.append("Not using HTTPS")
    if not uses_https and password_field:
        h_score += 15; h_reasons.append("Password field over HTTP")
    if injection.get("has_issues"):
        h_score += 20; h_reasons.append("Prompt injection payload in page")
    if dns.get("fast_flux_suspected"):
        h_score += 20; h_reasons.append("Fast-flux DNS detected")

    # URL signals — only flag combinations, not individual weak signals
    sus_kw = any(w in url.lower() for w in ["login", "verify", "secure", "account", "update", "confirm"])
    if sus_kw and password_field:
        h_score += 18; h_reasons.append("Suspicious URL keywords + password field")
    elif sus_kw and not uses_https:
        h_score += 12; h_reasons.append("Suspicious URL keywords + no HTTPS")

    if len(url) > 100:
        h_score += 12; h_reasons.append("Very long URL")
    if url.count(".") > 5:
        h_score += 12; h_reasons.append("Excessive subdomains")
    if redirects > 3:
        h_score += 10; h_reasons.append(f"Many redirects ({redirects})")
    if overlays.get("fake_login_overlay"):
        h_score += 30; h_reasons.append("Fake login overlay detected")

    h_score = min(h_score, 100)

    # ── Pre-fusion: blend heuristic + sandbox ─────────────────────
    pre_fusion = int(h_score * 0.40 + extra_risk * 0.60)

    # ── Fetch JS ──────────────────────────────────────────────────
    js_contents = []
    for src in sandbox.get("scripts_to_fetch", []):
        try:
            r = requests.get(urljoin(url, src), timeout=3,
                             headers={"User-Agent": "Mozilla/5.0"})
            js_contents.append(r.text[:2000])
        except Exception:
            continue

    # ── LLM analysis ──────────────────────────────────────────────
    features = {
        "url": url, "domain": domain,
        "has_password_field": password_field,
        "num_forms": forms,
        "external_scripts": len(ext_scripts),
        "uses_https": uses_https,
        "url_length": len(url),
        "has_suspicious_keywords": sus_kw,
        "redirects": redirects,
        "typosquatting_verdict": typo.get("verdict", "NO_MATCH"),
        "similar_to": typo.get("closest_legit_domain", ""),
        "cookie_issues": len(sandbox["cookies"].get("issues", [])),
        "iframe_count": overlays.get("iframe_count", 0),
        "fake_login_overlay": overlays.get("fake_login_overlay", False),
        "inline_js_issues": len(overlays.get("inline_js_issues", [])),
        "dynamic_suspicious_requests": len(dynamic.get("suspicious_requests", [])),
        "domain_age_days": domain_age.get("domain_age_days"),
        "is_new_domain": domain_age.get("is_new_domain", False),
        "has_spf": dns.get("has_spf", True),
        "has_dmarc": dns.get("has_dmarc", True),
        "fast_flux_suspected": dns.get("fast_flux_suspected", False),
        "missing_security_headers": headers.get("headers_missing", []),
        "prompt_injection_detected": injection.get("has_issues", False),
        "prompt_injection_count": len(injection.get("injections_found", [])),
    }

    llm_risk = "UNKNOWN"
    ai_analysis = "LLM skipped"
    is_fallback = True

    try:
        raw = analyze_with_llm(features)
        ai_analysis = raw
        llm_risk = _parse_risk_label(raw)
        is_fallback = False
    except Exception as e:
        print("LLM ERROR:", e)
        llm_risk = "HIGH" if pre_fusion >= 60 else "MEDIUM" if pre_fusion >= 35 else "LOW"
        ai_analysis = f"[Fallback] Pre-fusion: {pre_fusion}"
        is_fallback = True

    # ── JS analysis ───────────────────────────────────────────────
    js_risk = "LOW"
    js_analysis = "No JS content"

    actual_inline_issues = len(overlays.get("inline_js_issues", []))

    if js_contents:
        try:
            js_analysis = analyze_js_semantics(js_contents)
            # CRITICAL: parse ONLY the RISK: line, never scan full text
            js_risk = _parse_risk_label(js_analysis, default="LOW")
        except Exception:
            js_analysis = "JS analysis failed"
            js_risk = "LOW"
    elif actual_inline_issues >= 3:
        js_risk = "HIGH"
        js_analysis = f"[Static] {actual_inline_issues} high-risk inline JS patterns"
    elif actual_inline_issues >= 1:
        js_risk = "MEDIUM"
        js_analysis = f"[Static] {actual_inline_issues} inline JS pattern(s)"

    # If LLM called JS HIGH but we found zero inline issues, be sceptical
    if js_risk == "HIGH" and actual_inline_issues == 0 and not js_contents:
        js_risk = "LOW"

    # ── Final score fusion ────────────────────────────────────────
    llm_map = {"LOW": 12, "MEDIUM": 42, "HIGH": 78, "UNKNOWN": pre_fusion}
    js_map  = {"LOW": 8,  "MEDIUM": 38, "HIGH": 72}

    llm_s = llm_map[llm_risk]
    js_s  = js_map[js_risk]

    if is_fallback:
        final_score = int(pre_fusion * 0.80 + js_s * 0.20)
    else:
        final_score = int(pre_fusion * 0.60 + llm_s * 0.25 + js_s * 0.15)

    # ── Hard floors — only definitive, high-confidence signals ────
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        final_score = max(final_score, 78)
    if overlays.get("fake_login_overlay"):
        final_score = max(final_score, 72)
    if dynamic.get("dynamic_risk_score", 0) >= 60:
        final_score = max(final_score, 70)
    if domain_age.get("domain_age_days") is not None and domain_age["domain_age_days"] < 7:
        final_score = max(final_score, 68)
    if injection.get("prompt_injection_risk_score", 0) >= 50:
        final_score = max(final_score, 65)
    # JS floor only if LLM AND static scan both agree, or if exfil patterns found
    if js_risk == "HIGH" and actual_inline_issues >= 3:
        final_score = max(final_score, 65)

    final_score = min(final_score, 100)

    final_risk = "HIGH" if final_score >= 60 else "MEDIUM" if final_score >= 35 else "LOW"
    risk       = "HIGH" if h_score    >= 60 else "MEDIUM" if h_score    >= 35 else "LOW"

    disagreement = llm_risk not in ("UNKNOWN",) and llm_risk != final_risk
    confidence = 85
    if is_fallback:      confidence -= 15
    if disagreement:     confidence -= 10
    if typo.get("is_suspicious"): confidence = min(confidence + 10, 100)
    confidence = max(confidence, 40)

    all_reasons = list(dict.fromkeys(h_reasons + sandbox.get("extra_risk_reasons", [])))

    return {
        "domain": domain,
        "status_code": sandbox["status_code"],
        "reachable": True,
        "sandbox": {
            "redirects": sandbox["redirect_count"],
            "external_scripts": len(ext_scripts),
            "forms": forms,
            "has_password_field": password_field,
            "uses_https": uses_https,
            "external_links": sandbox["external_links_count"],
        },
        "typosquatting":    typo,
        "cookies":          sandbox.get("cookies", {}),
        "overlays":         overlays,
        "dynamic":          dynamic,
        "security_headers": sandbox.get("security_headers", {}),
        "domain_age":       domain_age,
        "dns":              dns,
        "prompt_injection": injection,
        "fingerprint":      sandbox.get("fingerprint", {}),
        "risk":             risk,
        "score":            h_score,
        "pre_fusion_score": pre_fusion,
        "final_score":      final_score,
        "final_risk":       final_risk,
        "llm_risk":         llm_risk,
        "js_risk":          js_risk,
        "confidence":       confidence,
        "disagreement":     disagreement,
        "reasons":          all_reasons,
        "ai_analysis":      ai_analysis,
        "js_analysis":      js_analysis,
    }
