import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


def run_sandbox(url: str):
    sandbox_data = {}

    # 🔹 normalize
    if not url.startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    sandbox_data["domain"] = domain

    try:
        response = requests.get(
            url,
            timeout=5,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        html = response.text[:20000]  # limit size
        final_url = response.url.lower()

        sandbox_data["reachable"] = True
        sandbox_data["status_code"] = response.status_code
        sandbox_data["final_url"] = final_url

    except Exception as e:
        return {
            "domain": domain,
            "reachable": False,
            "error": "Request failed"
        }

    soup = BeautifulSoup(html, "html.parser")

    # 🔥 BEHAVIOR SIGNALS

    # 1. Forms
    forms = soup.find_all("form")
    sandbox_data["num_forms"] = len(forms)

    form_actions = []
    for f in forms:
        action = f.get("action")
        if action:
            form_actions.append(action)

    sandbox_data["form_actions"] = form_actions

    # 2. Password field
    sandbox_data["has_password_field"] = bool(
        soup.find("input", {"type": "password"})
    )

    # 3. Scripts
    scripts = soup.find_all("script", src=True)
    external_scripts = [
        s["src"] for s in scripts if domain not in s["src"]
    ]

    sandbox_data["external_scripts"] = external_scripts

    # 4. Redirects
    sandbox_data["redirect_count"] = len(response.history)

    # 5. Links
    links = soup.find_all("a", href=True)
    external_links = [
        l["href"] for l in links if domain not in l["href"]
    ]

    sandbox_data["external_links_count"] = len(external_links)

    # 6. HTTPS check
    sandbox_data["uses_https"] = final_url.startswith("https")

    return sandbox_data