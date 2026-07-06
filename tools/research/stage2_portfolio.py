"""Stage-2 weekly PORTFOLIO simulation: one shared account, 39 names,
capital rotates into whichever names are in Stage 2.

- slots: max 10 concurrent positions, each sized to (equity / 10) at entry,
  capped by available cash (no leverage)
- entry: weekly close > max(prior 52 weekly closes), close > SMA30w, SMA30w
  rising vs 4 weeks ago; fill at weekly close; alphabetical priority
- exit: weekly close < SMA30w; fill at weekly close
- costs 0.25%/side; weekly mark-to-market; CAGR full period + modern (2013+)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path("data_cache")
MAX_SLOTS = 10
COST = 0.0025
START = 1_000_000.0
MODERN = pd.Timestamp("2013-01-01")

NAMES = sorted(
    ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "BHARTIARTL",
     "ITC", "LT", "HINDUNILVR", "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN",
     "ULTRACEMCO", "AXISBANK", "KOTAKBANK", "TATASTEEL", "ADANIGREEN",
     "WIPRO", "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND", "BAJAJFINSV",
     "ADANIPORTS", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "JSWSTEEL",
     "HINDALCO", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "BRITANNIA",
     "DABUR", "VEDL"]
)

data = {}
for n in NAMES:
    f = CACHE / f"{n}.csv"
    if not f.exists():
        continue
    d = pd.read_csv(f, index_col=0, parse_dates=True).dropna(subset=["Close"])
    w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
    if len(w) < 60:
        continue
    w["sma"] = w["c"].rolling(30).mean()
    w["anchor"] = w["c"].shift(1).rolling(52).max()
    w["rising"] = w["sma"] > w["sma"].shift(4)
    data[n] = w

calendar = sorted(set().union(*[set(w.index) for w in data.values()]))
cash = START
pos: dict[str, dict] = {}
curve = []
trades = 0

for wk in calendar:
    # exits
    for n in list(pos):
        w = data[n]
        if wk not in w.index:
            continue
        row = w.loc[wk]
        if pd.isna(row.sma):
            continue
        if row.c < row.sma:
            cash += row.c * pos[n]["qty"] * (1 - COST)
            del pos[n]
            trades += 1
    # mark to market
    mtm = cash
    for n, p in pos.items():
        w = data[n]
        px = w.loc[wk, "c"] if wk in w.index else w["c"].asof(wk)
        mtm += p["qty"] * px
    # entries
    for n in NAMES:
        if len(pos) >= MAX_SLOTS:
            break
        if n in pos or n not in data or wk not in data[n].index:
            continue
        row = data[n].loc[wk]
        if pd.isna(row.sma) or pd.isna(row.anchor) or not row.rising:
            continue
        if row.c > row.anchor and row.c > row.sma:
            alloc = min(mtm / MAX_SLOTS, cash)
            qty = int(alloc / (row.c * (1 + COST)))
            if qty < 1:
                continue
            cash -= row.c * qty * (1 + COST)
            pos[n] = {"qty": float(qty)}
    curve.append((wk, mtm))

eq = pd.Series(dict(curve)).sort_index()
yrs = (eq.index[-1] - eq.index[0]).days / 365.25
cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
mod = eq[eq.index >= MODERN]
myrs = (mod.index[-1] - mod.index[0]).days / 365.25
mcagr = (mod.iloc[-1] / mod.iloc[0]) ** (1 / myrs) - 1
dd = ((eq.cummax() - eq) / eq.cummax()).max()
mdd = ((mod.cummax() - mod) / mod.cummax()).max()
yearly = eq.resample("YE").last().pct_change().dropna()
myearly = yearly[yearly.index >= MODERN]

print(f"names loaded: {len(data)}  round-trips: {trades}")
print(f"FULL ~29y : CAGR {cagr:.1%}  maxDD {dd:.1%}  final {eq.iloc[-1]/1e7:.1f} cr")
print(f"MODERN 13+: CAGR {mcagr:.1%}  maxDD {mdd:.1%}  "
      f"neg years {(myearly < 0).sum()}/{len(myearly)}  worst {myearly.min():+.1%}")
print("modern yearly:", "  ".join(f"{t.year}:{v:+.0%}" for t, v in myearly.items()))
