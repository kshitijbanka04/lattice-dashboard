# Lattice Dashboard

Lives at: `kshitijbanka.com/projects/lattice` (static HTML on Hostinger)
+ `lattice-dashboard-n7mxynspqe9fd75e85cdsc.streamlit.app` (Streamlit Cloud, embedded via iframe).

## Layout

```
dashboard/
├── streamlit_app.py        # the Streamlit app (entrypoint for Streamlit Cloud)
├── requirements.txt        # Python deps for Streamlit Cloud
├── generate_data.py        # run locally to refresh data/ JSONs
├── index.html              # static page → upload to Hostinger /projects/lattice/
└── data/
    ├── paper_trades.json       # closed paper trades (from paper_book.sqlite)
    ├── cumulative_pnl.json     # date → cumulative P&L curve
    ├── backtest_summary.json   # V4 baseline numbers
    ├── variants_disproved.json # the 12+ variants tested
    └── daily_picks.json        # today's picks (populated by daily cron)
```

## Local dev

```bash
# 1. Regenerate JSON files (after a backtest run or new paper trades)
python3 dashboard/generate_data.py

# 2. Run the Streamlit app locally
python3 -m streamlit run dashboard/streamlit_app.py
# → http://localhost:8501
```

## Deployment

### Streamlit Cloud

1. Push this repo (or a `dashboard/` subtree) to GitHub.
2. On https://share.streamlit.io → New App:
   - Repository: `kshitijbanka04/lattice-dashboard`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: `lattice-dashboard`
3. Streamlit Cloud picks up `dashboard/requirements.txt` automatically.
4. The app reads `dashboard/data/*.json` from the repo at runtime — no DB
   connection from the cloud, no secrets needed.

### Hostinger static page

1. Edit `dashboard/index.html` and replace the iframe `src` with the live
   Streamlit Cloud URL (currently: `https://lattice-dashboard-n7mxynspqe9fd75e85cdsc.streamlit.app/?embed=true`).
2. Upload `index.html` to Hostinger at `/projects/lattice/index.html`.
3. (Optional) add a card linking to it on `kshitijbanka.com/projects`.

## Updating data

The dashboard is **fully static** — Streamlit Cloud only reads the committed
JSON files. To refresh:

```bash
python3 dashboard/generate_data.py
git add dashboard/data/
git commit -m "refresh dashboard data"
git push
```

Streamlit Cloud auto-redeploys on push.

For daily picks, the cron job `breakout_live_quote_scan.py` writes
`dashboard/data/daily_picks.json` directly at 14:00 IST, then a follow-up
commit/push from the laptop refreshes the cloud copy.
