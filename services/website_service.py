# services/website_service.py
"""
Website analysis service.

Scoring philosophy:
- Heuristic score: URL/content signals, 0–100, with per-signal weights
  calibrated so a legitimate site (Google, HSBC) stays well below 40.
- extra_risk_score from sandbox: already a weighted blend (0–100).
- LLM score and JS score: mapped to 0–100.
- Final score: weighted blend of all four — not additive stacking.

Legitimate site target: final_score < 30 (LOW).
Clear phishing site target: final_score > 65 (HIGH).
"""

from urllib.parse import urljoin, urlparse

import requests

from services.js_analysis_service import analyze_js_semantics
from services.llm_service import analyze_with_llm, parse_llm_risk
from services.sandbox_service import run_sandbox, _is_trusted


# ─────────────────────────────────────────────────────────────────────────────
# HEURISTIC SCORING
# ─────────────────────────────────────────────────────────────────────────────
#
# Weights are chosen so that a typical legitimate site accumulates < 35 points
# and a typical phishing site accumulates > 60 points — BEFORE blending with
# the sandbox sub-scores.
#
# Rule of thumb for weights:
#   - Signal is near-certain phishing indicator:  25–35
#   - Signal is suspicious but common on legit:   10–20
#   - Signal is weak / contextual:                5–10

