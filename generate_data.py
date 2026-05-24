"""Pre-compute all the JSON data the Streamlit dashboard needs.

Run this once after each major backtest update + after each trading day's
paper_book changes. It writes:
  - paper_trades.json    (trade history from paper_book.sqlite)
  - backtest_summary.json (V4 baseline numbers)
  - variants_disproved.json (the 12+ variants we tested)
  - daily_picks.json     (today's V4 picks if available)
  - cumulative_pnl.json  (date → cumulative P&L curve)
"""
import json, sqlite3, sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path("/Users/kshitijbanka/Documents/lattice")
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def gen_paper_trades():
    """Read paper_book.sqlite and dump all trades to JSON."""
    con = sqlite3.connect(PROJECT_ROOT / "data/paper_book.sqlite")
    cur = con.execute("""
        SELECT id, strategy, symbol, direction, entry_dt, entry_price,
               exit_dt, exit_price, shares, gross_pnl, net_pnl,
               exit_reason, score_at_signal, confluence_at_signal, product_type
        FROM positions
        WHERE status='CLOSED'
        ORDER BY exit_dt, id
    """)
    trades = []
    for r in cur.fetchall():
        trades.append({
            "id": r[0],
            "strategy": r[1],
            "symbol": r[2],
            "direction": r[3],
            "entry_dt": r[4],
            "entry_price": r[5],
            "exit_dt": r[6],
            "exit_price": r[7],
            "shares": r[8],
            "gross_pnl": r[9],
            "net_pnl": r[10],
            "exit_reason": r[11],
            "score": r[12],
            "confluence": r[13],
            "product": r[14],
            "return_pct": (r[7] - r[5]) / r[5] * 100 if r[5] and r[7] else None,
        })
    con.close()
    (DATA_DIR / "paper_trades.json").write_text(json.dumps(trades, indent=2, default=str))
    print(f"  paper_trades.json: {len(trades)} trades")
    return trades


def gen_cumulative_pnl(trades):
    """Build cumulative P&L curve by exit date."""
    by_date = {}
    for t in trades:
        dt = t["exit_dt"]
        if dt:
            by_date.setdefault(dt, 0)
            by_date[dt] += (t["net_pnl"] or 0)

    cum = 0
    curve = []
    for dt in sorted(by_date.keys()):
        cum += by_date[dt]
        curve.append({"date": dt, "daily_pnl": by_date[dt], "cumulative_pnl": cum})
    (DATA_DIR / "cumulative_pnl.json").write_text(json.dumps(curve, indent=2, default=str))
    print(f"  cumulative_pnl.json: {len(curve)} days")


def gen_backtest_summary():
    """V4 baseline backtest numbers."""
    summary = {
        "strategy": "V4 — Daily breakout BTST",
        "universe_size": 685,
        "universe_description": "F&O + curated mid-cap Indian equities (excludes 7 chronic losers)",
        "account_size_inr": 200_000,
        "backtest_period": "1 year (2025-05-20 to 2026-05-19)",
        "n_trades": 473,
        "win_rate_pct": 71.2,
        "avg_return_per_trade_pct": 0.514,
        "avg_pnl_per_trade_inr": 637,
        "annualized_pnl_inr": 311_144,
        "annualized_return_pct": 155.6,
        "sharpe_annualized": 5.40,
        "max_drawdown_pct": 10.7,
        "exit_breakdown": {
            "intraday_target_hit": {"n": 274, "win_pct": 100, "avg_pct": 1.50, "total_inr": 846_638},
            "next_day_close": {"n": 148, "win_pct": 21.6, "avg_pct": -1.63, "total_inr": -595_330},
            "no_intraday_data": {"n": 51, "win_pct": 60.8, "avg_pct": 0.53, "total_inr": 49_879},
        },
        "score_breakdown": {
            "score_7":  {"n": 18,  "win_pct": 55.6, "avg_inr": 254},
            "score_8":  {"n": 95,  "win_pct": 55.8, "avg_inr": 346},
            "score_9":  {"n": 142, "win_pct": 57.8, "avg_inr": 215},
            "score_10": {"n": 204, "win_pct": 59.3, "avg_inr": 458},
        },
    }
    (DATA_DIR / "backtest_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  backtest_summary.json")


