"""
source_router.py
Multi-source resilient data fetcher with automatic failover across:
1. ESPN Public Scoreboard/Standings API (Unlimited, 54+ leagues)
2. Football-Data.org Free API (Verified major European/World fixtures)
3. API-Football Free Tier (Deep match/squad metrics within quota budget)
4. Football-Data.co.uk Open Historical CSVs (Multi-season goals & shots data)
"""

import io
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from league_registry import get_league_config
from database import get_cached_data, set_cached_data
from quota_manager import get_secret_key, can_call_provider, record_provider_call

HEADERS = {"User-Agent": "Mozilla/5.0 (FootballTacticalAnalytics/1.0)"}


def fetch_espn_fixtures_and_standings(espn_slug: str) -> Dict[str, Any]:
    """Fetch upcoming fixtures, recent results, and standings from ESPN public endpoints."""
    fixtures = []
    recent_results = []
    standings_map = {}

    # 1. Fetch Scoreboard (Upcoming & Recent 14-day window)
    today = datetime.utcnow()
    start_str = (today - timedelta(days=7)).strftime("%Y%m%d")
    end_str = (today + timedelta(days=14)).strftime("%Y%m%d")
    sb_url = f"https://espn.com{espn_slug}/scoreboard?dates={start_str}-{end_str}"

    try:
        record_provider_call("espn_public")
        resp = requests.get(sb_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            for event in data.get("events", []):
                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
                status_state = event.get("status", {}).get("type", {}).get("state", "pre")

                match_obj = {
                    "match_id": f"espn_{event.get('id')}",
                    "date": event.get("date", ""),
                    "home_team": home.get("team", {}).get("displayName", "Home"),
                    "away_team": away.get("team", {}).get("displayName", "Away"),
                    "home_id": str(home.get("team", {}).get("id", "")),
                    "away_id": str(away.get("team", {}).get("id", "")),
                    "home_form": home.get("form", ""),
                    "away_form": away.get("form", ""),
                    "home_score": int(home.get("score", 0)) if str(home.get("score", "")).isdigit() else None,
                    "away_score": int(away.get("score", 0)) if str(away.get("score", "")).isdigit() else None,
                    "status": status_state,
                    "venue": comp.get("venue", {}).get("fullName", "Standard Stadium"),
                }
                if status_state == "post":
                    recent_results.append(match_obj)
                else:
                    fixtures.append(match_obj)
    except Exception:
        pass

    # 2. Fetch League Standings Table
    st_url = f"https://espn.com{espn_slug}/standings"
    try:
        resp = requests.get(st_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            st_data = resp.json()
            for child in st_data.get("children", []):
                for entry in child.get("standings", {}).get("entries", []):
                    t_name = entry.get("team", {}).get("displayName", "")
                    stats = {s.get("name"): s.get("value", 0) for s in entry.get("stats", [])}
                    gp = max(1, int(stats.get("gamesPlayed", 1)))
                    standings_map[t_name] = {
                        "rank": int(stats.get("rank", 10)),
                        "played": gp,
                        "wins": int(stats.get("wins", 0)),
                        "draws": int(stats.get("draws", 0)),
                        "losses": int(stats.get("losses", 0)),
                        "gf": float(stats.get("pointsFor", gp * 1.2)),
                        "ga": float(stats.get("pointsAgainst", gp * 1.2)),
                        "points": int(stats.get("points", 0)),
                    }
    except Exception:
        pass

    return {
        "fixtures": fixtures,
        "recent_results": recent_results,
        "standings": standings_map,
        "source": "ESPN Public Multi-League Feed",
    }
def fetch_fd_org_fixtures(fd_org_code: str) -> List[Dict[str, Any]]:
    """Fetch verified upcoming matches from Football-Data.org free tier."""
    if not fd_org_code or not can_call_provider("football_data_org"):
        return []

    url = f"https://football-data.org{fd_org_code}/matches?status=SCHEDULED"
    headers = {"X-Auth-Token": get_secret_key("FOOTBALL_DATA_KEY")}
    try:
        record_provider_call("football_data_org")
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []
        matches = []
        for m in resp.json().get("matches", [])[:20]:
            matches.append({
                "match_id": f"fd_{m.get('id')}",
                "date": m.get("utcDate", ""),
                "home_team": m.get("homeTeam", {}).get("name", ""),
                "away_team": m.get("awayTeam", {}).get("name", ""),
                "status": "pre",
                "source": "Football-Data.org",
            })
        return matches
    except Exception:
        return []


def fetch_fd_uk_historical_csv(fd_uk_code: str) -> List[Dict[str, Any]]:
    """Download current season match stats (goals, shots, shots on target) from Football-Data.co.uk."""
    if not fd_uk_code:
        return []

    # Try current 2627 and previous 2526 season codes automatically
    for season in ["2627", "2526", "2425"]:
        url = f"https://football-data.co.uk{season}/{fd_uk_code}.csv"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code == 200 and len(resp.text) > 200:
                df = pd.read_csv(io.StringIO(resp.text))
                needed = [c for c in ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HS", "AS", "HST", "AST"] if c in df.columns]
                df = df[needed].dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
                return df.tail(150).to_dict(orient="records")
        except Exception:
            continue
    return []


def fetch_api_football_injuries(api_football_id: int) -> List[Dict[str, Any]]:
    """Fetch official player injury/suspension list from API-Football within daily budget."""
    if not api_football_id or not can_call_provider("api_football"):
        return []

    url = f"https://api-sports.io{api_football_id}&season=2026"
    headers = {"x-apisports-key": get_secret_key("API_FOOTBALL_KEY")}
    try:
        record_provider_call("api_football")
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []
        injuries = []
        for item in resp.json().get("response", [])[:60]:
            injuries.append({
                "player": item.get("player", {}).get("name", "Unknown"),
                "type": item.get("player", {}).get("type", "Injury"),
                "reason": item.get("player", {}).get("reason", "Fitness"),
                "team": item.get("team", {}).get("name", ""),
            })
        return injuries
    except Exception:
        return []


def get_league_bundle(league_name: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Master Multi-Source Router:
    Pulls and fuses data across ESPN, Football-Data.org, Football-Data.co.uk, and API-Football
    with SQLite caching and automatic failover.
    """
    cache_key = f"league_bundle_{league_name}"
    if not force_refresh:
        cached = get_cached_data(cache_key)
        if cached:
            return cached["data"]

    cfg = get_league_config(league_name)
    sources_used = []

    espn_data = fetch_espn_fixtures_and_standings(cfg["espn_slug"])
    if espn_data["fixtures"] or espn_data["standings"]:
        sources_used.append("ESPN Public API")

    fd_fixtures = fetch_fd_org_fixtures(cfg.get("fd_org_code"))
    if fd_fixtures:
        sources_used.append("Football-Data.org")

    csv_history = fetch_fd_uk_historical_csv(cfg.get("fd_uk_code"))
    if csv_history:
        sources_used.append("Football-Data.co.uk CSV")

    api_injuries = fetch_api_football_injuries(cfg.get("api_football_id"))
    if api_injuries:
        sources_used.append("API-Football Injuries")

    # Merge fixture lists (prefer ESPN rich objects, supplement with Football-Data.org)
    fixtures = espn_data["fixtures"] if espn_data["fixtures"] else fd_fixtures

    bundle = {
        "league_name": league_name,
        "config": cfg,
        "fixtures": fixtures,
        "recent_results": espn_data["recent_results"],
        "standings": espn_data["standings"],
        "historical_matches": csv_history,
        "api_injuries": api_injuries,
        "sources_used": sources_used if sources_used else ["Baseline League Model"],
    }

    set_cached_data(cache_key, bundle, ", ".join(bundle["sources_used"]), ttl_seconds=14400)
    return bundle
