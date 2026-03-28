# services/sandbox_service.py
"""
Sandbox service — static + dynamic website analysis.

Scoring philosophy:
- Every sub-analyser returns a normalised 0–100 risk score.
- Scores are WEIGHTED and COMBINED, never blindly added.
- Hard floors only fire on definitive, high-confidence signals
  (exact spoof, runtime exfil, fake-login overlay).
- Legitimate sites (Google, HSBC, etc.) should score < 30.
"""

import re
import socket
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
import difflib

# ── Optional dependencies (graceful fallback) ─────────────────────────────────
try:
    import whois as whois_lib
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import dns.resolver
    import dns.exception
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# KNOWN DOMAINS
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_LEGIT_DOMAINS = [
    "barclays.com", "barclaysus.com",
    "hsbc.com", "hsbc.co.uk",
    "lloydsbank.com", "lloydsbankinggroup.com",
    "natwest.com", "rbs.co.uk",
    "santander.co.uk", "santander.com",
    "halifax.co.uk", "nationwide.co.uk",
    "monzo.com", "starlingbank.com", "revolut.com",
    "paypal.com", "paypal.co.uk",
    "amazon.com", "amazon.co.uk",
    "google.com", "apple.com", "microsoft.com",
    "gov.uk", "hmrc.gov.uk",
]

# Sites that are globally trusted — scoring should be more lenient
# (CDN-heavy, many external scripts, no MX record are all expected)
TRUSTED_APEX_DOMAINS = {
    "google.com", "google.co.uk", "youtube.com", "gmail.com",
    "microsoft.com", "office.com", "live.com", "outlook.com",
    "apple.com", "icloud.com",
    "amazon.com", "amazon.co.uk", "aws.amazon.com",
    "cloudflare.com", "fastly.com", "akamai.com",
    "github.com", "githubusercontent.com",
    "paypal.com", "stripe.com",
    "barclays.com", "hsbc.com", "lloydsbank.com", "natwest.com",
    "nationwide.co.uk", "santander.co.uk", "monzo.com",
    "gov.uk", "hmrc.gov.uk",
}

HOMOGLYPH_MAP = {
    "0": "o", "1": "l", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b",
    "@": "a", "rn": "m", "vv": "w", "ii": "u",
}


def _apex_domain(domain: str) -> str:
    """Return apex domain (e.g. 'sub.google.com' → 'google.com')."""
    parts = domain.lower().replace("www.", "").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _is_trusted(domain: str) -> bool:
    return _apex_domain(domain) in TRUSTED_APEX_DOMAINS


# ─────────────────────────────────────────────────────────────────────────────
# TYPOSQUATTING
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_domain(domain: str) -> str:
    d = domain.lower().replace("www.", "").split(":")[0]
    for fake, real in HOMOGLYPH_MAP.items():
        d = d.replace(fake, real)
    return d


def detect_typosquatting(domain: str) -> dict:
    """
    Returns a verdict and a 0–100 risk contribution.
    Trusted domains are excluded from spoof detection
    (google.com cannot be a spoof of itself).
    """
    apex = _apex_domain(domain)
    if apex in TRUSTED_APEX_DOMAINS:
        return {
            "closest_legit_domain": apex,
            "similarity_score": 1.0,
            "verdict": "TRUSTED_DOMAIN",
            "is_suspicious": False,
            "brand_in_subdomain": False,
            "risk_score": 0,
        }

    normalised = _normalize_domain(domain)
    best_match = None
    best_score = 0.0
    target_base = normalised.split(".")[0]

    for legit in KNOWN_LEGIT_DOMAINS:
        legit_base = legit.split(".")[0]
        score = difflib.SequenceMatcher(None, target_base, legit_base).ratio()
        if score > best_score:
            best_score = score
            best_match = legit

    # Brand hijacked into a subdomain (e.g. barclays.evil.com)
    brand_in_subdomain = False
    parts = normalised.split(".")
    if len(parts) > 2:
        subdomain_part = ".".join(parts[:-2])
        for legit in KNOWN_LEGIT_DOMAINS:
            legit_base = legit.split(".")[0]
            if legit_base in subdomain_part and len(legit_base) > 3:
                brand_in_subdomain = True
                best_match = legit
                best_score = 1.0
                break

    if brand_in_subdomain:
        verdict, is_suspicious, risk = "BRAND_IN_SUBDOMAIN", True, 85
    elif best_score >= 0.92:
        verdict, is_suspicious, risk = "EXACT_SPOOF", True, 90
    elif best_score >= 0.80:
        verdict, is_suspicious, risk = "HIGH_SIMILARITY", True, 60
    elif best_score >= 0.60:
        verdict, is_suspicious, risk = "MODERATE_SIMILARITY", False, 20
    else:
        verdict, is_suspicious, risk = "NO_MATCH", False, 0

    return {
        "closest_legit_domain": best_match,
        "similarity_score": round(best_score, 3),
        "verdict": verdict,
        "is_suspicious": is_suspicious,
        "brand_in_subdomain": brand_in_subdomain,
        "risk_score": risk,
    }


