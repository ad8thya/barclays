# utils/text.py
import re

PHISHING_KEYWORDS = [
    # Account / Security Urgency
    "verify your account", "account verification required",
    "your account has been suspended", "account suspended",
    "confirm your identity", "identity verification needed",
    "unusual activity detected", "suspicious login attempt",
    "security alert", "security notice",
    "unauthorized access detected", "login attempt blocked",
    "reset your password", "update your password",
    "password expired", "change your credentials",
    "secure your account", "protect your account",
    "account locked", "unlock your account",

    # Urgency / Pressure
    "click here immediately", "act now", "urgent action required",
    "immediate response required", "respond तुरंत",  # sometimes mixed language
    "within 24 hours", "within 12 hours",
    "expires today", "final warning", "last chance",
    "deadline approaching", "failure to act",
    "your account will be terminated",

    # Financial / Banking
    "bank details required", "update your bank details",
    "verify your bank account", "payment failed",
    "transaction declined", "transaction alert",
    "confirm your payment", "pending payment",
    "invoice attached", "billing issue",
    "refund available", "claim your refund",
    "unauthorized transaction", "suspicious transaction",
    "credit card verification", "debit card blocked",

    # OTP / Credentials
    "enter your otp", "share your otp",
    "otp verification required", "one time password",
    "login to continue", "sign in to verify",
    "re-authenticate your account",

    # Rewards / Lures
    "you have won", "claim your prize",
    "congratulations you are selected",
    "lottery winner", "free gift",
    "exclusive offer", "special promotion",
    "limited time offer", "reward waiting",
    "bonus credited", "cashback offer",

    # Attachments / Links
    "open attachment", "download attachment",
    "see attached file", "attachment included",
    "view document", "secure document",
    "click the link below", "access the document",
    "review the file", "important document",

    # Impersonation (common brands / roles)
    "from your bank", "bank notification",
    "it support team", "admin department",
    "customer support", "helpdesk",
    "hr department", "payroll update",
    "tax department", "irs notice", "income tax alert",

    # Threat / Fear tactics
    "legal action will be taken",
    "account will be closed",
    "service interruption",
    "penalty will be applied",
    "compliance issue detected",
    "violation notice",

    # Generic phishing patterns
    "verify now", "click to verify",
    "update now", "confirm now",
    "secure now", "login now",
    "take action now",

    # Slightly obfuscated / common tricks
    "cl1ck here", "ver1fy your account",
    "acc0unt update", "passw0rd reset",
    "l0gin required", "0tp required"
]

CREDENTIAL_PATTERNS = [
    r'\b(password|passwd|pin|otp|cvv|ssn|national.?insurance)\b',
    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # card numbers
    r'\b[A-Z]{2}\d{6}[A-Z]\b',                         # NI numbers
]

def extract_flags(text: str) -> list[str]:
    """Shared flag extractor — used by email AND attachment layers."""
    flags = []
    text_lower = text.lower()

    for kw in PHISHING_KEYWORDS:
        if kw in text_lower:
            flags.append("keyword:" + kw.replace(" ", "_"))

    for pattern in CREDENTIAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            flags.append("credential_pattern_detected")
            break  # one flag is enough, don't spam

    urls = re.findall(r'https?://\S+', text)
    suspicious_urls = [
        u for u in urls
        if any(w in u.lower() for w in
               ["login", "verify", "secure", "update", "account", "confirm"])
    ]
    if suspicious_urls:
        flags.append(f"suspicious_urls:{len(suspicious_urls)}")

    return list(dict.fromkeys(flags))  # deduplicate, preserve order

def score_from_flags(flags: list[str]) -> float:
    """Deterministic score from flags — no ML needed for attachment layer."""
    score = 0.0
    for f in flags:
        if f.startswith("keyword:"):
            score += 0.12
        elif f == "credential_pattern_detected":
            score += 0.30
        elif f.startswith("suspicious_urls:"):
            count = int(f.split(":")[1])
            score += 0.10 * count
    return round(min(score, 1.0), 3)

def build_reason(flags: list[str], score: float, file_type: str) -> str:
    if score < 0.3:
        return f"Attachment ({file_type}) contains no significant phishing signals."
    parts = []
    if any("credential" in f for f in flags):
        parts.append("requests or exposes sensitive credentials")
    if any("suspicious_urls" in f for f in flags):
        parts.append("contains suspicious verification/login URLs")
    if any("keyword" in f for f in flags):
        parts.append("uses known phishing language patterns")
    return f"This {file_type} attachment " + "; ".join(parts) + "."