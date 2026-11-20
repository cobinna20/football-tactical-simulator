"""
rating_engine.py
Calculates individual Player Ability (0-100), Player Consistency Index (0-100),
and aggregates available Starting XI ratings (Attack, Midfield, Defense, Cohesion)
after adjusting for injuries and suspensions.
"""

import requests
import numpy as np
from typing import Dict, List, Any
from rapidfuzz import fuzz
from database import get_cached_data, set_cached_data

HEADERS = {"User-Agent": "Mozilla/5.0 (FootballTacticalAnalytics/1.0)"}


def fetch_team_roster_players(espn_slug: str, team_id: str) -> List[Dict[str, Any]]:
    """Fetch real squad roster and available stats from ESPN public roster endpoint."""
    if not team_id:
        return []
    cache_key = f"roster_players_{espn_slug}_{team_id}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached["data"]

    url = f"https://espn.com{espn_slug}/teams/{team_id}/roster"
    players = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            athletes = resp.json().get("athletes", [])
            for p in athletes:
                pos = p.get("position", {}).get("abbreviation", "MID")
                if pos in ("G", "GK"):
                    norm_pos = "GK"
                elif pos in ("D", "DF", "CB", "LB", "RB", "WB"):
                    norm_pos = "DEF"
                elif pos in ("F", "FW", "ST", "CF", "LW", "RW"):
                    norm_pos = "FWD"
                else:
                    norm_pos = "MID"

                # Extract available season stats from ESPN athlete categories
                stat_map = {}
                for cat in p.get("statistics", {}).get("splits", {}).get("categories", []):
                    for st in cat.get("stats", []):
                        stat_map[st.get("name", "")] = float(st.get("value", 0) or 0)

                players.append({
                    "id": str(p.get("id", "")),
                    "name": p.get("displayName", "Player"),
                    "position": norm_pos,
                    "age": int(p.get("age", 25) or 25),
                    "appearances": int(stat_map.get("appearances", 0)),
                    "goals": float(stat_map.get("totalGoals", stat_map.get("goals", 0))),
                    "assists": float(stat_map.get("goalAssists", stat_map.get("assists", 0))),
                    "shots": float(stat_map.get("totalShots", 0)),
                    "saves": float(stat_map.get("saves", 0)),
                    "yellow_cards": float(stat_map.get("yellowCards", 0)),
                })
    except Exception:
        pass

    set_cached_data(cache_key, players, "ESPN Squad Roster", ttl_seconds=43200)
    return players


def score_individual_player(player: Dict[str, Any], team_baseline_rating: float) -> Dict[str, Any]:
    """
    Compute Player Ability (0-100) and Player Consistency Index (0-100)
    from per-appearance output, experience, and discipline variance.
    """
    apps = max(0, player.get("appearances", 0))
    pos = player.get("position", "MID")
    age = player.get("age", 25)

    # Base ability anchored to team tier, adjusted by real output per appearance
    ability = team_baseline_rating - 3.0
    if apps > 0:
        g_per_app = player.get("goals", 0) / apps
        a_per_app = player.get("assists", 0) / apps
        s_per_app = player.get("shots", 0) / apps

        if pos == "FWD":
            ability += (g_per_app * 22.0) + (a_per_app * 14.0) + (s_per_app * 1.2)
        elif pos == "MID":
            ability += (g_per_app * 18.0) + (a_per_app * 18.0) + (min(apps, 25) * 0.25)
        elif pos == "DEF":
            ability += (min(apps, 25) * 0.35) + (g_per_app * 15.0) - (player.get("yellow_cards", 0) / apps * 4.0)
        elif pos == "GK":
            saves_per_app = player.get("saves", 0) / apps
            ability += (min(apps, 25) * 0.35) + (saves_per_app * 1.5)

        # Regular starter bonus
        if apps >= 10:
            ability += 2.5

    ability = float(np.clip(ability, 52.0, 96.0))

    # Consistency Index (0-100): Driven by match sample reliability, prime age stability, and card volatility
    prime_age_bonus = 6.0 if 24 <= age <= 31 else (2.0 if 21 <= age <= 33 else -2.5)
    sample_stability = min(14.0, apps * 0.65)
    card_volatility = (player.get("yellow_cards", 0) / max(1, apps)) * 12.0 if apps > 0 else 2.0

    consistency = 62.0 + prime_age_bonus + sample_stability - card_volatility
    consistency = float(np.clip(consistency, 48.0, 96.0))

    return {
        "name": player["name"],
        "position": pos,
        "appearances": apps,
        "ability": round(ability, 1),
        "consistency": round(consistency, 1),
        "composite": round((ability * 0.7) + (consistency * 0.3), 1),
    }