_HEURISTIC_RULES = [
    # (condition_fn, weight, label)
    # High-confidence
    (lambda f: "@" in f["url"],                                                          35, "@ symbol in URL"),
    (lambda f: f["typosquatting_verdict"] in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"),      0,  ""),  # handled by hard floor
    (lambda f: f["fake_login_overlay"],                                                  30, "Fake login overlay"),
    (lambda f: f["inline_js_issues"] >= 3,                                               25, "Multiple suspicious inline JS patterns"),
    # Medium-confidence
    (lambda f: not f["uses_https"],                                                      20, "Not using HTTPS"),
    (lambda f: f["has_password_field"] and not f["uses_https"],                          20, "Password field on HTTP page"),
    (lambda f: f["is_new_domain"],                                                       0,  ""),  # handled by domain_age sub-score
    (lambda f: f["has_suspicious_keywords"] and f["has_password_field"],                 20, "Suspicious keywords + password field"),
    (lambda f: f["has_suspicious_keywords"] and not f["has_password_field"],             10, "Suspicious keywords in URL"),
    (lambda f: f["url_length"] > 100,                                                    15, "Very long URL (>100 chars)"),
    (lambda f: 75 < f["url_length"] <= 100,                                               8, "Long URL (>75 chars)"),
    (lambda f: f["url"].count(".") > 4,                                                  15, "Excessive subdomains"),
    (lambda f: f["redirects"] > 3,                                                       12, "Many redirects (>3)"),
    (lambda f: f["redirects"] == 3,                                                       6, "Several redirects"),
    # Low-confidence (only add if combined with other signals via weighting)
    (lambda f: f["has_password_field"] and f["uses_https"],                               8, "Password field (HTTPS — normal for login pages)"),
    (lambda f: f["num_forms"] > 0 and not f["has_password_field"],                        4, "Form without password field"),
    (lambda f: f["prompt_injection_detected"],                                            20, "Prompt injection payload in page"),
    (lambda f: f["fast_flux_suspected"],                                                  20, "Fast-flux DNS detected"),
]


def _compute_heuristic_score(features: dict) -> tuple[int, list[str]]:
    """Returns (0–100 score, list of reason strings)."""
    score = 0
    reasons = []
    for condition, weight, label in _HEURISTIC_RULES:
        try:
            if weight > 0 and condition(features):
                score += weight
                if label:
                    reasons.append(label)
        except Exception:
            continue
    return min(score, 100), reasons


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANALYSER
# ─────────────────────────────────────────────────────────────────────────────

def analyze_website(url: str) -> dict:
    result = {}

    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    result["domain"] = domain

    trusted = _is_trusted(domain)

    # ── Run sandbox ───────────────────────────────────────────────
    sandbox_data = run_sandbox(url)

    if not sandbox_data.get("reachable"):
        return {
            "domain": domain,
            "status_code": None,
            "reachable": False,
            "risk": "HIGH",
            "score": 85,
            "final_score": 85,
            "final_risk": "HIGH",
            "confidence": 70,
            "reasons": ["Website not reachable"],
            "ai_analysis": "Site unreachable — treating as high risk",
            "js_analysis": "No JS analysis",
            "sandbox": {},
            "typosquatting": {},
            "cookies": {},
            "overlays": {},
            "dynamic": {},
        }

    result["status_code"] = sandbox_data["status_code"]
    result["reachable"] = True

    forms           = sandbox_data["num_forms"]
    password_field  = sandbox_data["has_password_field"]
    external_scripts = sandbox_data["external_scripts"]
    redirects       = sandbox_data["redirect_count"]
    uses_https      = sandbox_data["uses_https"]
    typo            = sandbox_data.get("typosquatting", {})
    overlays        = sandbox_data.get("overlays", {})
    dynamic         = sandbox_data.get("dynamic", {})
    domain_age_data = sandbox_data.get("domain_age", {})
    dns_data        = sandbox_data.get("dns", {})
    header_data     = sandbox_data.get("security_headers", {})
    injection_data  = sandbox_data.get("prompt_injection", {})

    # ── Fetch JS content ──────────────────────────────────────────
    js_contents = []
    for script_src in sandbox_data.get("scripts_to_fetch", []):
        try:
            full_url = urljoin(url, script_src)
            js_res = requests.get(full_url, timeout=3,
                                  headers={"User-Agent": "Mozilla/5.0"})
            js_contents.append(js_res.text[:2000])
        except Exception:
            continue

    # ── Build feature dict for heuristics + LLM ──────────────────
    features = {
        "url": url,
        "domain": domain,
        "trusted": trusted,
        "has_password_field": password_field,
        "num_forms": forms,
        "external_scripts": len(external_scripts),
        "uses_https": uses_https,
        "url_length": len(url),
        "has_suspicious_keywords": any(
            word in url.lower()
            for word in ["login", "verify", "secure", "account", "update", "confirm"]
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
        "domain_age_days": domain_age_data.get("domain_age_days"),
        "is_new_domain": domain_age_data.get("is_new_domain", False),
        "has_spf": dns_data.get("has_spf", True),
        "has_dmarc": dns_data.get("has_dmarc", True),
        "fast_flux_suspected": dns_data.get("fast_flux_suspected", False),
        "missing_security_headers": header_data.get("headers_missing", []),
        "prompt_injection_detected": injection_data.get("has_issues", False),
        "prompt_injection_count": len(injection_data.get("injections_found", [])),
    }

    # ── Heuristic score ───────────────────────────────────────────
    heuristic_score, heuristic_reasons = _compute_heuristic_score(features)

    # Trusted domains get a heuristic ceiling — we trust our list, not the URL signals
    if trusted:
        heuristic_score = min(heuristic_score, 20)

    # ── Sandbox extra_risk_score (already a weighted blend 0–100) ─
    extra_risk = sandbox_data.get("extra_risk_score", 0)
    extra_reasons = sandbox_data.get("extra_risk_reasons", [])

    # Pre-fusion score: blend heuristic + sandbox signals
    # Heuristic: 45% — direct URL/content signals
    # Sandbox:   55% — richer sub-analyser signals
    pre_fusion_score = int(heuristic_score * 0.45 + extra_risk * 0.55)

    # ── LLM analysis ──────────────────────────────────────────────
    llm_risk = "UNKNOWN"
    llm_confidence = 50
    ai_analysis = "LLM analysis skipped"
    is_fallback = True

    try:
        raw_response = analyze_with_llm(features)
        ai_analysis = raw_response
        llm_risk, llm_confidence = parse_llm_risk(raw_response)
        is_fallback = False
    except Exception as e:
        print("LLM ERROR:", e)
        # Calibrated fallback — mirror pre_fusion_score
        if pre_fusion_score >= 60 or typo.get("is_suspicious") or overlays.get("fake_login_overlay"):
            llm_risk = "HIGH"
            ai_analysis = (
                f"[Fallback] Pre-fusion score {pre_fusion_score}, "
                f"typosquat: {typo.get('verdict', 'N/A')}, "
                f"domain age: {domain_age_data.get('domain_age_days', 'unknown')}d."
            )
        elif pre_fusion_score >= 30:
            llm_risk = "MEDIUM"
            ai_analysis = f"[Fallback] Moderate indicators. Pre-fusion score: {pre_fusion_score}."
        else:
            llm_risk = "LOW"
            ai_analysis = f"[Fallback] Low risk profile. Pre-fusion score: {pre_fusion_score}."
        is_fallback = True

    # ── JS analysis ───────────────────────────────────────────────
    js_risk = "LOW"
    js_analysis = "No JS content to analyse"
    if js_contents:
        try:
            js_analysis = analyze_js_semantics(js_contents)
            jl = js_analysis.lower()
            js_risk = "HIGH" if "high" in jl else "MEDIUM" if "medium" in jl else "LOW"
        except Exception as e:
            print("JS LLM ERROR:", e)
            js_analysis = "JS analysis failed"
    else:
        inline_issues = overlays.get("inline_js_issues", [])
        if inline_issues:
            js_analysis = f"[Static scan] Inline JS issues: {'; '.join(inline_issues)}"
            js_risk = "HIGH" if len(inline_issues) >= 3 else "MEDIUM"

    # ── Final score fusion ────────────────────────────────────────
    #
    # Weights:
    #   Pre-fusion (heuristic + sandbox):  60%  ← most reliable, our own signals
    #   LLM score:                         25%  ← useful when running, fallback otherwise
    #   JS score:                          15%  ← supporting signal
    #
    # When LLM is offline (fallback), shift weight to pre-fusion.

    llm_score_map = {"LOW": 15, "MEDIUM": 45, "HIGH": 80, "UNKNOWN": pre_fusion_score}
    js_score_map  = {"LOW": 10, "MEDIUM": 40, "HIGH": 75}

    llm_score = llm_score_map.get(llm_risk, pre_fusion_score)
    js_score  = js_score_map.get(js_risk, 10)

    if is_fallback:
        # LLM offline → trust our own signals more
        final_score = int(pre_fusion_score * 0.75 + js_score * 0.25)
    else:
        final_score = int(pre_fusion_score * 0.60 + llm_score * 0.25 + js_score * 0.15)

    # ── Hard floors — only truly definitive signals ───────────────
    # These exist because certain combinations are near-certain phishing
    # regardless of what other signals say.

    # Near-exact domain spoof of a bank/known brand
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        final_score = max(final_score, 78)

    # Overlay injecting a fake password form
    if overlays.get("fake_login_overlay"):
        final_score = max(final_score, 72)

    # Runtime exfiltration confirmed by dynamic analysis
    if dynamic.get("dynamic_risk_score", 0) >= 60:
        final_score = max(final_score, 70)

    # Domain less than 7 days old
    if domain_age_data.get("domain_age_days") is not None \
            and domain_age_data["domain_age_days"] < 7:
        final_score = max(final_score, 68)

    # Prompt injection / content poisoning (attacker knows tools are scanning)
    if injection_data.get("prompt_injection_risk_score", 0) >= 50:
        final_score = max(final_score, 65)

    # JS analysis confirmed exfil/keylogger
    if js_risk == "HIGH":
        final_score = max(final_score, 65)

    # Trusted domain ceiling — don't flag google.com as HIGH
    if trusted:
        final_score = min(final_score, 35)

    final_score = min(final_score, 100)

    # ── Risk label ────────────────────────────────────────────────
    # Thresholds chosen so: LOW < 35, MEDIUM 35–59, HIGH ≥ 60
    if final_score < 35:
        final_risk = "LOW"
    elif final_score < 60:
        final_risk = "MEDIUM"
    else:
        final_risk = "HIGH"

    # Heuristic-only label (for comparison)
    if heuristic_score < 35:
        risk = "LOW"
    elif heuristic_score < 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    # ── Confidence ────────────────────────────────────────────────
    disagreement = llm_risk not in ("UNKNOWN",) and llm_risk != final_risk
    confidence = 85

    if is_fallback:
        confidence -= 15
    if disagreement:
        confidence -= 10
    if typo.get("verdict") in ("EXACT_SPOOF", "BRAND_IN_SUBDOMAIN"):
        confidence = min(confidence + 10, 100)
    if overlays.get("fake_login_overlay"):
        confidence = min(confidence + 8, 100)
    if dynamic.get("available") and dynamic.get("dynamic_risk_score", 0) >= 40:
        confidence = min(confidence + 8, 100)
    if trusted:
        confidence = min(confidence + 10, 100)

    confidence = max(confidence, 40)

    # ── Assemble response ─────────────────────────────────────────
    all_reasons = list(dict.fromkeys(heuristic_reasons + extra_reasons))

    result.update({
        "sandbox": {
            "redirects":          sandbox_data["redirect_count"],
            "external_scripts":   len(sandbox_data["external_scripts"]),
            "same_origin_scripts": len(sandbox_data.get("same_origin_scripts", [])),
            "forms":              sandbox_data["num_forms"],
            "has_password_field": sandbox_data["has_password_field"],
            "uses_https":         sandbox_data["uses_https"],
            "external_links":     sandbox_data["external_links_count"],
        },
        "typosquatting":    typo,
        "cookies":          sandbox_data.get("cookies", {}),
        "overlays":         overlays,
        "dynamic":          dynamic,
        "security_headers": sandbox_data.get("security_headers", {}),
        "domain_age":       sandbox_data.get("domain_age", {}),
        "dns":              sandbox_data.get("dns", {}),
        "prompt_injection": sandbox_data.get("prompt_injection", {}),
        "fingerprint":      sandbox_data.get("fingerprint", {}),

        # Scores
        "risk":             risk,
        "score":            heuristic_score,
        "pre_fusion_score": pre_fusion_score,
        "final_score":      final_score,
        "final_risk":       final_risk,
        "llm_risk":         llm_risk,
        "js_risk":          js_risk,
        "confidence":       confidence,
        "disagreement":     disagreement,
        "is_trusted":       trusted,

        # Explanations
        "reasons":          all_reasons,
        "ai_analysis":      ai_analysis,
        "js_analysis":      js_analysis,
    })

    return result
