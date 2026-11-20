"""
app.py
Main Streamlit Web Application for the 54-League Multi-Source Football
Tactical Match Simulator, Player Rating Engine, and Predictive Informatics Platform.
"""

import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from league_registry import get_all_league_names
from database import init_db, save_prediction_record, get_prediction_history
from quota_manager import get_quota_status
from source_router import get_league_bundle
from data_fusion import build_match_fusion_profile
from rating_engine import evaluate_squad_ratings
from context_modifiers import compute_tactical_and_contextual_lambdas
from simulator_engine import run_monte_carlo_simulation, simulate_live_match_timeline
from tactical_analyst import generate_tactical_reasoning

st.set_page_config(
    page_title="Tactical Football AI Match Simulator",
    page_icon="⚽",
    layout="wide",
)

init_db()

st.title("⚽ Tactical Football AI Match Simulator & Informatics Engine")
st.caption("Multi-Source Free-Tier Data Fusion • Player Ability & Consistency Ratings • 10,000x Monte Carlo & Live Match Engine")

# ==================== SIDEBAR: LEAGUE & FIXTURE SELECTION ====================
with st.sidebar:
    st.header("🌍 1. Select Competition")
    all_leagues = get_all_league_names()
    default_idx = all_leagues.index("England - Premier League") if "England - Premier League" in all_leagues else 0
    selected_league = st.selectbox("Choose from 54 Global Leagues:", all_leagues, index=default_idx)

    force_refresh = st.button("🔄 Force Refresh Live Data", use_container_width=True)

    with st.spinner(f"Fusing multi-source data for {selected_league}..."):
        league_bundle = get_league_bundle(selected_league, force_refresh=force_refresh)

    fixtures = league_bundle.get("fixtures", [])

    st.header("📅 2. Select Upcoming Fixture")
    if fixtures:
        fixture_labels = [
            f"{f['home_team']} vs {f['away_team']} ({f.get('date', '')[:10]})"
            for f in fixtures
        ]
        selected_idx = st.selectbox("Upcoming Matches:", range(len(fixture_labels)), format_func=lambda i: fixture_labels[i])
        active_fixture = fixtures[selected_idx]
    else:
        st.info("No scheduled fixtures found in the next 14 days for this league. Use Custom Matchup below:")
        teams = sorted(list(league_bundle.get("standings", {}).keys())) or ["Home XI", "Away XI"]
        c_home = st.selectbox("Home Team:", teams, index=0)
        c_away = st.selectbox("Away Team:", teams, index=min(1, len(teams) - 1))
        active_fixture = {
            "match_id": f"custom_{c_home}_{c_away}",
            "date": "Upcoming",
            "home_team": c_home,
            "away_team": c_away,
            "home_id": "",
            "away_id": "",
            "home_form": "",
            "away_form": "",
            "venue": "League Stadium",
        }

    st.divider()
    st.subheader("📡 Active Data Sources")
    for src in league_bundle.get("sources_used", []):
        st.success(f"✓ {src}")

# ==================== RUN ANALYTICAL PIPELINE FOR SELECTED MATCH ====================
fusion = build_match_fusion_profile(active_fixture, league_bundle)
home_squad = evaluate_squad_ratings(fusion["home"], fusion["league_config"], active_fixture.get("home_id", ""))
away_squad = evaluate_squad_ratings(fusion["away"], fusion["league_config"], active_fixture.get("away_id", ""))
ctx = compute_tactical_and_contextual_lambdas(fusion, home_squad, away_squad, league_bundle.get("recent_results", []))
mc = run_monte_carlo_simulation(ctx["lambda_home"], ctx["lambda_away"], ctx["upset_volatility"], n_sims=10000)

# Save pre-match probability snapshot to SQLite ledger
save_prediction_record({
    "match_id": active_fixture["match_id"],
    "league_name": selected_league,
    "home_team": fusion["home"]["name"],
    "away_team": fusion["away"]["name"],
    "match_date": active_fixture.get("date", "")[:10],
    "prob_home": mc["prob_home"],
    "prob_draw": mc["prob_draw"],
    "prob_away": mc["prob_away"],
    "projected_score": mc["top_scorelines"]["score"],
})
# ==================== TOP MATCH BANNER & CONFIDENCE METER ====================
h_name = fusion["home"]["name"]
a_name = fusion["away"]["name"]

