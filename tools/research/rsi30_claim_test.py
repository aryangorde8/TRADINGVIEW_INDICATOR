"""Measure the claim: "when RSI is below 30, more than 80% of the time it
generates profit" — on NSE large caps, with the base rate alongside.

Also measures the overlap between RSI14<30 days and 52wk-breakout entry
days (mechanical compatibility of the proposed confluence).

Definition (stated before running): a "win" is close[t+10] > close[t]
(10 trading days forward). Universe = round-1 names. Both the conditional
rate AND the unconditional base rate are reported — the claim is only
meaningful relative to the base rate.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "SBIN", "BHARTIARTL", "ITC", "LT", "HINDUNILVR",
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "AXISBANK", "KOTAKBANK", "TATASTEEL", "ADANIGREEN",
]
HORIZON = 10
RSI_LEN = 14
ANCHOR_LEN = 252
EMA_LEN = 200


def wilder_rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = up / down
    return 100 - 100 / (1 + rs)


cond_wins = cond_n = base_wins = base_n = 0
breakout_days = breakout_with_rsi30 = 0

for name in UNIVERSE:
    df = yf.download(f"{name}.NS", period="max", interval="1d",
                     auto_adjust=True, progress=False, multi_level_index=False)
    if df is None or df.empty:
        continue
    df = df.dropna(subset=["Close"])
    close = df["Close"]
    rsi = wilder_rsi(close, RSI_LEN)
    fwd_win = close.shift(-HORIZON) > close
    valid = close.shift(-HORIZON).notna() & rsi.notna()

    cond = valid & (rsi < 30)
    cond_wins += int(fwd_win[cond].sum())
    cond_n += int(cond.sum())
    base_wins += int(fwd_win[valid].sum())
    base_n += int(valid.sum())

    ema = close.ewm(span=EMA_LEN, adjust=False).mean()
    anchor = close.shift(1).rolling(ANCHOR_LEN).max()
    breakout = (close > ema) & (close > anchor) & anchor.notna()
    breakout_days += int(breakout.sum())
    breakout_with_rsi30 += int((breakout & (rsi < 30)).sum())

print(f"days with RSI14<30:          {cond_n}")
print(f"  profitable {HORIZON}d later:      {cond_wins} ({100*cond_wins/cond_n:.1f}%)")
print(f"ALL days (base rate):        {base_n}")
print(f"  profitable {HORIZON}d later:      {base_wins} ({100*base_wins/base_n:.1f}%)")
print(f"52wk-breakout signal days:   {breakout_days}")
print(f"  of those with RSI14<30:    {breakout_with_rsi30}")
