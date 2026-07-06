"""Stage-2 weekly trend rider — registered spec (decided before running):

- weekly bars (W-FRI resample of cached daily data)
- ENTRY: weekly close > max(prior 52 weekly closes) AND close > SMA30(weekly)
         AND SMA30 rising (> its value 4 weeks earlier); fill at weekly close
- EXIT:  weekly close < SMA30(weekly); fill at weekly close; NO profit target
- one position per name, full per-name equity (cash, no leverage), 0.25%/side
- BAR:   pooled date-sorted PF >= 1.5 on BOTH universes separately,
         CI low > 1.0, survives top-3 removal. FAIL => REJECT, no re-tuning.
- also reported: holding-period distribution (the >1-year requirement)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CACHE = Path("data_cache")
R1 = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "BHARTIARTL",
      "ITC", "LT", "HINDUNILVR", "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN",
      "ULTRACEMCO", "AXISBANK", "KOTAKBANK", "TATASTEEL", "ADANIGREEN"]
OOS = ["WIPRO", "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND", "BAJAJFINSV",
       "ADANIPORTS", "POWERGRID", "NTPC", "ONGC", "COALINDIA", "JSWSTEEL",
       "HINDALCO", "DRREDDY", "CIPLA", "EICHERMOT", "HEROMOTOCO", "BRITANNIA",
       "DABUR", "VEDL"]

COST = 0.0025
START = 1_000_000.0


def weekly(name: str) -> pd.DataFrame | None:
    f = CACHE / f"{name}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, index_col=0, parse_dates=True).dropna(subset=["Close"])
    w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
    if len(w) < 60:
        return None
    w["sma30"] = w["c"].rolling(30).mean()
    w["anchor"] = w["c"].shift(1).rolling(52).max()
    w["rising"] = w["sma30"] > w["sma30"].shift(4)
    return w


def simulate(w: pd.DataFrame) -> list[dict]:
    trades = []
    equity = START
    qty = 0.0
    entry_px = 0.0
    entry_date = None
    for date, row in w.iterrows():
        if pd.isna(row.sma30) or pd.isna(row.anchor):
            continue
        if qty > 0:
            if row.c < row.sma30:
                gross = (row.c - entry_px) * qty
                costs = (entry_px + row.c) * qty * COST
                pnl = gross - costs
                equity += entry_px * qty + pnl - entry_px * qty + 0  # equity += proceeds - cost basis handled below
                trades.append({
                    "Entry Date": entry_date.date(), "Exit Date": date.date(),
                    "Days Held": (date - entry_date).days,
                    "Entry": round(entry_px, 2), "Exit": round(row.c, 2),
                    "Profit INR": round(pnl, 2),
                })
                qty = 0.0
            continue
        if row.c > row.anchor and row.c > row.sma30 and row.rising:
            qty = equity // row.c
            if qty < 1:
                qty = 0.0
                continue
            entry_px = row.c
            entry_date = date
            equity -= 0  # cash accounting folded into pnl on exit
    return trades


def pf(profits: list[float]) -> float:
    gp = sum(p for p in profits if p > 0)
    gl = -sum(p for p in profits if p < 0)
    return gp / gl if gl else float("inf")


def run(universe: list[str], out: Path) -> None:
    out.mkdir(exist_ok=True)
    all_rows = []
    for n in universe:
        w = weekly(n)
        if w is None:
            print(f"{n}: no data")
            continue
        # equity compounding: re-run with proper cash accounting
        trades = []
        equity = START
        qty = 0.0
        entry_px = 0.0
        entry_date = None
        for date, row in w.iterrows():
            if pd.isna(row.sma30) or pd.isna(row.anchor):
                continue
            if qty > 0:
                if row.c < row.sma30:
                    proceeds = row.c * qty * (1 - COST)
                    equity += proceeds
                    cost_basis = entry_px * qty * (1 + COST)
                    pnl = proceeds - cost_basis
                    trades.append({
                        "Entry Date": entry_date.date(), "Exit Date": date.date(),
                        "Days Held": (date - entry_date).days,
                        "Entry": round(entry_px, 2), "Exit": round(row.c, 2),
                        "Profit INR": round(pnl, 2),
                    })
                    qty = 0.0
                continue
            if row.c > row.anchor and row.c > row.sma30 and row.rising:
                q = int(equity / (row.c * (1 + COST)))
                if q < 1:
                    continue
                qty = float(q)
                entry_px = row.c
                entry_date = date
                equity -= row.c * q * (1 + COST)
        df = pd.DataFrame(trades)
        df.to_csv(out / f"{n.lower()}.csv", index=False)
        if trades:
            profits = [t["Profit INR"] for t in trades]
            wins = [t for t in trades if t["Profit INR"] > 0]
            over1y = sum(1 for t in trades if t["Days Held"] > 365)
            med_win_hold = (pd.Series([t["Days Held"] for t in wins]).median()
                            if wins else 0)
            print(f"{n:<12} trades={len(trades):<4} PF={pf(profits):.2f}  "
                  f">1yr holds={over1y}/{len(trades)}  "
                  f"median winner hold={med_win_hold:.0f}d")
            all_rows.append(df)
    pooled = pd.concat(all_rows).sort_values("Entry Date")
    pooled.to_csv(out.with_suffix(".pooled.csv"), index=False)
    profits = pooled["Profit INR"].tolist()
    wins = pooled[pooled["Profit INR"] > 0]
    print(f"POOLED: {len(pooled)} trades  PF={pf(profits):.2f}  "
          f">1yr: {(pooled['Days Held'] > 365).mean():.0%} of all trades, "
          f"{(wins['Days Held'] > 365).mean():.0%} of winners  "
          f"median winner hold={wins['Days Held'].median():.0f}d "
          f"max={pooled['Days Held'].max()}d")


if __name__ == "__main__":
    print("== round-1 universe ==")
    run(R1, Path("stage2_r1"))
    print("\n== OOS universe ==")
    run(OOS, Path("stage2_oos"))