# ─────────────────────────────────────────────────────────────────────────────
# COOKIE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def analyze_cookies(response: requests.Response, domain: str) -> dict:
    """
    Returns normalised 0–100 risk score.
    Tracking cookies on legit sites are LOW weight — they're normal.
    High-weight flags: session cookie not Secure, credential in localStorage.
    """
    cookies = response.cookies
    raw_headers = response.headers.get("set-cookie", "")
    raw_html = response.text

    issues = []
    weighted_score = 0.0   # accumulate weights, cap at end
    cookie_details = []

    for cookie in cookies:
        raw_lower = raw_headers.lower()
        same_site = None
        if "samesite=none" in raw_lower:
            same_site = "None"
        elif "samesite=lax" in raw_lower:
            same_site = "Lax"
        elif "samesite=strict" in raw_lower:
            same_site = "Strict"

        is_session = any(kw in cookie.name.lower() for kw in
                         ["sess", "session", "sid", "auth", "token"])

        detail = {
            "name": cookie.name,
            "secure": cookie.secure,
            "http_only": "httponly" in str(cookie).lower(),
            "same_site": same_site,
        }
        cookie_details.append(detail)

        # Only penalise session/auth cookies heavily
        if is_session:
            if not cookie.secure:
                issues.append(f"Session cookie '{cookie.name}' missing Secure — hijack risk")
                weighted_score += 30
            if not detail["http_only"]:
                issues.append(f"Session cookie '{cookie.name}' missing HttpOnly — XSS risk")
                weighted_score += 20
            if same_site == "None":
                issues.append(f"Session cookie '{cookie.name}' SameSite=None — CSRF risk")
                weighted_score += 15
        else:
            # Non-session: minor flags only
            if not cookie.secure and same_site == "None":
                issues.append(f"Cookie '{cookie.name}' insecure + SameSite=None")
                weighted_score += 8

    # High-value static source signals
    if re.search(r'atob\s*\(.*?cookie', raw_html, re.IGNORECASE | re.DOTALL):
        issues.append("Base64-obfuscated cookie operation — evasion attempt")
        weighted_score += 35

    if "localStorage.setItem" in raw_html and any(
        kw in raw_html.lower() for kw in ["pass", "password", "credential", "stolen"]
    ):
        issues.append("Credentials written to localStorage — insecure storage")
        weighted_score += 40

    return {
        "cookie_count": len(cookies),
        "issues": issues,
        "cookie_details": cookie_details,
        "cookie_risk_score": min(int(weighted_score), 100),
        "has_issues": len(issues) > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# IFRAME / OVERLAY / INLINE JS
# ─────────────────────────────────────────────────────────────────────────────

def detect_iframes_and_overlays(soup: BeautifulSoup, base_domain: str) -> dict:
    """
    High-confidence phishing indicators:
    - Hidden iframes, password field inside fixed overlay, keystroke loggers.
    Low-weight or ignored:
    - Visible same-origin iframes (YouTube embeds, etc.)
    - Common analytics JS patterns on legit sites.
    """
    issues = []
    weighted_score = 0.0

    # ── iframes ───────────────────────────────────────────────────
    iframes = soup.find_all("iframe")
    iframe_details = []
    for iframe in iframes:
        src = iframe.get("src", "")
        style = iframe.get("style", "").lower().replace(" ", "")
        width = str(iframe.get("width", ""))
        height = str(iframe.get("height", ""))
        hidden = (
            "display:none" in style
            or "visibility:hidden" in style
            or width in ("0", "0px", "1px")
            or height in ("0", "0px", "1px")
        )
        cross_origin = bool(src and base_domain not in src and src.startswith("http"))
        iframe_details.append({"src": src[:200] or "(no src)", "hidden": hidden, "cross_origin": cross_origin})

        if hidden:
            issues.append(f"Hidden iframe — clickjacking risk")
            weighted_score += 35
        # Visible cross-origin iframes are normal (YouTube, maps, etc.) — no penalty

    # ── Invisible overlay divs ────────────────────────────────────
    suspicious_names = ["ghost", "overlay", "invisible", "trap",
                        "capture", "cloak", "stealth", "shadow", "fake"]
    invisible_count = 0
    for el in soup.find_all(["div", "span", "section", "a"]):
        style = el.get("style", "").lower().replace(" ", "")
        el_id = (el.get("id") or "").lower()
        el_class = " ".join(el.get("class") or []).lower()

        # Only flag opacity:0 with suspicious name — opacity:0 alone is used by many legit animations
        has_suspicious_name = any(word in el_id + el_class for word in suspicious_names)
        is_hidden = "opacity:0" in style or "visibility:hidden" in style

        if is_hidden and has_suspicious_name:
            invisible_count += 1
            issues.append(f"Suspicious hidden element '{el.get('id') or el.get('class')}' — cloaking")
            weighted_score += 20

    # ── Full-page overlay ──────────────────────────────────────────
    for block in soup.find_all("style"):
        css = block.get_text().lower().replace(" ", "")
        if "position:fixed" in css and ("width:100%" in css or "inset:0" in css) and "z-index" in css:
            issues.append("CSS full-page fixed overlay — clickjacking risk")
            weighted_score += 30
            break  # one flag is enough

    # ── Password field inside positioned overlay ──────────────────
    fixed_with_password = 0
    for div in soup.find_all(["div", "section", "form"]):
        style = div.get("style", "").lower().replace(" ", "")
        if ("position:fixed" in style or "position:absolute" in style) and \
                div.find("input", {"type": "password"}):
            fixed_with_password += 1
    if fixed_with_password:
        issues.append("Password field inside positioned overlay — fake login injection")
        weighted_score += 45

    # ── Inline JS — only high-confidence patterns ─────────────────
    all_inline_js = " ".join(s.get_text() for s in soup.find_all("script", src=False))
    js_issues = []

    # Weighted patterns — only genuinely suspicious ones
    HIGH_RISK_JS = [
        (r'navigator\.sendBeacon',                              "sendBeacon() — silent background exfiltration", 35),
        (r'addEventListener\s*\(\s*["\']keydown',               "keydown listener — keystroke logger risk",       40),
        (r'addEventListener\s*\(\s*["\']keypress',              "keypress listener — keystroke logger risk",      40),
        (r'stealData|stealCreds|exfil|harvested|stolen_',       "Suspicious exfil function name in JS",           50),
        (r'atob\s*\([^)]{20,}\)',                               "atob() on long string — obfuscation",            25),
        (r'String\.fromCharCode\s*\([^)]{30,}\)',               "Long charCode chain — JS obfuscation",           20),
    ]
    # Lower-weight — common on legit sites, only flag if multiple present
    MEDIUM_RISK_JS = [
        (r'\beval\s*\(',                                        "eval() — possible obfuscation",                  15),
        (r'document\.cookie\s*=',                               "Runtime cookie write",                           10),
        (r'XMLHttpRequest|\.open\s*\(\s*["\']POST',             "XHR POST — possible data exfil",                 10),
    ]

    for pattern, label, weight in HIGH_RISK_JS:
        if re.search(pattern, all_inline_js, re.IGNORECASE):
            js_issues.append(label)
            weighted_score += weight

    medium_hits = 0
    for pattern, label, weight in MEDIUM_RISK_JS:
        if re.search(pattern, all_inline_js, re.IGNORECASE):
            js_issues.append(label)
            medium_hits += 1
            # Only add weight if 2+ medium signals — single eval() is fine on legit sites
            if medium_hits >= 2:
                weighted_score += weight

    if js_issues:
        issues.extend(js_issues)

    return {
        "iframe_count": len(iframes),
        "iframe_details": iframe_details,
        "invisible_elements": invisible_count,
        "fake_login_overlay": fixed_with_password > 0,
        "inline_js_issues": js_issues,
        "issues": issues,
        "overlay_risk_score": min(int(weighted_score), 100),
        "has_issues": len(issues) > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY HEADERS
# ─────────────────────────────────────────────────────────────────────────────

# Weight reflects actual impact — CSP matters most, Permissions-Policy least
SECURITY_HEADERS = {
    "Content-Security-Policy":    {"risk_weight": 20, "tip": "No CSP — XSS injection possible"},
    "X-Frame-Options":            {"risk_weight": 15, "tip": "No X-Frame-Options — clickjacking possible"},
    "Strict-Transport-Security":  {"risk_weight": 12, "tip": "No HSTS — protocol downgrade possible"},
    "X-Content-Type-Options":     {"risk_weight": 8,  "tip": "No X-Content-Type-Options — MIME sniffing"},
    "Referrer-Policy":            {"risk_weight": 4,  "tip": "No Referrer-Policy — referrer leakage"},
    "Permissions-Policy":         {"risk_weight": 3,  "tip": "No Permissions-Policy"},
}

WEAK_CSP_PATTERNS = [
    ("unsafe-inline", "CSP allows unsafe-inline", 15),
    ("unsafe-eval",   "CSP allows unsafe-eval",   15),
]


def analyze_security_headers(response: requests.Response) -> dict:
    """
    Returns normalised 0–100 risk score.
    Max raw score if ALL headers missing = 62.  Normalised → still 62.
    Most legit sites miss 2-3 headers → score ~20–35.
    """
    headers = {k.lower(): v for k, v in response.headers.items()}
    issues = []
    raw_score = 0
    present = []
    missing = []

    for header, meta in SECURITY_HEADERS.items():
        if header.lower() in headers:
            present.append(header)
            if header == "Content-Security-Policy":
                csp = headers[header.lower()]
                for pattern, label, weight in WEAK_CSP_PATTERNS:
                    if pattern in csp:
                        issues.append(f"Weak CSP: {label}")
                        raw_score += weight
        else:
            missing.append(header)
            issues.append(meta["tip"])
            raw_score += meta["risk_weight"]

    return {
        "headers_present": present,
        "headers_missing": missing,
        "issues": issues,
        "header_risk_score": min(raw_score, 100),
        "has_issues": len(issues) > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# WHOIS / DOMAIN AGE
# ─────────────────────────────────────────────────────────────────────────────

def analyze_domain_age(domain: str) -> dict:
    result = {
        "available": WHOIS_AVAILABLE,
        "domain_age_days": None,
        "creation_date": None,
        "registrar": None,
        "is_new_domain": False,
        "risk_score": 0,
        "issues": [],
    }

    if not WHOIS_AVAILABLE:
        return result

    clean_domain = _apex_domain(domain.split(":")[0])

    # Don't penalise known trusted apexes for domain age
    if clean_domain in TRUSTED_APEX_DOMAINS:
        result["risk_score"] = 0
        return result

    try:
        w = whois_lib.whois(clean_domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]

        if creation:
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - creation).days
            result["domain_age_days"] = age_days
            result["creation_date"] = creation.isoformat()
            result["registrar"] = str(w.registrar or "Unknown")

            if age_days < 7:
                result["is_new_domain"] = True
                result["issues"].append(f"Domain only {age_days}d old — extremely new")
                result["risk_score"] = 70
            elif age_days < 30:
                result["is_new_domain"] = True
                result["issues"].append(f"Domain {age_days}d old — newly registered")
                result["risk_score"] = 50
            elif age_days < 90:
                result["issues"].append(f"Domain {age_days}d old — less than 3 months")
                result["risk_score"] = 25
            else:
                result["risk_score"] = 0
        else:
            result["issues"].append("No creation date in WHOIS — data hidden")
            result["risk_score"] = 12

    except Exception as e:
        result["issues"].append(f"WHOIS lookup failed: {str(e)[:60]}")
        result["risk_score"] = 8

    return result


# ─────────────────────────────────────────────────────────────────────────────
# DNS ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def analyze_dns(domain: str) -> dict:
    result = {
        "available": DNS_AVAILABLE,
        "has_spf": False,
        "has_mx": False,
        "has_dmarc": False,
        "a_records": [],
        "ttl_seconds": None,
        "low_ttl": False,
        "fast_flux_suspected": False,
        "issues": [],
        "risk_score": 0,
    }

    if not DNS_AVAILABLE:
        return result

    clean_domain = domain.split(":")[0]
    apex = _apex_domain(clean_domain)

    # Trusted domains: don't hammer DNS or penalise CDN patterns
    if apex in TRUSTED_APEX_DOMAINS:
        result["has_spf"] = True
        result["has_mx"] = True
        result["has_dmarc"] = True
        result["risk_score"] = 0
        return result

    resolver = dns.resolver.Resolver()
    resolver.lifetime = 3.0

    # A records + TTL
    try:
        a_ans = resolver.resolve(clean_domain, "A")
        result["a_records"] = [str(r) for r in a_ans]
        result["ttl_seconds"] = a_ans.rrset.ttl
        # Only flag extremely low TTL (< 60s) as fast-flux — CDNs use 300s normally
        if a_ans.rrset.ttl < 60:
            result["low_ttl"] = True
            result["issues"].append(f"Very low DNS TTL ({a_ans.rrset.ttl}s) — fast-flux suspected")
            result["risk_score"] += 30
        # Fast-flux: many A records pointing to different IPs
        if len(result["a_records"]) > 8:
            result["fast_flux_suspected"] = True
            result["issues"].append(f"{len(result['a_records'])} A records — fast-flux pattern")
            result["risk_score"] += 25
    except Exception:
        result["issues"].append("No A record — unusual for a live site")
        result["risk_score"] += 10

    # SPF / DMARC
    try:
        txt_ans = resolver.resolve(apex, "TXT")
        for rdata in txt_ans:
            txt = str(rdata)
            if "v=spf1" in txt.lower():
                result["has_spf"] = True
            if "v=DMARC1" in txt:
                result["has_dmarc"] = True
    except Exception:
        pass

    # SPF missing is significant for a domain sending email
    if not result["has_spf"]:
        result["issues"].append("No SPF record — email spoofing risk")
        result["risk_score"] += 15

    if not result["has_dmarc"]:
        result["issues"].append("No DMARC record")
        result["risk_score"] += 8

    # MX — many legit domains (CDNs, landing pages) have no MX
    try:
        mx_ans = resolver.resolve(apex, "MX")
        result["has_mx"] = len(list(mx_ans)) > 0
    except Exception:
        pass
    # Don't penalise missing MX — it's common for non-email domains

    result["risk_score"] = min(result["risk_score"], 100)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT INJECTION / HIDDEN CONTENT
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_INJECTION_PATTERNS = [
    (r'ignore\s+(previous|all|prior)\s+(instructions?|prompts?|context)',
     "Prompt injection: 'ignore previous instructions'", 50),
    (r'you\s+are\s+now\s+(a\s+)?(?:an?\s+)?(helpful|unrestricted|jailbroken|DAN)',
     "Role override injection", 50),
    (r'\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>',
     "LLM control token injection", 50),
    (r'###\s*(instruction|system|human|assistant)\s*:',
     "Markdown instruction injection", 40),
    (r'disregard\s+(your|all)\s+(previous|prior|safety|guidelines)',
     "Safety bypass injection", 45),
    (r'font-size\s*:\s*0(?:px|em|rem)?',
     "Zero-size text — hidden content", 30),
]


def detect_prompt_injection(soup: BeautifulSoup, raw_html: str) -> dict:
    issues = []
    risk_score = 0
    injections_found = []

    for pattern, label, weight in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL):
            issues.append(label)
            injections_found.append(label)
            risk_score += weight

    # aria-hidden blocks with lots of text
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        text = el.get_text(strip=True)
        if len(text) > 50:
            issues.append(f"aria-hidden block with {len(text)} chars — possible hidden instructions")
            risk_score += 20
            break

    # JSON-LD poisoning
    for script in soup.find_all("script", type="application/ld+json"):
        ld_text = script.get_text()
        if any(kw in ld_text.lower() for kw in ["ignore", "jailbreak", "DAN"]):
            issues.append("Suspicious keywords in JSON-LD — LLM poisoning")
            risk_score += 35

    return {
        "injections_found": injections_found,
        "issues": issues,
        "prompt_injection_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PAGE FINGERPRINT
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_LEGIT_PAGE_HASHES: set = set()


def compute_page_fingerprint(html: str) -> dict:
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'(value|nonce|token)="[a-zA-Z0-9+/=_-]{16,}"', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    page_hash = hashlib.sha256(cleaned.encode()).hexdigest()

    return {
        "page_hash": page_hash,
        "is_known_clone": page_hash in KNOWN_LEGIT_PAGE_HASHES,
        "content_length": len(html),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT DYNAMIC ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def run_playwright_analysis(url: str) -> dict:
    if not PLAYWRIGHT_AVAILABLE:
        return {
            "available": False,
            "reason": "playwright not installed",
            "dynamic_risk_score": 0,
        }

    result = {
        "available": True,
        "runtime_cookies": [],
        "network_requests": [],
        "suspicious_requests": [],
        "console_logs": [],
        "js_redirects": [],
        "storage_writes": [],
        "issues": [],
        "dynamic_risk_score": 0,
    }
    risk_score = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            fired_requests = []
            page.on("request", lambda req: fired_requests.append({
                "url": req.url,
                "method": req.method,
                "resource_type": req.resource_type,
            }))

            try:
                page.goto(url, timeout=8000, wait_until="networkidle")
            except Exception:
                page.goto(url, timeout=8000, wait_until="domcontentloaded")

            final_url = page.url

            # Runtime cookies — only flag session cookies lacking security
            for c in context.cookies():
                is_session = any(kw in c["name"].lower() for kw in
                                 ["sess", "session", "sid", "auth", "token"])
                result["runtime_cookies"].append({
                    "name": c["name"], "secure": c["secure"],
                    "http_only": c["httpOnly"],
                    "same_site": c.get("sameSite", "None"),
                })
                if is_session:
                    if not c["secure"]:
                        result["issues"].append(f"Session cookie '{c['name']}' missing Secure")
                        risk_score += 20
                    if c.get("sameSite") == "None":
                        result["issues"].append(f"Session cookie '{c['name']}' SameSite=None")
                        risk_score += 10

            # Network requests — only flag clear exfil patterns
            parsed_origin = urlparse(url).netloc
            exfil_kws = ["steal", "exfil", "harvest", "beacon", "credential"]
            for req in fired_requests:
                is_suspicious = any(kw in req["url"].lower() for kw in exfil_kws)
                if is_suspicious:
                    result["suspicious_requests"].append(req)
                    result["issues"].append(f"Suspicious request to '{req['url'][:100]}'")
                    risk_score += 35

            result["network_requests"] = fired_requests[:30]

            # JS redirect
            if (final_url.lower() != url.lower()
                    and "localhost" not in final_url
                    and "127.0.0.1" not in final_url):
                result["js_redirects"].append(final_url)
                result["issues"].append(f"Page redirected to '{final_url}' after load")
                risk_score += 15

            # localStorage sensitive keys
            storage_data = page.evaluate("""() => {
                const d = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    d[k] = localStorage.getItem(k);
                }
                return d;
            }""")
            if storage_data:
                result["storage_writes"] = list(storage_data.keys())
                sensitive = [k for k in storage_data if any(
                    s in k.lower() for s in ["pass", "cred", "token", "stolen"]
                )]
                if sensitive:
                    result["issues"].append(f"Sensitive keys in localStorage: {sensitive}")
                    risk_score += 45

            browser.close()

    except Exception as e:
        result["error"] = str(e)

    result["dynamic_risk_score"] = min(risk_score, 100)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SANDBOX RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_sandbox(url: str) -> dict:
    """
    Orchestrates all sub-analysers and returns a unified dict.
    The composite `extra_risk_score` (0–100) is a WEIGHTED BLEND
    of normalised sub-scores — not a simple sum.
    """
    sandbox_data = {}

    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    sandbox_data["domain"] = domain
    trusted = _is_trusted(domain)
    sandbox_data["is_trusted_domain"] = trusted

    # ── Static HTTP fetch ─────────────────────────────────────────
    try:
        response = requests.get(
            url, timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            allow_redirects=True,
        )
        html = response.text[:20000]
        sandbox_data["reachable"] = True
        sandbox_data["status_code"] = response.status_code
        sandbox_data["final_url"] = response.url.lower()
    except Exception:
        return {"domain": domain, "reachable": False, "error": "Request failed"}

    soup = BeautifulSoup(html, "html.parser")

    # ── Basic signals ─────────────────────────────────────────────
    forms = soup.find_all("form")
    sandbox_data["num_forms"] = len(forms)
    sandbox_data["form_actions"] = [f.get("action") for f in forms if f.get("action")]
    sandbox_data["has_password_field"] = bool(soup.find("input", {"type": "password"}))

    all_scripts = soup.find_all("script", src=True)
    external_scripts = [s["src"] for s in all_scripts if s.get("src", "").startswith("http") and domain not in s.get("src", "")]
    same_origin_scripts = [s["src"] for s in all_scripts if not s.get("src", "").startswith("http") or domain in s.get("src", "")]
    sandbox_data["external_scripts"] = external_scripts
    sandbox_data["same_origin_scripts"] = same_origin_scripts
    sandbox_data["scripts_to_fetch"] = external_scripts[:2] + same_origin_scripts[:2]
    sandbox_data["redirect_count"] = len(response.history)
    links = soup.find_all("a", href=True)
    sandbox_data["external_links_count"] = len([l["href"] for l in links if domain not in l["href"]])
    sandbox_data["uses_https"] = sandbox_data["final_url"].startswith("https")

    # ── Sub-analysers ─────────────────────────────────────────────
    sandbox_data["typosquatting"]      = detect_typosquatting(domain)
    sandbox_data["cookies"]            = analyze_cookies(response, domain)
    sandbox_data["overlays"]           = detect_iframes_and_overlays(soup, domain)
    sandbox_data["security_headers"]   = analyze_security_headers(response)
    sandbox_data["domain_age"]         = analyze_domain_age(domain)
    sandbox_data["dns"]                = analyze_dns(domain)
    sandbox_data["prompt_injection"]   = detect_prompt_injection(soup, html)
    sandbox_data["fingerprint"]        = compute_page_fingerprint(html)
    sandbox_data["dynamic"]            = run_playwright_analysis(url)

    # ── Composite extra_risk_score — WEIGHTED BLEND ───────────────
    #
    # Each sub-score is 0–100. We assign weights that reflect
    # how decisive each signal is for phishing classification.
    #
    # Typosquatting:     0.30  (most decisive single signal)
    # Overlays/JS:       0.20  (fake login, keyloggers)
    # Dynamic (runtime): 0.18  (actual exfil behaviour)
    # Domain age:        0.12  (new domains are risky)
    # Cookie security:   0.08  (supporting signal)
    # DNS anomalies:     0.07  (supporting signal)
    # Security headers:  0.05  (weakest — many legit sites miss these)
    #
    # Prompt injection is treated as a hard additive bonus, not weighted,
    # because it's a very specific attacker behaviour.

    typo_score    = sandbox_data["typosquatting"]["risk_score"]
    overlay_score = sandbox_data["overlays"]["overlay_risk_score"]
    dynamic_score = sandbox_data["dynamic"].get("dynamic_risk_score", 0)
    age_score     = sandbox_data["domain_age"]["risk_score"]
    cookie_score  = sandbox_data["cookies"]["cookie_risk_score"]
    dns_score     = sandbox_data["dns"]["risk_score"]
    header_score  = sandbox_data["security_headers"]["header_risk_score"]
    inject_score  = sandbox_data["prompt_injection"]["prompt_injection_risk_score"]

    blended = (
        typo_score    * 0.30
        + overlay_score * 0.20
        + dynamic_score * 0.18
        + age_score     * 0.12
        + cookie_score  * 0.08
        + dns_score     * 0.07
        + header_score  * 0.05
    )

    # Prompt injection is a separate additive bonus (capped contribution)
    inject_bonus = min(inject_score * 0.5, 25)

    extra_risk = min(int(blended + inject_bonus), 100)

    # ── Extra risk reasons — only include meaningful contributors ──
    extra_reasons = []
    typo = sandbox_data["typosquatting"]
    if typo["is_suspicious"]:
        extra_reasons.append(f"Typosquatting: {typo['verdict']} of '{typo['closest_legit_domain']}'")
    if overlay_score >= 30:
        extra_reasons.append(f"Overlay/JS risk (score: {overlay_score})")
    if dynamic_score >= 30:
        extra_reasons.append(f"Runtime suspicious behaviour (score: {dynamic_score})")
    if age_score >= 25:
        extra_reasons.append(f"New domain: {sandbox_data['domain_age'].get('domain_age_days', '?')}d old")
    if cookie_score >= 30:
        extra_reasons.append(f"Cookie security issues (score: {cookie_score})")
    if dns_score >= 30:
        extra_reasons.append("DNS anomalies detected")
    if inject_score >= 30:
        extra_reasons.append("Prompt injection payload detected")

    sandbox_data["extra_risk_score"]   = extra_risk
    sandbox_data["extra_risk_reasons"] = extra_reasons

    return sandbox_data