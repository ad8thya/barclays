# ============================================================
# services/sandbox_service.py  — FULL FILE, COPY-PASTE READY
# ============================================================

import re
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import difflib

try:
    import whois as whois_lib
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ── Domain lists ──────────────────────────────────────────────────────────────

KNOWN_LEGIT_DOMAINS = [
    "barclays.com", "barclaysus.com", "hsbc.com", "hsbc.co.uk",
    "lloydsbank.com", "natwest.com", "rbs.co.uk", "santander.co.uk",
    "santander.com", "halifax.co.uk", "nationwide.co.uk", "monzo.com",
    "starlingbank.com", "revolut.com", "paypal.com", "paypal.co.uk",
    "amazon.com", "amazon.co.uk", "google.com", "apple.com",
    "microsoft.com", "gov.uk", "hmrc.gov.uk",
]

# Iframes from these hosts are always legitimate (analytics, tag managers, etc.)
SAFE_IFRAME_HOSTS = {
    "googletagmanager.com", "google.com", "doubleclick.net",
    "facebook.com", "linkedin.com", "twitter.com", "x.com",
    "youtube.com", "recaptcha.net", "gstatic.com", "cookieyes.com",
    "hotjar.com", "intercom.io", "hubspot.com", "stripe.com",
}

HOMOGLYPH_MAP = {
    "0": "o", "1": "l", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b",
    "@": "a", "rn": "m", "vv": "w",
}


def _apex(domain: str) -> str:
    parts = domain.lower().replace("www.", "").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


def _is_safe_iframe(src: str) -> bool:
    try:
        host = urlparse(src).netloc.lower()
        return any(host == s or host.endswith("." + s) for s in SAFE_IFRAME_HOSTS)
    except Exception:
        return False


# ── Typosquatting ─────────────────────────────────────────────────────────────

def detect_typosquatting(domain: str) -> dict:
    normalised = domain.lower().replace("www.", "").split(":")[0]
    for fake, real in HOMOGLYPH_MAP.items():
        normalised = normalised.replace(fake, real)

    apex = _apex(normalised)
    target_base = apex.split(".")[0]
    best_match, best_score = None, 0.0

    for legit in KNOWN_LEGIT_DOMAINS:
        legit_base = legit.split(".")[0]
        s = difflib.SequenceMatcher(None, target_base, legit_base).ratio()
        if s > best_score:
            best_score, best_match = s, legit

    brand_in_subdomain = False
    parts = normalised.split(".")
    if len(parts) > 2:
        sub = ".".join(parts[:-2])
        for legit in KNOWN_LEGIT_DOMAINS:
            lb = legit.split(".")[0]
            if lb in sub and len(lb) > 3:
                brand_in_subdomain = True
                best_match = legit
                best_score = 1.0
                break

    if brand_in_subdomain:
        verdict, suspicious, risk = "BRAND_IN_SUBDOMAIN", True, 85
    elif best_score >= 0.92:
        verdict, suspicious, risk = "EXACT_SPOOF", True, 90
    elif best_score >= 0.82:
        verdict, suspicious, risk = "HIGH_SIMILARITY", True, 55
    elif best_score >= 0.62:
        verdict, suspicious, risk = "MODERATE_SIMILARITY", False, 15
    else:
        verdict, suspicious, risk = "NO_MATCH", False, 0

    return {
        "closest_legit_domain": best_match,
        "similarity_score": round(best_score, 3),
        "verdict": verdict,
        "is_suspicious": suspicious,
        "brand_in_subdomain": brand_in_subdomain,
        "risk_score": risk,
    }


# ── Cookie analysis ───────────────────────────────────────────────────────────

