import re
import numpy as np
from difflib import SequenceMatcher

# ==========================================
# TRUSTED DOMAINS
# ==========================================
TRUSTED_DOMAINS = [
    "barclays.com",
    "hsbc.com",
    "paypal.com",
    "hdfcbank.com",
    "icicibank.com"
]

# ==========================================
# DOMAIN HELPERS
# ==========================================
def get_domain(sender):
    if not sender or "@" not in sender:
        return ""
    return sender.split("@")[-1].lower()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_suspicious_domain(sender):
    domain = get_domain(sender)

    if not domain:
        return False  # do not flag empty sender

    # exact trusted domain → safe
    if domain in TRUSTED_DOMAINS:
        return False

    # check similarity (typosquatting detection)
    for trusted in TRUSTED_DOMAINS:
        if similarity(domain, trusted) > 0.75:
            return True

    return False


def domain_similarity_score(sender):
    domain = get_domain(sender)

    if not domain:
        return 0.0

    sims = [similarity(domain, t) for t in TRUSTED_DOMAINS]
    max_sim = max(sims) if sims else 0.0

    if domain in TRUSTED_DOMAINS:
        return 0.0

    return round(max_sim, 3) if max_sim > 0.7 else 0.0


# ==========================================
# META FEATURES (USED BY MODEL)
# ==========================================
def extract_meta(text):
    text_lower = text.lower()
    urls = re.findall(r'http[s]?://\S+', text)

    return np.array([[  
        len(urls),
        int(len(urls) > 0),
        sum(c.isdigit() for c in text),
        sum(not c.isalnum() for c in text),
        len(text),
        int(bool(re.search(r'urgent|immediate|suspended', text_lower))),
        int(bool(re.search(r'otp|password|cvv|pin|login|verify', text_lower)))
    ]])


# ==========================================
# SIGNALS (RULE-BASED EXPLANATION)
# ==========================================
def extract_signals(text, sender):
    text_lower = text.lower()

    return {
        "urgency_detected": bool(re.search(
            r'urgent|immediate|suspended',
            text_lower
        )),

        "credential_request": bool(re.search(
            r'otp|password|cvv|pin|login|verify account|update details',
            text_lower
        )),

        "credential_request_context": bool(re.search(
            r'enter.*(otp|password|pin)|click.*login|verify.*account',
            text_lower
        )),

        "sender_domain_mismatch": is_suspicious_domain(sender),

        "domain_similarity_score": domain_similarity_score(sender),

        "generic_greeting": bool(re.search(
            r'dear customer|dear user',
            text_lower
        )),

        "link_present": "http" in text_lower
    }


# ==========================================
# FLAGGED PHRASES (FOR UI)
# ==========================================
def extract_flagged(text):
    return list(set(re.findall(
        r"urgent|verify|password|click|suspended|otp|login",
        text.lower()
    )))