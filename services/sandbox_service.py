import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import difflib
import re
 
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
 
 
# ── MAIN SANDBOX ───────────────────────────────────────────────────────────────
 
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
    # Both external AND same-origin scripts passed to website_service for JS analysis
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
 
    # ── 6. Playwright dynamic analysis ───────────────────────────
    sandbox_data["dynamic"] = run_playwright_analysis(url)
 
    # ── 7. Composite extra risk ───────────────────────────────────
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
 
    sandbox_data["extra_risk_score"] = min(extra_risk, 100)
    sandbox_data["extra_risk_reasons"] = extra_reasons
 
    return sandbox_data