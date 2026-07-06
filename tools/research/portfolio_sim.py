"""Shared-equity portfolio simulation of the two measured edges.

One account trades BOTH strategies (ribbon pullback + 52wk breakout, exact
rules from the earlier per-name replications) across all 39 names, with:
- one position max per name (ribbon has priority if both fire on one bar)
- a cap on concurrent positions (10)
- risk-based sizing: risk% of CURRENT equity per trade, capped by available
  cash (no leverage)
- alphabetical priority when more signals arrive than free slots
- fills/costs identical to the replications (close entry, gap-at-open,
  stop-first ambiguity, trend-break at close for ribbon, 0.25%/side)
- daily mark-to-market equity for drawdown measurement

Outputs per risk level: CAGR (full ~29y), CAGR modern era (2013+), max
drawdown, worst calendar year, yearly return table, trade count.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

CACHE = Path("data_cache")
UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "SBIN", "BHARTIARTL", "ITC", "LT", "HINDUNILVR",
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "AXISBANK", "KOTAKBANK", "TATASTEEL", "ADANIGREEN",
    "WIPRO", "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND",
    "BAJAJFINSV", "ADANIPORTS", "POWERGRID", "NTPC", "ONGC",
    "COALINDIA", "JSWSTEEL", "HINDALCO", "DRREDDY", "CIPLA",
    "EICHERMOT", "HEROMOTOCO", "BRITANNIA", "DABUR", "VEDL",
]

START_EQUITY = 1_000_000.0
MAX_POSITIONS = 10
COST = 0.0025
MODERN_ERA = pd.Timestamp("2013-01-01")


def load(name: str) -> pd.DataFrame | None:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{name}.csv"
    if f.exists():
        df = pd.read_csv(f, index_col=0, parse_dates=True)
    else:
        df = None
        for _ in range(3):
            try:
                df = yf.download(f"{name}.NS", period="max", interval="1d",
                                 auto_adjust=True, progress=False,
                                 multi_level_index=False)
                break
            except Exception:  # noqa: BLE001
                time.sleep(3)
        if df is None or df.empty:
            return None
        df.to_csv(f)
    if len(df) < 300:
        return None
    return df.dropna(subset=["Open", "High", "Low", "Close"])


def prep(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"]
    out = pd.DataFrame(index=df.index)
    out[["o", "h", "l", "c"]] = df[["Open", "High", "Low", "Close"]]
    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    prev = close.shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(),
                    (df["Low"] - prev).abs()], axis=1).max(axis=1)
    out["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    out["swlow"] = df["Low"].rolling(10).min()
    out["anchor"] = close.shift(1).rolling(252).max()
    out["bar"] = np.arange(len(out))
    return out


class NameState:
    __slots__ = ("arm", "pos")

    def __init__(self) -> None:
        self.arm = 0
        self.pos = None  # dict(kind, qty, entry, stop, target, edate)


def run_portfolio(data: dict[str, pd.DataFrame], risk_pct: float) -> dict:
    calendar = sorted(set().union(*[set(d.index) for d in data.values()]))
    states = {n: NameState() for n in data}
    equity_cash = START_EQUITY
    trades = 0
    daily_equity: list[tuple[pd.Timestamp, float]] = []
    concurrent: list[int] = []

    for day in calendar:
        # 1) exits
        for name in data:
            st = states[name]
            if st.pos is None or day not in data[name].index:
                continue
            row = data[name].loc[day]
            p = st.pos
            exit_px = None
            if row.o <= p["stop"]:
                exit_px = row.o
            elif row.o >= p["target"]:
                exit_px = row.o
            elif row.l <= p["stop"]:
                exit_px = p["stop"]
            elif row.h >= p["target"]:
                exit_px = p["target"]
            elif p["kind"] == "ribbon" and not (
                row.ema20 > row.ema50 > row.ema200 and row.c > row.ema200
            ):
                exit_px = row.c
            if exit_px is not None:
                gross = (exit_px - p["entry"]) * p["qty"]
                costs = (p["entry"] + exit_px) * p["qty"] * COST
                equity_cash += p["entry"] * p["qty"] + gross - costs
                st.pos = None
                trades += 1

        # mark-to-market equity + open slots
        open_names = [n for n in data if states[n].pos is not None]
        mtm = equity_cash
        for n in open_names:
            p = states[n].pos
            d = data[n]
            px = d.loc[day, "c"] if day in d.index else d["c"].asof(day)
            mtm += p["qty"] * px
        concurrent.append(len(open_names))

        # 2) entries (alphabetical priority; ribbon before breakout per name)
        slots = MAX_POSITIONS - len(open_names)
        for name in sorted(data):
            st = states[name]
            if day not in data[name].index:
                continue
            row = data[name].loc[day]
            if pd.isna(row.atr) or pd.isna(row.ema200) or row.bar < 200:
                continue
            eligible = row.ema20 > row.ema50 > row.ema200 and row.c > row.ema200

            # ribbon arm state machine runs even when position/slots blocked?
            # In the single-name sim the machine only runs while FLAT; keep that.
            if st.pos is not None:
                continue
            tag = row.l <= row.ema20 + 0.5 * row.atr
            confirm = row.c > row.ema20 and row.c > row.o
            setup = eligible and tag
            trig_ribbon = eligible and confirm and (setup or st.arm > 0)
            st.arm = 0 if trig_ribbon else (
                3 if setup else (st.arm - 1 if (st.arm > 0 and eligible) else 0)
            )
            trig_break = (
                not pd.isna(row.anchor) and row.c > row.ema200 and row.c > row.anchor
            )
            if slots <= 0 or not (trig_ribbon or trig_break):
                continue

            if trig_ribbon:  # validated edge takes priority on a double signal
                stop = min(row.swlow - 0.25 * row.atr, row.c - 1.5 * row.atr)
                kind = "ribbon"
            else:
                stop = row.c - 2.5 * row.atr
                kind = "breakout"
            r = row.c - stop
            if r <= 0:
                continue
            qty = int(min(mtm * risk_pct / r, equity_cash / row.c))
            if qty < 1:
                continue
            notional = qty * row.c
            equity_cash -= notional
            st.pos = {
                "kind": kind, "qty": float(qty), "entry": row.c,
                "stop": stop, "target": row.c + 2.0 * r, "edate": day,
            }
            slots -= 1

        daily_equity.append((day, mtm))

    eq = pd.Series(dict(daily_equity)).sort_index()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    modern = eq[eq.index >= MODERN_ERA]
    myears = (modern.index[-1] - modern.index[0]).days / 365.25
    mcagr = (modern.iloc[-1] / modern.iloc[0]) ** (1 / myears) - 1
    dd = ((eq.cummax() - eq) / eq.cummax()).max()
    mdd = ((modern.cummax() - modern) / modern.cummax()).max()
    yearly = eq.resample("YE").last().pct_change().dropna()
    return {
        "risk": risk_pct, "trades": trades, "cagr": cagr, "modern_cagr": mcagr,
        "max_dd": dd, "modern_dd": mdd,
        "worst_year": yearly.min(), "best_year": yearly.max(),
        "neg_years": int((yearly < 0).sum()), "n_years": len(yearly),
        "avg_concurrent": float(np.mean(concurrent)),
        "yearly": yearly, "final": eq.iloc[-1],
    }


def main() -> int:
    data = {}
    for n in UNIVERSE:
        df = load(n)
        if df is not None:
            data[n] = prep(df)
    print(f"loaded {len(data)} names")

    for risk in (0.01, 0.015, 0.02):
        r = run_portfolio(data, risk)
        print(
            f"\nrisk={risk:.1%}  trades={r['trades']}  "
            f"avg concurrent={r['avg_concurrent']:.1f}\n"
            f"  CAGR 29y: {r['cagr']:.1%}   modern era (2013+): {r['modern_cagr']:.1%}\n"
            f"  maxDD 29y: {r['max_dd']:.1%}  modern maxDD: {r['modern_dd']:.1%}\n"
            f"  years: {r['n_years']}  negative years: {r['neg_years']}  "
            f"worst: {r['worst_year']:.1%}  best: {r['best_year']:.1%}\n"
            f"  final equity from 10L: {r['final']/1e7:.2f} crore"
        )
        if risk == 0.015:
            print("  yearly returns (2013+):")
            for ts, v in r["yearly"][r["yearly"].index >= MODERN_ERA].items():
                print(f"    {ts.year}: {v:+.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
