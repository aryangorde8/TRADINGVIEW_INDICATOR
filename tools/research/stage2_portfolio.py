"""Stage-2 weekly PORTFOLIO simulation: one shared account, 39 names,
capital rotates into whichever names are in Stage 2.

- slots: max 10 concurrent positions, each sized to (equity / 10) at entry,
  capped by available cash (no leverage)
- entry: weekly close > max(prior 52 weekly closes), close > SMA30w, SMA30w
  rising vs 4 weeks ago; fill at weekly close; alphabetical priority
- exit: weekly close < SMA30w; fill at weekly close
- costs 0.25%/side; weekly mark-to-market

READ BEFORE CITING ANY NUMBER FROM THIS SCRIPT
----------------------------------------------
* Data is PINNED (data_cache/*.parquet, hashed in MANIFEST.md). It is no
  longer re-fetched, because auto_adjust=True restates the whole historical
  series on every split/dividend and silently moved past results.
* Only COMPLETED weekly bars are used (backported from stage2_scan.py:84).
  Previously the in-progress week was included, so the last bar changed
  depending on which weekday you ran the script.
* Fills are at the SIGNAL BAR'S OWN CLOSE — the same close that generates the
  signal. This is not lookahead (no future bar is read), but it is NOT
  EXECUTABLE: live, you would fill at the next open. Returns here are
  therefore optimistic by one bar's gap.
* Slot priority on more-signals-than-slots is ALPHABETICAL (NAMES is sorted).
  That is an arbitrary, untested rule, not a ranking.
* No stops. The only exit is the 30-week MA break. Sizing is equity/10, not
  risk-based.
* Universe = 39 large-cap NSE names that exist TODAY, tested backwards.
  Survivorship-biased by construction.

Outputs (committed): results/backtests/stage2_portfolio_equity.csv (date, nav)
and a printed summary reproduced in stage2_portfolio_snapshot.txt.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data_cache"          # pinned snapshot; see data_cache/MANIFEST.md
OUT = ROOT / "results" / "backtests" / "stage2_portfolio_equity.csv"

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


def load() -> dict[str, pd.DataFrame]:
    data: dict[str, pd.DataFrame] = {}
    for n in NAMES:
        pq, csv = CACHE / f"{n}.parquet", CACHE / f"{n}.csv"
        if pq.exists():
            d = pd.read_parquet(pq)
        elif csv.exists():
            d = pd.read_csv(csv, index_col=0, parse_dates=True)
        else:
            continue
        d = d.dropna(subset=["Close"])
        w = d["Close"].resample("W-FRI").last().dropna().to_frame("c")
        # Completed weeks only (see stage2_scan.py:84): a W-FRI label in the
        # future is a bar that has not closed yet.
        w = w[w.index <= pd.Timestamp.now()]
        if len(w) < 60:
            continue
        w["sma"] = w["c"].rolling(30).mean()
        w["anchor"] = w["c"].shift(1).rolling(52).max()
        w["rising"] = w["sma"] > w["sma"].shift(4)
        data[n] = w
    return data


def simulate(data: dict[str, pd.DataFrame]) -> tuple[pd.Series, int]:
    calendar = sorted(set().union(*[set(w.index) for w in data.values()]))
    cash = START
    pos: dict[str, dict] = {}
    curve: list[tuple[pd.Timestamp, float]] = []
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
        # entries (alphabetical priority — arbitrary, untested)
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

    return pd.Series(dict(curve)).sort_index(), trades


def cagr(start_nav: float, end_nav: float, years: float) -> float:
    return (end_nav / start_nav) ** (1 / years) - 1


def main() -> int:
    data = load()
    eq, trades = simulate(data)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    eq.rename("nav").rename_axis("date").to_csv(OUT)

    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    full_cagr = cagr(eq.iloc[0], eq.iloc[-1], yrs)
    dd = ((eq.cummax() - eq) / eq.cummax()).max()

    mod = eq[eq.index >= MODERN]
    myrs = (mod.index[-1] - mod.index[0]).days / 365.25
    mod_cagr = cagr(mod.iloc[0], mod.iloc[-1], myrs)
    mdd = ((mod.cummax() - mod) / mod.cummax()).max()

    yearly = eq.resample("YE").last().pct_change().dropna()
    last_year = eq.index[-1].year
    complete = yearly[(yearly.index.year >= 2013) & (yearly.index.year < last_year)]
    partial = yearly[yearly.index.year == last_year]

    def chain(rets: pd.Series) -> float:
        prod = float((1 + rets).prod())
        return prod ** (1 / len(rets)) - 1 if len(rets) else float("nan")

    complete_cagr = chain(complete)
    ex2020 = complete[complete.index.year != 2020]
    ex2020_cagr = chain(ex2020)

    print(f"names loaded: {len(data)}   round-trips: {trades}")
    print(f"period: {eq.index[0].date()} -> {eq.index[-1].date()}  ({yrs:.1f} years)")
    print(f"start NAV: {eq.iloc[0]:,.0f}   end NAV: {eq.iloc[-1]:,.0f} "
          f"({eq.iloc[-1] / eq.iloc[0]:.1f}x, {eq.iloc[-1] / 1e7:.1f} cr)")
    print()
    print(f"FULL PERIOD : CAGR {full_cagr:.1%}   maxDD {dd:.1%}")
    print(f"MODERN 2013+: CAGR {mod_cagr:.1%}   maxDD {mdd:.1%}   "
          f"(includes partial {last_year})")
    print()
    print(f"COMPLETE YEARS 2013-{last_year - 1} ({len(complete)} yrs): "
          f"CAGR {complete_cagr:.1%}")
    print(f"  ... excluding 2020 ({len(ex2020)} yrs): CAGR {ex2020_cagr:.1%}   "
          f"[2020 alone contributes {(complete_cagr - ex2020_cagr) * 100:+.1f}pp]")
    for t, v in partial.items():
        print(f"PARTIAL {t.year} (year to {eq.index[-1].date()}): {v:+.1%} "
              f"— NOT comparable to complete years")
    print()
    print("complete-year returns:",
          "  ".join(f"{t.year}:{v:+.0%}" for t, v in complete.items()))
    print(f"\nequity curve -> {OUT.relative_to(ROOT)} ({len(eq)} weekly rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
