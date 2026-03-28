import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import difflib
import re


# ── TYPOSQUATTING ──────────────────────────────────────────────────────────────
# Well-known banking / financial domains to compare against
KNOWN_LEGIT_DOMAINS = [
    "barclays.com", "barclaysus.com",
    "hsbc.com", "hsbc.co.uk",
    "lloydsbank.com", "lloydsbankinggroup.com",
    "natwest.com", "rbs.co.uk",
    "santander.co.uk", "santander.com",
    "halifax.co.uk",
    "nationwide.co.uk",
    "monzo.com", "starlingbank.com",
    "revolut.com",
    "paypal.com", "paypal.co.uk",
    "amazon.com", "amazon.co.uk",
    "google.com", "apple.com", "microsoft.com",
    "gov.uk", "hmrc.gov.uk",
]

# Homoglyph / leet-speak substitutions commonly used in phishing
HOMOGLYPH_MAP = {
    "0": "o", "1": "l", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b",
    "@": "a", "rn": "m", "vv": "w", "ii": "u",
}


def _normalize_domain(domain: str) -> str:
    """Strip www prefix, lowercase, apply homoglyph normalisation."""
    d = domain.lower().replace("www.", "")
    for fake, real in HOMOGLYPH_MAP.items():
        d = d.replace(fake, real)
    return d


def detect_typosquatting(domain: str) -> dict:
    """
    Compare the target domain against known-legit domains using
    sequence-similarity. Returns the closest match and a suspicion flag.
    """
    normalised = _normalize_domain(domain)
    best_match = None
    best_score = 0.0

    # Only compare the registered domain (drop TLD differences)
    target_base = normalised.split(".")[0]

    for legit in KNOWN_LEGIT_DOMAINS:
        legit_base = legit.split(".")[0]
        score = difflib.SequenceMatcher(None, target_base, legit_base).ratio()
        if score > best_score:
            best_score = score
            best_match = legit

    # Score thresholds
    if best_score >= 0.95:
        # Almost identical — likely exact spoof or subdomain trick
        verdict = "EXACT_SPOOF"
        is_suspicious = True
    elif best_score >= 0.75:
        # High similarity — strong typosquatting signal
        verdict = "HIGH_SIMILARITY"
        is_suspicious = True
    elif best_score >= 0.55:
        verdict = "MODERATE_SIMILARITY"
        is_suspicious = False   # flag but don't score heavily
    else:
        verdict = "NO_MATCH"
        is_suspicious = False

    # Extra: check if a legit brand name appears as a subdomain
    # e.g. barclays.evil-domain.com
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


# ── COOKIE ANALYSIS ────────────────────────────────────────────────────────────

