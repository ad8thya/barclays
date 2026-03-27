import sys
sys.path.append(".")
from services.graph_service import init_db, store_incident

init_db()

# Pre-existing victims — same domain, same IP
store_incident("INC-2031", "acct_001",
    {"email": 0.76, "website": 0.82, "attachment": 0.5, "audio": 0.3, "final": 0.71},
    {"domains": ["barcl4ys-secure.com"], "ips": ["185.220.101.45"]})

store_incident("INC-2039", "acct_002",
    {"email": 0.81, "website": 0.85, "attachment": 0.6, "audio": 0.7, "final": 0.79},
    {"domains": ["barcl4ys-secure.com"], "ips": ["185.220.101.45"]})

print("Graph seeded with 2 prior victims.")