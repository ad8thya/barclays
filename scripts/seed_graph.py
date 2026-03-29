import sys
sys.path.append(".")
from services.graph_service import init_db, store_incident

init_db()

# ── Campaign A: barcl4ys-secure.com phishing ring ──
store_incident("INC-2031", "acct_001",
    {"email": 0.76, "website": 0.82, "attachment": 0.50, "audio": 0.30, "final": 0.71},
    {"domains": ["barcl4ys-secure.com"], "ips": ["185.220.101.45"]})

store_incident("INC-2032", "acct_002",
    {"email": 0.81, "website": 0.85, "attachment": 0.60, "audio": 0.70, "final": 0.79},
    {"domains": ["barcl4ys-secure.com"], "ips": ["185.220.101.45"]})

store_incident("INC-2033", "acct_003",
    {"email": 0.79, "website": 0.80, "attachment": 0.55, "audio": 0.40, "final": 0.74},
    {"domains": ["barcl4ys-secure.com"], "ips": ["185.220.101.45"]})

print("Graph seeded: Campaign A (3 victims, barcl4ys-secure.com)")