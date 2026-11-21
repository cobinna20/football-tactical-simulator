# quota_manager.py
import os
from datetime import datetime
try:
    import streamlit as st
except Exception:
    st = None

PROVIDER_LIMITS = {"API-Football": 100, "Football-Data.org": 100, "ESPN": 1000, "TheSportsDB": 100, "Gemini": 50}

def _clean(v):
    return str(v).strip().strip('"').strip("'") if v is not None else ""

def get_api_keys():
    keys = {}
    for k in ["GEMINI_API_KEY", "FOOTBALL_DATA_KEY", "API_FOOTBALL_KEY", "THESPORTSDB_KEY"]:
        val = ""
        if st is not None:
            try:
                if hasattr(st, "secrets") and k in st.secrets:
                    val = _clean(st.secrets[k])
            except Exception:
                pass
        if not val:
            val = _clean(os.getenv(k, ""))
        keys[k] = val
    return keys

def can_call_provider(provider):
    try:
        from database import get_quota_count
        today = datetime.now().strftime("%Y-%m-%d")
        used = get_quota_count(provider, today)
        limit = PROVIDER_LIMITS.get(provider, 100)
        if used >= limit:
            return False, 0, f"Daily limit reached: {used}/{limit}"
        return True, limit - used, f"{used}/{limit} used"
    except Exception:
        return True, 99, "Quota check skipped"

def record_provider_call(provider):
    try:
        from database import log_quota
        log_quota(provider)
    except Exception:
        pass

def get_quota_status():
    out = []
    for p, lim in PROVIDER_LIMITS.items():
        ok, rem, msg = can_call_provider(p)
        out.append({"provider": p, "limit": lim, "remaining": rem, "status": msg, "can_call": ok})
    return out
