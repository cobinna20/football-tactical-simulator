"""
data_fusion.py
Cross-source consensus & normalization engine.
Unifies team names across multiple free providers using rapidfuzz, extracts
home/away splits, shot efficiency, H2H history, and computes Data Confidence %.
"""

from typing import Dict, List, Any, Optional
from rapidfuzz import fuzz, process
from news_injury_engine import compile_team_injury_report


def match_team_name(target: str, candidates: List[str], threshold: int = 72) -> Optional[str]:
    """Fuzzy match team name across different APIs (e.g. 'Man City' vs 'Manchester City')."""
    if not target or not candidates:
        return None
    if target in candidates:
        return target
    result = process.extractOne(target, candidates, scorer=fuzz.token_sort_ratio)
    if result and result[1] >= threshold:
        return result[0]
    return None


def extract_team_csv_metrics(team_name: str, historical_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute home/away goal & shot metrics from Football-Data.co.uk historical CSV rows."""
    if not historical_matches:
        return {"found": False}

    all_teams = list({m["HomeTeam"] for m in historical_matches} | {m["AwayTeam"] for m in historical_matches})
    matched = match_team_name(team_name, all_teams)
    if not matched:
        return {"found": False}

    home_games = [m for m in historical_matches if m["HomeTeam"] == matched]
    away_games = [m for m in historical_matches if m["AwayTeam"] == matched]
    all_games = home_games + away_games

    if not all_games:
        return {"found": False}

    home_gf = sum(float(m["FTHG"]) for m in home_games) / max(1, len(home_games))
    home_ga = sum(float(m["FTAG"]) for m in home_games) / max(1, len(home_games))
    away_gf = sum(float(m["FTAG"]) for m in away_games) / max(1, len(away_games))
    away_ga = sum(float(m["FTHG"]) for m in away_games) / max(1, len(away_games))

    # Shots & Shots on Target for xG proxy when advanced xG is unavailable
    shots_for, shots_against, sot_for = [], [], []
    for m in home_games:
        if "HS" in m and m["HS"] == m["HS"]:
            shots_for.append(float(m["HS"]))
            shots_against.append(float(m.get("AS", 10)))
        if "HST" in m and m["HST"] == m["HST"]:
            sot_for.append(float(m["HST"]))

    for m in away_games:
        if "AS" in m and m["AS"] == m["AS"]:
            shots_for.append(float(m["AS"]))
            shots_against.append(float(m.get("HS", 10)))
        if "AST" in m and m["AST"] == m["AST"]:
            sot_for.append(float(m["AST"]))

    avg_shots = sum(shots_for) / len(shots_for) if shots_for else 11.5
    avg_sot = sum(sot_for) / len(sot_for) if sot_for else 4.0
    # Empirical xG proxy from shots & shots on target
    xg_proxy = round((avg_sot * 0.28) + ((avg_shots - avg_sot) * 0.04), 2)

    return {
        "found": True,
        "matched_name": matched,
        "samples": len(all_games),
        "home_gf_avg": round(home_gf, 2),
        "home_ga_avg": round(home_ga, 2),
        "away_gf_avg": round(away_gf, 2),
        "away_ga_avg": round(away_ga, 2),
        "avg_shots": round(avg_shots, 1),
        "avg_sot": round(avg_sot, 1),
        "xg_proxy": max(0.55, xg_proxy),
    }


def extract_h2h_metrics(home_team: str, away_team: str, historical_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze historical Head-to-Head encounters between the two teams."""
    if not historical_matches:
        return {"matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "h2h_edge": 0.0}

    all_teams = list({m["HomeTeam"] for m in historical_matches} | {m["AwayTeam"] for m in historical_matches})
    h_match = match_team_name(home_team, all_teams)
    a_match = match_team_name(away_team, all_teams)

    if not h_match or not a_match:
        return {"matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "h2h_edge": 0.0}

    h2h_games = [
        m for m in historical_matches
        if {m["HomeTeam"], m["AwayTeam"]} == {h_match, a_match}
    ]

    if not h2h_games:
        return {"matches": 0, "home_wins": 0, "draws": 0, "away_wins": 0, "h2h_edge": 0.0}

    hw, dr, aw = 0, 0, 0
    for g in h2h_games:
        hg, ag = float(g["FTHG"]), float(g["FTAG"])
        if g["HomeTeam"] == h_match:
            if hg > ag:
                hw += 1
            elif hg == ag:
                dr += 1
            else:
                aw += 1
        else:
            if ag > hg:
                hw += 1
            elif ag == hg:
                dr += 1
            else:
                aw += 1

    total = len(h2h_games)
    edge = round((hw - aw) / total, 3)  # Ranges from -1.0 to +1.0
    return {"matches": total, "home_wins": hw, "draws": dr, "away_wins": aw, "h2h_edge": edge}
def parse_form_string(form_str: str) -> float:
    """Convert form string like 'WWDLW' into a weighted 0-100 momentum score (recent games weighted higher)."""
    if not form_str:
        return 55.0
    weights = [1.0, 1.15, 1.3, 1.5, 1.8]
    clean = [c for c in form_str.upper() if c in ("W", "D", "L")][-5:]
    if not clean:
        return 55.0

    score_sum, weight_sum = 0.0, 0.0
    for idx, res in enumerate(clean):
        w = weights[idx] if idx < len(weights) else 1.5
        pts = 100.0 if res == "W" else (45.0 if res == "D" else 10.0)
        score_sum += pts * w
        weight_sum += w
    return round(score_sum / weight_sum, 1)


def build_match_fusion_profile(fixture: Dict[str, Any], league_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fuse all available multi-source data for a specific fixture into a unified,
    verified analytical profile with a Data Confidence Score (0-100%).
    """
    cfg = league_bundle["config"]
    standings = league_bundle.get("standings", {})
    hist_matches = league_bundle.get("historical_matches", [])
    api_injuries = league_bundle.get("api_injuries", [])

    home_name = fixture["home_team"]
    away_name = fixture["away_team"]
    avg_goals = cfg["avg_league_goals"] / 2.0

    # 1. Standings Lookup
    st_keys = list(standings.keys())
    h_st_key = match_team_name(home_name, st_keys)
    a_st_key = match_team_name(away_name, st_keys)
    h_st = standings.get(h_st_key, {"rank": 10, "played": 10, "wins": 4, "draws": 3, "losses": 3, "gf": 10 * avg_goals, "ga": 10 * avg_goals, "points": 15})
    a_st = standings.get(a_st_key, {"rank": 10, "played": 10, "wins": 4, "draws": 3, "losses": 3, "gf": 10 * avg_goals, "ga": 10 * avg_goals, "points": 15})

    # 2. CSV Historical Splits & Shot/xG Metrics
    h_csv = extract_team_csv_metrics(home_name, hist_matches)
    a_csv = extract_team_csv_metrics(away_name, hist_matches)
    h2h = extract_h2h_metrics(home_name, away_name, hist_matches)

    # 3. Blend Standings + CSV Splits for Attack/Defense Goal Rates
    h_st_gf = h_st["gf"] / max(1, h_st["played"])
    h_st_ga = h_st["ga"] / max(1, h_st["played"])
    a_st_gf = a_st["gf"] / max(1, a_st["played"])
    a_st_ga = a_st["ga"] / max(1, a_st["played"])

    if h_csv.get("found"):
        h_att_rate = round((h_st_gf * 0.45) + (h_csv["home_gf_avg"] * 0.35) + (h_csv["xg_proxy"] * 0.20), 3)
        h_def_rate = round((h_st_ga * 0.50) + (h_csv["home_ga_avg"] * 0.50), 3)
    else:
        h_att_rate = round(h_st_gf, 3)
        h_def_rate = round(h_st_ga, 3)

    if a_csv.get("found"):
        a_att_rate = round((a_st_gf * 0.45) + (a_csv["away_gf_avg"] * 0.35) + (a_csv["xg_proxy"] * 0.20), 3)
        a_def_rate = round((a_st_ga * 0.50) + (a_csv["away_ga_avg"] * 0.50), 3)
    else:
        a_att_rate = round(a_st_gf, 3)
        a_def_rate = round(a_st_ga, 3)

    # 4. Injury & News Reports
    h_inj = compile_team_injury_report(home_name, cfg["espn_slug"], fixture.get("home_id", ""), api_injuries)
    a_inj = compile_team_injury_report(away_name, cfg["espn_slug"], fixture.get("away_id", ""), api_injuries)

    # 5. Calculate Data Confidence Score (0-100%) based on how many sources verified this fixture
    confidence = 45  # Base live fixture feed
    if h_st_key and a_st_key:
        confidence += 20
    if h_csv.get("found") and a_csv.get("found"):
        confidence += 20
    if h2h["matches"] > 0:
        confidence += 5
    if fixture.get("home_form") or fixture.get("away_form"):
        confidence += 5
    if len(league_bundle.get("sources_used", [])) >= 2:
        confidence += 5

    return {
        "fixture": fixture,
        "league_config": cfg,
        "home": {
            "name": home_name,
            "standings": h_st,
            "csv_metrics": h_csv,
            "form_score": parse_form_string(fixture.get("home_form", "")),
            "form_raw": fixture.get("home_form", "N/A"),
            "attack_goal_rate": max(0.35, h_att_rate),
            "defense_concede_rate": max(0.35, h_def_rate),
            "injuries": h_inj,
        },
        "away": {
            "name": away_name,
            "standings": a_st,
            "csv_metrics": a_csv,
            "form_score": parse_form_string(fixture.get("away_form", "")),
            "form_raw": fixture.get("away_form", "N/A"),
            "attack_goal_rate": max(0.35, a_att_rate),
            "defense_concede_rate": max(0.35, a_def_rate),
            "injuries": a_inj,
        },
        "h2h": h2h,
        "data_confidence_pct": min(99, confidence),
        "sources_used": league_bundle.get("sources_used", []),
    }