def analyze_cookies(response: requests.Response, domain: str) -> dict:
    cookies = response.cookies
    raw_html = response.text
    issues = []
    score = 0.0

    for cookie in cookies:
        is_session = any(kw in cookie.name.lower() for kw in
                         ["sess", "session", "sid", "auth", "token"])
        is_secure = cookie.secure
        is_httponly = "httponly" in str(cookie).lower()

        if is_session:
            if not is_secure:
                issues.append(f"Session cookie '{cookie.name}' missing Secure flag")
                score += 30
            if not is_httponly:
                issues.append(f"Session cookie '{cookie.name}' missing HttpOnly")
                score += 20

    # High-confidence malicious patterns only
    if re.search(r'atob\s*\(.*?cookie', raw_html, re.IGNORECASE | re.DOTALL):
        issues.append("Base64-obfuscated cookie operation — evasion attempt")
        score += 35

    if "localStorage.setItem" in raw_html and any(
        kw in raw_html.lower() for kw in ["password", "credential", "stolen"]
    ):
        issues.append("Credentials written to localStorage")
        score += 40

    return {
        "cookie_count": len(cookies),
        "issues": issues,
        "cookie_details": [{"name": c.name, "secure": c.secure} for c in cookies],
        "cookie_risk_score": min(int(score), 100),
        "has_issues": len(issues) > 0,
    }


# ── Iframes / overlays / inline JS ───────────────────────────────────────────

def detect_iframes_and_overlays(soup: BeautifulSoup, base_domain: str) -> dict:
    issues = []
    score = 0.0

    # iframes
    iframes = soup.find_all("iframe")
    iframe_details = []
    for iframe in iframes:
        src = iframe.get("src", "")
        style = iframe.get("style", "").lower().replace(" ", "")
        w, h = str(iframe.get("width", "")), str(iframe.get("height", ""))
        hidden = (
            "display:none" in style or "visibility:hidden" in style
            or w in ("0", "0px", "1px") or h in ("0", "0px", "1px")
        )
        cross_origin = bool(src and base_domain not in src and src.startswith("http"))
        iframe_details.append({"src": src[:200] or "(no src)", "hidden": hidden, "cross_origin": cross_origin})

        if hidden:
            if _is_safe_iframe(src):
                pass  # GTM noscript iframes, analytics — completely normal
            else:
                issues.append(f"Unknown hidden iframe (src: {src[:80] or 'none'})")
                score += 35

    # Fake login overlay (password field inside fixed/absolute positioned container)
    fake_login = 0
    for div in soup.find_all(["div", "section", "form"]):
        style = div.get("style", "").lower().replace(" ", "")
        if ("position:fixed" in style or "position:absolute" in style) \
                and div.find("input", {"type": "password"}):
            fake_login += 1
    if fake_login:
        issues.append("Password field inside positioned overlay — fake login injection")
        score += 45

    # Full-page overlay in <style>
    for block in soup.find_all("style"):
        css = block.get_text().lower().replace(" ", "")
        if "position:fixed" in css and ("width:100%" in css or "inset:0" in css) and "z-index" in css:
            issues.append("CSS full-page fixed overlay")
            score += 30
            break

    # Inline JS — only definitive malicious patterns
    all_inline_js = " ".join(s.get_text() for s in soup.find_all("script", src=False))
    js_issues = []

    HIGH_RISK_JS = [
        (r'navigator\.sendBeacon',                         "sendBeacon() — silent exfiltration",      35),
        (r'addEventListener\s*\(\s*["\']keydown',          "keydown listener — keystroke logger",     40),
        (r'addEventListener\s*\(\s*["\']keypress',         "keypress listener — keystroke logger",    40),
        (r'stealData|stealCreds|exfil|harvested|stolen_',  "Suspicious exfil function name",          50),
        (r'atob\s*\(["\'][A-Za-z0-9+/]{40,}',             "Long base64 decode — obfuscation",        25),
        (r'String\.fromCharCode\s*\([^)]{40,}\)',          "Long charCode chain — obfuscation",       20),
    ]

    for pattern, label, weight in HIGH_RISK_JS:
        if re.search(pattern, all_inline_js, re.IGNORECASE):
            js_issues.append(label)
            score += weight

    if js_issues:
        issues.extend(js_issues)

    return {
        "iframe_count": len(iframes),
        "iframe_details": iframe_details,
        "invisible_elements": 0,
        "fake_login_overlay": fake_login > 0,
        "inline_js_issues": js_issues,
        "issues": issues,
        "overlay_risk_score": min(int(score), 100),
        "has_issues": len(issues) > 0,
    }


