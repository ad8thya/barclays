# services/graph_service.py

import sqlite3
import hashlib
import networkx as nx
from datetime import datetime

DB_PATH = "fraud_graph.db"


# ─────────────────────────────────────────────
# STEP 1 — init_db
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS incidents (
        incident_id      TEXT PRIMARY KEY,
        account_id       TEXT,
        timestamp        TEXT,
        email_score      REAL,
        website_score    REAL,
        attachment_score REAL,
        audio_score      REAL,
        final_score      REAL,
        campaign_id      TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS signals (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id   TEXT,
        signal_type   TEXT,
        signal_value  TEXT
    )''')
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# STEP 2 — store_incident
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# STEP 3 — find_correlated_incidents
#   Now generates a real campaign_id and persists
#   it to all linked incidents in the DB.
# ─────────────────────────────────────────────
def _generate_campaign_id(incident_ids: list[str]) -> str:
    """Deterministic campaign id from sorted member ids."""
    key = "|".join(sorted(incident_ids))
    return "CAMP-" + hashlib.sha256(key.encode()).hexdigest()[:8].upper()


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

    linked: dict[str, list[str]] = {}
    shared_signals: list[str] = []
    for sig_type, sig_value in my_signals:
        c.execute('''SELECT DISTINCT incident_id FROM signals
                     WHERE signal_value=? AND incident_id!=?''',
                  (sig_value, incident_id))
        for (matched_id,) in c.fetchall():
            linked.setdefault(matched_id, []).append(sig_value)
            if sig_value not in shared_signals:
                shared_signals.append(sig_value)

    if not linked:
        conn.close()
        return {"campaign_detected": False, "linked_incidents": [],
                "shared_signals": [], "victim_count": 1}

    # Build campaign membership and assign a persistent campaign_id
    all_members = sorted(set([incident_id] + list(linked.keys())))
    campaign_id = _generate_campaign_id(all_members)

    # Persist campaign_id to every member
    placeholders = ",".join("?" for _ in all_members)
    c.execute(
        f"UPDATE incidents SET campaign_id=? WHERE incident_id IN ({placeholders})",
        [campaign_id] + all_members,
    )
    conn.commit()
    conn.close()

    return {
        "campaign_detected": True,
        "campaign_id": campaign_id,
        "linked_incidents": list(linked.keys()),
        "shared_signals": shared_signals,
        "victim_count": len(all_members),
    }


# ─────────────────────────────────────────────
# STEP 4 — build_graph (multi-type intelligence graph)
#
#   Node types: incident | domain | ip
#   Edge relations: uses_domain | uses_ip | shared_signal
# ─────────────────────────────────────────────
def build_graph() -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # --- Incident nodes ---
    c.execute("SELECT incident_id, final_score, campaign_id, timestamp FROM incidents")
    incidents = c.fetchall()

    nodes_map: dict[str, dict] = {}
    for inc_id, score, camp_id, ts in incidents:
        nodes_map[inc_id] = {
            "id": inc_id,
            "type": "incident",
            "label": inc_id,
            "risk_score": score,
            "campaign_id": camp_id,
            "timestamp": ts,
        }

    # --- Signal nodes + edges ---
    c.execute("SELECT DISTINCT incident_id, signal_type, signal_value FROM signals")
    signal_rows = c.fetchall()

    edges: list[dict] = []
    for inc_id, sig_type, sig_value in signal_rows:
        node_id = f"{sig_type}:{sig_value}"

        # Create domain / ip node if new
        if node_id not in nodes_map:
            nodes_map[node_id] = {
                "id": node_id,
                "type": sig_type,          # "domain" or "ip"
                "label": sig_value,
                "risk_score": None,
                "campaign_id": None,
            }

        # Edge: incident → domain/ip
        relation = "uses_domain" if sig_type == "domain" else "uses_ip"
        edges.append({
            "source": inc_id,
            "target": node_id,
            "relation": relation,
        })

    # --- shared_signal edges (incident ↔ incident via same signal) ---
    c.execute('''SELECT DISTINCT s1.incident_id, s2.incident_id, s1.signal_value
                 FROM signals s1 JOIN signals s2
                 ON s1.signal_value = s2.signal_value
                 AND s1.incident_id < s2.incident_id''')
    for src, tgt, sig in c.fetchall():
        edges.append({
            "source": src,
            "target": tgt,
            "relation": "shared_signal",
            "signal": sig,
        })

    # --- Propagate campaign_id to signal nodes ---
    for edge in edges:
        if edge["relation"] in ("uses_domain", "uses_ip"):
            src_node = nodes_map.get(edge["source"])
            tgt_node = nodes_map.get(edge["target"])
            if src_node and src_node.get("campaign_id") and tgt_node:
                tgt_node["campaign_id"] = src_node["campaign_id"]

    conn.close()

    nodes = list(nodes_map.values())
    return {"nodes": nodes, "edges": edges}


# ─────────────────────────────────────────────
# STEP 5 — get_graph_score
# ─────────────────────────────────────────────
def get_graph_score(incident_id: str) -> float:
    result = find_correlated_incidents(incident_id)
    if not result["campaign_detected"]:
        return 0.0
    score = min(1.0, (result["victim_count"] * 0.2) +
                     (len(result["shared_signals"]) * 0.15))
    return round(score, 2)