"""
OOB (Out-of-Band) Verification Service
Adaptive channel selection, context-rich notifications, feedback loop.
"""

import sqlite3
from datetime import datetime

DB_PATH = "fraud_graph.db"


def init_oob_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS oob_events (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id     TEXT NOT NULL,
        account_id      TEXT,
        timestamp       TEXT,
        frs             REAL,
        channel         TEXT,
        reason          TEXT,
        campaign_summary TEXT,
        user_response   TEXT,
        resolved        INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()


def select_channel(layer_scores: dict) -> dict:
    """
    Choose the safest OOB verification channel based on which
    attack vectors are compromised.  Higher layer score = that
    channel is less trustworthy for verification.
    """
    audio_score = layer_scores.get("audio", 0)
    email_score = layer_scores.get("email", 0)
    compromised = []

    if audio_score >= 0.6:
        compromised.append("voice")
    if email_score >= 0.6:
        compromised.append("email")

    # Pick safest remaining channel
    if "voice" in compromised and "email" in compromised:
        channel = "in_app_biometric"
        reason = "Voice and email channels compromised — biometric-only verification"
    elif "voice" in compromised:
        channel = "push_notification"
        reason = "Voice channel compromised (deepfake detected) — using push notification"
    elif "email" in compromised:
        channel = "sms"
        reason = "Email channel compromised — using SMS to registered number"
    else:
        channel = "push_notification"
        reason = "Standard push notification verification"

    return {
        "channel": channel,
        "reason": reason,
        "compromised_channels": compromised,
    }


def build_oob_notification(incident_id: str, frs: float,
                           layer_scores: dict, graph_info: dict,
                           score_breakdown: dict) -> dict:
    """
    Build a context-rich OOB notification with channel selection
    and a human-readable campaign summary.
    """
    channel_info = select_channel(layer_scores)

    # Build one-line campaign context
    campaign_detected = graph_info.get("campaign_detected", False)
    victim_count = graph_info.get("victim_count", 1)
    shared = graph_info.get("shared_signals", [])

    if campaign_detected and shared:
        campaign_line = (
            f"Linked to campaign targeting {victim_count} customers "
            f"via shared infrastructure: {', '.join(shared[:3])}"
        )
    elif campaign_detected:
        campaign_line = f"Part of coordinated campaign across {victim_count} victims"
    else:
        campaign_line = "Isolated suspicious event — no campaign link detected yet"

    # Top contributing layers (sorted by contribution)
    top_layers = sorted(score_breakdown.items(), key=lambda x: x[1], reverse=True)
    top_trigger = top_layers[0][0].replace("_contribution", "").title() if top_layers else "Unknown"

    return {
        "incident_id": incident_id,
        "frs": round(frs, 2),
        "verdict": "OOB_TRIGGERED",
        "channel": channel_info["channel"],
        "channel_reason": channel_info["reason"],
        "compromised_channels": channel_info["compromised_channels"],
        "notification": {
            "title": "CrossShield: Suspicious Activity Detected",
            "body": (
                f"A transaction was flagged with {int(frs * 100)}% risk confidence. "
                f"Primary trigger: {top_trigger} layer. {campaign_line}. "
                f"Did you initiate this activity?"
            ),
            "actions": ["Approve", "Deny"],
        },
        "campaign_summary": campaign_line,
        "timestamp": datetime.utcnow().isoformat(),
    }


def store_oob_event(incident_id: str, account_id: str, frs: float,
                    channel: str, reason: str, campaign_summary: str):
    """Persist OOB event for audit trail and feedback loop."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO oob_events (incident_id, account_id, timestamp, frs, "
        "channel, reason, campaign_summary, resolved) VALUES (?,?,?,?,?,?,?,0)",
        (incident_id, account_id, datetime.utcnow().isoformat(),
         round(frs, 2), channel, reason, campaign_summary)
    )
    conn.commit()
    conn.close()


def record_oob_response(incident_id: str, response: str) -> dict:
    """
    Record user's Approve/Deny response.
    If Deny → amplify campaign in graph (boost linked incident scores).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "UPDATE oob_events SET user_response=?, resolved=1 WHERE incident_id=?",
        (response, incident_id)
    )

    result = {"incident_id": incident_id, "response": response, "action_taken": "logged"}

    if response.lower() == "deny":
        # Fraud confirmed by user → amplify campaign signals
        # Find all incidents sharing infrastructure with this one
        c.execute("SELECT signal_value FROM signals WHERE incident_id=?", (incident_id,))
        my_signals = [row[0] for row in c.fetchall()]

        amplified = []
        for sig_val in my_signals:
            c.execute(
                "SELECT DISTINCT incident_id FROM signals "
                "WHERE signal_value=? AND incident_id!=?",
                (sig_val, incident_id)
            )
            for (linked_id,) in c.fetchall():
                # Boost the linked incident's final score by 0.05 (capped at 1.0)
                c.execute(
                    "UPDATE incidents SET final_score = MIN(1.0, final_score + 0.05) "
                    "WHERE incident_id=?", (linked_id,)
                )
                if linked_id not in amplified:
                    amplified.append(linked_id)

        result["action_taken"] = "campaign_amplified"
        result["amplified_incidents"] = amplified
        result["message"] = (
            f"User denied transaction. {len(amplified)} linked incidents "
            f"amplified in fraud graph."
        )
    elif response.lower() == "approve":
        result["action_taken"] = "cleared"
        result["message"] = "User approved transaction. Event cleared."

    conn.commit()
    conn.close()
    return result
