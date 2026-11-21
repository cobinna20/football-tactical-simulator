# simulator_engine.py - 10000x Dixon-Coles Monte Carlo plus 90 minute timeline
import math, random
import numpy as np

def _pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)

def build_score_matrix(lh, la, max_goals=8):
    rho = -0.13 if lh < 3 and la < 3 else 0.0
    m = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = _pmf(i, lh) * _pmf(j, la)
            tau = 1.0
            if i == 0 and j == 0: tau = 1 - lh * la * rho
            elif i == 0 and j == 1: tau = 1 + lh * rho
            elif i == 1 and j == 0: tau = 1 + la * rho
            elif i == 1 and j == 1: tau = 1 - rho
            m[i, j] = p * tau
    m = m / m.sum()
    return m

def run_monte_carlo(lh, la, n=10000):
    mat = build_score_matrix(lh, la)
    flat = mat.flatten()
    idx = np.random.choice(len(flat), size=n, p=flat)
    home_w = draw = away_w = 0
    scores = {}
    for v in idx:
        i, j = divmod(int(v), mat.shape[1])
        scores[(i, j)] = scores.get((i, j), 0) + 1
        if i > j: home_w += 1
        elif i < j: away_w += 1
        else: draw += 1
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:6]
    most = top[0][0] if top else (1, 1)
    return {"home_prob": round(home_w / n * 100, 1), "draw_prob": round(draw / n * 100, 1), "away_prob": round(away_w / n * 100, 1), "expected_home": round(lh, 2), "expected_away": round(la, 2), "most_likely": f"{most[0]}-{most[1]}", "most_likely_pct": round(top[0][1] / n * 100, 1) if top else 0, "top_scores": [{"score": f"{k[0]}-{k[1]}", "pct": round(v / n * 100, 1)} for k, v in top], "matrix": mat}

def simulate_90_min(lh, la, home_team, away_team, seed=None):
    rnd = random.Random(seed or 42)
    mat = build_score_matrix(lh, la)
    flat = mat.flatten()
    pick = int(rnd.choices(range(len(flat)), weights=flat, k=1)[0])
    hg, ag = divmod(pick, mat.shape[1])
    goal_minutes_h = sorted(rnd.sample(range(1, 91), hg)) if hg else []
    goal_minutes_a = sorted(rnd.sample(range(1, 91), ag)) if ag else []
    events = []
    momentum = 50
    for minute in range(1, 91):
        if minute in goal_minutes_h:
            events.append({"minute": minute, "team": home_team, "type": "GOAL", "detail": f"GOAL {home_team} scores"})
            momentum = min(85, momentum + 12)
        elif minute in goal_minutes_a:
            events.append({"minute": minute, "team": away_team, "type": "GOAL", "detail": f"GOAL {away_team} scores"})
            momentum = max(15, momentum - 12)
        elif rnd.random() < 0.18:
            team = home_team if rnd.random() < 0.5 else away_team
            events.append({"minute": minute, "team": team, "type": "Chance", "detail": f"Big chance for {team}"})
            momentum += rnd.randint(-6, 6)
    events.append({"minute": 90, "team": "Referee", "type": "Full Time", "detail": f"Full Time: {home_team} {hg}-{ag} {away_team}"})
    return {"events": events, "final_score": f"{hg}-{ag}", "home_goals": hg, "away_goals": ag, "momentum_end": momentum}
