# source_router.py - ESPN first, visible diagnostics, season handling for 2026
import os, time, csv, io
from datetime import datetime, timedelta
try:
    import streamlit as st
except Exception:
    st = None
try:
    import requests
except Exception:
    requests = None
try:
    from league_registry import LEAGUE_REGISTRY
except Exception:
    LEAGUE_REGISTRY = {}
try:
    from quota_manager import get_api_keys, can_call_provider, record_provider_call
except Exception:
    def get_api_keys(): return {}
    def can_call_provider(p): return True, 99, ""
    def record_provider_call(p): pass
try:
    from database import get_cached_data, set_cached_data
except Exception:
    def get_cached_data(k): return None
    def set_cached_data(k, v, ttl_seconds=3600): pass

HEADERS = {"User-Agent": "football-tactical-simulator/1.0"}

def _clean(v):
    return str(v).strip().strip('"').strip("'") if v is not None else ""

def _log(diags, provider, url, status, error, found, note=""):
    diags.append({"provider": provider, "url": url, "status": status, "error": error or "", "found": found, "note": note, "time": datetime.now().strftime("%H:%M:%S")})

def _http_get(url, headers=None, params=None, timeout=12):
    if requests is None:
        return {"status": 0, "error": "requests not installed", "json": None, "text": ""}
    try:
        r = requests.get(url, headers=headers or HEADERS, params=params, timeout=timeout)
        try:
            j = r.json()
        except Exception:
            j = None
        return {"status": r.status_code, "error": "", "json": j, "text": r.text[:2000]}
    except Exception as e:
        return {"status": 0, "error": f"{type(e).__name__}: {e}", "json": None, "text": ""}

def _seasons():
    now = datetime.now()
    primary = now.year if now.month >= 7 else now.year - 1
    return [primary, primary - 1]

def _fdcuk_str(y):
    a = int(y) % 100
    return f"{a:02d}{(a+1)%100:02d}"

def _fetch_espn(entry, diags):
    slug = entry.get("espn_slug")
    if not slug:
        _log(diags, "ESPN", "-", 0, "No espn_slug", 0, "Skipped")
        return []
    today = datetime.now().date()
    end = today + timedelta(days=35)
    dates = f"{today.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
    res = _http_get(url, params={"limit": 1000, "dates": dates})
    if res["status"] != 200 or not res["json"]:
        _log(diags, "ESPN", url, res["status"], res["error"] or res["text"][:200], 0, "Check slug e.g. eng.1")
        return []
    fixtures = []
    for ev in res["json"].get("events", []):
        try:
            comp = ev.get("competitions", [{}])[0]
            m = {c.get("homeAway"): c.get("team", {}).get("displayName") for c in comp.get("competitors", [])}
            if m.get("home") and m.get("away"):
                fixtures.append({"home": m["home"], "away": m["away"], "date": ev.get("date"), "status": "SCHEDULED", "source": "【entity-ESPN¦canonical_name=ESPN】"})
        except Exception:
            continue
    _log(diags, "ESPN", url, 200, "", len(fixtures), f"dates={dates}")
    return fixtures

def _fetch_fd(entry, diags):
    code = entry.get("football_data_code")
    key = _clean(get_api_keys().get("FOOTBALL_DATA_KEY", ""))
    if not code:
        _log(diags, "Football-Data.org", "-", 0, "No football_data_code", 0, "Skipped")
        return []
    if not key:
        _log(diags, "Football-Data.org", "-", 0, "FOOTBALL_DATA_KEY missing", 0, "Add to Secrets")
        return []
    ok, _, _ = can_call_provider("Football-Data.org")
    if not ok:
        _log(diags, "Football-Data.org", "-", 429, "Quota reached", 0, "")
        return []
    for season in _seasons():
        url = f"https://api.football-data.org/v4/competitions/{code}/matches"
        res = _http_get(url, headers={**HEADERS, "X-Auth-Token": key}, params={"status": "SCHEDULED", "season": season, "limit": 100})
        record_provider_call("Football-Data.org")
        if res["status"] == 403:
            _log(diags, "Football-Data.org", url, 403, "Free tier does not cover this league", 0, "Use ESPN")
            return []
        if res["status"] == 200 and res["json"]:
            fx = [{"home": m.get("homeTeam", {}).get("name"), "away": m.get("awayTeam", {}).get("name"), "date": m.get("utcDate"), "status": "SCHEDULED", "source": "Football-Data.org"} for m in res["json"].get("matches", [])]
            if fx:
                _log(diags, "Football-Data.org", url, 200, "", len(fx), f"season={season}")
                return fx
    _log(diags, "Football-Data.org", f".../{code}/matches", 200, "No SCHEDULED matches", 0, "Tried 2026 and 2025")
    return []

