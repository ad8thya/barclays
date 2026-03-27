from services.js_analysis_service import analyze_js_semantics
from services.llm_service import analyze_with_llm
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def analyze_website(url: str):
    result = {}

    # 🔹 Normalize URL
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    result["domain"] = domain

    # 🔹 Fetch website
    try:
        response = requests.get(url, timeout=5)
        final_url = response.url.lower()
        html = response.text
        result["status_code"] = response.status_code
        result["reachable"] = True
    except Exception as e:
        print("REQUEST ERROR:", e)
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
            "ai_analysis": "Site is unreachable, cannot perform full analysis",
            "js_analysis": "No JS analysis available"
        }

    # 🔹 Parse HTML
    soup = BeautifulSoup(html, "html.parser")

    # 🔹 Extract features
    forms = soup.find_all("form")
    password_field = soup.find("input", {"type": "password"})

    scripts = soup.find_all("script", src=True)
    external_scripts = [
        s["src"] for s in scripts if domain not in s["src"]
    ]

    # 🔹 Fetch JS content
    js_contents = []
    for script in external_scripts[:2]:
        try:
            if script.startswith("http"):
                js_res = requests.get(script, timeout=3)
                js_contents.append(js_res.text[:1000])
        except:
            continue

    # 🔹 Feature object
    features = {
        "url": url,
        "domain": domain,
        "has_password_field": bool(password_field),
        "num_forms": len(forms),
        "external_scripts": len(external_scripts),
        "uses_https": final_url.startswith("https"),
        "url_length": len(url),
        "has_suspicious_keywords": any(
            word in url.lower() for word in ["login", "verify", "secure", "account"]
        ),
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

    if not features["uses_https"]:
        risk_score += 15
        reasons.append("Not using HTTPS")

    if forms:
        risk_score += 15
        reasons.append("Contains form (possible login page)")

    if password_field:
        risk_score += 20
        reasons.append("Password field detected")

    if len(external_scripts) > 3:
        risk_score += 10
        reasons.append("Multiple external scripts")

    if len(response.history) > 2:
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

    # 🔹 FINAL FUSION SCORE
    final_score = int((risk_score * 0.8) + (llm_score * 0.2))

    if confidence < 70:
        final_score += 5  # uncertainty bump

    # 🔹 Final classification
    if final_score < 30:
        final_risk = "LOW"
    elif final_score < 60:
        final_risk = "MEDIUM"
    else:
        final_risk = "HIGH"

    # 🔹 Final result
    result.update({
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