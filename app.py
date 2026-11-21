# app.py - Main Streamlit UI, 4 tabs
import streamlit as st
import pandas as pd
import plotly.express as px
from league_registry import LEAGUE_REGISTRY
from database import init_db, get_prediction_history, save_prediction_record
from quota_manager import get_quota_status
from source_router import get_league_bundle
from news_injury_engine import get_injury_report
from data_fusion import fuse_data
from rating_engine import get_team_bundle
from context_modifiers import apply_context
from simulator_engine import run_monte_carlo, simulate_90_min
from tactical_analyst import generate_tactical_report

st.set_page_config(page_title="Tactical Football AI Match Simulator", layout="wide")
init_db()
st.title("Tactical Football AI Match Simulator")
st.caption("Sports analytics and tactical modeling. No betting language.")

# Sidebar
league_keys = list(LEAGUE_REGISTRY.keys())
league_labels = {k: LEAGUE_REGISTRY[k]["name"] for k in league_keys}
sel_label = st.sidebar.selectbox("Select League", [league_labels[k] for k in league_keys])
sel_key = [k for k, v in league_labels.items() if v == sel_label][0]
st.sidebar.subheader("Match Setup")
rest_home = st.sidebar.slider("Home rest days", 1, 7, 4)
rest_away = st.sidebar.slider("Away rest days", 1, 7, 4)
stakes = st.sidebar.selectbox("Stakes", ["League Match", "Title Decider", "Relegation Battle", "Cup Final", "Derby"])

with st.spinner("Fetching fixtures..."):
    bundle = get_league_bundle(sel_key)
st.sidebar.subheader("Active Data Sources")
for s in bundle["active_sources"]:
    st.sidebar.write(f"✓ {s}")
st.sidebar.metric("Data Confidence", f"{bundle['data_confidence_pct']}%")
with st.sidebar.expander("Data Source Diagnostics", expanded=not bundle["has_live_data"]):
    for d in bundle["diagnostics"]:
        st.write(f"**{d['provider']}** - HTTP {d['status']} - found {d['found']}")
        if d["error"]:
            st.code(d["error"][:400])
        if d["note"]:
            st.caption(d["note"])
    if not bundle["diagnostics"]:
        st.write("No diagnostics yet.")

# Fixture pick or manual baseline
fixtures = bundle.get("fixtures", [])
if fixtures:
    options = [f"{f['home']} vs {f['away']} - {str(f.get('date',''))[:10]}" for f in fixtures]
    choice = st.sidebar.selectbox("Select Fixture", options)
    idx = options.index(choice)
    home_team = fixtures[idx]["home"]
    away_team = fixtures[idx]["away"]
else:
    st.sidebar.info("No live fixtures returned. Using Baseline League Model. Type teams to simulate.")
    home_team = st.sidebar.text_input("Home Team", "Home XI")
    away_team = st.sidebar.text_input("Away Team", "Away XI")

injuries = get_injury_report(home_team, away_team)
fusion = fuse_data(bundle, home_team, away_team)
home_b = get_team_bundle(home_team, injuries["home_penalty"])
away_b = get_team_bundle(away_team, injuries["away_penalty"])
ctx = apply_context(home_b["ratings"], away_b["ratings"], fusion, rest_home, rest_away, stakes, home_team, away_team)
sim = run_monte_carlo(ctx["lambda_home"], ctx["lambda_away"], n=10000)

tab1, tab2, tab3, tab4 = st.tabs(["Live Match Simulator & Probabilities", "Player Ability & Consistency", "Injuries / News & Tactical Context", "Accuracy Ledger & Free API Quotas"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric(f"{home_team} Win", f"{sim['home_prob']}%")
    c2.metric("Draw", f"{sim['draw_prob']}%")
    c3.metric(f"{away_team} Win", f"{sim['away_prob']}%")
    st.write(f"**Most likely:** {sim['most_likely']} ({sim['most_likely_pct']}%) | **Expected goals:** {sim['expected_home']} - {sim['expected_away']} | **Volatility:** {ctx['volatility']}")
    df = pd.DataFrame([{"Outcome": home_team, "Prob": sim["home_prob"]}, {"Outcome": "Draw", "Prob": sim["draw_prob"]}, {"Outcome": away_team, "Prob": sim["away_prob"]}])
    st.plotly_chart(px.bar(df, x="Outcome", y="Prob", title="10,000x Dixon-Coles Monte Carlo Probabilities"), use_container_width=True)
    df2 = pd.DataFrame(sim["top_scores"])
    if not df2.empty:
        st.plotly_chart(px.bar(df2, x="score", y="pct", title="Top scorelines"), use_container_width=True)
    if st.button("Run 90-Minute Simulation", type="primary"):
        timeline = simulate_90_min(ctx["lambda_home"], ctx["lambda_away"], home_team, away_team)
        st.subheader(f"Full Time: {timeline['final_score']}")
        for e in timeline["events"]:
            st.write(f"{e['minute']}' - {e['detail']}")
        save_prediction_record(sel_label, home_team, away_team, timeline["home_goals"], timeline["away_goals"], sim["home_prob"], sim["draw_prob"], sim["away_prob"], bundle["data_confidence_pct"])
    st.subheader("AI Tactical Reasoning Report")
    report = generate_tactical_report(home_team, away_team, home_b["ratings"], away_b["ratings"], sim, ctx, ctx)
    st.write(report)
    st.subheader("Team Ratings")
    r = pd.DataFrame([{"Team": home_team, **home_b["ratings"]}, {"Team": away_team, **away_b["ratings"]}])
    st.dataframe(r, use_container_width=True)

with tab2:
    st.subheader(f"{home_team} - Starting XI")
    st.dataframe(pd.DataFrame(home_b["xi"])[["name", "position", "ability", "consistency", "age"]], use_container_width=True)
    st.subheader(f"{away_team} - Starting XI")
    st.dataframe(pd.DataFrame(away_b["xi"])[["name", "position", "ability", "consistency", "age"]], use_container_width=True)
    st.subheader("Full Squads")
    col_a, col_b = st.columns(2)
    col_a.dataframe(pd.DataFrame(home_b["squad"]), use_container_width=True)
    col_b.dataframe(pd.DataFrame(away_b["squad"]), use_container_width=True)

with tab3:
    st.subheader("Injuries and News")
    st.write(f"**{home_team}** penalty: {injuries['home_penalty']:.2f} | Injured reports: {len(injuries['home']['injured'])}")
    for n in injuries["home"]["news"]:
        st.write(f"- {n['title']}")
    st.write(f"**{away_team}** penalty: {injuries['away_penalty']:.2f} | Injured reports: {len(injuries['away']['injured'])}")
    for n in injuries["away"]["news"]:
        st.write(f"- {n['title']}")
    st.subheader("Tactical Context")
    st.write(ctx["explanation"])
    for m in ctx["modifiers"]:
        st.write(f"- {m}")
    st.write(f"H2H: {fusion['h2h']} | Historical rates: Home {fusion['home_goals_rate']} Away {fusion['away_goals_rate']}")

with tab4:
    st.subheader("Prediction History")
    hist = get_prediction_history(50)
    if hist:
        st.dataframe(pd.DataFrame(hist), use_container_width=True)
    else:
        st.write("No predictions saved yet. Run a 90-minute simulation to log one.")
    st.subheader("Free API Quotas")
    st.dataframe(pd.DataFrame(get_quota_status()), use_container_width=True)
