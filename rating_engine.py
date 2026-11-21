# rating_engine.py - Player Ability 0-100, Consistency 0-100, Starting XI
import random
FIRST = ["James", "Liam", "Noah", "Lucas", "Mateo", "Ethan", "Leo", "Kai", "Owen", "Max", "Hugo", "Gabriel", "Diego", "Andre", "Yusuf", "Chidi", "Emeka", "Tobi", "Rafael", "Bruno"]
LAST = ["Smith", "Garcia", "Silva", "Muller", "Kante", "Okafor", "Adeyemi", "Costa", "Rossi", "Novak", "Diallo", "Mensah", "Petrov", "Larsen", "Moreau", "Almeida", "Kovac", "Haddad", "Ndiaye", "Osei"]
POSITIONS = [("GK", 3), ("DF", 7), ("MF", 7), ("FW", 6)]

def _seed(team):
    return sum(ord(c) for c in str(team)) % 10000 + 7

def _base_for_team(team):
    s = str(team).lower()
    if any(x in s for x in ["city", "madrid", "bayern", "barcelona", "arsenal", "liverpool", "paris"]):
        return 82
    if any(x in s for x in ["united", "chelsea", "milan", "dortmund", "juventus", "ajax"]):
        return 76
    return 68

def generate_squad(team_name, base_rating=None):
    base = base_rating if base_rating is not None else _base_for_team(team_name)
    rnd = random.Random(_seed(team_name))
    squad = []
    pid = 1
    for pos, count in POSITIONS:
        for i in range(count):
            ability = max(45, min(96, int(base + rnd.gauss(0, 7) + (3 if i < 2 else 0))))
            consistency = max(45, min(97, int(74 + rnd.gauss(0, 9))))
            squad.append({"id": pid, "name": f"{rnd.choice(FIRST)} {rnd.choice(LAST)}", "position": pos, "ability": ability, "consistency": consistency, "age": rnd.randint(19, 34), "team": team_name})
            pid += 1
    return squad

def build_starting_xi(squad):
    def top(pos, n):
        return sorted([p for p in squad if p["position"] == pos], key=lambda x: x["ability"], reverse=True)[:n]
    xi = top("GK", 1) + top("DF", 4) + top("MF", 3) + top("FW", 3)
    return sorted(xi, key=lambda x: {"GK": 0, "DF": 1, "MF": 2, "FW": 3}[x["position"]])

def calculate_team_ratings(squad, xi, injury_penalty=0.0):
    def avg(players, key):
        return sum(p[key] for p in players) / len(players) if players else 60
    gk = [p for p in xi if p["position"] == "GK"]
    df = [p for p in xi if p["position"] == "DF"]
    mf = [p for p in xi if p["position"] == "MF"]
    fw = [p for p in xi if p["position"] == "FW"]
    attack = avg(fw + mf, "ability") * (1 - injury_penalty * 0.5)
    midfield = avg(mf, "ability") * (1 - injury_penalty * 0.3)
    defense = avg(df + gk, "ability") * (1 - injury_penalty * 0.4)
    overall = avg(xi, "ability") * (1 - injury_penalty * 0.4)
    consistency = avg(xi, "consistency")
    return {"Attack": round(attack, 1), "Midfield": round(midfield, 1), "Defense": round(defense, 1), "Overall": round(overall, 1), "Squad Consistency": round(consistency, 1)}

def get_team_bundle(team_name, injury_penalty=0.0):
    squad = generate_squad(team_name)
    xi = build_starting_xi(squad)
    ratings = calculate_team_ratings(squad, xi, injury_penalty)
    return {"team": team_name, "squad": squad, "xi": xi, "ratings": ratings}
