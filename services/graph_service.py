# services/graph_service.py

import sqlite3
import networkx as nx
from datetime import datetime

DB_PATH = "fraud_graph.db"

# ── STEP 1 ── init_db
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS incidents (
        incident_id   TEXT PRIMARY KEY,
        account_id    TEXT,
        timestamp     TEXT,
        email_score   REAL,
        website_score REAL,
        attachment_score REAL,
        audio_score   REAL,
        final_score   REAL,
        campaign_id   TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS signals (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id   TEXT,
        signal_type   TEXT,
        signal_value  TEXT
    )''')
    conn.commit()
    conn.close()


# ── STEP 2 ── store_incident
def store_incident(incident_id, account_id, scores: dict, signals: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO incidents VALUES (?,?,?,?,?,?,?,?,?)''',
        (incident_id, account_id, datetime.utcnow().isoformat(),
         scores.get("email", 0), scores.get("website", 0),
         scores.get("attachment", 0), scores.get("audio", 0),
         scores.get("final", 0), None))
    for domain in signals.get("domains", []):
        c.execute("INSERT INTO signals VALUES (null,?,?,?)",
                  (incident_id, "domain", domain))
    for ip in signals.get("ips", []):
        c.execute("INSERT INTO signals VALUES (null,?,?,?)",
                  (incident_id, "ip", ip))
    conn.commit()
    conn.close()


# ── STEP 3 ── find_correlated_incidents
def find_correlated_incidents(incident_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT signal_type, signal_value FROM signals WHERE incident_id=?",
              (incident_id,))
    my_signals = c.fetchall()
    if not my_signals:
        conn.close()
        return {"campaign_detected": False, "linked_incidents": [],
                "shared_signals": [], "victim_count": 1}
    linked = {}
    shared_signals = []
    for sig_type, sig_value in my_signals:
        c.execute('''SELECT DISTINCT incident_id FROM signals
                     WHERE signal_value=? AND incident_id!=?''',
                  (sig_value, incident_id))
        for (matched_id,) in c.fetchall():
            if matched_id not in linked:
                linked[matched_id] = []
            linked[matched_id].append(sig_value)
            if sig_value not in shared_signals:
                shared_signals.append(sig_value)
    conn.close()
    if not linked:
        return {"campaign_detected": False, "linked_incidents": [],
                "shared_signals": [], "victim_count": 1}
    return {
        "campaign_detected": True,
        "campaign_id": "CAMP-A",
        "linked_incidents": list(linked.keys()),
        "shared_signals": shared_signals,
        "victim_count": len(linked) + 1
    }


# ── STEP 4 ── build_graph
def build_graph() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT incident_id, final_score, campaign_id, timestamp FROM incidents")
    incidents = c.fetchall()
    G = nx.Graph()
    nodes = []
    for inc_id, score, camp_id, ts in incidents:
        G.add_node(inc_id, risk_score=score, campaign_id=camp_id)
        nodes.append({"id": inc_id, "risk_score": score,
                      "campaign_id": camp_id, "timestamp": ts})
    c.execute('''SELECT DISTINCT s1.incident_id, s2.incident_id, s1.signal_value
                 FROM signals s1 JOIN signals s2
                 ON s1.signal_value = s2.signal_value
                 AND s1.incident_id < s2.incident_id''')
    edges = {}
    for src, tgt, sig in c.fetchall():
        key = (src, tgt)
        if key not in edges:
            edges[key] = []
        edges[key].append(sig)
        G.add_edge(src, tgt)
    conn.close()
    return {
        "nodes": nodes,
        "edges": [{"source": k[0], "target": k[1], "shared": v}
                  for k, v in edges.items()]
    }


# ── STEP 5 ── get_graph_score
def get_graph_score(incident_id: str) -> float:
    result = find_correlated_incidents(incident_id)
    if not result["campaign_detected"]:
        return 0.0
    score = min(1.0, (result["victim_count"] * 0.2) +
                     (len(result["shared_signals"]) * 0.15))
    return round(score, 2)