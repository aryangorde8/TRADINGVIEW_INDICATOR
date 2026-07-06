#!/usr/bin/env python3
"""Weekly Stage-2 scanner — the monster-catching net.

    python3 tools/stage2_scan.py                     # scan built-in watchlist
    python3 tools/stage2_scan.py --watchlist my.txt  # one NSE symbol per line

A 50x move cannot happen without repeatedly making new 52-week-high weekly
closes above a rising 30-week SMA — so a Stage-2 scan over a WIDE universe
is mathematically guaranteed to surface every monster while it is still
running. The strategy never misses monsters; watchlists do. This tool makes
the watchlist as wide as your patience.

Run it once a week after Friday's close (free data via Yahoo). Output:
  NEW BREAKOUT — fired Stage-2 entry this week (candidates to buy per the
                 stock_stage2_trend_weekly.pine rules)
  IN STAGE-2   — already riding; hold list
  EXIT         — weekly close fell below the 30-week SMA this week

Liquidity gate: 3-month average daily turnover >= 5 cr INR (skip illiquid
names — smallcap circuits and impact costs eat systems alive).

Position discipline (from the tested portfolio sim): equal slots (~10% of
equity per name), max ~10 concurrent, never skip a signal because the last
one lost, never hold a name below its 30-week SMA.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

DEFAULT_WATCHLIST = """
RELIANCE HDFCBANK ICICIBANK INFY TCS SBIN BHARTIARTL ITC LT HINDUNILVR
BAJFINANCE MARUTI SUNPHARMA TITAN ULTRACEMCO AXISBANK KOTAKBANK TATASTEEL
ADANIGREEN WIPRO HCLTECH TECHM ASIANPAINT NESTLEIND BAJAJFINSV ADANIPORTS
POWERGRID NTPC ONGC COALINDIA JSWSTEEL HINDALCO DRREDDY CIPLA EICHERMOT
HEROMOTOCO BRITANNIA DABUR VEDL
SUZLON CGPOWER RVNL BSE CDSL MCX DIXON POLYCAB ASTRAL PERSISTENT COFORGE
TATAELXSI TIINDIA BALKRISIND CROMPTON INDHOTEL EXIDEIND VGUARD LEMONTREE
JUBLFOOD
TRENT DMART HAL BEL BHEL SIEMENS ABB TATAPOWER ADANIENT IRCTC CONCOR PIIND
SRF DEEPAKNTR UPL TATACHEM ALKEM TORNTPHARM LUPIN AUROPHARMA GLENMARK
BIOCON ZYDUSLIFE APOLLOHOSP MAXHEALTH FORTIS GODREJPROP DLF OBEROIRLTY
PHOENIXLTD PRESTIGE LODHA HAVELLS VOLTAS BLUESTARCO AMBER KAYNES MAZDOCK
COCHINSHIP GRSE IRFC RECLTD PFC HUDCO INDUSTOWER TATACOMM PVRINOX
BHARATFORG MOTHERSON SONACOMS TVSMOTOR ASHOKLEY ESCORTS M&M NATIONALUM
NMDC SAIL JINDALSTEL HINDZINC APLAPOLLO RATNAMANI KEI PAGEIND KPRMILL
SUPREMEIND AIAENG CUMMINSIND THERMAX SKFINDIA LTIM LTTS MPHASIS KPITTECH
TATATECH OFSS NAUKRI DATAPATTNS ZENTEC IREDA
""".split()

MIN_TURNOVER_CR = 5.0


def classify(name: str) -> tuple[str, str] | None:
    for attempt in range(2):
        try:
            d = yf.download(f"{name}.NS", period="2y", interval="1d",
                            auto_adjust=True, progress=False,
                            multi_level_index=False)
            break
        except Exception:  # noqa: BLE001
            if attempt:
                return None
            time.sleep(2)
    if d is None or d.empty or len(d) < 300:
        return None
    d = d.dropna(subset=["Close"])
    turnover_cr = (d["Close"] * d["Volume"]).tail(63).mean() / 1e7
    if turnover_cr < MIN_TURNOVER_CR:
        return None
    w = d["Close"].resample("W-FRI").last().dropna()
    # Judge COMPLETED weeks only: W-FRI labels each week by its Friday, so a
    # label in the future means the bar is still forming (e.g. a Monday run).
    # Signals on a partial week can un-fire by Friday — that's repainting.
    w = w[w.index <= pd.Timestamp.now()]
    if len(w) < 60:
        return None
    sma = w.rolling(30).mean()
    anchor = w.shift(1).rolling(52).max()
    rising = sma.iloc[-1] > sma.iloc[-5]
    c, s, a = w.iloc[-1], sma.iloc[-1], anchor.iloc[-1]
    prev_c, prev_s = w.iloc[-2], sma.iloc[-2]
    info = f"close {c:,.0f} | SMA30w {s:,.0f} | turnover {turnover_cr:.0f}cr/d"

    if c > a and c > s and rising and not (prev_c > anchor.iloc[-2]):
        return ("NEW BREAKOUT", f"{name:<12} {info}")
    if c > s and rising:
        return ("IN STAGE-2", f"{name:<12} {info}")
    if prev_c > prev_s and c < s:
        return ("EXIT", f"{name:<12} {info}")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly Stage-2 scanner")
    ap.add_argument("--watchlist", type=Path, default=None,
                    help="text file, one NSE symbol per line (no .NS suffix)")
    args = ap.parse_args()

    names = (
        [ln.strip().upper() for ln in args.watchlist.read_text().splitlines()
         if ln.strip() and not ln.startswith("#")]
        if args.watchlist else DEFAULT_WATCHLIST
    )
    print(f"scanning {len(names)} names (liquidity gate {MIN_TURNOVER_CR:.0f}cr/day)...",
          file=sys.stderr)

    groups: dict[str, list[str]] = {"NEW BREAKOUT": [], "IN STAGE-2": [], "EXIT": []}
    skipped = 0
    for n in names:
        r = classify(n)
        if r is None:
            skipped += 1
            continue
        groups[r[0]].append(r[1])

    for title in ("NEW BREAKOUT", "EXIT", "IN STAGE-2"):
        print(f"\n=== {title} ({len(groups[title])}) ===")
        for line in groups[title]:
            print("  " + line)
    print(f"\n(skipped {skipped}: no data / illiquid / delisted)")

    # Breadth thermometer: % of scanned names in Stage-2 is a free market
    # regime gauge. Appends one row per run; plot or eyeball the trend.
    scanned = len(names) - skipped
    if scanned > 0:
        breadth = 100.0 * (len(groups["IN STAGE-2"]) + len(groups["NEW BREAKOUT"])) / scanned
        log = Path(__file__).parent / "breadth_log.csv"
        new_file = not log.exists()
        with log.open("a") as f:
            if new_file:
                f.write("date,scanned,new_breakouts,in_stage2,exits,breadth_pct\n")
            f.write(
                f"{pd.Timestamp.now():%Y-%m-%d},{scanned},"
                f"{len(groups['NEW BREAKOUT'])},{len(groups['IN STAGE-2'])},"
                f"{len(groups['EXIT'])},{breadth:.1f}\n"
            )
        print(f"breadth: {breadth:.1f}% of scanned names in Stage-2 "
              f"(logged to {log.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
