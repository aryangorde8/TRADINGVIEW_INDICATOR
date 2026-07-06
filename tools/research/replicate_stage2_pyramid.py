"""Stage-2 MONSTER RIDER: pyramiding variant — registered before running.

Base rules = tested Stage-2 (weekly close > prior-52w-high close, close >
rising SMA30w; exit ALL on weekly close < SMA30w). Structural addition:
- up to 3 units per name; allocation 40% / 30% / 30% of current equity
- unit 2/3 added only on a FRESH 52w-closing-high breakout >= 4 weeks after
  the previous buy, while still above the rising SMA30w
- each unit recorded as its own trade (own entry price) for PF accounting

BAR (registered): pooled PF >= 1.5 both universes, CI low > 1, top-3
survival, AND terminal equity beats plain Stage-2 on BOTH universes.
FAIL => plain Stage-2 stands. No re-tuning.
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
ALLOC = [0.40, 0.30, 0.30]
MIN_WEEKS_BETWEEN_ADDS = 4


def weekly(name: str) -> pd.DataFrame | None:
    f = CACHE / f"{name}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, index_col=0, parse_dates=True).dropna(subset=["Close"])
    w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
    if len(w) < 60:
        return None
    w["sma"] = w["c"].rolling(30).mean()
    w["anchor"] = w["c"].shift(1).rolling(52).max()
    w["rising"] = w["sma"] > w["sma"].shift(4)
    return w


def simulate(w: pd.DataFrame) -> tuple[list[dict], float]:
    trades: list[dict] = []
    cash = START
    units: list[dict] = []          # {qty, entry, edate}
    weeks_since_buy = 99
    for date, row in w.iterrows():
        weeks_since_buy += 1
        if pd.isna(row.sma) or pd.isna(row.anchor):
            continue
        open_val = sum(u["qty"] * row.c for u in units)
        equity = cash + open_val

        if units and row.c < row.sma:                      # exit everything
            for u in units:
                proceeds = row.c * u["qty"] * (1 - COST)
                basis = u["entry"] * u["qty"] * (1 + COST)
                cash += proceeds
                trades.append({
                    "Entry Date": u["edate"].date(), "Exit Date": date.date(),
                    "Days Held": (date - u["edate"]).days,
                    "Unit": u["unit"], "Entry": round(u["entry"], 2),
                    "Exit": round(row.c, 2),
                    "Profit INR": round(proceeds - basis, 2),
                })
            units = []
            continue

        breakout = row.c > row.anchor and row.c > row.sma and row.rising
        can_add = (
            breakout
            and len(units) < len(ALLOC)
            and weeks_since_buy >= (MIN_WEEKS_BETWEEN_ADDS if units else 0)
        )
        if can_add:
            alloc = min(equity * ALLOC[len(units)], cash)
            qty = int(alloc / (row.c * (1 + COST)))
            if qty >= 1:
                cash -= row.c * qty * (1 + COST)
                units.append({"qty": float(qty), "entry": row.c,
                              "edate": date, "unit": len(units) + 1})
                weeks_since_buy = 0
    final = cash + sum(u["qty"] * w["c"].iloc[-1] for u in units)
    return trades, final


def pf(profits: list[float]) -> float:
    gp = sum(p for p in profits if p > 0)
    gl = -sum(p for p in profits if p < 0)
    return gp / gl if gl else float("inf")


def run(universe: list[str], tag: str) -> None:
    out = Path(f"stage2pyr_{tag}")
    out.mkdir(exist_ok=True)
    frames = []
    finals = {}
    for n in universe:
        w = weekly(n)
        if w is None:
            continue
        trades, final = simulate(w)
        finals[n] = final
        df = pd.DataFrame(trades)
        df.to_csv(out / f"{n.lower()}.csv", index=False)
        if trades:
            frames.append(df)
    pooled = pd.concat(frames).sort_values("Entry Date")
    pooled.to_csv(f"stage2pyr_{tag}.pooled.csv", index=False)
    total_final = sum(finals.values())
    adds = (pooled["Unit"] > 1).mean()
    print(f"[{tag}] pooled trades={len(pooled)}  PF={pf(pooled['Profit INR'].tolist()):.2f}  "
          f"adds={adds:.0%} of units  Σ final equity={total_final/1e7:.1f} cr")
    for special in ("ADANIGREEN", "BAJFINANCE", "SUNPHARMA", "EICHERMOT"):
        if special in finals:
            print(f"    {special}: final {finals[special]/1e7:.2f} cr")


if __name__ == "__main__":
    run(R1, "r1")
    run(OOS, "oos")