col_b1, col_b2, col_b3, col_b4 = st.columns([2, 1, 2, 1.3])
with col_b1:
    st.subheader(f"🏠 {h_name}")
    st.caption(f"Rank #{fusion['home']['standings']['rank']} • Form: {fusion['home']['form_raw']} • Rest: {ctx['home_rest_days']}d")
with col_b2:
    st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
    st.caption(f"📍 {active_fixture.get('venue', 'Stadium')}")
with col_b3:
    st.subheader(f"✈️ {a_name}")
    st.caption(f"Rank #{fusion['away']['standings']['rank']} • Form: {fusion['away']['form_raw']} • Rest: {ctx['away_rest_days']}d")
with col_b4:
    st.metric("Data Confidence", f"{fusion['data_confidence_pct']}%", delta=f"Tier {fusion['league_config']['tier']} League")

# ==================== MAIN NAVIGATION TABS ====================
tab_sim, tab_squads, tab_context, tab_history = st.tabs([
    "🎮 Live Match Simulator & Probabilities",
    "🏃 Player Ability & Consistency Ratings",
    "🏥 Injuries, News & Tactical Context",
    "📊 Accuracy Ledger & Free API Quotas",
])

# -------------------- TAB 1: MATCH SIMULATOR & PROBABILITIES --------------------
with tab_sim:
    st.markdown("#### 10,000x Dixon-Coles Monte Carlo Pre-Match Distribution")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(f"{h_name} Win", f"{mc['prob_home']}%")
    m2.metric("Draw", f"{mc['prob_draw']}%")
    m3.metric(f"{a_name} Win", f"{mc['prob_away']}%")
    m4.metric("Projected xG", f"{ctx['lambda_home']} - {ctx['lambda_away']}")
    m5.metric("Most Likely Score", mc["top_scorelines"]["score"], delta=f"{mc['top_scorelines']['probability']}% prob")

    # Probability bar chart
    prob_df = pd.DataFrame({
        "Outcome": [f"{h_name} Win", "Draw", f"{a_name} Win"],
        "Probability (%)": [mc["prob_home"], mc["prob_draw"], mc["prob_away"]],
    })
    fig_prob = px.bar(
        prob_df, x="Probability (%)", y="Outcome", orientation="h",
        color="Outcome", text="Probability (%)", height=210,
        color_discrete_sequence=["#1f77b4", "#7f7f7f", "#d62728"],
    )
    fig_prob.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_prob, use_container_width=True)

    st.divider()
    st.markdown("#### 🏟️ Interactive 90-Minute Tactical Match Simulation")
    sim_col1, sim_col2 = st.columns([1, 2])
    with sim_col1:
        animate_sim = st.checkbox("Animate live match clock", value=True)
        run_sim_btn = st.button("▶️ Simulate Match Now", type="primary", use_container_width=True)

    if "sim_seed" not in st.session_state:
        st.session_state.sim_seed = 1
    if run_sim_btn:
        st.session_state.sim_seed += 1

    sim_data = simulate_live_match_timeline(
        h_name, a_name, ctx, mc, home_squad, away_squad, seed_offset=st.session_state.sim_seed
    )

    if run_sim_btn and animate_sim:
        live_box = st.empty()
        prog = st.progress(0)
        key_events = [e for e in sim_data["events"] if e["type"] in ("kickoff", "goal", "halftime", "tactical", "fulltime")]
        for idx, ev in enumerate(key_events):
            live_box.info(ev["text"])
            prog.progress(int(((idx + 1) / len(key_events)) * 100))
            time.sleep(0.35)
        prog.empty()

    # Final Simulated Scoreboard
    st.success(f"### 🏁 Simulated Final Score: {h_name}  {sim_data['final_home_goals']}  —  {sim_data['final_away_goals']}  {a_name}")

    # Match Stats & Momentum Chart
    sc1, sc2 = st.columns([1, 1.3])
    with sc1:
        ms = sim_data["match_stats"]
        stats_df = pd.DataFrame({
            "Metric": ["Possession %", "Total Shots", "Shots on Target", "Simulated xG"],
            h_name: [f"{ms['possession_home']}%", ms["shots_home"], ms["sot_home"], ms["xg_home"]],
            a_name: [f"{ms['possession_away']}%", ms["shots_away"], ms["sot_away"], ms["xg_away"]],
        })
        st.table(stats_df)

    with sc2:
        mom_df = pd.DataFrame(sim_data["momentum_timeline"])
        if not mom_df.empty:
            fig_mom = go.Figure()
            fig_mom.add_trace(go.Scatter(
                x=mom_df["minute"], y=mom_df["momentum"], fill="tozeroy",
                line=dict(color="#2ca02c"), name="Match Momentum",
            ))
            fig_mom.update_layout(
                title=f"Match Momentum (+ {h_name} / - {a_name})",
                xaxis_title="Minute", yaxis_title="Momentum Index",
                height=240, margin=dict(l=10, r=10, t=35, b=10),
            )
            st.plotly_chart(fig_mom, use_container_width=True)

    # AI Tactical Reasoning Report
    with st.spinner("Generating AI Tactical Match Reasoning Report..."):
        reasoning_md = generate_tactical_reasoning(fusion, home_squad, away_squad, ctx, mc, sim_data)
    st.markdown(reasoning_md)

    with st.expander("📜 View Full Minute-by-Minute Match Commentary"):
        for ev in sim_data["events"]:
            st.write(ev["text"])