def gen_variants_disproved():
    """The 12+ variants we tested that all hurt the baseline."""
    variants = [
        {"name": "V4 BASELINE (685 universe, pure)", "annualized_pnl": 311_144, "win_rate": 71.2, "max_dd": 10.7, "verdict": "WINNER", "delta_from_baseline": 0},
        {"name": "Universe expansion to 1,672 stocks", "annualized_pnl": 239_300, "win_rate": 58.9, "max_dd": 24.4, "verdict": "DILUTED ALPHA", "delta_from_baseline": -71_844},
        {"name": "Universe filtered (719 intraday-eligible)", "annualized_pnl": 248_543, "win_rate": 70.4, "max_dd": 10.9, "verdict": "FEWER NET SIGNALS", "delta_from_baseline": -62_601},
        {"name": "Cup-and-Handle pattern bonus", "annualized_pnl": 184_424, "win_rate": 68.3, "max_dd": 12.9, "verdict": "REORDERED PICKS WORSE", "delta_from_baseline": -126_720},
        {"name": "Rectangle pattern alone", "annualized_pnl": 33_405, "win_rate": 54.1, "max_dd": "n/a", "verdict": "MARGINAL — overlaps with V4", "delta_from_baseline": -277_739},
        {"name": "Trendline breakout pattern alone", "annualized_pnl": -508_379, "win_rate": 50.3, "max_dd": "n/a", "verdict": "DISASTER — too noisy", "delta_from_baseline": -819_523},
        {"name": "4 concurrent slots × 25% allocation", "annualized_pnl": 198_048, "win_rate": 69.6, "max_dd": 15.1, "verdict": "SMALLER POSITIONS LOSE", "delta_from_baseline": -113_096},
        {"name": "Intraday -2% stop loss", "annualized_pnl": 295_136, "win_rate": 64.7, "max_dd": 7.9, "verdict": "STOPS BACKFIRE ON NOISE", "delta_from_baseline": -16_008},
        {"name": "MIS intraday-only (5× leverage)", "annualized_pnl": -219_869, "win_rate": 62.3, "max_dd": "n/a", "verdict": "NO OVERNIGHT GAP ALPHA", "delta_from_baseline": -531_013},
        {"name": "MIS + BTST hybrid (50/50)", "annualized_pnl": -391_818, "win_rate": 61.4, "max_dd": "n/a", "verdict": "MIS DRAGS HYBRID", "delta_from_baseline": -702_962},
        {"name": "Sector momentum bonus (26 NSE indices)", "annualized_pnl": "neutral", "win_rate": 58.2, "max_dd": "n/a", "verdict": "NO INCREMENTAL ALPHA", "delta_from_baseline": "≈0"},
        {"name": "Partial booking + trailing stop", "annualized_pnl": "≈baseline", "win_rate": 62.9, "max_dd": "n/a", "verdict": "OPERATIONALLY COMPLEX", "delta_from_baseline": "≈+₹40k"},
        {"name": "Gap-up filter (skip if open > +1.3%)", "annualized_pnl": -58_073, "win_rate": 58.0, "max_dd": 58.3, "verdict": "KILLS MOONSHOTS", "delta_from_baseline": -369_217},
    ]
    (DATA_DIR / "variants_disproved.json").write_text(json.dumps(variants, indent=2))
    print(f"  variants_disproved.json: {len(variants)} variants")


def gen_daily_picks_placeholder():
    """Today's picks. Real one populated by daily cron; this is a placeholder."""
    today = datetime.now().strftime("%Y-%m-%d")
    picks = {
        "as_of": today,
        "vix_regime": "ELEVATED",
        "size_mult": 0.5,
        "picks": [
            {"rank": 1, "ticker": "(placeholder)", "score": 0, "vol_mult": 0,
             "entry": 0, "target": 0, "shares": 0, "notional": 0},
        ],
        "note": "Run scripts/breakout_live_quote_scan.py at 14:00 IST to populate.",
    }
    (DATA_DIR / "daily_picks.json").write_text(json.dumps(picks, indent=2))
    print(f"  daily_picks.json (placeholder)")


def main():
    print("Generating dashboard data files...")
    trades = gen_paper_trades()
    gen_cumulative_pnl(trades)
    gen_backtest_summary()
    gen_variants_disproved()
    gen_daily_picks_placeholder()
    print(f"\nData written to: {DATA_DIR}/")
    print(f"Files: {[f.name for f in DATA_DIR.iterdir()]}")


if __name__ == "__main__":
    main()
