from urllib.parse import urljoin
from services.js_analysis_service import analyze_js_semantics
from services.llm_service import analyze_with_llm
from services.sandbox_service import run_sandbox

from urllib.parse import urlparse
import requests


def analyze_website(url: str):
    result = {}

    # 🔹 Normalize
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    result["domain"] = domain

    # 🔹 Run sandbox
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
            "js_analysis": "No JS analysis"
        }

    # 🔹 Extract from sandbox
    result["status_code"] = sandbox_data["status_code"]
    result["reachable"] = True

    forms = sandbox_data["num_forms"]
    password_field = sandbox_data["has_password_field"]
    external_scripts = sandbox_data["external_scripts"]
    redirects = sandbox_data["redirect_count"]
    uses_https = sandbox_data["uses_https"]

    # 🔹 Fetch JS content (light)

    js_contents = []

    for script in external_scripts[:2]:
        try:
            full_url = urljoin(url, script)  # 🔥 FIX

            js_res = requests.get(full_url, timeout=3)
            js_contents.append(js_res.text[:1000])

        except Exception as e:
            continue
    # 🔹 Features for LLM
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
        "redirects": redirects
    }

    # 🔹 Heuristic scoring
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

    # 🔹 Base classification
    if risk_score < 30:
        risk = "LOW"
    elif risk_score < 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    # 🔹 LLM analysis
    llm_risk = "UNKNOWN"
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
        ai_analysis = "LLM analysis failed"

    # 🔹 JS analysis
    try:
        js_analysis = analyze_js_semantics(js_contents)
    except Exception as e:
        print("JS LLM ERROR:", e)
        js_analysis = "JS analysis failed"

    # 🔹 Disagreement
    disagreement = (
        llm_risk != "UNKNOWN" and llm_risk != risk
    )

    # 🔹 Confidence
    confidence = 100

    if disagreement:
        confidence -= 30

    if risk_score < 20:
        confidence -= 10
    elif risk_score > 70:
        confidence += 5

    # 🔹 LLM score mapping
    llm_score_map = {
        "LOW": 20,
        "MEDIUM": 50,
        "HIGH": 80,
        "UNKNOWN": 50
    }

    llm_score = llm_score_map.get(llm_risk, 50)

    # 🔹 Final fusion
    final_score = int((risk_score * 0.5) + (llm_score * 0.5))

    if confidence < 70:
        final_score += 5

    # 🔹 Final classification
    if final_score < 30:
        final_risk = "LOW"
    elif final_score < 60:
        final_risk = "MEDIUM"
    else:
        final_risk = "HIGH"

    # 🔹 Final output
    result.update({
        
        "sandbox": {
            "redirects": sandbox_data["redirect_count"],
            "external_scripts": len(sandbox_data["external_scripts"]),
            "forms": sandbox_data["num_forms"],
            "has_password_field": sandbox_data["has_password_field"],
            "uses_https": sandbox_data["uses_https"],
            "external_links": sandbox_data["external_links_count"]
        }, 

        "risk": risk,
        "score": risk_score,

        "llm_risk": llm_risk,
        "confidence": confidence,
        "disagreement": disagreement,

        "final_score": final_score,
        "final_risk": final_risk,

        "reasons": reasons,
        "ai_analysis": ai_analysis,
        "js_analysis": js_analysis
    })

    return result