# -------------------- TAB 2: PLAYER ABILITY & CONSISTENCY --------------------
with tab_squads:
    st.markdown("#### Team Tactical Line Ratings & Squad Consistency (0–100)")
    r_df = pd.DataFrame({
        "Rating Category": ["Overall XI", "Attack", "Midfield Control", "Defensive Solidity", "Squad Consistency"],
        h_name: [
            home_squad["overall_rating"], home_squad["attack_rating"],
            home_squad["midfield_rating"], home_squad["defense_rating"], home_squad["team_consistency"],
        ],
        a_name: [
            away_squad["overall_rating"], away_squad["attack_rating"],
            away_squad["midfield_rating"], away_squad["defense_rating"], away_squad["team_consistency"],
        ],
    })
    st.dataframe(r_df, use_container_width=True, hide_index=True)

    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.subheader(f"{h_name} Projected Starting XI")
        st.dataframe(pd.DataFrame(home_squad["starting_xi"]), use_container_width=True, hide_index=True)
    with p_col2:
        st.subheader(f"{a_name} Projected Starting XI")
        st.dataframe(pd.DataFrame(away_squad["starting_xi"]), use_container_width=True, hide_index=True)

# -------------------- TAB 3: INJURIES, NEWS & TACTICAL CONTEXT --------------------
with tab_context:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader(f"🏥 {h_name} Squad Availability")
        st.metric("Injury Strength Impact", f"-{fusion['home']['injuries']['penalty_pct']}%", delta=f"{fusion['home']['injuries']['absence_count']} Absences", delta_color="inverse")
        if fusion["home"]["injuries"]["absences"]:
            st.dataframe(pd.DataFrame(fusion["home"]["injuries"]["absences"]), use_container_width=True, hide_index=True)
        else:
            st.info("No major structured absences reported.")
    with c2:
        st.subheader(f"🏥 {a_name} Squad Availability")
        st.metric("Injury Strength Impact", f"-{fusion['away']['injuries']['penalty_pct']}%", delta=f"{fusion['away']['injuries']['absence_count']} Absences", delta_color="inverse")
        if fusion["away"]["injuries"]["absences"]:
            st.dataframe(pd.DataFrame(fusion["away"]["injuries"]["absences"]), use_container_width=True, hide_index=True)
        else:
            st.info("No major structured absences reported.")

    st.divider()
    st.markdown(f"**Tactical Matchup Profile:** {ctx['tactical_style']} | **Upset Volatility:** {int(ctx['upset_volatility']*100)}%")
    st.markdown(f"**H2H Historical Sample:** {fusion['h2h']['matches']} matches ({h_name} Wins: {fusion['h2h']['home_wins']}, Draws: {fusion['h2h']['draws']}, {a_name} Wins: {fusion['h2h']['away_wins']})")

# -------------------- TAB 4: ACCURACY LEDGER & QUOTAS --------------------
with tab_history:
    st.subheader("📡 Free-Tier API Quota Health")
    q_stat = get_quota_status()
    q_cols = st.columns(len(q_stat))
    for idx, (prov, info) in enumerate(q_stat.items()):
        q_cols[idx].metric(prov, f"{info['remaining']} left", delta=f"{info['used']}/{info['max']} used")

    st.divider()
    st.subheader("🎯 Saved Pre-Match Probability Ledger")
    hist_rows = get_prediction_history(limit=30)
    if hist_rows:
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Simulated fixtures will appear here automatically.")
