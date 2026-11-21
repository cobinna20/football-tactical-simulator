# news_injury_engine.py - RSS scan plus safe fallback
try:
    import feedparser
except Exception:
    feedparser = None
from league_registry import RSS_INJURY_FEEDS

def _scan_team(team):
    hits = []
    if not feedparser or not team:
        return hits
    for feed_url in RSS_INJURY_FEEDS:
        try:
            f = feedparser.parse(feed_url)
            for e in f.entries[:20]:
                title = (e.get("title", "") + " " + e.get("summary", ""))[:400]
                if team.split()[-1].lower() in title.lower() and any(w in title.lower() for w in ["injury", "injured", "out", "doubt", "sidelined", "miss"]):
                    hits.append({"title": e.get("title", ""), "link": e.get("link", ""), "summary": title[:200]})
        except Exception:
            continue
    return hits[:5]

def get_injury_report(home_team, away_team):
    def build(team):
        news = _scan_team(team)
        penalty = min(0.18, len(news) * 0.04)
        injured = []
        for n in news:
            injured.append({"player": "Reported in news", "detail": n["title"][:80], "status": "Doubtful"})
        return {"team": team, "injured": injured, "penalty": penalty, "news": news}
    h = build(home_team)
    a = build(away_team)
    return {"home": h, "away": a, "home_penalty": h["penalty"], "away_penalty": a["penalty"]}
