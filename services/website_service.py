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

    # 🔹 Try fetching website
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
            "reasons": ["Website not reachable"],
            "ai_analysis": "Site is unreachable, cannot perform full analysis"
        }

    # 🔹 Parse HTML
    soup = BeautifulSoup(html, "html.parser")

    # 🔹 Extract features FIRST
    forms = soup.find_all("form")
    password_field = soup.find("input", {"type": "password"})

    scripts = soup.find_all("script", src=True)
    external_scripts = [
        s["src"] for s in scripts if domain not in s["src"]
    ]

    # 🔹 Feature object (for LLM)
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

    # 🔹 Risk scoring
    risk_score = 0
    reasons = []

    # URL checks
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

    # Content checks
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

    # 🔹 Classification
    if risk_score < 30:
        risk = "LOW"
    elif risk_score < 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    # 🔹 LLM analysis (safe)
    try:
        ai_analysis = analyze_with_llm(features)
    except Exception as e:
        print("LLM ERROR:", e)
        ai_analysis = "LLM analysis failed"

    # 🔹 Final result
    result.update({
        "risk": risk,
        "score": risk_score,
        "reasons": reasons,
        "ai_analysis": ai_analysis
    })

    return result