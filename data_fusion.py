# data_fusion.py - unify names, compute rates, confidence
try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

def normalize_team_name(name):
    if not name:
        return ""
    n = str(name).lower().strip()
    repl = {"【entity-manchester united¦canonical_name=manchester united】": "man utd", "【entity-manchester city¦canonical_name=manchester city】": "man city", "【entity-tottenham hotspur¦canonical_name=tottenham hotspur】": "tottenham", "【entity-newcastle united¦canonical_name=newcastle united】": "newcastle", "【entity-west ham united¦canonical_name=west ham united】": "west ham", "【entity-brighton and hove albion¦canonical_name=Brighton & Hove Albion】": "brighton"}
    return repl.get(n, n)

def similarity(a, b):
    if fuzz:
        return fuzz.ratio(normalize_team_name(a), normalize_team_name(b))
    return 100 if normalize_team_name(a) == normalize_team_name(b) else 0

def fuse_data(bundle, home_team, away_team):
    fixtures = bundle.get("fixtures", []) if bundle else []
    hist = bundle.get("historical", []) if bundle else []
    home_goals = 1.45
    away_goals = 1.15
    if hist:
        try:
            hg = [float(r.get("FTHG", 0)) for r in hist if r.get("FTHG")]
            ag = [float(r.get("FTAG", 0)) for r in hist if r.get("FTAG")]
            if hg and ag:
                home_goals = sum(hg) / len(hg)
                away_goals = sum(ag) / len(ag)
        except Exception:
            pass
    h2h = {"home_wins": 0, "draws": 0, "away_wins": 0, "matches": 0}
    if hist:
        for r in hist[-50:]:
            ht, at = r.get("HomeTeam", ""), r.get("AwayTeam", "")
            if similarity(ht, home_team) > 85 and similarity(at, away_team) > 85:
                h2h["matches"] += 1
                try:
                    hg, ag = int(r["FTHG"]), int(r["FTAG"])
                    if hg > ag: h2h["home_wins"] += 1
                    elif hg < ag: h2h["away_wins"] += 1
                    else: h2h["draws"] += 1
                except Exception:
                    pass
    return {"home_goals_rate": round(home_goals, 2), "away_goals_rate": round(away_goals, 2), "h2h": h2h, "fixtures_found": len(fixtures), "confidence": bundle.get("data_confidence_pct", 15) if bundle else 15}
