# database.py - SQLite cache, quota log, prediction history
import sqlite3, json, time, os
DB_PATH = os.path.join(os.path.dirname(__file__), "football_engine.db")

def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = _conn()
    c.execute("CREATE TABLE IF NOT EXISTS api_cache (cache_key TEXT PRIMARY KEY, data TEXT, expires_at REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS quota_log (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS prediction_history (id INTEGER PRIMARY KEY AUTOINCREMENT, league TEXT, home TEXT, away TEXT, home_goals INTEGER, away_goals INTEGER, home_prob REAL, draw_prob REAL, away_prob REAL, confidence REAL, created_at TEXT)")
    c.commit()
    c.close()

def get_cached_data(key):
    try:
        c = _conn()
        row = c.execute("SELECT data, expires_at FROM api_cache WHERE cache_key=?", (key,)).fetchone()
        c.close()
        if row and row["expires_at"] > time.time():
            return json.loads(row["data"])
        return None
    except Exception:
        return None

def set_cached_data(key, data, ttl_seconds=3600):
    try:
        c = _conn()
        c.execute("INSERT OR REPLACE INTO api_cache VALUES (?,?,?)", (key, json.dumps(data, default=str), time.time() + ttl_seconds))
        c.commit()
        c.close()
    except Exception:
        pass

def save_prediction_record(league, home, away, home_goals, away_goals, home_prob, draw_prob, away_prob, confidence):
    try:
        from datetime import datetime
        c = _conn()
        c.execute("INSERT INTO prediction_history (league, home, away, home_goals, away_goals, home_prob, draw_prob, away_prob, confidence, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (league, home, away, int(home_goals), int(away_goals), float(home_prob), float(draw_prob), float(away_prob), float(confidence), datetime.now().isoformat()))
        c.commit()
        c.close()
    except Exception:
        pass

def get_prediction_history(limit=50):
    try:
        c = _conn()
        rows = c.execute("SELECT * FROM prediction_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        c.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def log_quota(provider):
    try:
        from datetime import datetime
        c = _conn()
        c.execute("INSERT INTO quota_log (provider, created_at) VALUES (?,?)", (provider, datetime.now().strftime("%Y-%m-%d")))
        c.commit()
        c.close()
    except Exception:
        pass

def get_quota_count(provider, date_str):
    try:
        c = _conn()
        row = c.execute("SELECT COUNT(*) as n FROM quota_log WHERE provider=? AND created_at=?", (provider, date_str)).fetchone()
        c.close()
        return int(row["n"]) if row else 0
    except Exception:
        return 0
