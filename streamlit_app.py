"""Lattice — Live dashboard for the V4 breakout BTST strategy.

Reads pre-computed JSON files in ./data/ (built by generate_data.py).
Deploy via Streamlit Cloud → embed via iframe on kshitijbanka.com/projects/lattice.
"""
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(
    page_title="Lattice — V4 Breakout Strategy",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_json(name):
    path = DATA_DIR / name
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


trades = load_json("paper_trades.json") or []
cum_pnl = load_json("cumulative_pnl.json") or []
backtest = load_json("backtest_summary.json") or {}
variants = load_json("variants_disproved.json") or []
picks = load_json("daily_picks.json") or {}

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
        .main { padding-top: 1rem; }
        h1 { font-size: 2.2rem !important; margin-bottom: 0.2rem !important; }
        .subtle { color: #888; font-size: 0.95rem; }
        .metric-card { background: #f7f7f9; padding: 1rem 1.2rem; border-radius: 10px;
                       border: 1px solid #ececec; }
        .verdict-winner { color: #1c8a3f; font-weight: 600; }
        .verdict-loser { color: #b53939; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Lattice — V4 Breakout Strategy")
st.markdown(
    '<div class="subtle">A regime-aware quantitative BTST system for the Indian '
    'equity market. Live paper-traded since May 2026.</div>',
    unsafe_allow_html=True,
)
st.markdown("&nbsp;")

# ------------------------------------------------------------------
# Hero metrics — live paper trade aggregates
# ------------------------------------------------------------------
df_trades = pd.DataFrame(trades)
if not df_trades.empty:
    total_pnl = df_trades["net_pnl"].sum()
    n_trades = len(df_trades)
    n_wins = (df_trades["net_pnl"] > 0).sum()
    win_rate = (n_wins / n_trades * 100) if n_trades else 0
    avg_ret = df_trades["return_pct"].dropna().mean() if "return_pct" in df_trades else 0
    days_live = df_trades["exit_dt"].nunique()
else:
    total_pnl = n_trades = win_rate = avg_ret = days_live = 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Net P&L (paper)", f"₹{total_pnl:,.0f}", help="Cumulative net P&L from paper trades")
col2.metric("Trades closed", f"{n_trades}")
col3.metric("Win rate", f"{win_rate:.0f}%")
col4.metric("Avg return / trade", f"{avg_ret:+.2f}%")
col5.metric("Days live", f"{days_live}")

st.markdown("---")

# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Paper Trades", "📈 Backtest", "🧪 What I disproved", "🎯 Today's Picks"]
)

# ------------------------------------------------------------------
# TAB 1 — Paper trades
# ------------------------------------------------------------------
with tab1:
    st.subheader("Live paper-traded book")
    st.caption(
        "Trades are placed at market close (15:25 IST) using V4's top picks, "
        "held overnight as MTF (4× leverage), and exited at +1.5% intraday "
        "target or next-day close."
    )

    if df_trades.empty:
        st.info("No closed trades yet — first signals start May 19, 2026.")
    else:
        # Cumulative P&L line chart
        df_curve = pd.DataFrame(cum_pnl)
        if not df_curve.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_curve["date"],
                    y=df_curve["cumulative_pnl"],
                    mode="lines+markers",
                    line=dict(color="#1c8a3f", width=3),
                    marker=dict(size=8),
                    name="Cumulative P&L",
                    fill="tozeroy",
                    fillcolor="rgba(28,138,63,0.08)",
                )
            )
            fig.update_layout(
                height=300,
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis_title=None,
                yaxis_title="P&L (₹)",
                showlegend=False,
                plot_bgcolor="white",
                title=dict(text="Cumulative P&L", x=0.01, font=dict(size=14)),
            )
            fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", tickprefix="₹")
            st.plotly_chart(fig, use_container_width=True)

        # Trade table
        st.markdown("##### Trade history")
        display = df_trades[[
            "exit_dt", "symbol", "entry_price", "exit_price",
            "shares", "return_pct", "net_pnl", "exit_reason"
        ]].copy()
        display.columns = ["Exit Date", "Symbol", "Entry", "Exit", "Shares", "Return %", "Net P&L", "Exit Reason"]
        display["Return %"] = display["Return %"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "—")
        display["Net P&L"] = display["Net P&L"].apply(lambda x: f"₹{x:+,.0f}")
        display["Entry"] = display["Entry"].apply(lambda x: f"₹{x:,.2f}")
        display["Exit"] = display["Exit"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# TAB 2 — Backtest
# ------------------------------------------------------------------
with tab2:
    st.subheader("V4 baseline — 1-year backtest")
    st.caption(
        f"{backtest.get('backtest_period', '')} · {backtest.get('universe_size', 0)}-stock universe "
        f"· ₹{backtest.get('account_size_inr', 0):,} account"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annualized return", f"{backtest.get('annualized_return_pct', 0)}%")
    c2.metric("Annualized P&L", f"₹{backtest.get('annualized_pnl_inr', 0):,}")
    c3.metric("Win rate", f"{backtest.get('win_rate_pct', 0)}%")
    c4.metric("Max drawdown", f"{backtest.get('max_drawdown_pct', 0)}%")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Sharpe (annualized)", f"{backtest.get('sharpe_annualized', 0)}")
    c6.metric("Trades / year", f"{backtest.get('n_trades', 0)}")
    c7.metric("Avg return / trade", f"{backtest.get('avg_return_per_trade_pct', 0)}%")
    c8.metric("Avg P&L / trade", f"₹{backtest.get('avg_pnl_per_trade_inr', 0):,}")

    st.markdown("---")

    # Exit breakdown
    st.markdown("##### Exit breakdown")
    exit_bd = backtest.get("exit_breakdown", {})
    if exit_bd:
        ex_df = pd.DataFrame([
            {
                "Exit Type": k.replace("_", " ").title(),
                "Trades": v["n"],
                "Win %": f"{v['win_pct']}%",
                "Avg %": f"{v['avg_pct']:+.2f}%",
                "Total ₹": f"₹{v['total_inr']:+,}",
            }
            for k, v in exit_bd.items()
        ])
        st.dataframe(ex_df, use_container_width=True, hide_index=True)

        # Bar chart for exit contribution
        fig = go.Figure()
        labels = [k.replace("_", " ").title() for k in exit_bd.keys()]
        values = [v["total_inr"] for v in exit_bd.values()]
        colors = ["#1c8a3f" if v > 0 else "#b53939" for v in values]
        fig.add_trace(go.Bar(x=labels, y=values, marker_color=colors, text=[f"₹{v:+,}" for v in values], textposition="outside"))
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="P&L Contribution (₹)",
            showlegend=False,
            plot_bgcolor="white",
            title=dict(text="P&L by exit type", x=0.01, font=dict(size=14)),
        )
        fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", tickprefix="₹")
        st.plotly_chart(fig, use_container_width=True)

    # Score breakdown
    score_bd = backtest.get("score_breakdown", {})
    if score_bd:
        st.markdown("##### Performance by signal score")
        sc_df = pd.DataFrame([
            {"Score": k.replace("_", " ").title(), "Trades": v["n"], "Win %": f"{v['win_pct']}%", "Avg ₹/trade": f"₹{v['avg_inr']:+,}"}
            for k, v in score_bd.items()
        ])
        st.dataframe(sc_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# TAB 3 — What I disproved
# ------------------------------------------------------------------
with tab3:
    st.subheader("Variants tested — all under-performed baseline")
    st.caption(
        "Across 12+ enhancement variants (universe expansion, chart patterns, "
        "sector momentum, intraday stops, MIS leverage), the V4 baseline held up. "
        "Most ideas that sounded good destroyed alpha."
    )

    if variants:
        v_df = pd.DataFrame(variants)

        def fmt_pnl(v):
            if isinstance(v, (int, float)):
                return f"₹{v:+,}"
            return str(v)

        def fmt_delta(v):
            if isinstance(v, (int, float)):
                if v == 0:
                    return "—"
                return f"₹{v:+,}"
            return str(v)

        v_df["Annualized P&L"] = v_df["annualized_pnl"].apply(fmt_pnl)
        v_df["Δ vs baseline"] = v_df["delta_from_baseline"].apply(fmt_delta)
        v_df["Win %"] = v_df["win_rate"].apply(lambda x: f"{x}%")
        v_df["Max DD"] = v_df["max_dd"].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else str(x))

        display_v = v_df[["name", "Annualized P&L", "Win %", "Max DD", "Δ vs baseline", "verdict"]].copy()
        display_v.columns = ["Variant", "Annualized P&L", "Win %", "Max DD", "Δ vs baseline", "Verdict"]

        def style_verdict(val):
            if "WINNER" in str(val):
                return "background-color: #e6f4ea; color: #1c8a3f; font-weight: 600"
            return "color: #b53939"

        styled = display_v.style.map(style_verdict, subset=["Verdict"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    st.markdown(
        """
        ##### Takeaway
        Most "improvements" hurt the system. Spent more time disproving ideas
        than adding them — the baseline V4 (685 universe, score≥7 + 1.5×
        volume, +1.5% intraday target, MTF overnight) sits at a local optimum
        for this regime. Each variant attempted gave back P&L, win rate, or
        added drawdown without compensating returns.
        """
    )

# ------------------------------------------------------------------
# TAB 4 — Today's picks
# ------------------------------------------------------------------
with tab4:
    st.subheader(f"Today's picks — {picks.get('as_of', 'N/A')}")
    st.caption(
        f"VIX regime: **{picks.get('vix_regime', 'N/A')}** · "
        f"Size multiplier: **{picks.get('size_mult', 1.0)}×**"
    )

    p_list = picks.get("picks", [])
    if not p_list or (len(p_list) == 1 and "placeholder" in str(p_list[0].get("ticker", ""))):
        st.info("Today's picks are generated at 14:00 IST by the live quote scanner. "
                "Run `scripts/breakout_live_quote_scan.py` to populate.")
        if picks.get("note"):
            st.caption(picks["note"])
    else:
        p_df = pd.DataFrame(p_list)
        for col in ["entry", "target"]:
            if col in p_df:
                p_df[col] = p_df[col].apply(lambda x: f"₹{x:,.2f}")
        if "notional" in p_df:
            p_df["notional"] = p_df["notional"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(p_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------
st.markdown("---")
st.markdown(
    f"<div class='subtle'>Lattice · built by "
    f"<a href='https://kshitijbanka.com' target='_blank'>Kshitij Banka</a> · "
    f"data refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M IST')} · "
    f"<a href='https://github.com/kshitijbanka/lattice' target='_blank'>source</a></div>",
    unsafe_allow_html=True,
)
