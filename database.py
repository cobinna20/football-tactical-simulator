"""
database.py
Local SQLite caching layer, API quota ledger, and prediction calibration storage.
Runs at $0 cost with zero external database setup required.
"""

import sqlite3
import json
import time
from typing import Any, Optional, List, Dict

DB_PATH = "football_engine.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create all required tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            source_name TEXT NOT NULL,
            created_at REAL NOT NULL,
            ttl_seconds INTEGER NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS quota_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            called_at REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            match_id TEXT PRIMARY KEY,
            league_name TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            match_date TEXT NOT NULL,
            prob_home REAL NOT NULL,
            prob_draw REAL NOT NULL,
            prob_away REAL NOT NULL,
            projected_score TEXT NOT NULL,
            actual_home_goals INTEGER DEFAULT NULL,
            actual_away_goals INTEGER DEFAULT NULL,
            brier_score REAL DEFAULT NULL,
            created_at REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Return cached JSON payload and source if still within TTL."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT payload, source_name, created_at, ttl_seconds FROM api_cache WHERE cache_key = ?",
        (cache_key,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    age = time.time() - row["created_at"]
    if age > row["ttl_seconds"]:
        return None

    return {
        "data": json.loads(row["payload"]),
        "source": row["source_name"],
        "cached": True,
    }


def set_cached_data(cache_key: str, data: Any, source_name: str, ttl_seconds: int = 21600) -> None:
    """Store JSON-serializable data in SQLite cache (default 6 hours TTL)."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO api_cache (cache_key, payload, source_name, created_at, ttl_seconds)
        VALUES (?, ?, ?, ?, ?)
        """,
        (cache_key, json.dumps(data), source_name, time.time(), ttl_seconds),
    )
    conn.commit()
    conn.close()


def save_prediction_record(record: Dict[str, Any]) -> None:
    """Save pre-match simulation probabilities for future accuracy & Brier score tracking."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO prediction_history
        (match_id, league_name, home_team, away_team, match_date,
         prob_home, prob_draw, prob_away, projected_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["match_id"],
            record["league_name"],
            record["home_team"],
            record["away_team"],
            record["match_date"],
            record["prob_home"],
            record["prob_draw"],
            record["prob_away"],
            record["projected_score"],
            time.time(),
        ),
    )
    conn.commit()
    conn.close()


def get_prediction_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent predictions for the accuracy tracker tab."""
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM prediction_history ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
