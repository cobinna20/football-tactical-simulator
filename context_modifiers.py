# context_modifiers.py - fatigue, motivation, style clash, calibrated lambdas
def apply_context(home_ratings, away_ratings, fusion=None, rest_home=4, rest_away=4, stakes="League Match", home_team="", away_team=""):
    hr, ar = home_ratings, away_ratings
    # Base lambdas from ratings and historical rates
    base_home = 1.15 + (hr["Attack"] - ar["Defense"]) / 28.0 + 0.25
    base_away = 1.05 + (ar["Attack"] - hr["Defense"]) / 28.0
    if fusion:
        base_home = (base_home + fusion.get("home_goals_rate", base_home)) / 2
        base_away = (base_away + fusion.get("away_goals_rate", base_away)) / 2
    mods = []
    lam_h, lam_a = base_home, base_away
    # Fatigue: less than 3 rest days costs goals
    if rest_home < 3:
        pen = (3 - rest_home) * 0.11
        lam_h -= pen
        mods.append(f"{home_team or 'Home'} fatigue: -{pen:.2f} lambda, {rest_home} rest days")
    if rest_away < 3:
        pen = (3 - rest_away) * 0.11
        lam_a -= pen
        mods.append(f"{away_team or 'Away'} fatigue: -{pen:.2f} lambda, {rest_away} rest days")
    # Motivation
    if stakes in ["Title Decider", "Relegation Battle", "Cup Final"]:
        lam_h += 0.07
        lam_a += 0.07
        mods.append(f"High stakes ({stakes}): both teams +0.07 lambda")
    # Style clash: strong attack vs weak defence creates volatility
    gap = abs(hr["Attack"] - ar["Defense"]) + abs(ar["Attack"] - hr["Defense"])
    volatility = "High" if gap > 25 else "Medium" if gap > 15 else "Low"
    if volatility == "High":
        mods.append("Style clash: attack vs defence gap is large, expect open game and high volatility")
    lam_h = max(0.2, min(4.5, lam_h))
    lam_a = max(0.2, min(4.5, lam_a))
    return {"lambda_home": round(lam_h, 3), "lambda_away": round(lam_a, 3), "modifiers": mods, "volatility": volatility, "explanation": f"Home lambda {lam_h:.2f} from Attack {hr['Attack']} vs Defence {ar['Defense']}. Away lambda {lam_a:.2f} from Attack {ar['Attack']} vs Defence {hr['Defense']}."}
