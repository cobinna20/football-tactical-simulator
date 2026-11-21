# Tactical Football AI Match Simulator

Zero cost sports analytics app. 54 leagues, real fixtures, Player Ability 0-100, Consistency 0-100, Starting XI ratings, 10000x Dixon-Coles Monte Carlo, 90 minute simulation, AI Tactical Reasoning Report.

## Setup
1. Create repo and paste all files.
2. In Streamlit Cloud, add Secrets:
GEMINI_API_KEY = "your key"
FOOTBALL_DATA_KEY = "your key"
API_FOOTBALL_KEY = "your key"
3. Deploy from main branch, file app.py.

## How data works
Order is ESPN (no key) then Football-Data.org then API-Football then TheSportsDB then Football-Data.co.uk CSV for history. If all fail, app falls back to Baseline League Model and shows the exact HTTP status in sidebar diagnostics.

## Current year
In 2026 the European season is 2026 for API-Football and Football-Data.org, and 2627 for Football-Data.co.uk CSVs. The router tries both 2026 and 2025 automatically.

## Tabs
1. Live Match Simulator and Probabilities
2. Player Ability and Consistency Ratings
3. Injuries News and Tactical Context
4. Accuracy Ledger and Free API Quotas
