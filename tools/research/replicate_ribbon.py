"""Independent replication of stock_swing_ribbon_pullback.pine (defaults:
light ribbon, pullback EMA20, runner OFF, long-only, fixed 2R).

Faithful to the Pine file:
- regime (light): EMA20 > EMA50 > EMA200 and close > EMA200
- tag:     low <= EMA20 + 0.5*ATR14
- confirm: close > EMA20 and close > open, on the tag bar or within a 3-bar
           armed window while the regime holds (armLong state machine ported
           line-for-line)
- stop:    min(swingLow(10) - 0.25*ATR, close - 1.5*ATR)  [wider of the two]
- target:  entry + 2R;  trend-break (regime lost) closes at that bar's close
- fills:   entry at signal-bar close (process_orders_on_close); stop/target
           active from the next bar; gap through a level fills at the open;
           same-bar stop+target ambiguity fills STOP FIRST (the conservative
           assumption the Pine header documents for TV)
- sizing:  risk 1% of compounding equity, no-leverage cap; costs 0.25%/side
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

UNIVERSE_R1 = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "SBIN", "BHARTIARTL", "ITC", "LT", "HINDUNILVR",
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "AXISBANK", "KOTAKBANK", "TATASTEEL", "ADANIGREEN",
]
UNIVERSE_OOS = [
    "WIPRO", "HCLTECH", "TECHM", "ASIANPAINT", "NESTLEIND",
    "BAJAJFINSV", "ADANIPORTS", "POWERGRID", "NTPC", "ONGC",
    "COALINDIA", "JSWSTEEL", "HINDALCO", "DRREDDY", "CIPLA",
    "EICHERMOT", "HEROMOTOCO", "BRITANNIA", "DABUR", "VEDL",
]

EMA_FAST, EMA_MID, EMA_SLOW = 20, 50, 200
ATR_LEN = 14
PULL_TOL_ATR = 0.5
CONFIRM_WIN = 3
SWING_LOOK = 10
SWING_BUF_ATR = 0.25
FLOOR_ATR = 1.5
RR_TARGET = 2.0
RISK_PCT = 0.01
COST_PER_SIDE = 0.0025
START_EQUITY = 1_000_000.0


def wilder_atr(df: pd.DataFrame, length: int) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [df["High"] - df["Low"], (df["High"] - prev_close).abs(),
         (df["Low"] - prev_close).abs()], axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def simulate(df: pd.DataFrame) -> list[dict]:
    close, high, low, open_ = df["Close"], df["High"], df["Low"], df["Open"]
    ema20 = close.ewm(span=EMA_FAST, adjust=False).mean()
    ema50 = close.ewm(span=EMA_MID, adjust=False).mean()
    ema200 = close.ewm(span=EMA_SLOW, adjust=False).mean()
    atr = wilder_atr(df, ATR_LEN)
    swing_low = low.rolling(SWING_LOOK).min()

    eligible = (ema20 > ema50) & (ema50 > ema200) & (close > ema200)
    tag = low <= ema20 + PULL_TOL_ATR * atr
    confirm = (close > ema20) & (close > open_)

    o, h, l, c = open_.values, high.values, low.values, close.values
    elig, tg, cf = eligible.values, tag.values, confirm.values
    dates = df.index

    trades: list[dict] = []
    equity = START_EQUITY
    in_pos = False
    entry_px = stop_px = target_px = qty = 0.0
    entry_date = None
    arm = 0

    for i in range(len(df)):
        if pd.isna(atr.iloc[i]) or pd.isna(ema200.iloc[i]) or i < EMA_SLOW:
            continue

        if in_pos:
            exit_px = reason = None
            if o[i] <= stop_px:
                exit_px, reason = o[i], "stop-gap"
            elif o[i] >= target_px:
                exit_px, reason = o[i], "target-gap"
            elif l[i] <= stop_px:               # stop first on same-bar ambiguity
                exit_px, reason = stop_px, "stop"
            elif h[i] >= target_px:
                exit_px, reason = target_px, "target"
            elif not elig[i]:                   # trend break -> close at close
                exit_px, reason = c[i], "trendBreak"
            if exit_px is not None:
                gross = (exit_px - entry_px) * qty
                costs = (entry_px + exit_px) * qty * COST_PER_SIDE
                pnl = gross - costs
                equity += pnl
                trades.append({
                    "Entry Date": entry_date.date(), "Exit Date": dates[i].date(),
                    "Entry": round(entry_px, 2), "Exit": round(exit_px, 2),
                    "Qty": int(qty), "Reason": reason, "Profit INR": round(pnl, 2),
                })
                in_pos = False
            continue

        # flat: state machine (ported from the Pine armLong lines)
        setup = elig[i] and tg[i]
        trig = elig[i] and cf[i] and (setup or arm > 0)
        arm = 0 if trig else (CONFIRM_WIN if setup else (arm - 1 if (arm > 0 and elig[i]) else 0))
        if not trig:
            continue

        struct_stop = swing_low.iloc[i] - SWING_BUF_ATR * atr.iloc[i]
        floor_stop = c[i] - FLOOR_ATR * atr.iloc[i]
        init_stop = min(struct_stop, floor_stop)
        r = c[i] - init_stop
        if r <= 0:
            continue
        shares = min(int(equity * RISK_PCT / r), int(equity / c[i]))
        if shares < 1:
            continue
        in_pos = True
        qty = float(shares)
        entry_px = c[i]
        entry_date = dates[i]
        stop_px = init_stop
        target_px = entry_px + RR_TARGET * r

    return trades


def run(universe: list[str], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in universe:
        df = None
        for attempt in range(3):
            try:
                df = yf.download(f"{name}.NS", period="max", interval="1d",
                                 auto_adjust=True, progress=False,
                                 multi_level_index=False)
                break
            except Exception:  # noqa: BLE001
                time.sleep(3)
        if df is None or df.empty or len(df) < EMA_SLOW + 50:
            print(f"{name}: insufficient data — skipped")
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        trades = simulate(df)
        pd.DataFrame(trades).to_csv(out_dir / f"{name.lower()}.csv", index=False)
        gp = sum(t["Profit INR"] for t in trades if t["Profit INR"] > 0)
        gl = -sum(t["Profit INR"] for t in trades if t["Profit INR"] < 0)
        pf = (gp / gl) if gl > 0 else float("inf")
        print(f"{name:<12} trades={len(trades):<5} PF={pf:.2f}")


if __name__ == "__main__":
    print("== round-1 universe ==")
    run(UNIVERSE_R1, Path("trades_ribbon"))
    print("== OOS universe ==")
    run(UNIVERSE_OOS, Path("trades_ribbon_oos"))
