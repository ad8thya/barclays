import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import difflib
import re
 # ── ADD THESE IMPORTS at the top of sandbox_service.py ──────────────────────
import socket
import hashlib
from datetime import datetime, timezone

# Optional — graceful fallback if not installed
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



# ── PLAYWRIGHT (graceful fallback if not installed) ────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
 
 
# ── TYPOSQUATTING ──────────────────────────────────────────────────────────────
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
 
HOMOGLYPH_MAP = {
    "0": "o", "1": "l", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b",
    "@": "a", "rn": "m", "vv": "w", "ii": "u",
}
 
 
def _normalize_domain(domain: str) -> str:
    d = domain.lower().replace("www.", "").split(":")[0]  # strip port too
    for fake, real in HOMOGLYPH_MAP.items():
        d = d.replace(fake, real)
    return d
 
 
def detect_typosquatting(domain: str) -> dict:
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
 
    if best_score >= 0.95:
        verdict, is_suspicious = "EXACT_SPOOF", True
    elif best_score >= 0.75:
        verdict, is_suspicious = "HIGH_SIMILARITY", True
    elif best_score >= 0.55:
        verdict, is_suspicious = "MODERATE_SIMILARITY", False
    else:
        verdict, is_suspicious = "NO_MATCH", False
 
    brand_in_subdomain = False
    parts = normalised.split(".")
    if len(parts) > 2:
        subdomain_part = ".".join(parts[:-2])
        for legit in KNOWN_LEGIT_DOMAINS:
            legit_base = legit.split(".")[0]
            if legit_base in subdomain_part and len(legit_base) > 3:
                brand_in_subdomain = True
                best_match = legit
                verdict = "BRAND_IN_SUBDOMAIN"
                is_suspicious = True
                break
 
    return {
        "closest_legit_domain": best_match,
        "similarity_score": round(best_score, 3),
        "verdict": verdict,
        "is_suspicious": is_suspicious,
        "brand_in_subdomain": brand_in_subdomain,
    }
 
 
# ── STATIC COOKIE ANALYSIS ────────────────────────────────────────────────────
 
