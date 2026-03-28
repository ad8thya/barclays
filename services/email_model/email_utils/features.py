import re
import numpy as np

def extract_meta(text):
    urls = re.findall(r'http[s]?://\\S+', text)

    return np.array([[
        len(urls),
        int(len(urls) > 0),
        sum(c.isdigit() for c in text),
        sum(not c.isalnum() for c in text),
        len(text),
        int(bool(re.search(r'urgent|immediate|suspended', text.lower()))),
        int(bool(re.search(r'otp|password|cvv|pin', text.lower())))
    ]])

def extract_signals(text, sender):
    return {
        "urgency_detected": bool(re.search(r'urgent|immediate|suspended', text.lower())),
        "credential_harvesting": bool(re.search(r'otp|password|cvv|pin', text.lower())),
        "sender_domain_mismatch": not sender.endswith(("barclays.com","hsbc.com","paypal.com")),
        "generic_greeting": bool(re.search(r"dear customer|dear user", text.lower()))
    }

def extract_flagged(text):
    return list(set(re.findall(
        r"urgent|verify|password|click|suspended|otp",
        text.lower()
    )))