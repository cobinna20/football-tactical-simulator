"""
simulator_engine.py
1. 10,000-run Dixon-Coles calibrated Monte Carlo probability engine.
2. Minute-by-minute (1' to 90'+) tactical match simulator featuring real player
   names, dynamic 70th-minute game-state shifts, momentum tracking, and events.
"""

import numpy as np
from collections import Counter
from typing import Dict, List, Any


def run_monte_carlo_simulation(
    lambda_home: float,
    lambda_away: float,
    upset_volatility: float = 0.22,
    n_sims: int = 10000,
) -> Dict[str, Any]:
    """
    Simulate the match 10,000 times using Gamma-Poisson (Negative Binomial) variance
    adjusted by team consistency and Dixon-Coles low-score draw calibration.
    """
    rng = np.random.default_rng(seed=42)

    # Gamma noise models match-to-match performance variance driven by squad consistency
    shape = max(2.5, 1.0 / max(0.05, upset_volatility ** 2))
    h_rates = rng.gamma(shape, lambda_home / shape, size=n_sims)
    a_rates = rng.gamma(shape, lambda_away / shape, size=n_sims)

    home_goals = rng.poisson(h_rates)
    away_goals = rng.poisson(a_rates)

    # Apply Dixon-Coles correlation boost for tight 0-0 and 1-1 low-scoring draws
    rho = 0.08
    for i in range(n_sims):
        if home_goals[i] == 1 and away_goals[i] == 0 and rng.random() < rho:
            away_goals[i] = 1
        elif home_goals[i] == 0 and away_goals[i] == 1 and rng.random() < rho:
            home_goals[i] = 1

    home_wins = int(np.sum(home_goals > away_goals))
    draws = int(np.sum(home_goals == away_goals))
    away_wins = int(np.sum(home_goals < away_goals))

    prob_home = round((home_wins / n_sims) * 100, 1)
    prob_draw = round((draws / n_sims) * 100, 1)
    prob_away = round(100.0 - prob_home - prob_draw, 1)

    btts_yes = round(float(np.mean((home_goals > 0) & (away_goals > 0))) * 100, 1)
    over_25 = round(float(np.mean((home_goals + away_goals) >= 3)) * 100, 1)

    score_counts = Counter(zip(home_goals.tolist(), away_goals.tolist()))
    top_scores = [
        {
            "score": f"{hg}-{ag}",
            "probability": round((cnt / n_sims) * 100, 1),
            "home_goals": hg,
            "away_goals": ag,
        }
        for (hg, ag), cnt in score_counts.most_common(5)
    ]

    return {
        "simulations_run": n_sims,
        "prob_home": prob_home,
        "prob_draw": prob_draw,
        "prob_away": prob_away,
        "btts_prob": btts_yes,
        "over_25_prob": over_25,
        "expected_home_goals": round(float(np.mean(home_goals)), 2),
        "expected_away_goals": round(float(np.mean(away_goals)), 2),
        "top_scorelines": top_scores,
    }
