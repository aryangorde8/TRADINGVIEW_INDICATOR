"""Live Magic-Formula-style value screen on liquid NSE non-financials.

Rank = rank(earnings yield, i.e. 1/PE) + rank(return on equity).
Filters: market cap >= 5,000 cr, 0 < trailing PE < 100, debt/equity < 1.0.
Financials excluded (ratios not comparable — standard Magic Formula rule).
For the top candidates, also compute the Stage-2 state (weekly close >
rising 30-week SMA) and distance from the 52-week closing high.

Data: Yahoo Finance, fetched live at run time. Screen output is a research
starting point, not advice — every name needs manual verification.
"""

from __future__ import annotations

import math

import pandas as pd
import yfinance as yf

UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM",
    "ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO",
    "GODREJCP", "TATACONSUM", "COLPAL", "ASIANPAINT", "BERGEPAINT",
    "PIDILITIND", "TITAN", "LT", "ULTRACEMCO", "GRASIM", "SHREECEM",
    "AMBUJACEM", "JSWSTEEL", "TATASTEEL", "HINDALCO", "VEDL", "HINDZINC",
    "NATIONALUM", "SAIL", "JINDALSTEL", "COALINDIA", "NMDC", "ONGC", "IOC",
    "BPCL", "HPCL", "GAIL", "NTPC", "POWERGRID", "TATAPOWER", "ADANIGREEN",
    "ADANIPORTS", "ADANIENT", "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB",
    "LUPIN", "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "GLENMARK", "BIOCON",
    "APOLLOHOSP", "MARUTI", "M&M", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO",
    "TVSMOTOR", "BHARATFORG", "MOTHERSON", "BOSCHLTD", "BHARTIARTL",
    "INDIGO", "DLF", "GODREJPROP", "OBEROIRLTY", "HAVELLS", "VOLTAS",
    "SIEMENS", "ABB", "BHEL", "BEL", "HAL", "IRCTC", "CONCOR", "DMART",
    "TRENT", "JUBLFOOD", "PAGEIND", "UPL", "PIIND", "SRF", "DEEPAKNTR",
    "TATACHEM", "EXIDEIND", "ASHOKLEY", "CUMMINSIND", "THERMAX",
]

MIN_MCAP = 5e10   # 5,000 cr INR
MAX_PE = 100.0
MAX_DE = 100.0    # yfinance debtToEquity is in percent

rows = []
for name in UNIVERSE:
    try:
        info = yf.Ticker(f"{name}.NS").info
    except Exception:  # noqa: BLE001
        continue
    pe = info.get("trailingPE")
    roe = info.get("returnOnEquity")
    de = info.get("debtToEquity")
    mcap = info.get("marketCap")
    pb = info.get("priceToBook")
    if not pe or not roe or not mcap:
        continue
    if not (0 < pe < MAX_PE) or mcap < MIN_MCAP:
        continue
    if de is not None and de > MAX_DE:
        continue
    rows.append({
        "name": name, "pe": pe, "ey": 100.0 / pe, "roe": roe * 100,
        "de": (de or 0) / 100, "pb": pb if pb else math.nan,
        "mcap_cr": mcap / 1e7,
    })

df = pd.DataFrame(rows)
df["rank_ey"] = df["ey"].rank(ascending=False)
df["rank_roe"] = df["roe"].rank(ascending=False)
df["magic"] = df["rank_ey"] + df["rank_roe"]
df = df.sort_values("magic").reset_index(drop=True)
top = df.head(15).copy()

# Stage-2 state for the top candidates only
flags = []
for name in top["name"]:
    try:
        h = yf.download(f"{name}.NS", period="2y", interval="1d",
                        auto_adjust=True, progress=False,
                        multi_level_index=False)
        w = h["Close"].resample("W-FRI").last().dropna()
        sma = w.rolling(30).mean()
        in_s2 = bool(w.iloc[-1] > sma.iloc[-1] and sma.iloc[-1] > sma.iloc[-5])
        below_hi = (w.iloc[-53:-1].max() - w.iloc[-1]) / w.iloc[-1] * 100
        flags.append(("STAGE-2" if in_s2 else "not-S2",
                      f"{max(below_hi, 0):.0f}% below 52wH"))
    except Exception:  # noqa: BLE001
        flags.append(("?", "?"))

top["stage"] = [f[0] for f in flags]
top["vs52wH"] = [f[1] for f in flags]

print(f"screened {len(UNIVERSE)} names, {len(df)} passed filters; top 15 by cheap+good rank:\n")
print(f"{'name':<12} {'PE':>6} {'earnYld%':>8} {'ROE%':>6} {'D/E':>5} "
      f"{'P/B':>6} {'mcap(cr)':>10}  {'trend state':<10} {'price vs 52w high'}")
for _, r in top.iterrows():
    print(f"{r['name']:<12} {r.pe:>6.1f} {r.ey:>8.1f} {r.roe:>6.1f} "
          f"{r.de:>5.2f} {r.pb:>6.1f} {r.mcap_cr:>10,.0f}  {r.stage:<10} {r.vs52wH}")
