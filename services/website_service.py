import requests
from urllib.parse import urlparse

def analyze_website(url: str):
    result = {}

    # normalize URL
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    result["domain"] = domain

    # check if reachable
    try:
        response = requests.get(url, timeout=5)
        final_url = response.url.lower()
        result["status_code"] = response.status_code
        result["reachable"] = True
    except:
        return {
            "domain": domain,
            "reachable": False,
            "risk": "HIGH",
            "score": 90,
            "reasons": ["Website not reachable"]
        }

    # 🔥 smarter scoring
    risk_score = 0
    reasons = []

    # 1. suspicious words in URL (NOT HTML anymore)
    suspicious_words = ["login", "verify", "secure", "account", "update"]
    if any(word in url.lower() for word in suspicious_words):
        risk_score += 30
        reasons.append("Suspicious keywords in URL")

    # 2. too many dots (subdomain abuse)
    if domain.count(".") > 3:
        risk_score += 20
        reasons.append("Too many subdomains")

    # 3. URL length
    if len(url) > 75:
        risk_score += 10
        reasons.append("URL is unusually long")

    # 4. HTTP instead of HTTPS (check actual final URL)
    if not final_url.startswith("https"):
        risk_score += 20
        reasons.append("Not using HTTPS")

    # 5. numbers in domain (common in fake sites)
    if any(char.isdigit() for char in domain):
        risk_score += 10
        reasons.append("Numbers in domain")

    # 6. @ symbol trick
    if "@" in url:
        risk_score += 30
        reasons.append("Contains @ symbol")

    # 🔥 classify
    if risk_score < 30:
        risk = "LOW"
    elif risk_score < 60:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    result["risk"] = risk
    result["score"] = risk_score
    result["reasons"] = reasons
    print('new version running')
    return result