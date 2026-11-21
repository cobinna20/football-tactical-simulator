# tactical_analyst.py - Gemini with deterministic fallback
import os
try:
    import streamlit as st
except Exception:
    st = None

def _key():
    if st is not None:
        try:
            if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
                return str(st.secrets["GEMINI_API_KEY"]).strip().strip('"')
        except Exception:
            pass
    return os.getenv("GEMINI_API_KEY", "").strip()

def generate_tactical_report(home_team, away_team, home_ratings, away_ratings, sim, lambdas, modifiers):
    prompt = f"""Write a 3 paragraph tactical match reasoning report for {home_team} vs {away_team}.
Home ratings: {home_ratings}. Away ratings: {away_ratings}.
Simulation: Home {sim.get('home_prob')}% Draw {sim.get('draw_prob')}% Away {sim.get('away_prob')}%, Most likely {sim.get('most_likely')}, Expected goals {lambdas.get('lambda_home')} vs {lambdas.get('lambda_away')}.
Modifiers: {modifiers.get('modifiers')}.
Paragraph 1: tactical matchup and key battles. Paragraph 2: why the probabilities look like this and where the model could be wrong. Paragraph 3: what each team must do to win. No betting language, only sports analytics."""
    key = _key()
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            txt = (resp.text or "").strip()
            if len(txt) > 200:
                return txt
        except Exception:
            pass
    # Deterministic fallback, always works offline
    p1 = f"{home_team} ({home_ratings['Overall']} overall) host {away_team} ({away_ratings['Overall']} overall) in a matchup shaped by attack against defence. Home Attack {home_ratings['Attack']} meets Away Defence {away_ratings['Defense']}, while Away Attack {away_ratings['Attack']} meets Home Defence {home_ratings['Defense']}. The midfield battle, Home {home_ratings['Midfield']} vs Away {away_ratings['Midfield']}, will decide who controls tempo and who is forced to chase second balls."
    p2 = f"The Monte Carlo model gives Home {sim.get('home_prob')}%, Draw {sim.get('draw_prob')}%, Away {sim.get('away_prob')}% with a most likely score of {sim.get('most_likely')} and expected goals of {lambdas.get('lambda_home')} to {lambdas.get('lambda_away')}. That aligns with the rating gap and home advantage, but the model is sensitive to early goals, set pieces and squad consistency ({home_ratings['Squad Consistency']} vs {away_ratings['Squad Consistency']}). If the underdog scores first, the volatility noted in the context modifiers becomes the real story."
    p3 = f"For {home_team} to win, they must turn midfield control into early chances and protect against the counter. For {away_team} to win, they must stay compact, survive the first 20 minutes, and exploit transitions when the home side commits full backs forward. The decisive factor is not possession alone, it is shot quality in the final third and discipline after conceding."
    return f"{p1}\n\n{p2}\n\n{p3}"
