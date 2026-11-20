"""
quota_manager.py
Protects free-tier API quotas (Football-Data.org 10/min, API-Football 100/day)
and safely reads API keys from Streamlit Secrets or environment variables.
"""

import os
import time
import streamlit as st
from database import get_connection, init_db

PROVIDER_LIMITS = {
    "football_data_org": {"window_seconds": 60, "max_calls": 8},     # Buffer below 10/min
    "api_football": {"window_seconds": 86400, "max_calls": 90},      # Buffer below 100/day
    "espn_public": {"window_seconds": 60, "max_calls": 120},         # Unlimited public
    "thesportsdb": {"window_seconds": 60, "max_calls": 25},          # Free key '3' limit 30/min
}


def get_secret_key(key_name: str) -> str:
    """Safely fetch API key from Streamlit Secrets or OS environment."""
    try:
        if key_name in st.secrets:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass
    return os.environ.get(key_name, "").strip()


def can_call_provider(provider: str) -> bool:
    """Check if provider key exists (if required) and is within free-tier rate limits."""
    if provider == "football_data_org" and not get_secret_key("FOOTBALL_DATA_KEY"):
        return False
    if provider == "api_football" and not get_secret_key("API_FOOTBALL_KEY"):
        return False

    limits = PROVIDER_LIMITS.get(provider)
    if not limits:
        return True

    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cutoff = time.time() - limits["window_seconds"]

    cur.execute("DELETE FROM quota_log WHERE called_at < ?", (time.time() - 90000,))
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM quota_log WHERE provider = ? AND called_at >= ?",
        (provider, cutoff),
    )
    count = cur.fetchone()["cnt"]
    conn.commit()
    conn.close()

    return count < limits["max_calls"]


def record_provider_call(provider: str) -> None:
    """Log an outbound API call to track free-tier usage."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO quota_log (provider, called_at) VALUES (?, ?)",
        (provider, time.time()),
    )
    conn.commit()
    conn.close()


def get_quota_status() -> dict:
    """Return remaining daily/minute calls for display on the dashboard."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    status = {}
    now = time.time()

    for provider, cfg in PROVIDER_LIMITS.items():
        cutoff = now - cfg["window_seconds"]
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM quota_log WHERE provider = ? AND called_at >= ?",
            (provider, cutoff),
        )
        used = cur.fetchone()["cnt"]
        status[provider] = {
            "used": used,
            "max": cfg["max_calls"],
            "remaining": max(0, cfg["max_calls"] - used),
        }

    conn.close()
    return status