# ── Security headers ──────────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "Content-Security-Policy":   {"risk_weight": 18, "tip": "No CSP — XSS injection possible"},
    "X-Frame-Options":           {"risk_weight": 12, "tip": "No X-Frame-Options — clickjacking possible"},
    "Strict-Transport-Security": {"risk_weight": 10, "tip": "No HSTS — protocol downgrade possible"},
    "X-Content-Type-Options":    {"risk_weight": 6,  "tip": "No X-Content-Type-Options — MIME sniffing"},
    "Referrer-Policy":           {"risk_weight": 3,  "tip": "No Referrer-Policy"},
    "Permissions-Policy":        {"risk_weight": 2,  "tip": "No Permissions-Policy"},
}


def analyze_security_headers(response: requests.Response) -> dict:
    headers = {k.lower(): v for k, v in response.headers.items()}
    issues, present, missing = [], [], []
    raw_score = 0

    for header, meta in SECURITY_HEADERS.items():
        if header.lower() in headers:
            present.append(header)
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


# ── WHOIS / domain age ────────────────────────────────────────────────────────

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

    try:
        w = whois_lib.whois(_apex(domain.split(":")[0]))
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if creation:
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - creation).days
            result.update({
                "domain_age_days": age,
                "creation_date": creation.isoformat(),
                "registrar": str(w.registrar or "Unknown"),
            })
            if age < 7:
                result["is_new_domain"] = True
                result["issues"].append(f"Domain {age}d old — extremely new")
                result["risk_score"] = 70
            elif age < 30:
                result["is_new_domain"] = True
                result["issues"].append(f"Domain {age}d old — newly registered")
                result["risk_score"] = 50
            elif age < 90:
                result["issues"].append(f"Domain {age}d old — less than 3 months")
                result["risk_score"] = 20
        else:
            result["issues"].append("No creation date in WHOIS")
            result["risk_score"] = 10
    except Exception as e:
        result["issues"].append(f"WHOIS failed: {str(e)[:60]}")
        result["risk_score"] = 5

    return result


# ── DNS ───────────────────────────────────────────────────────────────────────

def analyze_dns(domain: str) -> dict:
    result = {
        "available": DNS_AVAILABLE,
        "has_spf": False, "has_mx": False, "has_dmarc": False,
        "a_records": [], "ttl_seconds": None,
        "low_ttl": False, "fast_flux_suspected": False,
        "issues": [], "risk_score": 0,
    }
    if not DNS_AVAILABLE:
        return result

    clean = domain.split(":")[0]
    apex = _apex(clean)
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 3.0

    try:
        a_ans = resolver.resolve(clean, "A")
        result["a_records"] = [str(r) for r in a_ans]
        result["ttl_seconds"] = a_ans.rrset.ttl
        # < 30s is genuine fast-flux; 30–300s is CDN/load-balancer (normal)
        if a_ans.rrset.ttl < 30:
            result["low_ttl"] = True
            result["issues"].append(f"TTL {a_ans.rrset.ttl}s — fast-flux suspected")
            result["risk_score"] += 35
        # Fast-flux also = many A records AND low TTL together
        if len(result["a_records"]) > 8 and a_ans.rrset.ttl < 60:
            result["fast_flux_suspected"] = True
            result["issues"].append("Many A records + low TTL — fast-flux pattern")
            result["risk_score"] += 20
    except Exception:
        result["issues"].append("No A record resolved")
        result["risk_score"] += 8

    try:
        for rdata in resolver.resolve(apex, "TXT"):
            txt = str(rdata)
            if "v=spf1" in txt.lower():
                result["has_spf"] = True
            if "v=DMARC1" in txt:
                result["has_dmarc"] = True
    except Exception:
        pass

    if not result["has_spf"]:
        result["issues"].append("No SPF record")
        result["risk_score"] += 12
    if not result["has_dmarc"]:
        result["issues"].append("No DMARC record")
        result["risk_score"] += 6

    try:
        result["has_mx"] = len(list(resolver.resolve(apex, "MX"))) > 0
    except Exception:
        pass
    # Missing MX = no penalty (many legit non-email domains)

    result["risk_score"] = min(result["risk_score"], 100)
    return result


# ── Prompt injection ──────────────────────────────────────────────────────────

