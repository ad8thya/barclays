# services/llm_service.py
import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MAX_RETRIES = 0
RETRY_DELAY = 0


def analyze_with_llm(features: dict, retries: int = MAX_RETRIES) -> str:
    """
    Structured prompt with explicit JSON-like output format.
    Retries on transient failures. Returns raw string for caller to parse.
    """
    # Format new signals clearly so LLM can use them
    age_info = ""
    if features.get("domain_age_days") is not None:
        age_info = f"Domain age: {features['domain_age_days']} days old."
    elif features.get("is_new_domain"):
        age_info = "Domain age: very new (< 30 days)."

    dns_info = []
    if not features.get("has_spf", True):
        dns_info.append("no SPF record")
    if not features.get("has_dmarc", True):
        dns_info.append("no DMARC record")
    if features.get("fast_flux_suspected"):
        dns_info.append("fast-flux DNS suspected")
    dns_summary = f"DNS issues: {', '.join(dns_info)}." if dns_info else "DNS: normal."

    missing_headers = features.get("missing_security_headers", [])
    header_summary = (
        f"Missing security headers: {', '.join(missing_headers[:4])}."
        if missing_headers else "Security headers: adequate."
    )

    injection_note = (
        f"ALERT: {features.get('prompt_injection_count', 0)} prompt injection / hidden content "
        f"payloads detected in page — possible AI-targeted attack."
        if features.get("prompt_injection_detected") else ""
    )

    prompt = f"""You are a cybersecurity analyst specialising in phishing and web fraud detection.

Analyse the following website signals and return EXACTLY this format:
RISK: [LOW|MEDIUM|HIGH]
CONFIDENCE: [0-100]
REASON: [2-3 sentences max]

Website signals:
- URL: {features.get("url")}
- Domain: {features.get("domain")}
- HTTPS: {features.get("uses_https")}
- URL length: {features.get("url_length")} chars
- Typosquatting: {features.get("typosquatting_verdict")} (similar to: {features.get("similar_to") or "none"})
- Login form: {features.get("has_password_field")} | Forms: {features.get("num_forms")}
- External scripts: {features.get("external_scripts")} | Redirects: {features.get("redirects")}
- Cookie issues: {features.get("cookie_issues")} | Iframe count: {features.get("iframe_count")}
- Fake login overlay: {features.get("fake_login_overlay")}
- Inline JS issues: {features.get("inline_js_issues")}
- Suspicious network requests (runtime): {features.get("dynamic_suspicious_requests")}
- Sensitive localStorage writes: {features.get("dynamic_storage_writes")}
- {age_info}
- {dns_summary}
- {header_summary}
{injection_note}

Respond ONLY with the RISK/CONFIDENCE/REASON lines. No markdown, no preamble."""

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 120,
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(RETRY_DELAY)

    raise ConnectionError(f"Ollama unavailable after {retries + 1} attempts: {last_error}")


def parse_llm_risk(response_text: str) -> tuple[str, int]:
    """
    Extracts RISK level and CONFIDENCE from structured LLM output.
    Returns (risk_level, confidence) with safe defaults.
    """
    risk = "UNKNOWN"
    confidence = 50

    for line in response_text.upper().splitlines():
        if line.startswith("RISK:"):
            val = line.replace("RISK:", "").strip()
            if val in ("LOW", "MEDIUM", "HIGH"):
                risk = val
        elif line.startswith("CONFIDENCE:"):
            try:
                confidence = int(line.replace("CONFIDENCE:", "").strip().split()[0])
            except (ValueError, IndexError):
                pass

    return risk, confidence