def simulate_live_match_timeline(
    home_name: str,
    away_name: str,
    context_lambdas: Dict[str, Any],
    mc_results: Dict[str, Any],
    home_squad: Dict[str, Any],
    away_squad: Dict[str, Any],
    seed_offset: int = 0,
) -> Dict[str, Any]:
    """
    Play out a realistic 90-minute match simulation weighted by real probabilities,
    producing minute-by-minute commentary, shots, momentum shifts, and final score.
    """
    rng = np.random.default_rng(seed=None if seed_offset == 0 else seed_offset)

    # Anchor featured simulation toward realistic top-probability distribution
    top_scores = mc_results["top_scorelines"]
    weights = np.array([s["probability"] for s in top_scores], dtype=float)
    weights = weights / weights.sum()
    chosen_idx = rng.choice(len(top_scores), p=weights)
    target_hg = top_scores[chosen_idx]["home_goals"]
    target_ag = top_scores[chosen_idx]["away_goals"]

    # Distribute target goals across realistic match minutes (heavier in 2nd half)
    minute_weights = np.array([0.85 if m <= 45 else 1.15 for m in range(1, 91)], dtype=float)
    minute_weights /= minute_weights.sum()

    h_goal_mins = sorted(rng.choice(range(1, 91), size=target_hg, replace=False, p=minute_weights).tolist()) if target_hg > 0 else []
    avail_mins = [m for m in range(1, 91) if m not in h_goal_mins]
    avail_w = np.array([0.85 if m <= 45 else 1.15 for m in avail_mins], dtype=float)
    avail_w /= avail_w.sum()
    a_goal_mins = sorted(rng.choice(avail_mins, size=target_ag, replace=False, p=avail_w).tolist()) if target_ag > 0 else []

    h_scorers = [p["name"] for p in home_squad["starting_xi"] if p["position"] in ("FWD", "MID")] or [home_name]
    a_scorers = [p["name"] for p in away_squad["starting_xi"] if p["position"] in ("FWD", "MID")] or [away_name]

    events: List[Dict[str, Any]] = []
    momentum_timeline: List[Dict[str, Any]] = []
    cur_hg, cur_ag = 0, 0
    h_shots, a_shots = 0, 0
    h_sot, a_sot = 0, 0

    base_h_share = home_squad["midfield_rating"] / max(1.0, (home_squad["midfield_rating"] + away_squad["midfield_rating"]))
    possession_h = int(np.clip(round(base_h_share * 100), 34, 68))
    possession_a = 100 - possession_h

    events.append({
        "minute": 1,
        "type": "kickoff",
        "team": "Match",
        "text": f"1' Kick-off! {home_name} vs {away_name} gets underway ({context_lambdas['tactical_style']}).",
    })

    for minute in range(1, 91):
        # Dynamic 70th-minute game-state tactical push if one team trails by 1 goal
        trailing_push_h = 1.25 if (minute >= 70 and cur_hg < cur_ag) else 1.0
        trailing_push_a = 1.25 if (minute >= 70 and cur_ag < cur_hg) else 1.0

        momentum_val = round(((possession_h - 50) * 0.6) + ((cur_hg - cur_ag) * 12.0) + rng.normal(0, 6), 1)
        if minute % 5 == 0 or minute in h_goal_mins or minute in a_goal_mins:
            momentum_timeline.append({"minute": minute, "momentum": float(np.clip(momentum_val, -50, 50))})

        if minute in h_goal_mins:
            cur_hg += 1
            h_shots += 1
            h_sot += 1
            scorer = rng.choice(h_scorers[:4])
            events.append({
                "minute": minute,
                "type": "goal",
                "team": home_name,
                "text": f"⚽ {minute}' GOAL! {scorer} finishes clinically for {home_name}! ({home_name} {cur_hg} - {cur_ag} {away_name})",
            })
        elif minute in a_goal_mins:
            cur_ag += 1
            a_shots += 1
            a_sot += 1
            scorer = rng.choice(a_scorers[:4])
            events.append({
                "minute": minute,
                "type": "goal",
                "team": away_name,
                "text": f"⚽ {minute}' GOAL! {scorer} strikes for {away_name}! ({home_name} {cur_hg} - {cur_ag} {away_name})",
            })
        else:
            # Generate realistic shots, saves, and tactical moments
            shot_chance_h = (context_lambdas["lambda_home"] / 11.5) * trailing_push_h
            shot_chance_a = (context_lambdas["lambda_away"] / 11.5) * trailing_push_a

            if rng.random() < shot_chance_h:
                h_shots += 1
                shooter = rng.choice(h_scorers[:5])
                if rng.random() < 0.36:
                    h_sot += 1
                    events.append({
                        "minute": minute,
                        "type": "chance",
                        "team": home_name,
                        "text": f"🧤 {minute}' Big chance! {shooter} ({home_name}) forces a sharp save on target.",
                    })
            elif rng.random() < shot_chance_a:
                a_shots += 1
                shooter = rng.choice(a_scorers[:5])
                if rng.random() < 0.36:
                    a_sot += 1
                    events.append({
                        "minute": minute,
                        "type": "chance",
                        "team": away_name,
                        "text": f"🧤 {minute}' Danger! {shooter} ({away_name}) tests the goalkeeper from inside the box.",
                    })
            elif minute == 45:
                events.append({
                    "minute": 45,
                    "type": "halftime",
                    "team": "Match",
                    "text": f"⏱️ 45' Half-Time Whistle: {home_name} {cur_hg} - {cur_ag} {away_name}.",
                })
            elif minute == 72 and cur_hg != cur_ag:
                chasing = home_name if cur_hg < cur_ag else away_name
                events.append({
                    "minute": 72,
                    "type": "tactical",
                    "team": chasing,
                    "text": f"🔄 72' Tactical Shift: {chasing} commits extra attackers forward in search of an equalizer.",
                })

    events.append({
        "minute": 90,
        "type": "fulltime",
        "team": "Match",
        "text": f"🏁 90'+ Full-Time: {home_name} {cur_hg} - {cur_ag} {away_name}.",
    })

    return {
        "final_home_goals": cur_hg,
        "final_away_goals": cur_ag,
        "scoreline": f"{cur_hg}-{cur_ag}",
        "events": events,
        "momentum_timeline": momentum_timeline,
        "match_stats": {
            "possession_home": possession_h,
            "possession_away": possession_a,
            "shots_home": max(h_shots, cur_hg + 2),
            "shots_away": max(a_shots, cur_ag + 2),
            "sot_home": max(h_sot, cur_hg),
            "sot_away": max(a_sot, cur_ag),
            "xg_home": round(context_lambdas["lambda_home"] * rng.uniform(0.88, 1.14), 2),
            "xg_away": round(context_lambdas["lambda_away"] * rng.uniform(0.88, 1.14), 2),
        },
    }
