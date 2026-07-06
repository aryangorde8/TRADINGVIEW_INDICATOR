"""Independent replication of the registered 52wk-breakout test.

Mirrors src/stock_swing_52wk_breakout.pine exactly:
- regime: close > EMA200 (pandas ewm, adjust=False == Pine ta.ema)
- anchor: highest of the PRIOR 252 closes
- entry:  close > anchor while flat, fill at that bar's close
- stop:   entry - 2.5 * ATR14 (Wilder RMA, == Pine ta.atr)
- target: entry + 2R
- fills:  TradingView broker-emulator bar path — if open is nearer the high,
          path is O-H-L-C (target checked before stop); else O-L-H-C.
          Gap through a level fills at the OPEN, as the emulator does.
- sizing: risk 1% of compounding per-symbol equity (start 10,00,000 INR),
          capped at no-leverage; costs 0.25%/side (0.2% commission + ~0.05%
          slippage) on notional.

Declared BEFORE running: universe of 20 liquid NSE large-caps (fixed below),
max available Yahoo history, no parameter changes. Output: one CSV per name
with a "Profit INR" column + entry/exit dates, consumable by
`python3 -m fallacy_auditor`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

UNIVERSE = [
    "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
    "SBIN", "BHARTIARTL", "ITC", "LT", "HINDUNILVR",
    "BAJFINANCE", "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO",
    "AXISBANK", "KOTAKBANK", "TATAMOTORS", "TATASTEEL", "ADANIGREEN",
]

EMA_LEN = 200
ANCHOR_LEN = 252
ATR_LEN = 14
STOP_ATR_MULT = 2.5
RR_TARGET = 2.0
RISK_PCT = 0.01
COST_PER_SIDE = 0.0025  # 0.2% commission + ~0.05% slippage
START_EQUITY = 1_000_000.0

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("trades_52wk_replication")


def wilder_atr(df: pd.DataFrame, length: int) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def simulate(df: pd.DataFrame) -> list[dict]:
    ema = df["Close"].ewm(span=EMA_LEN, adjust=False).mean()
    atr = wilder_atr(df, ATR_LEN)
    anchor = df["Close"].shift(1).rolling(ANCHOR_LEN).max()

    trades: list[dict] = []
    equity = START_EQUITY
    in_pos = False
    entry_px = stop_px = target_px = qty = 0.0
    entry_date = None

    o, h, l, c = df["Open"].values, df["High"].values, df["Low"].values, df["Close"].values
    dates = df.index

    for i in range(len(df)):
        if in_pos:
            exit_px = None
            reason = None
            # TV emulator bar path: open nearer the high -> O-H-L-C else O-L-H-C
            up_first = (h[i] - o[i]) <= (o[i] - l[i])  # False => high visited first
            checks = ["target", "stop"] if not up_first else ["stop", "target"]
            # gap fills at the open
            if o[i] <= stop_px:
                exit_px, reason = o[i], "stop-gap"
            elif o[i] >= target_px:
                exit_px, reason = o[i], "target-gap"
            else:
                for what in checks:
                    if what == "stop" and l[i] <= stop_px:
                        exit_px, reason = stop_px, "stop"
                        break
                    if what == "target" and h[i] >= target_px:
                        exit_px, reason = target_px, "target"
                        break
            if exit_px is not None:
                gross = (exit_px - entry_px) * qty
                costs = (entry_px + exit_px) * qty * COST_PER_SIDE
                pnl = gross - costs
                equity += pnl
                trades.append(
                    {
                        "Entry Date": entry_date.date(),
                        "Exit Date": dates[i].date(),
                        "Entry": round(entry_px, 2),
                        "Exit": round(exit_px, 2),
                        "Qty": int(qty),
                        "Reason": reason,
                        "Profit INR": round(pnl, 2),
                    }
                )
                in_pos = False
            continue

        # flat: entry check on this bar's close (fills at close, like
        # process_orders_on_close)
        if i < max(EMA_LEN, ANCHOR_LEN + 1, ATR_LEN):
            continue
        if pd.isna(anchor.iloc[i]) or pd.isna(atr.iloc[i]):
            continue
        if c[i] > ema.iloc[i] and c[i] > anchor.iloc[i]:
            stop_dist = STOP_ATR_MULT * atr.iloc[i]
            if stop_dist <= 0:
                continue
            risk_shares = int(equity * RISK_PCT / stop_dist)
            cap_shares = int(equity / c[i])
            q = max(min(risk_shares, cap_shares), 0)
            if q == 0:
                continue
            in_pos = True
            qty = float(q)
            entry_px = c[i]
            entry_date = dates[i]
            stop_px = entry_px - stop_dist
            target_px = entry_px + RR_TARGET * stop_dist

    return trades


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []
    for name in UNIVERSE:
        ticker = f"{name}.NS"
        for attempt in range(3):
            try:
                df = yf.download(
                    ticker, period="max", interval="1d",
                    auto_adjust=True, progress=False, multi_level_index=False,
                )
                break
            except Exception as exc:  # noqa: BLE001 — retry then surface
                if attempt == 2:
                    print(f"{name}: download failed: {exc}", file=sys.stderr)
                    df = None
                time.sleep(3)
        if df is None or df.empty or len(df) < ANCHOR_LEN + EMA_LEN // 2:
            print(f"{name}: insufficient data ({0 if df is None else len(df)} bars) — skipped")
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        trades = simulate(df)
        out = OUT_DIR / f"{name.lower()}.csv"
        pd.DataFrame(trades).to_csv(out, index=False)
        n = len(trades)
        gp = sum(t["Profit INR"] for t in trades if t["Profit INR"] > 0)
        gl = -sum(t["Profit INR"] for t in trades if t["Profit INR"] < 0)
        pf = (gp / gl) if gl > 0 else float("inf")
        summary.append((name, len(df), n, pf))
        print(f"{name:<12} bars={len(df):<6} trades={n:<4} PF={pf:.2f}")
    print(f"\n{len(summary)} names simulated -> {OUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