def _fetch_apif(entry, diags):
    lid = entry.get("api_football_id")
    key = _clean(get_api_keys().get("API_FOOTBALL_KEY", ""))
    if not lid:
        _log(diags, "API-Football", "-", 0, "No api_football_id", 0, "Skipped")
        return []
    if not key:
        _log(diags, "API-Football", "-", 0, "API_FOOTBALL_KEY missing", 0, "Skipped")
        return []
    for season in _seasons():
        url = "https://v3.football.api-sports.io/fixtures"
        res = _http_get(url, headers={**HEADERS, "x-apisports-key": key}, params={"league": lid, "season": season, "status": "NS", "next": 50})
        record_provider_call("API-Football")
        if res["status"] == 200 and res["json"]:
            resp = res["json"].get("response", [])
            fx = [{"home": x.get("teams", {}).get("home", {}).get("name"), "away": x.get("teams", {}).get("away", {}).get("name"), "date": x.get("fixture", {}).get("date"), "status": "NS", "source": "API-Football"} for x in resp]
            if fx:
                _log(diags, "API-Football", url, 200, "", len(fx), f"league={lid} season={season}")
                return fx
        else:
            _log(diags, "API-Football", url, res["status"], res["error"] or str(res["json"])[:200], 0, f"season={season}")
    return []

def _fetch_tsdb(entry, diags):
    tid = entry.get("thesportsdb_id")
    if not tid:
        _log(diags, "TheSportsDB", "-", 0, "No thesportsdb_id", 0, "Skipped")
        return []
    key = _clean(get_api_keys().get("THESPORTSDB_KEY", "")) or "3"
    url = f"https://www.thesportsdb.com/api/v1/json/{key}/eventsnextleague.php"
    res = _http_get(url, params={"id": tid})
    if res["status"] != 200 or not res["json"]:
        _log(diags, "TheSportsDB", url, res["status"], res["error"] or "Empty JSON", 0, "Test key 3 is rate limited")
        return []
    events = res["json"].get("events", []) or []
    fx = [{"home": e.get("strHomeTeam"), "away": e.get("strAwayTeam"), "date": f"{e.get('dateEvent')}T{e.get('strTime') or '00:00:00'}", "status": "NS", "source": "TheSportsDB"} for e in events if e.get("strHomeTeam")]
    _log(diags, "TheSportsDB", url, 200, "", len(fx), f"id={tid}")
    return fx

def _fetch_fdcuk(entry, diags):
    code = entry.get("fdcuk_code")
    if not code:
        return []
    for season in _seasons():
        s = _fdcuk_str(season)
        url = f"https://www.football-data.co.uk/mmz4281/{s}/{code}.csv"
        res = _http_get(url, timeout=10)
        if res["status"] == 200 and "Date" in res["text"]:
            rows = list(csv.DictReader(io.StringIO(res["text"])))
            _log(diags, "Football-Data.co.uk", url, 200, "", len(rows), f"Historical season={s}")
            return rows
    _log(diags, "Football-Data.co.uk", f".../{code}.csv", 404, "CSV not found", 0, "Only top leagues have CSVs")
    return []

def get_league_bundle(league_key, league_entry=None):
    entry = league_entry or LEAGUE_REGISTRY.get(league_key, {}) or {}
    cache_key = f"bundle:{league_key}"
    cached = get_cached_data(cache_key)
    if cached and cached.get("fixtures"):
        return cached
    diags = []
    all_fx = []
    sources = []
    hist = []
    for fn, name in [(_fetch_espn, "ESPN"), (_fetch_fd, "Football-Data.org"), (_fetch_apif, "API-Football"), (_fetch_tsdb, "TheSportsDB")]:
        try:
            got = fn(entry, diags)
            if got:
                all_fx.extend(got)
                sources.append(name)
        except Exception as e:
            _log(diags, name, "-", 0, f"Python error: {e}", 0, "")
    try:
        hist = _fetch_fdcuk(entry, diags)
    except Exception as e:
        _log(diags, "Football-Data.co.uk", "-", 0, str(e), 0, "")
    seen = set()
    fixtures = []
    for f in all_fx:
        k = (str(f.get("home", "")).lower(), str(f.get("away", "")).lower(), str(f.get("date", ""))[:10])
        if k not in seen:
            seen.add(k)
            fixtures.append(f)
    has_live = len(fixtures) > 0
    conf = 90 if len(sources) >= 2 else 75 if len(sources) == 1 else 40 if hist else 15
    out = {"league": league_key, "league_name": entry.get("name", league_key), "fixtures": fixtures, "historical": hist, "sources_used": sources, "active_sources": sources if sources else ["Baseline League Model"], "diagnostics": diags, "data_confidence_pct": conf, "has_live_data": has_live}
    if has_live:
        set_cached_data(cache_key, out, ttl_seconds=1800)
    return out
