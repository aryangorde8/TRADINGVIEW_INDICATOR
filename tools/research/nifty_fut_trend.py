"""NIFTY futures weekly trend system — registered before running.

RULES (same Stage-2 family, applied to the index):
- weekly close > max(prior 52 weekly closes) AND close > rising SMA30w -> LONG 1 lot
- exit on weekly close < SMA30w
- fills at weekly close

FUTURES MECHANICS (modelled honestly):
- lot size 75 (current NIFTY lot), notional = 75 * index
- SPAN+exposure margin ~13% of notional, marked to market weekly
- carry drag: long futures give price return minus (rf - dividend) carry;
  we charge 4%/yr carry on notional while in position, and credit 6%/yr
  liquid-fund yield on ALL idle cash (capital not consumed by MTM losses)
- costs: 0.02%/side on notional (futures are cheap; STT+brokerage+slippage)
- RUIN CHECK: if account equity < required margin while in position ->
  forced exit at that week's close, position cannot be re-established until
  equity recovers above margin + buffer

BAR (registered): PF >= 1.5 on the trade list; and a minimum-capital line
where 30 years of history produce ZERO forced liquidations. Below that
line the system is not tradeable regardless of PF.
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf

LOT = 75
MARGIN_PCT = 0.13
CARRY_YR = 0.04
CASH_YIELD_YR = 0.06
COST_SIDE = 0.0002

d = yf.download("^NSEI", period="max", interval="1d", auto_adjust=True,
                progress=False, multi_level_index=False)
w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
w = w[w.index <= pd.Timestamp.now()]
w["sma"] = w["c"].rolling(30).mean()
w["anchor"] = w["c"].shift(1).rolling(52).max()
w["rising"] = w["sma"] > w["sma"].shift(4)
print(f"NIFTY weekly bars: {len(w)}  ({w.index[0].date()} -> {w.index[-1].date()})")


def run(capital0: float) -> dict:
    cash = capital0
    in_pos = False
    entry_px = 0.0
    entry_date = None
    trades = []
    forced = 0
    curve = []
    for date, row in w.iterrows():
        if pd.isna(row.sma) or pd.isna(row.anchor):
            continue
        cash *= (1 + CASH_YIELD_YR / 52)          # idle-cash yield, weekly
        if in_pos:
            pnl_week = (row.c - entry_px) * LOT   # cumulative MTM vs entry
            equity = cash + pnl_week
            margin_req = MARGIN_PCT * LOT * row.c
            carry_week = CARRY_YR / 52 * LOT * row.c
            cash -= carry_week
            equity -= carry_week
            exit_now = row.c < row.sma
            forced_now = equity < margin_req
            if exit_now or forced_now:
                costs = COST_SIDE * LOT * (entry_px + row.c)
                cash += pnl_week - costs
                trades.append({"Entry Date": entry_date.date(),
                               "Exit Date": date.date(),
                               "Forced": forced_now and not exit_now,
                               "Profit INR": round(pnl_week - costs, 2)})
                if forced_now and not exit_now:
                    forced += 1
                in_pos = False
        else:
            margin_req = MARGIN_PCT * LOT * row.c
            if (row.c > row.anchor and row.c > row.sma and row.rising
                    and cash > margin_req * 1.25):
                in_pos = True
                entry_px = row.c
                entry_date = date
        curve.append((date, cash + ((row.c - entry_px) * LOT if in_pos else 0)))
    eq = pd.Series(dict(curve)).sort_index()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    profits = [t["Profit INR"] for t in trades]
    gp = sum(p for p in profits if p > 0)
    gl = -sum(p for p in profits if p < 0)
    return {
        "capital": capital0,
        "trades": len(trades),
        "pf": gp / gl if gl else float("inf"),
        "forced_liq": forced,
        "cagr": (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if eq.iloc[-1] > 0 else -1,
        "maxdd": ((eq.cummax() - eq) / eq.cummax()).max(),
        "final": eq.iloc[-1],
        "trade_rows": trades,
    }


for cap in (500_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000):
    r = run(cap)
    print(f"capital {cap/1e5:>4.0f}L: trades={r['trades']:<3} PF={r['pf']:.2f}  "
          f"forced-liq={r['forced_liq']}  CAGR={r['cagr']:+.1%}  "
          f"maxDD={r['maxdd']:.1%}  final={r['final']/1e5:.0f}L")

# write the trade list (capital-independent PF basis) for the auditor
base = run(3_000_000)
pd.DataFrame(base["trade_rows"]).to_csv("nifty_fut_trades.csv", index=False)
print("trade list -> nifty_fut_trades.csv")
