def analyze_text(text: str) -> dict:
    text_lower = text.lower()

    risk_score = 0.0
    reasons = []

    # English + Hindi keywords
    if "bank" in text_lower or "खाता" in text_lower:
        risk_score += 0.3
        reasons.append("bank-related keywords")

    if "urgent" in text_lower or "तुरंत" in text_lower:
        risk_score += 0.3
        reasons.append("urgent tone")

    if "click" in text_lower or "http" in text_lower or "लिंक" in text_lower:
        risk_score += 0.4
        reasons.append("suspicious link")

    return {
        "risk_score": min(risk_score, 1.0),
        "reason": ", ".join(reasons) if reasons else "No strong scam signals"
    }