def evaluate_squad_ratings(
    team_profile: Dict[str, Any],
    league_config: Dict[str, Any],
    team_id: str,
) -> Dict[str, Any]:
    """
    Build the strongest available Starting XI (filtering out injured/suspended players)
    and calculate Attack, Midfield, Defense, Overall, and Squad Consistency ratings.
    """
    st = team_profile["standings"]
    played = max(1, st.get("played", 10))
    ppg = st.get("points", 15) / played
    tier_base = 76.0 if league_config["tier"] == 1 else (69.0 if league_config["tier"] == 2 else 63.0)
    team_baseline = float(np.clip(tier_base + ((ppg - 1.35) * 7.5), 56.0, 92.0))

    raw_players = fetch_team_roster_players(league_config["espn_slug"], team_id)
    injured_names = [i["player"].lower() for i in team_profile["injuries"].get("absences", [])]

    available_players = []
    sidelined_rated = []

    for p in raw_players:
        scored = score_individual_player(p, team_baseline)
        is_out = any(fuzz.partial_ratio(scored["name"].lower(), inj) >= 85 for inj in injured_names)
        if is_out:
            sidelined_rated.append(scored)
        else:
            available_players.append(scored)

    # Fallback synthetic squad if external endpoint returned empty roster for lower-tier league
    if len(available_players) < 11:
        positions = ["GK"] + ["DEF"] * 4 + ["MID"] * 3 + ["FWD"] * 3
        for idx, pos in enumerate(positions):
            available_players.append({
                "name": f"{team_profile['name']} {pos} #{idx+1}",
                "position": pos,
                "appearances": 12,
                "ability": round(team_baseline + np.random.uniform(-2.0, 2.5), 1),
                "consistency": round(68.0 + ((ppg - 1.3) * 6.0), 1),
                "composite": round(team_baseline, 1),
            })

    # Select strongest available Starting XI by formation (1 GK, 4 DEF, 3 MID, 3 FWD)
    def top_by_pos(pos_code: str, count: int) -> List[Dict[str, Any]]:
        pool = sorted([p for p in available_players if p["position"] == pos_code], key=lambda x: x["composite"], reverse=True)
        if len(pool) < count:
            fillers = sorted([p for p in available_players if p not in pool], key=lambda x: x["composite"], reverse=True)
            pool.extend(fillers[: count - len(pool)])
        return pool[:count]

    xi_gk = top_by_pos("GK", 1)
    xi_def = top_by_pos("DEF", 4)
    xi_mid = top_by_pos("MID", 3)
    xi_fwd = top_by_pos("FWD", 3)
    starting_xi = xi_gk + xi_def + xi_mid + xi_fwd

    # Apply injury strength multiplier from Step 4
    inj_mult = team_profile["injuries"].get("strength_multiplier", 1.0)

    attack_rating = round(float(np.mean([p["ability"] for p in xi_fwd])) * inj_mult, 1)
    midfield_rating = round(float(np.mean([p["ability"] for p in xi_mid])) * inj_mult, 1)
    defense_rating = round(float(np.mean([p["ability"] for p in (xi_def + xi_gk)])) * inj_mult, 1)
    overall_rating = round((attack_rating * 0.35) + (midfield_rating * 0.32) + (defense_rating * 0.33), 1)
    team_consistency = round(float(np.mean([p["consistency"] for p in starting_xi])), 1)

    # Top 3 key active players to highlight in match simulation & tactical reasoning
    key_players = sorted(starting_xi, key=lambda x: x["ability"], reverse=True)[:3]

    return {
        "overall_rating": overall_rating,
        "attack_rating": attack_rating,
        "midfield_rating": midfield_rating,
        "defense_rating": defense_rating,
        "team_consistency": team_consistency,
        "starting_xi": starting_xi,
        "sidelined_players": sidelined_rated,
        "key_players": key_players,
    }