PROMPT_INJECTION_PATTERNS = [
    (r'ignore\s+(previous|all|prior)\s+(instructions?|prompts?|context)',
     "Prompt injection: ignore previous instructions", 50),
    (r'\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>',
     "LLM control token injection", 50),
    (r'you\s+are\s+now\s+(a\s+)?(?:an?\s+)?(unrestricted|jailbroken|DAN)',
     "Role override injection", 50),
    (r'###\s*(instruction|system|human|assistant)\s*:',
     "Markdown instruction injection", 40),
    (r'font-size\s*:\s*0(?:px|em|rem)?',
     "Zero-size text — hidden content", 25),
]


def detect_prompt_injection(soup: BeautifulSoup, raw_html: str) -> dict:
    issues, found, score = [], [], 0
    for pattern, label, weight in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL):
            issues.append(label)
            found.append(label)
            score += weight
    for script in soup.find_all("script", type="application/ld+json"):
        if any(kw in script.get_text().lower() for kw in ["jailbreak", "DAN", "ignore previous"]):
            issues.append("Suspicious keywords in JSON-LD — LLM poisoning")
            score += 35
    return {
        "injections_found": found,
        "issues": issues,
        "prompt_injection_risk_score": min(score, 100),
        "has_issues": len(issues) > 0,
    }


# ── Page fingerprint ──────────────────────────────────────────────────────────

KNOWN_LEGIT_PAGE_HASHES: set = set()


def compute_page_fingerprint(html: str) -> dict:
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'(value|nonce|token)="[a-zA-Z0-9+/=_-]{16,}"', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()
    page_hash = hashlib.sha256(cleaned.encode()).hexdigest()
    return {"page_hash": page_hash, "is_known_clone": page_hash in KNOWN_LEGIT_PAGE_HASHES,
            "content_length": len(html)}


# ── Playwright ────────────────────────────────────────────────────────────────

def run_playwright_analysis(url: str) -> dict:
    if not PLAYWRIGHT_AVAILABLE:
        return {"available": False, "dynamic_risk_score": 0, "issues": [],
                "suspicious_requests": [], "storage_writes": [], "runtime_cookies": [],
                "network_requests": [], "js_redirects": []}

    result = {
        "available": True, "runtime_cookies": [], "network_requests": [],
        "suspicious_requests": [], "console_logs": [], "js_redirects": [],
        "storage_writes": [], "issues": [], "dynamic_risk_score": 0,
    }
    score = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            fired = []
            page.on("request", lambda r: fired.append({"url": r.url, "method": r.method,
                                                        "resource_type": r.resource_type}))
            try:
                page.goto(url, timeout=8000, wait_until="networkidle")
            except Exception:
                page.goto(url, timeout=8000, wait_until="domcontentloaded")

            final_url = page.url

            for c in context.cookies():
                is_session = any(k in c["name"].lower() for k in ["sess", "session", "sid", "auth", "token"])
                result["runtime_cookies"].append({"name": c["name"], "secure": c["secure"],
                                                  "http_only": c["httpOnly"]})
                if is_session and not c["secure"]:
                    result["issues"].append(f"Session cookie '{c['name']}' missing Secure")
                    score += 20

            exfil_kws = ["steal", "exfil", "harvest", "credential"]
            for req in fired:
                if any(kw in req["url"].lower() for kw in exfil_kws):
                    result["suspicious_requests"].append(req)
                    result["issues"].append(f"Suspicious request: {req['url'][:100]}")
                    score += 35

            result["network_requests"] = fired[:30]

            if (final_url.lower() != url.lower()
                    and "localhost" not in final_url and "127.0.0.1" not in final_url):
                result["js_redirects"].append(final_url)
                result["issues"].append(f"Redirected to '{final_url}'")
                score += 12

            storage = page.evaluate("""() => {
                const d = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    d[k] = localStorage.getItem(k);
                }
                return d;
            }""")
            if storage:
                result["storage_writes"] = list(storage.keys())
                sensitive = [k for k in storage if any(
                    s in k.lower() for s in ["pass", "cred", "stolen"])]
                if sensitive:
                    result["issues"].append(f"Sensitive keys in localStorage: {sensitive}")
                    score += 45

            browser.close()
    except Exception as e:
        result["error"] = str(e)

    result["dynamic_risk_score"] = min(score, 100)
    return result


# ── Main sandbox runner ───────────────────────────────────────────────────────

