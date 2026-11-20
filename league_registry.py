"""
league_registry.py
Master directory of 54 global football leagues mapped across multiple free-tier
data providers for zero-cost, multi-source resilient data ingestion.
"""

from typing import Dict, List, Any

LEAGUE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "England - Premier League": {"country": "England", "tier": 1, "espn_slug": "eng.1", "fd_org_code": "PL", "api_football_id": 39, "fd_uk_code": "E0", "has_xg": True, "home_adv_boost": 1.12, "avg_league_goals": 2.85},
    "Spain - La Liga": {"country": "Spain", "tier": 1, "espn_slug": "esp.1", "fd_org_code": "PD", "api_football_id": 140, "fd_uk_code": "SP1", "has_xg": True, "home_adv_boost": 1.14, "avg_league_goals": 2.62},
    "Italy - Serie A": {"country": "Italy", "tier": 1, "espn_slug": "ita.1", "fd_org_code": "SA", "api_football_id": 135, "fd_uk_code": "I1", "has_xg": True, "home_adv_boost": 1.11, "avg_league_goals": 2.68},
    "Germany - Bundesliga": {"country": "Germany", "tier": 1, "espn_slug": "ger.1", "fd_org_code": "BL1", "api_football_id": 78, "fd_uk_code": "D1", "has_xg": True, "home_adv_boost": 1.13, "avg_league_goals": 3.12},
    "France - Ligue 1": {"country": "France", "tier": 1, "espn_slug": "fra.1", "fd_org_code": "FL1", "api_football_id": 61, "fd_uk_code": "F1", "has_xg": True, "home_adv_boost": 1.12, "avg_league_goals": 2.70},
    "UEFA - Champions League": {"country": "Europe", "tier": 1, "espn_slug": "uefa.champions", "fd_org_code": "CL", "api_football_id": 2, "fd_uk_code": None, "has_xg": True, "home_adv_boost": 1.15, "avg_league_goals": 2.95},
    "UEFA - Europa League": {"country": "Europe", "tier": 1, "espn_slug": "uefa.europa", "fd_org_code": "EL", "api_football_id": 3, "fd_uk_code": None, "has_xg": True, "home_adv_boost": 1.14, "avg_league_goals": 2.82},
    "UEFA - Europa Conference League": {"country": "Europe", "tier": 2, "espn_slug": "uefa.europa.conf", "fd_org_code": None, "api_football_id": 848, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.78},
    "England - Championship": {"country": "England", "tier": 2, "espn_slug": "eng.2", "fd_org_code": "ELC", "api_football_id": 40, "fd_uk_code": "E1", "has_xg": True, "home_adv_boost": 1.13, "avg_league_goals": 2.65},
    "England - League One": {"country": "England", "tier": 2, "espn_slug": "eng.3", "fd_org_code": None, "api_football_id": 41, "fd_uk_code": "E2", "has_xg": False, "home_adv_boost": 1.12, "avg_league_goals": 2.60},
    "England - League Two": {"country": "England", "tier": 2, "espn_slug": "eng.4", "fd_org_code": None, "api_football_id": 42, "fd_uk_code": "E3", "has_xg": False, "home_adv_boost": 1.12, "avg_league_goals": 2.58},
    "Spain - Segunda División": {"country": "Spain", "tier": 2, "espn_slug": "esp.2", "fd_org_code": None, "api_football_id": 141, "fd_uk_code": "SP2", "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.28},
    "Italy - Serie B": {"country": "Italy", "tier": 2, "espn_slug": "ita.2", "fd_org_code": None, "api_football_id": 136, "fd_uk_code": "I2", "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.45},
    "Germany - 2. Bundesliga": {"country": "Germany", "tier": 2, "espn_slug": "ger.2", "fd_org_code": None, "api_football_id": 79, "fd_uk_code": "D2", "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.95},
    "France - Ligue 2": {"country": "France", "tier": 2, "espn_slug": "fra.2", "fd_org_code": None, "api_football_id": 62, "fd_uk_code": "F2", "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.40},
    "Netherlands - Eredivisie": {"country": "Netherlands", "tier": 1, "espn_slug": "ned.1", "fd_org_code": "DED", "api_football_id": 88, "fd_uk_code": "N1", "has_xg": True, "home_adv_boost": 1.14, "avg_league_goals": 3.10},
    "Portugal - Primeira Liga": {"country": "Portugal", "tier": 1, "espn_slug": "por.1", "fd_org_code": "PPL", "api_football_id": 94, "fd_uk_code": "P1", "has_xg": True, "home_adv_boost": 1.13, "avg_league_goals": 2.65},
    "Belgium - Pro League": {"country": "Belgium", "tier": 2, "espn_slug": "bel.1", "fd_org_code": None, "api_football_id": 144, "fd_uk_code": "B1", "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.80},
    "Turkey - Süper Lig": {"country": "Turkey", "tier": 2, "espn_slug": "tur.1", "fd_org_code": None, "api_football_id": 203, "fd_uk_code": "T1", "has_xg": False, "home_adv_boost": 1.16, "avg_league_goals": 2.75},
    "Scotland - Premiership": {"country": "Scotland", "tier": 2, "espn_slug": "sco.1", "fd_org_code": None, "api_football_id": 179, "fd_uk_code": "SC0", "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.72},
    "Greece - Super League": {"country": "Greece", "tier": 2, "espn_slug": "gre.1", "fd_org_code": None, "api_football_id": 197, "fd_uk_code": "G1", "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.45},
    "Switzerland - Super League": {"country": "Switzerland", "tier": 2, "espn_slug": "sui.1", "fd_org_code": None, "api_football_id": 207, "fd_uk_code": "SWZ", "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.90},
    "Austria - Bundesliga": {"country": "Austria", "tier": 2, "espn_slug": "aut.1", "fd_org_code": None, "api_football_id": 218, "fd_uk_code": "AUT", "has_xg": False, "home_adv_boost": 1.12, "avg_league_goals": 2.88},
    "Denmark - Superliga": {"country": "Denmark", "tier": 2, "espn_slug": "den.1", "fd_org_code": None, "api_football_id": 119, "fd_uk_code": "DNK", "has_xg": False, "home_adv_boost": 1.12, "avg_league_goals": 2.76},
    "Sweden - Allsvenskan": {"country": "Sweden", "tier": 2, "espn_slug": "swe.1", "fd_org_code": None, "api_football_id": 113, "fd_uk_code": "SWE", "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.74},
    "Norway - Eliteserien": {"country": "Norway", "tier": 2, "espn_slug": "nor.1", "fd_org_code": None, "api_football_id": 103, "fd_uk_code": "NOR", "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.92},
    "Poland - Ekstraklasa": {"country": "Poland", "tier": 2, "espn_slug": "pol.1", "fd_org_code": None, "api_football_id": 106, "fd_uk_code": "POL", "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.55},
    "Croatia - HNL": {"country": "Croatia", "tier": 3, "espn_slug": "cro.1", "fd_org_code": None, "api_football_id": 210, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.50},
    "Serbia - SuperLiga": {"country": "Serbia", "tier": 3, "espn_slug": "srb.1", "fd_org_code": None, "api_football_id": 286, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.58},
    "Czech Republic - First League": {"country": "Czech Republic", "tier": 3, "espn_slug": "cze.1", "fd_org_code": None, "api_football_id": 345, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.68},
    "Romania - Liga I": {"country": "Romania", "tier": 2, "espn_slug": "rou.1", "fd_org_code": None, "api_football_id": 283, "fd_uk_code": "ROU", "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.42},
    "Ukraine - Premier League": {"country": "Ukraine", "tier": 3, "espn_slug": "ukr.1", "fd_org_code": None, "api_football_id": 333, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.10, "avg_league_goals": 2.52},
    "Brazil - Serie A (Brasileirão)": {"country": "Brazil", "tier": 1, "espn_slug": "bra.1", "fd_org_code": "BSA", "api_football_id": 71, "fd_uk_code": "BRA", "has_xg": True, "home_adv_boost": 1.18, "avg_league_goals": 2.48},
    "Brazil - Serie B": {"country": "Brazil", "tier": 3, "espn_slug": "bra.2", "fd_org_code": None, "api_football_id": 72, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.17, "avg_league_goals": 2.25},
    "Argentina - Liga Profesional": {"country": "Argentina", "tier": 2, "espn_slug": "arg.1", "fd_org_code": None, "api_football_id": 128, "fd_uk_code": "ARG", "has_xg": False, "home_adv_boost": 1.17, "avg_league_goals": 2.22},
    "USA - Major League Soccer (MLS)": {"country": "USA", "tier": 1, "espn_slug": "usa.1", "fd_org_code": None, "api_football_id": 253, "fd_uk_code": "USA", "has_xg": True, "home_adv_boost": 1.16, "avg_league_goals": 2.92},
    "Mexico - Liga MX": {"country": "Mexico", "tier": 2, "espn_slug": "mex.1", "fd_org_code": None, "api_football_id": 262, "fd_uk_code": "MEX", "has_xg": False, "home_adv_boost": 1.16, "avg_league_goals": 2.75},
    "Colombia - Categoría Primera A": {"country": "Colombia", "tier": 3, "espn_slug": "col.1", "fd_org_code": None, "api_football_id": 239, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.18, "avg_league_goals": 2.30},
    "Chile - Primera División": {"country": "Chile", "tier": 3, "espn_slug": "chi.1", "fd_org_code": None, "api_football_id": 265, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.60},
    "CONMEBOL - Copa Libertadores": {"country": "South America", "tier": 2, "espn_slug": "conmebol.libertadores", "fd_org_code": None, "api_football_id": 13, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.20, "avg_league_goals": 2.55},
    "Nigeria - Premier Football League (NPFL)": {"country": "Nigeria", "tier": 3, "espn_slug": "nga.1", "fd_org_code": None, "api_football_id": 399, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.24, "avg_league_goals": 2.15},
    "South Africa - Premier Soccer League (PSL)": {"country": "South Africa", "tier": 3, "espn_slug": "rsa.1", "fd_org_code": None, "api_football_id": 288, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.16, "avg_league_goals": 2.20},
    "Egypt - Premier League": {"country": "Egypt", "tier": 3, "espn_slug": "egy.1", "fd_org_code": None, "api_football_id": 233, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.16, "avg_league_goals": 2.32},
    "Morocco - Botola Pro": {"country": "Morocco", "tier": 3, "espn_slug": "mar.1", "fd_org_code": None, "api_football_id": 200, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.17, "avg_league_goals": 2.18},
    "Ghana - Premier League": {"country": "Ghana", "tier": 3, "espn_slug": "gha.1", "fd_org_code": None, "api_football_id": 570, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.22, "avg_league_goals": 2.12},
    "CAF - Champions League": {"country": "Africa", "tier": 3, "espn_slug": "caf.champions", "fd_org_code": None, "api_football_id": 12, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.22, "avg_league_goals": 2.28},
    "Saudi Arabia - Pro League": {"country": "Saudi Arabia", "tier": 3, "espn_slug": "ksa.1", "fd_org_code": None, "api_football_id": 307, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.95},
    "Japan - J1 League": {"country": "Japan", "tier": 2, "espn_slug": "jpn.1", "fd_org_code": None, "api_football_id": 98, "fd_uk_code": "JPN", "has_xg": False, "home_adv_boost": 1.12, "avg_league_goals": 2.65},
    "South Korea - K League 1": {"country": "South Korea", "tier": 3, "espn_slug": "kor.1", "fd_org_code": None, "api_football_id": 292, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.13, "avg_league_goals": 2.58},
    "China - Super League": {"country": "China", "tier": 2, "espn_slug": "chn.1", "fd_org_code": None, "api_football_id": 169, "fd_uk_code": "CHN", "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.80},
    "Australia - A-League Men": {"country": "Australia", "tier": 3, "espn_slug": "aus.1", "fd_org_code": None, "api_football_id": 188, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 3.05},
    "India - Indian Super League": {"country": "India", "tier": 3, "espn_slug": "ind.1", "fd_org_code": None, "api_football_id": 323, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.15, "avg_league_goals": 2.75},
    "UAE - Pro League": {"country": "UAE", "tier": 3, "espn_slug": "uae.1", "fd_org_code": None, "api_football_id": 301, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.14, "avg_league_goals": 2.90},
    "FIFA - World Cup / International Friendlies": {"country": "World", "tier": 2, "espn_slug": "fifa.friendly", "fd_org_code": "WC", "api_football_id": 10, "fd_uk_code": None, "has_xg": False, "home_adv_boost": 1.08, "avg_league_goals": 2.55},
}

RSS_INJURY_FEEDS: List[str] = [
    "https://bbci.co.uk",
    "https://espn.com",
    "https://skysports.com",
    "https://goal.com",
]


def get_all_league_names() -> List[str]:
    return list(LEAGUE_REGISTRY.keys())


def get_league_config(league_name: str) -> Dict[str, Any]:
    if league_name not in LEAGUE_REGISTRY:
        raise ValueError(f"League '{league_name}' not found in LEAGUE_REGISTRY.")
    return LEAGUE_REGISTRY[league_name]


def get_leagues_by_tier(tier: int) -> List[str]:
    return [name for name, cfg in LEAGUE_REGISTRY.items() if cfg["tier"] == tier]