def analyze_cookies(response: requests.Response, domain: str) -> dict:
    """
    Inspect Set-Cookie headers for security misconfigurations and
    tracking / fingerprinting patterns.
    """
    cookies = response.cookies
    raw_headers = response.headers.get("set-cookie", "")

    issues = []
    cookie_details = []
    risk_score = 0

    for cookie in cookies:
        detail = {
            "name": cookie.name,
            "domain": cookie.domain or domain,
            "path": cookie.path,
            "secure": cookie.secure,
            "http_only": cookie.has_nonstandard_attr("HttpOnly") or "httponly" in str(cookie).lower(),
            "same_site": None,
            "expires": str(cookie.expires) if cookie.expires else "session",
        }

        # Extract SameSite from raw header (requests doesn't parse it natively)
        raw_lower = raw_headers.lower()
        if "samesite=none" in raw_lower:
            detail["same_site"] = "None"
        elif "samesite=lax" in raw_lower:
            detail["same_site"] = "Lax"
        elif "samesite=strict" in raw_lower:
            detail["same_site"] = "Strict"

        # ── Security checks ──────────────────────────────────────────
        if not cookie.secure:
            issues.append(f"Cookie '{cookie.name}' missing Secure flag — transmittable over HTTP")
            risk_score += 15

        if not detail["http_only"]:
            issues.append(f"Cookie '{cookie.name}' missing HttpOnly — readable by JavaScript (XSS risk)")
            risk_score += 10

        if detail["same_site"] == "None":
            issues.append(f"Cookie '{cookie.name}' SameSite=None — CSRF risk if not Secure")
            risk_score += 10

        if detail["same_site"] is None:
            issues.append(f"Cookie '{cookie.name}' has no SameSite attribute — defaults to Lax but worth noting")
            risk_score += 5

        # Cross-domain cookie (set for a parent domain, suspicious if domain != target)
        if cookie.domain and cookie.domain not in domain and domain not in (cookie.domain or ""):
            issues.append(f"Cookie '{cookie.name}' scoped to foreign domain '{cookie.domain}' — possible tracking")
            risk_score += 20

        cookie_details.append(detail)

    # ── Session fixation pattern ──────────────────────────────────
    session_cookies = [c for c in cookies if any(
        kw in c.name.lower() for kw in ["sess", "session", "sid", "auth", "token"]
    )]
    if session_cookies:
        # Warn if session cookie doesn't have Secure + HttpOnly
        for sc in session_cookies:
            if not sc.secure:
                issues.append(f"Session cookie '{sc.name}' not Secure — session hijack risk over HTTP")
                risk_score += 25

    # ── Tracking / fingerprinting heuristics ─────────────────────
    tracking_names = ["_ga", "_gid", "_fbp", "_fbc", "__utma", "IDE", "NID", "DSID", "fr"]
    trackers_found = [c.name for c in cookies if c.name in tracking_names]
    if trackers_found:
        issues.append(f"Third-party tracking cookies detected: {', '.join(trackers_found)}")
        risk_score += 5   # low weight — common but worth flagging

    # ── Cookie count anomaly ──────────────────────────────────────
    if len(cookies) > 10:
        issues.append(f"Unusually high cookie count ({len(cookies)}) — possible fingerprinting")
        risk_score += 10

    return {
        "cookie_count": len(cookies),
        "session_cookies": [c.name for c in session_cookies] if session_cookies else [],
        "tracking_cookies": trackers_found,
        "issues": issues,
        "cookie_details": cookie_details,
        "cookie_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }


# ── IFRAME & OVERLAY DETECTION ─────────────────────────────────────────────────

def detect_iframes_and_overlays(soup: BeautifulSoup, base_domain: str) -> dict:
    """
    Detect credential-harvesting iframes, invisible overlay divs,
    and CSS-based cloaking techniques.
    """
    issues = []
    risk_score = 0

    # ── 1. iframes ────────────────────────────────────────────────
    iframes = soup.find_all("iframe")
    iframe_details = []
    for iframe in iframes:
        src = iframe.get("src", "")
        style = iframe.get("style", "").lower()
        width = iframe.get("width", "")
        height = iframe.get("height", "")
        hidden = (
            "display:none" in style.replace(" ", "") or
            "visibility:hidden" in style.replace(" ", "") or
            width in ("0", "0px", "1px") or
            height in ("0", "0px", "1px")
        )
        cross_origin = src and base_domain not in src and src.startswith("http")

        detail = {
            "src": src[:200] if src else "(no src)",
            "hidden": hidden,
            "cross_origin": cross_origin,
        }
        iframe_details.append(detail)

        if hidden:
            issues.append(f"Hidden iframe detected (src: {src[:80] or 'none'}) — common in clickjacking")
            risk_score += 30
        elif cross_origin:
            issues.append(f"Cross-origin iframe from '{src[:80]}' — possible credential harvesting frame")
            risk_score += 20
        else:
            issues.append(f"iframe present (src: {src[:80] or 'none'})")
            risk_score += 5

    # ── 2. Invisible overlay divs ─────────────────────────────────
    overlay_patterns = [
        {"position": "fixed", "z-index": True},   # full-screen overlay
        {"position": "absolute", "opacity": "0"},
        {"visibility": "hidden"},
        {"display": "none"},
    ]

    invisible_divs = 0
    all_elements = soup.find_all(["div", "span", "section", "a"])
    for el in all_elements:
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
        if any(word in el_id + el_class for word in ["ghost", "overlay", "invisible", "hidden", "trap", "capture", "cloak"]):
            invisible_divs += 1
            issues.append(f"Suspicious element id/class '{el.get('id') or el.get('class')}' — possible cloaking layer")
            risk_score += 20

    if invisible_divs > 3:
        issues.append(f"{invisible_divs} invisible/overlay elements detected — possible CSS cloaking or clickjacking overlay")
        risk_score += 25
    elif invisible_divs > 0:
        issues.append(f"{invisible_divs} invisible element(s) found — minor flag")
        risk_score += 8

    # ── 3. Full-page overlay via CSS ─────────────────────────────
    style_blocks = soup.find_all("style")
    full_page_overlay = False
    for block in style_blocks:
        css_text = block.get_text().lower()
        if (
            "position:fixed" in css_text.replace(" ", "") and
            ("width:100%" in css_text.replace(" ", "") or "inset:0" in css_text.replace(" ", "")) and
            "z-index" in css_text
        ):
            full_page_overlay = True
            issues.append("CSS defines full-page fixed overlay — potential clickjacking or credential theft layer")
            risk_score += 35

    # ── 4. Transparent/invisible form fields ─────────────────────
    inputs = soup.find_all("input")
    hidden_inputs = []
    for inp in inputs:
        style = inp.get("style", "").lower().replace(" ", "")
        inp_type = inp.get("type", "").lower()
        if inp_type == "hidden":
            hidden_inputs.append(inp.get("name", "unnamed"))
        elif "opacity:0" in style or "visibility:hidden" in style:
            issues.append(f"Invisible input field '{inp.get('name', 'unnamed')}' — may capture keystrokes covertly")
            risk_score += 25

    if len(hidden_inputs) > 5:
        issues.append(f"{len(hidden_inputs)} hidden input fields — unusually high, possible data exfiltration")
        risk_score += 15

    # ── 5. Fake login overlay pattern ────────────────────────────
    # A page with a password field inside a fixed/absolute positioned div
    fixed_divs_with_password = 0
    for div in soup.find_all(["div", "section", "form"]):
        style = div.get("style", "").lower().replace(" ", "")
        if "position:fixed" in style or "position:absolute" in style:
            if div.find("input", {"type": "password"}):
                fixed_divs_with_password += 1

    if fixed_divs_with_password > 0:
        issues.append("Password field inside positioned overlay — classic fake login injection pattern")
        risk_score += 40

    return {
        "iframe_count": len(iframes),
        "iframe_details": iframe_details,
        "invisible_elements": invisible_divs,
        "hidden_inputs": hidden_inputs,
        "full_page_overlay_css": full_page_overlay,
        "fake_login_overlay": fixed_divs_with_password > 0,
        "issues": issues,
        "overlay_risk_score": min(risk_score, 100),
        "has_issues": len(issues) > 0,
    }


# ── MAIN SANDBOX ───────────────────────────────────────────────────────────────

def run_sandbox(url: str):
    sandbox_data = {}

    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    sandbox_data["domain"] = domain

    # ── 1. HTTP request ───────────────────────────────────────────
    try:
        response = requests.get(
            url,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
        )
        html = response.text[:20000]
        final_url = response.url.lower()
        sandbox_data["reachable"] = True
        sandbox_data["status_code"] = response.status_code
        sandbox_data["final_url"] = final_url
    except Exception:
        return {
            "domain": domain,
            "reachable": False,
            "error": "Request failed",
        }

    soup = BeautifulSoup(html, "html.parser")

    # ── 2. Original signals (kept for backward compat) ───────────
    forms = soup.find_all("form")
    sandbox_data["num_forms"] = len(forms)
    sandbox_data["form_actions"] = [f.get("action") for f in forms if f.get("action")]
    sandbox_data["has_password_field"] = bool(soup.find("input", {"type": "password"}))

    scripts = soup.find_all("script", src=True)
    all_scripts = soup.find_all("script", src=True)
    external_scripts = [s["src"] for s in all_scripts if domain not in s.get("src", "")]
    same_origin_scripts = [s["src"] for s in all_scripts if domain in s.get("src", "")]

    # Fetch both for JS analysis, just track external separately
    scripts_to_fetch = external_scripts[:2] + same_origin_scripts[:2]


    sandbox_data["external_scripts"] = external_scripts
    sandbox_data["redirect_count"] = len(response.history)

    links = soup.find_all("a", href=True)
    external_links = [l["href"] for l in links if domain not in l["href"]]
    sandbox_data["external_links_count"] = len(external_links)
    sandbox_data["uses_https"] = final_url.startswith("https")

    # ── 3. NEW: Typosquatting ─────────────────────────────────────
    sandbox_data["typosquatting"] = detect_typosquatting(domain)

    # ── 4. NEW: Cookie analysis ───────────────────────────────────
    sandbox_data["cookies"] = analyze_cookies(response, domain)

    # ── 5. NEW: iFrame & overlay detection ───────────────────────
    sandbox_data["overlays"] = detect_iframes_and_overlays(soup, domain)

    # ── 6. Composite enhanced risk score ─────────────────────────
    # Combine new signals into a single extra_risk number (0-100)
    extra_risk = 0
    extra_reasons = []

    typo = sandbox_data["typosquatting"]
    if typo["is_suspicious"]:
        if typo["verdict"] == "EXACT_SPOOF":
            extra_risk += 40
            extra_reasons.append(f"Typosquatting: near-exact spoof of '{typo['closest_legit_domain']}'")
        elif typo["verdict"] == "BRAND_IN_SUBDOMAIN":
            extra_risk += 35
            extra_reasons.append(f"Brand '{typo['closest_legit_domain'].split('.')[0]}' used as subdomain — spoofing attempt")
        elif typo["verdict"] == "HIGH_SIMILARITY":
            extra_risk += 25
            extra_reasons.append(f"High domain similarity to '{typo['closest_legit_domain']}' ({typo['similarity_score']:.0%})")

    cookie_risk = sandbox_data["cookies"]["cookie_risk_score"]
    if cookie_risk >= 40:
        extra_risk += 20
        extra_reasons.append(f"Cookie security issues detected (score: {cookie_risk})")
    elif cookie_risk >= 15:
        extra_risk += 10
        extra_reasons.append("Minor cookie security flags")

    overlay_risk = sandbox_data["overlays"]["overlay_risk_score"]
    if overlay_risk >= 40:
        extra_risk += 25
        extra_reasons.append("Iframe/overlay credential-harvesting pattern detected")
    elif overlay_risk >= 15:
        extra_risk += 10
        extra_reasons.append("Suspicious iframe or overlay elements found")

    sandbox_data["extra_risk_score"] = min(extra_risk, 100)
    sandbox_data["extra_risk_reasons"] = extra_reasons

    return sandbox_data