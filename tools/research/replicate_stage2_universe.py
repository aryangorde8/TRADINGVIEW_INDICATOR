"""Stage-2 replication over an arbitrary watchlist (e.g. full Nifty 500).

    python3 replicate_stage2_universe.py ../watchlist_nifty500.txt out_dir

Same registered rules as replicate_stage2.py (weekly close > prior-52w-high
close, close > rising SMA30w; exit ALL on weekly close < SMA30w; full
per-name equity; 0.25%/side). Writes one trade CSV per name + pooled CSV,
prints breadth and pooled PF.

Survivorship caveat (stated up front): a watchlist of TODAY'S index members
tested backwards over-represents winners — treat pooled PF as an upper
bound; breadth (% of names PF>1) is the more robust readout.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE = Path("data_cache")
COST = 0.0025
START = 1_000_000.0


SUFFIX = ".NS"


def weekly(name: str) -> pd.DataFrame | None:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{name}.csv"
    if f.exists():
        d = pd.read_csv(f, index_col=0, parse_dates=True)
    else:
        d = None
        for _ in range(2):
            try:
                d = yf.download(f"{name}{SUFFIX}", period="max", interval="1d",
                                auto_adjust=True, progress=False,
                                multi_level_index=False)
                break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        if d is None or d.empty:
            return None
        d.to_csv(f)
    d = d.dropna(subset=["Close"])
    w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
    if len(w) < 90:
        return None
    w["sma"] = w["c"].rolling(30).mean()
    w["anchor"] = w["c"].shift(1).rolling(52).max()
    w["rising"] = w["sma"] > w["sma"].shift(4)
    return w


def simulate(w: pd.DataFrame, name: str) -> list[dict]:
    trades = []
    cash, qty, epx, edate = START, 0.0, 0.0, None
    for date, row in w.iterrows():
        if pd.isna(row.sma) or pd.isna(row.anchor):
            continue
        if qty > 0:
            if row.c < row.sma:
                proceeds = row.c * qty * (1 - COST)
                basis = epx * qty * (1 + COST)
                cash += proceeds
                trades.append({"Symbol": name,
                               "Entry Date": edate.date(),
                               "Exit Date": date.date(),
                               "Days Held": (date - edate).days,
                               "Profit INR": round(proceeds - basis, 2)})
                qty = 0.0
            continue
        if row.c > row.anchor and row.c > row.sma and row.rising:
            q = int(cash / (row.c * (1 + COST)))
            if q < 1:
                continue
            qty, epx, edate = float(q), row.c, date
            cash -= row.c * q * (1 + COST)
    return trades


def pf(profits) -> float:
    gp = sum(p for p in profits if p > 0)
    gl = -sum(p for p in profits if p < 0)
    return gp / gl if gl else float("inf")


def main() -> int:
    watchlist = Path(sys.argv[1])
    out = Path(sys.argv[2])
    global SUFFIX
    if len(sys.argv) > 3:
        SUFFIX = sys.argv[3]
    out.mkdir(exist_ok=True)
    names = [ln.strip().upper() for ln in watchlist.read_text().splitlines()
             if ln.strip() and not ln.startswith("#")]
    frames, profitable, tested = [], 0, 0
    for i, n in enumerate(names, 1):
        w = weekly(n)
        if w is None:
            continue
        trades = simulate(w, n)
        if not trades:
            continue
        tested += 1
        df = pd.DataFrame(trades)
        df.to_csv(out / f"{n.lower()}.csv", index=False)
        frames.append(df)
        if pf(df["Profit INR"].tolist()) > 1:
            profitable += 1
        if i % 50 == 0:
            print(f"...{i}/{len(names)} processed", file=sys.stderr)
    pooled = pd.concat(frames).sort_values("Entry Date")
    pooled.to_csv(out.with_suffix(".pooled.csv"), index=False)
    print(f"names tested: {tested}  breadth: {profitable}/{tested} PF>1 "
          f"({100*profitable/tested:.0f}%)")
    print(f"POOLED: {len(pooled)} trades  cumulative PF={pf(pooled['Profit INR'].tolist()):.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
