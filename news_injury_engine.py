"""
news_injury_engine.py
Scans multiple free sports RSS feeds + ESPN team roster/injury endpoints
to detect player absences, suspensions, and calculate squad availability impact.
"""

import feedparser
import requests
from typing import Dict, List, Any
from rapidfuzz import fuzz
from league_registry import RSS_INJURY_FEEDS
from database import get_cached_data, set_cached_data

HEADERS = {"User-Agent": "Mozilla/5.0 (FootballTacticalAnalytics/1.0)"}

INJURY_KEYWORDS = {
    "ruled out": 1.0,
    "surgery": 1.0,
    "torn": 1.0,
    "fracture": 1.0,
    "suspended": 0.95,
    "red card": 0.95,
    "hamstring": 0.85,
    "knee": 0.85,
    "ankle": 0.80,
    "groin": 0.80,
    "muscle": 0.75,
    "injured": 0.75,
    "injury": 0.70,
    "sidelined": 0.85,
    "doubtful": 0.45,
    "fitness test": 0.40,
    "illness": 0.50,
}


def fetch_rss_injury_headlines() -> List[Dict[str, str]]:
    """Fetch and cache recent football injury/team news headlines across free RSS feeds."""
    cache_key = "global_rss_injury_news"
    cached = get_cached_data(cache_key)
    if cached:
        return cached["data"]

    articles = []
    for feed_url in RSS_INJURY_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:25]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined = f"{title} {summary}".lower()
                matched_kw = [kw for kw in INJURY_KEYWORDS if kw in combined]
                if matched_kw:
                    max_sev = max(INJURY_KEYWORDS[k] for k in matched_kw)
                    articles.append({
                        "title": title,
                        "summary": summary[:220],
                        "keywords": ", ".join(matched_kw[:3]),
                        "severity": max_sev,
                    })
        except Exception:
            continue

    set_cached_data(cache_key, articles, "Multi-Source RSS Feeds", ttl_seconds=3600)
    return articles


def fetch_espn_team_injuries(espn_slug: str, team_id: str) -> List[Dict[str, Any]]:
    """Fetch team-specific injury/roster status from ESPN public team endpoint."""
    if not team_id:
        return []
    cache_key = f"espn_inj_{espn_slug}_{team_id}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached["data"]

    url = f"https://espn.com{espn_slug}/teams/{team_id}?enable=roster"
    injuries = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            team_data = resp.json().get("team", {})
            for inj in team_data.get("injuries", []):
                athlete = inj.get("athlete", {})
                status = inj.get("status", "Out")
                injuries.append({
                    "player": athlete.get("displayName", "Squad Player"),
                    "position": athlete.get("position", {}).get("abbreviation", "MID"),
                    "status": status,
                    "reason": inj.get("details", {}).get("type", "Injury"),
                    "severity": 0.45 if "doubt" in status.lower() else 0.90,
                })
    except Exception:
        pass

    set_cached_data(cache_key, injuries, "ESPN Roster/Injury Endpoint", ttl_seconds=3600)
    return injuries


def compile_team_injury_report(
    team_name: str,
    espn_slug: str,
    team_id: str,
    api_injuries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Combine ESPN injuries, API-Football injuries, and RSS news alerts for a team
    into an actionable squad availability report and strength penalty multiplier.
    """
    report_items = []
    seen_players = set()

    # 1. ESPN Structured Injuries
    for item in fetch_espn_team_injuries(espn_slug, team_id):
        p_key = item["player"].lower()
        if p_key not in seen_players:
            seen_players.add(p_key)
            report_items.append(item)

    # 2. API-Football Injuries (fuzzy match team name)
    for item in api_injuries:
        if fuzz.partial_ratio(team_name.lower(), item.get("team", "").lower()) >= 80:
            p_key = item["player"].lower()
            if p_key not in seen_players:
                seen_players.add(p_key)
                report_items.append({
                    "player": item["player"],
                    "position": "OUTFIELD",
                    "status": item.get("type", "Out"),
                    "reason": item.get("reason", "Injury"),
                    "severity": 0.85,
                })

    # 3. RSS Live News Mentions
    news_alerts = []
    short_name = team_name.replace("FC", "").replace("CF", "").strip().lower()
    for art in fetch_rss_injury_headlines():
        if len(short_name) >= 4 and short_name in art["title"].lower():
            news_alerts.append(art)

    # Calculate cumulative squad impact penalty (capped at 18% max reduction)
    structured_penalty = sum(i["severity"] * 0.025 for i in report_items)
    news_penalty = sum(n["severity"] * 0.015 for n in news_alerts[:3])
    total_penalty = min(0.18, round(structured_penalty + news_penalty, 4))

    return {
        "team": team_name,
        "absences": report_items,
        "news_alerts": news_alerts[:4],
        "absence_count": len(report_items),
        "strength_multiplier": round(1.0 - total_penalty, 4),
        "penalty_pct": round(total_penalty * 100, 1),
    }