def analyze_cookies(response: requests.Response, domain: str) -> dict:
    cookies = response.cookies
    raw_headers = response.headers.get("set-cookie", "")
    raw_html = response.text
 
    issues = []
    cookie_details = []
    risk_score = 0
 
    # ── Server-set cookies ────────────────────────────────────────
    for cookie in cookies:
        raw_lower = raw_headers.lower()
        same_site = None
        if "samesite=none" in raw_lower:
            same_site = "None"
        elif "samesite=lax" in raw_lower:
            same_site = "Lax"
        elif "samesite=strict" in raw_lower:
            same_site = "Strict"
 
        detail = {
            "name": cookie.name,
            "domain": cookie.domain or domain,
            "path": cookie.path,
            "secure": cookie.secure,
            "http_only": cookie.has_nonstandard_attr("HttpOnly") or "httponly" in str(cookie).lower(),
            "same_site": same_site,
            "expires": str(cookie.expires) if cookie.expires else "session",
        }
 
        if not cookie.secure:
            issues.append(f"Cookie '{cookie.name}' missing Secure flag — transmittable over HTTP")
            risk_score += 15
        if not detail["http_only"]:
            issues.append(f"Cookie '{cookie.name}' missing HttpOnly — readable by JS (XSS risk)")
            risk_score += 10
        if same_site == "None":
            issues.append(f"Cookie '{cookie.name}' SameSite=None — CSRF risk")
            risk_score += 10
        if same_site is None:
            issues.append(f"Cookie '{cookie.name}' missing SameSite attribute")
            risk_score += 5
        if cookie.domain and cookie.domain not in domain and domain not in (cookie.domain or ""):
            issues.append(f"Cookie '{cookie.name}' scoped to foreign domain '{cookie.domain}'")
            risk_score += 20
 
        cookie_details.append(detail)
 
    session_cookies = [c for c in cookies if any(
        kw in c.name.lower() for kw in ["sess", "session", "sid", "auth", "token"]
    )]
    for sc in session_cookies:
        if not sc.secure:
            issues.append(f"Session cookie '{sc.name}' not Secure — session hijack risk")
            risk_score += 25
 
    tracking_names = ["_ga", "_gid", "_fbp", "_fbc", "__utma", "IDE", "NID", "DSID", "fr"]
    trackers_found = [c.name for c in cookies if c.name in tracking_names]
    if trackers_found:
        issues.append(f"Third-party tracking cookies: {', '.join(trackers_found)}")
        risk_score += 5
 
    if len(cookies) > 10:
        issues.append(f"Unusually high cookie count ({len(cookies)}) — possible fingerprinting")
        risk_score += 10
 
    # ── JS-based cookie manipulation (static source scan) ─────────
    # requests doesn't execute JS so runtime cookies won't show above —
    # scan raw HTML/JS source for the patterns instead
    if "document.cookie" in raw_html:
        issues.append("JavaScript cookie manipulation found in page source")
        risk_score += 20
    if "SameSite=None" in raw_html:
        issues.append("SameSite=None set via JavaScript — CSRF risk")
        risk_score += 15
    if re.search(r'atob\s*\(.*?cookie', raw_html, re.IGNORECASE | re.DOTALL):
        issues.append("Base64-obfuscated cookie operation (atob) — evasion attempt")
        risk_score += 30
    if "localStorage.setItem" in raw_html and any(
        kw in raw_html.lower() for kw in ["pass", "password", "credential", "token", "auth"]
    ):
        issues.append("Credentials written to localStorage — insecure sensitive data storage")
        risk_score += 35
 
    return {
        "cookie_count": len(cookies),
        "session_cookies": [c.name for c in session_cookies],
        "tracking_cookies": trackers_found,
        "issues": issues,
        "cookie_details": cookie_details,
        "cookie_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }
 
 
# ── IFRAME, OVERLAY & INLINE JS DETECTION ─────────────────────────────────────
 
def detect_iframes_and_overlays(soup: BeautifulSoup, base_domain: str) -> dict:
    issues = []
    risk_score = 0
 
    # ── 1. iframes ────────────────────────────────────────────────
    iframes = soup.find_all("iframe")
    iframe_details = []
    for iframe in iframes:
        src = iframe.get("src", "")
        style = iframe.get("style", "").lower().replace(" ", "")
        width = iframe.get("width", "")
        height = iframe.get("height", "")
        hidden = (
            "display:none" in style or
            "visibility:hidden" in style or
            width in ("0", "0px", "1px") or
            height in ("0", "0px", "1px")
        )
        cross_origin = bool(src and base_domain not in src and src.startswith("http"))
        iframe_details.append({"src": src[:200] or "(no src)", "hidden": hidden, "cross_origin": cross_origin})
 
        if hidden:
            issues.append(f"Hidden iframe (src: {src[:80] or 'none'}) — clickjacking risk")
            risk_score += 30
        elif cross_origin:
            issues.append(f"Cross-origin iframe '{src[:80]}' — possible credential harvesting")
            risk_score += 20
        else:
            issues.append(f"Same-origin iframe (src: {src[:80] or 'none'})")
            risk_score += 5
 
    # ── 2. Invisible overlay divs ─────────────────────────────────
    invisible_divs = 0
    suspicious_names = ["ghost", "overlay", "invisible", "hidden", "trap",
                        "capture", "cloak", "stealth", "shadow", "fake"]
 
    for el in soup.find_all(["div", "span", "section", "a"]):
        style = el.get("style", "").lower().replace(" ", "")
        if any([
            "opacity:0" in style,
            "visibility:hidden" in style,
            ("position:fixed" in style and "z-index" in style),
            ("position:absolute" in style and "opacity:0" in style),
        ]):
            invisible_divs += 1
 
        el_id = (el.get("id") or "").lower()
        el_class = " ".join(el.get("class") or []).lower()
        if any(word in el_id + el_class for word in suspicious_names):
            invisible_divs += 1
            issues.append(f"Suspicious element name '{el.get('id') or el.get('class')}' — possible cloaking layer")
            risk_score += 20
 
    if invisible_divs > 3:
        issues.append(f"{invisible_divs} invisible/overlay elements — CSS cloaking or clickjacking")
        risk_score += 25
    elif invisible_divs > 0:
        issues.append(f"{invisible_divs} invisible element(s) found")
        risk_score += 8
 
    # ── 3. Full-page overlay in <style> blocks ────────────────────
    full_page_overlay = False
    for block in soup.find_all("style"):
        css = block.get_text().lower().replace(" ", "")
        if "position:fixed" in css and ("width:100%" in css or "inset:0" in css) and "z-index" in css:
            full_page_overlay = True
            issues.append("CSS full-page fixed overlay — potential clickjacking layer")
            risk_score += 35
 
    # ── 4. Hidden & invisible inputs ─────────────────────────────
    hidden_inputs = []
    for inp in soup.find_all("input"):
        style = inp.get("style", "").lower().replace(" ", "")
        inp_type = inp.get("type", "").lower()
        if inp_type == "hidden":
            hidden_inputs.append(inp.get("name", "unnamed"))
        elif "opacity:0" in style or "visibility:hidden" in style:
            issues.append(f"Invisible input '{inp.get('name', 'unnamed')}' — covert keystroke capture")
            risk_score += 25
 
    if len(hidden_inputs) > 5:
        issues.append(f"{len(hidden_inputs)} hidden inputs — fingerprinting / data exfiltration")
        risk_score += 15
 
    # ── 5. Password field inside positioned overlay ───────────────
    fixed_divs_with_password = 0
    for div in soup.find_all(["div", "section", "form"]):
        style = div.get("style", "").lower().replace(" ", "")
        if ("position:fixed" in style or "position:absolute" in style) and div.find("input", {"type": "password"}):
            fixed_divs_with_password += 1
    if fixed_divs_with_password > 0:
        issues.append("Password field inside positioned overlay — fake login injection")
        risk_score += 40
 
    # ── 6. Inline JS static scan ──────────────────────────────────
    all_inline_js = " ".join(s.get_text() for s in soup.find_all("script", src=False))
    js_issues = []
 
    JS_PATTERNS = [
        (r'\beval\s*\(',                                              "eval() — code obfuscation",                    20),
        (r'atob\s*\(',                                                "atob() base64 decode — obfuscation",           15),
        (r'navigator\.sendBeacon',                                    "sendBeacon() — silent background exfiltration", 30),
        (r'fetch\s*\(\s*["\']https?://',                              "fetch() to external URL — possible exfil",    25),
        (r'addEventListener\s*\(\s*["\']keydown',                     "keydown listener — possible keystroke logger", 35),
        (r'addEventListener\s*\(\s*["\']keypress',                    "keypress listener — possible keystroke logger",35),
        (r'localStorage\.setItem',                                    "localStorage write detected",                  10),
        (r'window\.location\s*=|window\.location\.href\s*=',         "JS redirect — possible post-theft redirect",   15),
        (r'stealData|stealCreds|exfil|harvested|stolen_',             "Suspicious function name in JS source",        40),
        (r'document\.cookie\s*=',                                     "Runtime cookie write via JS",                  20),
        (r'XMLHttpRequest|\.open\s*\(\s*["\']POST',                   "XHR POST request — possible data exfil",       20),
        (r'btoa\s*\(',                                                 "btoa() base64 encode — possible data hiding",  10),
        (r'String\.fromCharCode|\\x[0-9a-fA-F]{2}',                  "Character code obfuscation in JS",             15),
    ]
 
    for pattern, label, weight in JS_PATTERNS:
        if re.search(pattern, all_inline_js, re.IGNORECASE):
            js_issues.append(label)
            risk_score += weight
 
    if js_issues:
        issues.extend(js_issues)
 
    # ── 7. Stolen favicon ─────────────────────────────────────────
    for tag in soup.find_all("link", rel=lambda r: r and "icon" in " ".join(r).lower()):
        href = tag.get("href", "")
        if href.startswith("http") and "localhost" not in href and "127.0.0.1" not in href:
            for legit in KNOWN_LEGIT_DOMAINS:
                if legit.split(".")[0] in href.lower():
                    issues.append(f"Favicon stolen from '{legit}' — brand impersonation")
                    risk_score += 25
                    break
            else:
                issues.append(f"External favicon from '{href[:80]}' — possible brand theft")
                risk_score += 10
 
    return {
        "iframe_count": len(iframes),
        "iframe_details": iframe_details,
        "invisible_elements": invisible_divs,
        "hidden_inputs": hidden_inputs,
        "full_page_overlay_css": full_page_overlay,
        "fake_login_overlay": fixed_divs_with_password > 0,
        "inline_js_issues": js_issues,
        "issues": issues,
        "overlay_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }
 
 
# ── PLAYWRIGHT DYNAMIC ANALYSIS ───────────────────────────────────────────────
 
def run_playwright_analysis(url: str) -> dict:
    """
    Headless browser analysis — catches what static requests cannot:
    runtime cookies, network requests, localStorage writes, JS redirects.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"available": False, "reason": "playwright not installed — run: pip install playwright && playwright install chromium"}
 
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
            console_logs = []
            page.on("console", lambda msg: console_logs.append(msg.text))
 
            try:
                page.goto(url, timeout=8000, wait_until="networkidle")
            except Exception:
                page.goto(url, timeout=8000, wait_until="domcontentloaded")
 
            final_url = page.url
 
            # ── Runtime cookies ───────────────────────────────────
            for c in context.cookies():
                result["runtime_cookies"].append({
                    "name": c["name"], "secure": c["secure"],
                    "http_only": c["httpOnly"],
                    "same_site": c.get("sameSite", "None"),
                    "domain": c.get("domain", ""),
                })
                if not c["secure"]:
                    result["issues"].append(f"Runtime cookie '{c['name']}' missing Secure flag")
                    risk_score += 15
                if not c["httpOnly"]:
                    result["issues"].append(f"Runtime cookie '{c['name']}' missing HttpOnly")
                    risk_score += 10
                if c.get("sameSite") == "None":
                    result["issues"].append(f"Runtime cookie '{c['name']}' SameSite=None — CSRF risk")
                    risk_score += 10
 
            # ── Network requests ──────────────────────────────────
            parsed_origin = urlparse(url).netloc
            suspicious_kws = ["steal", "exfil", "harvest", "collect", "beacon", "capture", "credential", "track"]
            for req in fired_requests:
                req_domain = urlparse(req["url"]).netloc
                is_cross = req_domain and req_domain != parsed_origin
                is_suspicious = any(kw in req["url"].lower() for kw in suspicious_kws)
 
                if is_suspicious:
                    result["suspicious_requests"].append(req)
                    result["issues"].append(f"Suspicious {req['method']} to '{req['url'][:100]}'")
                    risk_score += 30
                elif is_cross and req["method"] == "POST":
                    result["suspicious_requests"].append(req)
                    result["issues"].append(f"Cross-origin POST to '{req['url'][:100]}' — possible exfil")
                    risk_score += 25
 
            result["network_requests"] = fired_requests[:30]
 
            # ── JS redirect ───────────────────────────────────────
            if final_url.lower() != url.lower() and "localhost" not in final_url and "127.0.0.1" not in final_url:
                result["js_redirects"].append(final_url)
                result["issues"].append(f"Page redirected to '{final_url}' after load")
                risk_score += 20
 
            # ── localStorage sensitive data ────────────────────────
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
                    s in k.lower() for s in ["pass", "user", "cred", "token", "auth", "stolen"]
                )]
                if sensitive:
                    result["issues"].append(f"Sensitive keys in localStorage: {sensitive}")
                    risk_score += 40
 
            result["console_logs"] = console_logs[:20]
            browser.close()
 
    except Exception as e:
        result["error"] = str(e)
        result["issues"].append(f"Playwright error: {str(e)[:100]}")
 
    result["dynamic_risk_score"] = min(risk_score, 100)
    return result
 
 
 # ── SECURITY HEADERS ANALYSIS ─────────────────────────────────────────────────

SECURITY_HEADERS = {
    "Content-Security-Policy": {
        "required": True,
        "risk_weight": 25,
        "tip": "No CSP — allows XSS and inline script injection"
    },
    "X-Frame-Options": {
        "required": True,
        "risk_weight": 20,
        "tip": "No X-Frame-Options — clickjacking possible"
    },
    "X-Content-Type-Options": {
        "required": True,
        "risk_weight": 10,
        "tip": "No X-Content-Type-Options — MIME sniffing enabled"
    },
    "Strict-Transport-Security": {
        "required": True,
        "risk_weight": 15,
        "tip": "No HSTS — protocol downgrade attack possible"
    },
    "Referrer-Policy": {
        "required": False,
        "risk_weight": 5,
        "tip": "No Referrer-Policy — data leakage via referrer header"
    },
    "Permissions-Policy": {
        "required": False,
        "risk_weight": 5,
        "tip": "No Permissions-Policy — unrestricted access to browser APIs"
    },
}

WEAK_CSP_PATTERNS = [
    ("unsafe-inline", "CSP allows unsafe-inline — neutralises XSS protection", 20),
    ("unsafe-eval", "CSP allows unsafe-eval — JS eval() execution permitted", 20),
    ("*", "CSP wildcard source — overly permissive policy", 15),
    ("data:", "CSP allows data: URIs — potential exfil vector", 10),
]

def analyze_security_headers(response: requests.Response) -> dict:
    headers = {k.lower(): v for k, v in response.headers.items()}
    issues = []
    risk_score = 0
    present = []
    missing = []

    for header, meta in SECURITY_HEADERS.items():
        if header.lower() in headers:
            present.append(header)
            # Extra: audit CSP value quality if present
            if header == "Content-Security-Policy":
                csp_value = headers[header.lower()]
                for pattern, label, weight in WEAK_CSP_PATTERNS:
                    if pattern in csp_value:
                        issues.append(f"Weak CSP: {label}")
                        risk_score += weight
        else:
            missing.append(header)
            if meta["required"]:
                issues.append(meta["tip"])
                risk_score += meta["risk_weight"]
            else:
                issues.append(meta["tip"])
                risk_score += meta["risk_weight"]

    # Suspicious server headers — leaking backend info
    server = headers.get("server", "")
    x_powered = headers.get("x-powered-by", "")
    if server:
        issues.append(f"Server header exposed: '{server}' — fingerprinting risk")
        risk_score += 5
    if x_powered:
        issues.append(f"X-Powered-By exposed: '{x_powered}' — version disclosure")
        risk_score += 10

    # Meta-refresh redirect in headers (not HTML — header level)
    if "refresh" in headers:
        issues.append(f"HTTP Refresh header found: '{headers['refresh'][:80]}' — silent redirect")
        risk_score += 15

    return {
        "headers_present": present,
        "headers_missing": missing,
        "issues": issues,
        "header_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }


# ── WHOIS + DOMAIN AGE ───────────────────────────────────────────────────────

def analyze_domain_age(domain: str) -> dict:
    """
    Newly registered domains (< 30 days) are a massive phishing signal.
    Uses python-whois with graceful fallback.
    """
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
        result["issues"].append("WHOIS unavailable (pip install python-whois)")
        return result

    # Strip port from domain if present
    clean_domain = domain.split(":")[0]

    try:
        w = whois_lib.whois(clean_domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]

        if creation:
            # Normalise timezone
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - creation).days
            result["domain_age_days"] = age_days
            result["creation_date"] = creation.isoformat()
            result["registrar"] = str(w.registrar or "Unknown")

            if age_days < 7:
                result["is_new_domain"] = True
                result["issues"].append(
                    f"Domain registered {age_days}d ago — extremely new, high phishing risk"
                )
                result["risk_score"] = 60
            elif age_days < 30:
                result["is_new_domain"] = True
                result["issues"].append(
                    f"Domain registered {age_days}d ago — newly registered domain"
                )
                result["risk_score"] = 40
            elif age_days < 90:
                result["issues"].append(f"Domain registered {age_days}d ago — less than 3 months old")
                result["risk_score"] = 20
            else:
                result["risk_score"] = 0
        else:
            result["issues"].append("No creation date in WHOIS — registration data hidden")
            result["risk_score"] = 15

    except Exception as e:
        result["issues"].append(f"WHOIS lookup failed: {str(e)[:80]}")
        result["risk_score"] = 10  # unknown = slight suspicion

    return result


# ── DNS ANOMALY DETECTION ─────────────────────────────────────────────────────

def analyze_dns(domain: str) -> dict:
    """
    Checks for DNS signals commonly associated with phishing infrastructure:
    - No/missing SPF record (email spoofing vector)
    - No MX record (disposable domain, not used for legit email)
    - Very low TTL (rapid rotation — bulletproof hosting pattern)
    - Multiple A records pointing to different ASNs (fast-flux)
    """
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
        result["issues"].append("DNS resolver unavailable (pip install dnspython)")
        return result

    clean_domain = domain.split(":")[0]
    # Strip subdomains to root for SPF/MX/DMARC
    parts = clean_domain.split(".")
    root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else clean_domain

    resolver = dns.resolver.Resolver()
    resolver.lifetime = 3.0  # tight timeout

    # ── A records + TTL ───────────────────────────────────────────
    try:
        a_ans = resolver.resolve(clean_domain, "A")
        result["a_records"] = [str(r) for r in a_ans]
        result["ttl_seconds"] = a_ans.rrset.ttl
        if a_ans.rrset.ttl < 300:
            result["low_ttl"] = True
            result["issues"].append(
                f"Very low DNS TTL ({a_ans.rrset.ttl}s) — rapid rotation / fast-flux suspected"
            )
            result["risk_score"] += 30
        if len(result["a_records"]) > 4:
            result["fast_flux_suspected"] = True
            result["issues"].append(
                f"{len(result['a_records'])} A records — fast-flux network pattern"
            )
            result["risk_score"] += 25
    except Exception:
        result["issues"].append("No A record found — unusual for a live site")
        result["risk_score"] += 15

    # ── SPF ───────────────────────────────────────────────────────
    try:
        txt_ans = resolver.resolve(root_domain, "TXT")
        for rdata in txt_ans:
            txt = str(rdata)
            if "v=spf1" in txt.lower():
                result["has_spf"] = True
            if "v=DMARC1" in txt:
                result["has_dmarc"] = True
    except Exception:
        pass

    if not result["has_spf"]:
        result["issues"].append("No SPF record — domain vulnerable to email spoofing")
        result["risk_score"] += 20
    if not result["has_dmarc"]:
        result["issues"].append("No DMARC record — phishing emails can impersonate this domain")
        result["risk_score"] += 10

    # ── MX ────────────────────────────────────────────────────────
    try:
        mx_ans = resolver.resolve(root_domain, "MX")
        result["has_mx"] = len(list(mx_ans)) > 0
    except Exception:
        pass

    if not result["has_mx"]:
        result["issues"].append(
            "No MX record — domain not configured for email (disposable / throwaway domain)"
        )
        result["risk_score"] += 15

    result["risk_score"] = min(result["risk_score"], 100)
    return result


# ── PROMPT INJECTION + HIDDEN CONTENT DETECTION ───────────────────────────────

# Patterns that indicate an attacker is trying to poison an AI that
# might process this page (e.g. an AI assistant browsing the web,
# an agent scraping URLs, or LLM-based fraud analysis tool)
PROMPT_INJECTION_PATTERNS = [
    # Classic instruction override patterns
    (r'ignore\s+(previous|all|prior)\s+(instructions?|prompts?|context)',
     "Classic prompt injection: 'ignore previous instructions'", 50),
    (r'you\s+are\s+now\s+(a\s+)?(?:an?\s+)?(helpful|unrestricted|jailbroken|DAN)',
     "Role override injection: 'you are now...'", 50),
    (r'system\s*:\s*(you|your|ignore|forget)',
     "Fake system prompt injection attempt", 45),
    (r'<\s*system\s*>.*?<\s*/\s*system\s*>',
     "XML system tag injection in page content", 45),
    (r'\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>',
     "LLM control token injection (Llama/Mistral/ChatML format)", 50),
    (r'###\s*(instruction|system|human|assistant)\s*:',
     "Markdown-format instruction injection", 40),
    (r'disregard\s+(your|all)\s+(previous|prior|safety|guidelines)',
     "Safety bypass injection attempt", 45),
    # Data exfiltration via AI tool calls
    (r'fetch\s*\(\s*["\']https?://[^"\']{10,}["\'].*?cookie|token|session',
     "Credential exfil via fetch() in page JS", 50),
    (r'summarize\s+(and\s+)?(send|post|upload|exfiltrate)',
     "Exfil instruction targeting AI summarization", 45),
    # Hidden instructions in whitespace (CSS display:none, white-on-white text)
    (r'color\s*:\s*(?:#fff(?:fff)?|white|rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*0\s*\))',
     "White/invisible text — hidden instructions", 30),
    (r'font-size\s*:\s*0(?:px|em|rem)?',
     "Zero-size text — hidden content injection", 30),
    (r'display\s*:\s*none[^"]*>[^<]{20,}<',
     "Hidden text block (display:none with content)", 25),
    # Meta tag poisoning
    (r'<meta[^>]+content=["\'][^"\']*(?:ignore|system|jailbreak|DAN)[^"\']*["\']',
     "Suspicious content in meta tag — possible AI poisoning", 40),
]

def detect_prompt_injection(soup: "BeautifulSoup", raw_html: str) -> dict:
    """
    Detects prompt injection payloads and hidden content that could
    manipulate an AI model processing this page.
    Also catches data poisoning patterns in page metadata.
    """
    issues = []
    risk_score = 0
    injections_found = []

    html_lower = raw_html.lower()

    for pattern, label, weight in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, raw_html, re.IGNORECASE | re.DOTALL):
            issues.append(label)
            injections_found.append(label)
            risk_score += weight

    # ── Meta-refresh redirect (HTML level) ───────────────────────
    for meta in soup.find_all("meta"):
        http_equiv = (meta.get("http-equiv") or "").lower()
        if http_equiv == "refresh":
            content = meta.get("content", "")
            issues.append(f"Meta-refresh redirect found: '{content[:80]}' — silent redirect")
            risk_score += 20

    # ── Invisible text via aria-hidden + non-empty ────────────────
    aria_hidden_blocks = soup.find_all(attrs={"aria-hidden": "true"})
    for el in aria_hidden_blocks:
        text = el.get_text(strip=True)
        if len(text) > 30:
            issues.append(
                f"aria-hidden element with {len(text)} chars — hidden instructions for AI scrapers"
            )
            risk_score += 25
            break  # one flag sufficient

    # ── Honeypot / data poisoning in structured data ──────────────
    for script in soup.find_all("script", type="application/ld+json"):
        ld_text = script.get_text()
        if any(kw in ld_text.lower() for kw in ["ignore", "system", "jailbreak", "assistant"]):
            issues.append("Suspicious keywords in JSON-LD structured data — LLM poisoning attempt")
            risk_score += 35

    # ── Base tag hijacking ────────────────────────────────────────
    base_tags = soup.find_all("base")
    for base in base_tags:
        href = base.get("href", "")
        if href and href.startswith("http"):
            issues.append(
                f"<base href> redirects all relative URLs to '{href[:80]}' — link hijacking"
            )
            risk_score += 30

    return {
        "injections_found": injections_found,
        "issues": issues,
        "prompt_injection_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }


# ── CONTENT FINGERPRINTING ────────────────────────────────────────────────────

KNOWN_LEGIT_PAGE_HASHES: set = set()  # In production: load from DB

def compute_page_fingerprint(html: str) -> dict:
    """
    Normalise page and compute hash to detect cloned legitimate sites.
    Strips dynamic content (timestamps, tokens) before hashing.
    """
    # Strip scripts, styles, comments before fingerprinting structure
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
    # Strip dynamic tokens (CSRF, nonce values)
    cleaned = re.sub(r'(value|nonce|token)="[a-zA-Z0-9+/=_-]{16,}"', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().lower()

    page_hash = hashlib.sha256(cleaned.encode()).hexdigest()
    is_clone = page_hash in KNOWN_LEGIT_PAGE_HASHES

    return {
        "page_hash": page_hash,
        "is_known_clone": is_clone,
        "content_length": len(html),
    }   
    
    
    
    
    
    
 

 
def run_sandbox(url: str) -> dict:
    sandbox_data = {}

    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    sandbox_data["domain"] = domain

    # ── 1. Static HTTP fetch ──────────────────────────────────────
    try:
        response = requests.get(url, timeout=5,
                                headers={"User-Agent": "Mozilla/5.0"},
                                allow_redirects=True)
        html = response.text[:20000]
        sandbox_data["reachable"] = True
        sandbox_data["status_code"] = response.status_code
        sandbox_data["final_url"] = response.url.lower()
    except Exception:
        return {"domain": domain, "reachable": False, "error": "Request failed"}

    soup = BeautifulSoup(html, "html.parser")

    # ── 2. Basic signals ──────────────────────────────────────────
    forms = soup.find_all("form")
    sandbox_data["num_forms"] = len(forms)
    sandbox_data["form_actions"] = [f.get("action") for f in forms if f.get("action")]
    sandbox_data["has_password_field"] = bool(soup.find("input", {"type": "password"}))

    all_scripts = soup.find_all("script", src=True)
    external_scripts = [s["src"] for s in all_scripts if domain not in s.get("src", "")]
    same_origin_scripts = [
        s["src"] for s in all_scripts
        if domain in s.get("src", "") or not s.get("src", "").startswith("http")
    ]
    sandbox_data["external_scripts"] = external_scripts
    sandbox_data["same_origin_scripts"] = same_origin_scripts
    sandbox_data["scripts_to_fetch"] = external_scripts[:2] + same_origin_scripts[:2]

    sandbox_data["redirect_count"] = len(response.history)
    links = soup.find_all("a", href=True)
    sandbox_data["external_links_count"] = len([l["href"] for l in links if domain not in l["href"]])
    sandbox_data["uses_https"] = sandbox_data["final_url"].startswith("https")

    # ── 3. Typosquatting ─────────────────────────────────────────
    sandbox_data["typosquatting"] = detect_typosquatting(domain)

    # ── 4. Static cookie analysis ────────────────────────────────
    sandbox_data["cookies"] = analyze_cookies(response, domain)

    # ── 5. Iframe, overlay, inline JS ────────────────────────────
    sandbox_data["overlays"] = detect_iframes_and_overlays(soup, domain)

    # ── 6. NEW: Security headers ──────────────────────────────────
    sandbox_data["security_headers"] = analyze_security_headers(response)

    # ── 7. NEW: WHOIS domain age ──────────────────────────────────
    sandbox_data["domain_age"] = analyze_domain_age(domain)

    # ── 8. NEW: DNS anomaly detection ─────────────────────────────
    sandbox_data["dns"] = analyze_dns(domain)

    # ── 9. NEW: Prompt injection / hidden content ─────────────────
    sandbox_data["prompt_injection"] = detect_prompt_injection(soup, html)

    # ── 10. NEW: Page fingerprint ─────────────────────────────────
    sandbox_data["fingerprint"] = compute_page_fingerprint(html)

    # ── 11. Playwright dynamic analysis ───────────────────────────
    sandbox_data["dynamic"] = run_playwright_analysis(url)

    # ── 12. Composite extra risk (expanded) ───────────────────────
    extra_risk = 0
    extra_reasons = []

    typo = sandbox_data["typosquatting"]
    if typo["is_suspicious"]:
        if typo["verdict"] == "EXACT_SPOOF":
            extra_risk += 40
            extra_reasons.append(f"Typosquatting: near-exact spoof of '{typo['closest_legit_domain']}'")
        elif typo["verdict"] == "BRAND_IN_SUBDOMAIN":
            extra_risk += 35
            extra_reasons.append(f"Brand '{typo['closest_legit_domain'].split('.')[0]}' hijacked as subdomain")
        elif typo["verdict"] == "HIGH_SIMILARITY":
            extra_risk += 25
            extra_reasons.append(f"High domain similarity to '{typo['closest_legit_domain']}'")

    cookie_risk = sandbox_data["cookies"]["cookie_risk_score"]
    if cookie_risk >= 40:
        extra_risk += 20
        extra_reasons.append(f"Cookie security issues (score: {cookie_risk})")
    elif cookie_risk >= 15:
        extra_risk += 10
        extra_reasons.append("Minor cookie security flags")

    overlay_risk = sandbox_data["overlays"]["overlay_risk_score"]
    if overlay_risk >= 40:
        extra_risk += 25
        extra_reasons.append("Iframe/overlay credential-harvesting pattern detected")
    elif overlay_risk >= 15:
        extra_risk += 10
        extra_reasons.append("Suspicious iframe or overlay elements")

    dynamic_risk = sandbox_data["dynamic"].get("dynamic_risk_score", 0)
    if dynamic_risk >= 40:
        extra_risk += 30
        extra_reasons.append(f"Dynamic runtime analysis flagged suspicious behaviour (score: {dynamic_risk})")
    elif dynamic_risk >= 15:
        extra_risk += 15
        extra_reasons.append("Dynamic analysis: minor runtime flags")

    # ── NEW signal contributions ──────────────────────────────────
    header_risk = sandbox_data["security_headers"]["header_risk_score"]
    if header_risk >= 50:
        extra_risk += 20
        extra_reasons.append(f"Critical security headers missing (score: {header_risk})")
    elif header_risk >= 25:
        extra_risk += 10
        extra_reasons.append("Several security headers absent")

    domain_age_risk = sandbox_data["domain_age"]["risk_score"]
    if domain_age_risk >= 40:
        extra_risk += 25
        extra_reasons.append(
            f"Newly registered domain: {sandbox_data['domain_age'].get('domain_age_days', '?')} days old"
        )
    elif domain_age_risk >= 20:
        extra_risk += 12
        extra_reasons.append("Domain less than 90 days old — elevated caution")

    dns_risk = sandbox_data["dns"]["risk_score"]
    if dns_risk >= 40:
        extra_risk += 20
        extra_reasons.append("DNS anomalies detected (low TTL / fast-flux / missing SPF)")
    elif dns_risk >= 20:
        extra_risk += 10
        extra_reasons.append("DNS signals: missing email authentication records")

    injection_risk = sandbox_data["prompt_injection"]["prompt_injection_risk_score"]
    if injection_risk >= 40:
        extra_risk += 30
        extra_reasons.append("Prompt injection / content poisoning payload detected in page")
    elif injection_risk >= 20:
        extra_risk += 15
        extra_reasons.append("Hidden content or suspicious meta tags detected")

    sandbox_data["extra_risk_score"] = min(extra_risk, 100)
    sandbox_data["extra_risk_reasons"] = extra_reasons

    return sandbox_data