"""
tactical_analyst.py
Generates a human-readable, data-backed Tactical Reasoning Report using
Google Gemini Free Tier (gemini-2.5-flash), with a zero-dependency rule-based
fallback so tactical explanations always work even offline.
"""

from typing import Dict, Any
from google import genai
from quota_manager import get_secret_key


def build_fallback_tactical_report(
    fusion_profile: Dict[str, Any],
    home_squad: Dict[str, Any],
    away_squad: Dict[str, Any],
    context_lambdas: Dict[str, Any],
    mc_results: Dict[str, Any],
    sim_result: Dict[str, Any],
) -> str:
    """Deterministic sports-science reasoning report when Gemini API is unavailable."""
    h_name = fusion_profile["home"]["name"]
    a_name = fusion_profile["away"]["name"]

    h_inj_count = fusion_profile["home"]["injuries"]["absence_count"]
    a_inj_count = fusion_profile["away"]["injuries"]["absence_count"]

    h_key = ", ".join(p["name"] for p in home_squad["key_players"][:2])
    a_key = ", ".join(p["name"] for p in away_squad["key_players"][:2])

    return (
        f"### Tactical & Statistical Match Reasoning ({h_name} vs {a_name})\n\n"
        f"**1. Real-World Probability Alignment:** Across **10,000 Monte Carlo simulations**, "
        f"**{h_name}** holds a **{mc_results['prob_home']}%** win probability, **Draw** is **{mc_results['prob_draw']}%**, "
        f"and **{a_name}** holds **{mc_results['prob_away']}%**. The simulated **{sim_result['scoreline']}** scoreline reflects "
        f"calibrated Expected Goals of **{context_lambdas['lambda_home']} xG** vs **{context_lambdas['lambda_away']} xG**.\n\n"
        f"**2. Squad Ability & Consistency Impact:** {h_name} enters with an Overall Starting XI rating of "
        f"**{home_squad['overall_rating']}/100** (Consistency: **{home_squad['team_consistency']}/100**, led by {h_key}), "
        f"facing {a_name}'s **{away_squad['overall_rating']}/100** XI (Consistency: **{away_squad['team_consistency']}/100**, led by {a_key}).\n\n"
        f"**3. Tactical Clash & Contextual Factors:** Expected style: **{context_lambdas['tactical_style']}**. "
        f"Squad availability shows **{h_inj_count}** noted absences for {h_name} and **{a_inj_count}** for {a_name}. "
        f"Recovery window stands at **{context_lambdas['home_rest_days']} days** rest for {h_name} vs "
        f"**{context_lambdas['away_rest_days']} days** for {a_name}."
    )


def generate_tactical_reasoning(
    fusion_profile: Dict[str, Any],
    home_squad: Dict[str, Any],
    away_squad: Dict[str, Any],
    context_lambdas: Dict[str, Any],
    mc_results: Dict[str, Any],
    sim_result: Dict[str, Any],
) -> str:
    """Use free Google Gemini Flash to synthesize a concise, data-grounded tactical analysis."""
    api_key = get_secret_key("GEMINI_API_KEY")
    if not api_key:
        return build_fallback_tactical_report(
            fusion_profile, home_squad, away_squad, context_lambdas, mc_results, sim_result
        )

    h_name = fusion_profile["home"]["name"]
    a_name = fusion_profile["away"]["name"]

    prompt = f"""
    Act as an elite football tactical analyst and sports data scientist. Write a concise, insightful
    3-paragraph Tactical Match Reasoning Report explaining why the simulated result ({h_name} {sim_result['scoreline']} {a_name})
    aligns with real-world statistical probabilities before kickoff. Strictly focus on football tactics,
    player ratings, consistency, fatigue, and injuries. Do NOT mention gambling, betting, or odds.

    DATA SUMMARY:
    - Fixture: {h_name} vs {a_name} ({fusion_profile['fixture'].get('date', '')[:10]})
    - 10,000x Monte Carlo Probabilities: Home Win {mc_results['prob_home']}%, Draw {mc_results['prob_draw']}%, Away Win {mc_results['prob_away']}%
    - Calibrated Expected Goals: {h_name} {context_lambdas['lambda_home']} xG vs {a_name} {context_lambdas['lambda_away']} xG
    - {h_name} Squad Ratings: Overall {home_squad['overall_rating']}, Attack {home_squad['attack_rating']}, Midfield {home_squad['midfield_rating']}, Defense {home_squad['defense_rating']}, Squad Consistency {home_squad['team_consistency']}/100
    - {a_name} Squad Ratings: Overall {away_squad['overall_rating']}, Attack {away_squad['attack_rating']}, Midfield {away_squad['midfield_rating']}, Defense {away_squad['defense_rating']}, Squad Consistency {away_squad['team_consistency']}/100
    - {h_name} Key Players: {[p['name'] + ' (Ability ' + str(p['ability']) + ', Cons ' + str(p['consistency']) + ')' for p in home_squad['key_players']]}
    - {a_name} Key Players: {[p['name'] + ' (Ability ' + str(p['ability']) + ', Cons ' + str(p['consistency']) + ')' for p in away_squad['key_players']]}
    - Injuries/Absences: {h_name} ({fusion_profile['home']['injuries']['absence_count']} out, -{fusion_profile['home']['injuries']['penalty_pct']}% impact) vs {a_name} ({fusion_profile['away']['injuries']['absence_count']} out, -{fusion_profile['away']['injuries']['penalty_pct']}% impact)
    - Context: {context_lambdas['tactical_style']} | Rest Days: {h_name} {context_lambdas['home_rest_days']}d vs {a_name} {context_lambdas['away_rest_days']}d
    - Match Stakes: {h_name} ({context_lambdas['home_motivation']}) vs {a_name} ({context_lambdas['away_motivation']})
    """

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    return build_fallback_tactical_report(
        fusion_profile, home_squad, away_squad, context_lambdas, mc_results, sim_result
    )