def run_sandbox(url: str) -> dict:
    sandbox = {}
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    sandbox["domain"] = domain

    try:
        response = requests.get(url, timeout=8,
                                headers={"User-Agent": "Mozilla/5.0"},
                                allow_redirects=True)
        html = response.text[:20000]
        sandbox["reachable"] = True
        sandbox["status_code"] = response.status_code
        sandbox["final_url"] = response.url.lower()
    except Exception:
        return {"domain": domain, "reachable": False, "error": "Request failed"}

    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    sandbox["num_forms"] = len(forms)
    sandbox["form_actions"] = [f.get("action") for f in forms if f.get("action")]
    sandbox["has_password_field"] = bool(soup.find("input", {"type": "password"}))

    all_scripts = soup.find_all("script", src=True)
    external_scripts = [s["src"] for s in all_scripts
                        if s.get("src", "").startswith("http") and domain not in s.get("src", "")]
    same_origin_scripts = [s["src"] for s in all_scripts
                           if not s.get("src", "").startswith("http")
                           or domain in s.get("src", "")]
    sandbox["external_scripts"] = external_scripts
    sandbox["same_origin_scripts"] = same_origin_scripts
    sandbox["scripts_to_fetch"] = external_scripts[:2] + same_origin_scripts[:2]
    sandbox["redirect_count"] = len(response.history)
    links = soup.find_all("a", href=True)
    sandbox["external_links_count"] = len([l["href"] for l in links if domain not in l["href"]])
    sandbox["uses_https"] = sandbox["final_url"].startswith("https")

    sandbox["typosquatting"]    = detect_typosquatting(domain)
    sandbox["cookies"]          = analyze_cookies(response, domain)
    sandbox["overlays"]         = detect_iframes_and_overlays(soup, domain)
    sandbox["security_headers"] = analyze_security_headers(response)
    sandbox["domain_age"]       = analyze_domain_age(domain)
    sandbox["dns"]              = analyze_dns(domain)
    sandbox["prompt_injection"] = detect_prompt_injection(soup, html)
    sandbox["fingerprint"]      = compute_page_fingerprint(html)
    sandbox["dynamic"]          = run_playwright_analysis(url)

    # ── Weighted blend of all sub-scores ──────────────────────────
    # Weights reflect how decisive each signal is for phishing.
    # They sum to 1.0 intentionally so the blend stays in 0–100.
    typo_s    = sandbox["typosquatting"]["risk_score"]
    overlay_s = sandbox["overlays"]["overlay_risk_score"]
    dynamic_s = sandbox["dynamic"]["dynamic_risk_score"]
    age_s     = sandbox["domain_age"]["risk_score"]
    cookie_s  = sandbox["cookies"]["cookie_risk_score"]
    dns_s     = sandbox["dns"]["risk_score"]
    header_s  = sandbox["security_headers"]["header_risk_score"]
    inject_s  = sandbox["prompt_injection"]["prompt_injection_risk_score"]

    blended = (
        typo_s    * 0.30
        + overlay_s * 0.22
        + dynamic_s * 0.18
        + age_s     * 0.12
        + cookie_s  * 0.08
        + dns_s     * 0.06
        + header_s  * 0.04
    )
    # Prompt injection is additive bonus (capped) — it's a specific attacker signal
    inject_bonus = min(inject_s * 0.5, 20)

    extra_risk = min(int(blended + inject_bonus), 100)

    reasons = []
    if typo_s >= 55:
        reasons.append(f"Typosquatting: {sandbox['typosquatting']['verdict']} of '{sandbox['typosquatting']['closest_legit_domain']}'")
    if overlay_s >= 30:
        reasons.append(f"Overlay/JS risk (score: {overlay_s})")
    if dynamic_s >= 30:
        reasons.append(f"Runtime suspicious behaviour (score: {dynamic_s})")
    if age_s >= 25:
        reasons.append(f"New domain: {sandbox['domain_age'].get('domain_age_days', '?')}d old")
    if cookie_s >= 30:
        reasons.append(f"Cookie security issues (score: {cookie_s})")
    if dns_s >= 35:
        reasons.append("DNS anomalies (fast-flux pattern)")
    if inject_s >= 30:
        reasons.append("Prompt injection payload detected")

    sandbox["extra_risk_score"]   = extra_risk
    sandbox["extra_risk_reasons"] = reasons
    return sandbox

    
