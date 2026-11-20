"""
context_modifiers.py
Applies contextual, physical, and tactical modifiers to team ratings:
- Rest days & fixture congestion fatigue decay
- Strength-of-Schedule & table rank quality adjustment
- Match importance / motivation index (title race, top 4, relegation)
- Tactical style clash matrix (Pressing, Shot Volume, Defensive Block, H2H)
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Any


def calculate_rest_days(team_name: str, fixture_date_str: str, recent_results: List[Dict[str, Any]]) -> int:
    """Calculate exact days of rest since the team's most recent completed match."""
    if not fixture_date_str or not recent_results:
        return 6  # Standard full week rest default

    try:
        target_dt = datetime.fromisoformat(fixture_date_str.replace("Z", "+00:00"))
    except Exception:
        return 6

    latest_prev = None
    for m in recent_results:
        if team_name in (m.get("home_team", ""), m.get("away_team", "")):
            try:
                m_dt = datetime.fromisoformat(m["date"].replace("Z", "+00:00"))
                if m_dt < target_dt and (latest_prev is None or m_dt > latest_prev):
                    latest_prev = m_dt
            except Exception:
                continue

    if not latest_prev:
        return 6
    days = max(2, (target_dt - latest_prev).days)
    return min(14, days)


def compute_motivation_index(standings: Dict[str, Any], total_teams: int = 20) -> Dict[str, Any]:
    """Estimate match stakes based on league rank and season progress."""
    rank = standings.get("rank", 10)
    played = standings.get("played", 10)

    if rank <= 2:
        return {"label": "Title Contender", "boost": 1.04}
    elif rank <= 5:
        return {"label": "Continental Qualification Push", "boost": 1.03}
    elif rank >= max(14, total_teams - 3) and played >= 12:
        return {"label": "Relegation Survival Fight", "boost": 1.035}
    elif played >= 28 and 8 <= rank <= 13:
        return {"label": "Mid-Table Consolidation", "boost": 0.985}
    return {"label": "Standard Competitive Stakes", "boost": 1.00}


def compute_tactical_and_contextual_lambdas(
    fusion_profile: Dict[str, Any],
    home_squad: Dict[str, Any],
    away_squad: Dict[str, Any],
    recent_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Synthesize ratings, form, H2H, fatigue, motivation, and tactical style clashes
    into calibrated Expected Goals (lambda_home, lambda_away) and variance metrics.
    """
    cfg = fusion_profile["league_config"]
    fixture = fusion_profile["fixture"]
    h_prof = fusion_profile["home"]
    a_prof = fusion_profile["away"]
    h2h = fusion_profile["h2h"]

    league_half_avg = cfg["avg_league_goals"] / 2.0

    # 1. Base Attack & Defense Ratios relative to league average
    h_att_ratio = h_prof["attack_goal_rate"] / max(0.6, league_half_avg)
    h_def_ratio = h_prof["defense_concede_rate"] / max(0.6, league_half_avg)
    a_att_ratio = a_prof["attack_goal_rate"] / max(0.6, league_half_avg)
    a_def_ratio = a_prof["defense_concede_rate"] / max(0.6, league_half_avg)

    raw_lambda_h = league_half_avg * h_att_ratio * a_def_ratio * cfg["home_adv_boost"]
    raw_lambda_a = league_half_avg * a_att_ratio * h_def_ratio

    # 2. Starting XI Quality & Injury Differential Modifier
    att_vs_def_h = (home_squad["attack_rating"] - away_squad["defense_rating"]) / 100.0
    att_vs_def_a = (away_squad["attack_rating"] - home_squad["defense_rating"]) / 100.0
    mid_control_diff = (home_squad["midfield_rating"] - away_squad["midfield_rating"]) / 150.0

    raw_lambda_h *= (1.0 + att_vs_def_h + mid_control_diff)
    raw_lambda_a *= (1.0 + att_vs_def_a - mid_control_diff)

    # 3. Rolling Momentum (Form) & H2H Psychological Edge
    form_diff = (h_prof["form_score"] - a_prof["form_score"]) / 500.0
    h2h_adj = h2h.get("h2h_edge", 0.0) * 0.06
    raw_lambda_h *= (1.0 + form_diff + h2h_adj)
    raw_lambda_a *= (1.0 - form_diff - h2h_adj)

    # 4. Rest Days & Fixture Congestion Fatigue Penalty
    h_rest = calculate_rest_days(h_prof["name"], fixture.get("date", ""), recent_results)
    a_rest = calculate_rest_days(a_prof["name"], fixture.get("date", ""), recent_results)
    h_fatigue_mult = 0.93 if h_rest <= 3 else (0.97 if h_rest == 4 else 1.0)
    a_fatigue_mult = 0.93 if a_rest <= 3 else (0.97 if a_rest == 4 else 1.0)

    # 5. Match Motivation / Stakes
    h_mot = compute_motivation_index(h_prof["standings"])
    a_mot = compute_motivation_index(a_prof["standings"])

    final_lambda_h = float(np.clip(raw_lambda_h * h_fatigue_mult * h_mot["boost"], 0.28, 4.20))
    final_lambda_a = float(np.clip(raw_lambda_a * a_fatigue_mult * a_mot["boost"], 0.22, 3.80))

    # 6. Tactical Style Clash Classification
    h_shots = h_prof["csv_metrics"].get("avg_shots", 11.5)
    a_shots = a_prof["csv_metrics"].get("avg_shots", 11.5)
    if h_shots >= 14.0 and a_shots >= 14.0:
        tactical_style = "High-Tempo Open End-to-End Battle"
    elif home_squad["midfield_rating"] - away_squad["midfield_rating"] >= 5.0:
        tactical_style = "Home Territorial Possession vs. Counter-Attack"
    elif away_squad["midfield_rating"] - home_squad["midfield_rating"] >= 5.0:
        tactical_style = "Away Ball Dominance vs. Home Low-Block Transitions"
    elif home_squad["defense_rating"] >= 80 and away_squad["defense_rating"] >= 80:
        tactical_style = "Tight Tactical Chess Match (Compact Defenses)"
    else:
        tactical_style = "Balanced Midfield Duel & Set-Piece Contest"

    # 7. Match Volatility (driven by inverse of Team Consistency ratings)
    avg_consistency = (home_squad["team_consistency"] + away_squad["team_consistency"]) / 2.0
    upset_volatility = round(float(np.clip((100.0 - avg_consistency) / 100.0, 0.12, 0.52)), 2)

    return {
        "lambda_home": round(final_lambda_h, 3),
        "lambda_away": round(final_lambda_a, 3),
        "home_rest_days": h_rest,
        "away_rest_days": a_rest,
        "home_motivation": h_mot["label"],
        "away_motivation": a_mot["label"],
        "tactical_style": tactical_style,
        "upset_volatility": upset_volatility,
    }
