#!/usr/bin/env python3
"""Percent-return audit of the committed pooled CSVs. NO NETWORK.

WHY THIS EXISTS
---------------
`replicate_stage2.py` resets `equity = START` inside the per-name loop, so each
name compounds its own independent account. Pooling the resulting `Profit INR`
column mixes trades taken at wildly different equity levels: a name that
compounded 50x emits rupee P&Ls two orders of magnitude larger than an early
trade elsewhere. Every rupee-denominated statistic (profit factor, expectancy,
bootstrap CI, drawdown) is therefore SIZE-WEIGHTED and uninterpretable as a
per-trade edge measure.

The fix is to work in percentage space, which is size-invariant. The committed
CSVs carry Entry and Exit prices, so the cost-adjusted per-trade return is
recoverable exactly:

    r = (Exit * (1 - COST)) / (Entry * (1 + COST)) - 1

Bootstrap parameters (seed 7, 1000 rounds) and the percentile convention are
copied from fallacy_auditor.profit so the two are directly comparable.

Usage:  python3 tools/research/percent_audit.py
"""

from __future__ import annotations

import random
import statistics
from pathlib import Path

import pandas as pd

COST = 0.0025
BOOTSTRAP_SEED = 7          # same as fallacy_auditor.profit
BOOTSTRAP_ROUNDS = 1000

ROOT = Path(__file__).resolve().parent.parent.parent
FILES = {
    "U1": ROOT / "results/backtests/stage2_universe1_pooled.csv",
    "U2": ROOT / "results/backtests/stage2_universe2_oos_pooled.csv",
}


def pf(values: list[float]) -> float | None:
    gp = sum(v for v in values if v > 0)
    gl = -sum(v for v in values if v < 0)
    return gp / gl if gl > 0 else None


def bootstrap_ci(values: list[float]) -> tuple[float | None, float | None]:
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_ROUNDS):
        p = pf(rng.choices(values, k=len(values)))
        if p is not None:
            samples.append(p)
    if len(samples) < BOOTSTRAP_ROUNDS // 2:
        return None, None
    samples.sort()
    return samples[int(0.025 * len(samples))], samples[int(0.975 * len(samples)) - 1]


def pf_excl_top(values: list[float], k: int) -> float | None:
    return pf(sorted(values)[: len(values) - k]) if len(values) > k else None


def max_consec_losses(values: list[float]) -> int:
    worst = streak = 0
    for v in values:
        streak = streak + 1 if v < 0 else 0
        worst = max(worst, streak)
    return worst


def audit(name: str, df: pd.DataFrame) -> dict:
    df = df.sort_values("Entry Date").reset_index(drop=True)

    rupees = df["Profit INR"].astype(float).tolist()
    r = ((df["Exit"] * (1 - COST)) / (df["Entry"] * (1 + COST)) - 1).tolist()

    half = len(r) // 2
    gross_pos = sum(x for x in r if x > 0)
    top_sorted = sorted((x for x in r if x > 0), reverse=True)

    wins_mask = [x > 0 for x in r]
    days = df["Days Held"].astype(float).tolist()
    win_days = [d for d, w in zip(days, wins_mask) if w]
    loss_days = [d for d, w in zip(days, wins_mask) if not w]

    lo, hi = bootstrap_ci(r)
    rlo, rhi = bootstrap_ci(rupees)
    q = lambda p: statistics.quantiles(r, n=100, method="inclusive")[p - 1]  # noqa: E731

    return {
        "name": name,
        "n": len(r),
        # --- rupee (the withdrawn figures) ---
        "rup_pf": pf(rupees),
        "rup_mean": statistics.mean(rupees),
        "rup_ci": (rlo, rhi),
        "rup_excl3": pf_excl_top(rupees, 3),
        # --- percent (the replacements) ---
        "pct_pf": pf(r),
        "pct_mean": statistics.mean(r),
        "pct_median": statistics.median(r),
        "pct_stdev": statistics.stdev(r),
        "pct_ci": (lo, hi),
        "pct_excl1": pf_excl_top(r, 1),
        "pct_excl3": pf_excl_top(r, 3),
        "pct_excl5": pf_excl_top(r, 5),
        "pct_first": pf(r[:half]),
        "pct_second": pf(r[half:]),
        "top1_share": (top_sorted[0] / gross_pos) if top_sorted else 0.0,
        "top3_share": (sum(top_sorted[:3]) / gross_pos) if len(top_sorted) >= 3 else 0.0,
        "dist": {
            "min": min(r), "p10": q(10), "p25": q(25), "p50": q(50),
            "p75": q(75), "p90": q(90), "max": max(r),
        },
        # --- unaffected by the size-weighting bug ---
        "win_rate": sum(wins_mask) / len(r),
        "max_consec_losses": max_consec_losses(r),
        "mean_hold_win": statistics.mean(win_days) if win_days else 0,
        "mean_hold_loss": statistics.mean(loss_days) if loss_days else 0,
    }


def fmt(v, pct=False, dec=2):
    if v is None:
        return "n/a"
    return f"{v * 100:.{dec}f}%" if pct else f"{v:.{dec}f}"


def main() -> int:
    results = [audit(k, pd.read_csv(v)) for k, v in FILES.items()]

    print("=" * 78)
    print("RUPEE vs PERCENT — the same trades, two measurement spaces")
    print("=" * 78)
    print(f"{'':<34}{'U1':>21}{'U2':>21}")
    print("-" * 78)

    def row(label, key, pct=False, dec=2, sub=None):
        cells = []
        for a in results:
            v = a[key] if sub is None else a[key][sub]
            cells.append(fmt(v, pct, dec))
        print(f"{label:<34}{cells[0]:>21}{cells[1]:>21}")

    print("RUPEE SPACE (size-weighted — WITHDRAWN)")
    row("  profit factor", "rup_pf")
    row("  PF excl top-3", "rup_excl3")
    row("  mean P&L per trade (INR)", "rup_mean", dec=0)
    for i, a in enumerate(results):
        lo, hi = a["rup_ci"]
        label = "  bootstrap 95% CI" if i == 0 else ""
        if i == 0:
            c0 = f"{fmt(lo)}-{fmt(hi)}"
            lo1, hi1 = results[1]["rup_ci"]
            c1 = f"{fmt(lo1)}-{fmt(hi1)}"
            print(f"{label:<34}{c0:>21}{c1:>21}")

    print("\nPERCENT SPACE (size-invariant — THE REPLACEMENT)")
    row("  profit factor", "pct_pf")
    row("  PF excl top-1", "pct_excl1")
    row("  PF excl top-3", "pct_excl3")
    row("  PF excl top-5", "pct_excl5")
    c0 = f"{fmt(results[0]['pct_ci'][0])}-{fmt(results[0]['pct_ci'][1])}"
    c1 = f"{fmt(results[1]['pct_ci'][0])}-{fmt(results[1]['pct_ci'][1])}"
    print(f"{'  bootstrap 95% CI':<34}{c0:>21}{c1:>21}")
    row("  PF first half", "pct_first")
    row("  PF second half", "pct_second")
    row("  mean return per trade", "pct_mean", pct=True)
    row("  median return per trade", "pct_median", pct=True)
    row("  stdev of returns", "pct_stdev", pct=True)
    row("  top-1 share of gross gain", "top1_share", pct=True, dec=1)
    row("  top-3 share of gross gain", "top3_share", pct=True, dec=1)

    print("\nDISTRIBUTION OF PER-TRADE RETURNS")
    for k in ("min", "p10", "p25", "p50", "p75", "p90", "max"):
        row(f"  {k}", "dist", pct=True, dec=1, sub=k)

    print("\nUNAFFECTED BY THE BUG (count-based, not size-based)")
    row("  trades", "n", dec=0)
    row("  win rate", "win_rate", pct=True, dec=1)
    row("  max consecutive losses", "max_consec_losses", dec=0)
    row("  mean hold, winners (days)", "mean_hold_win", dec=0)
    row("  mean hold, losers (days)", "mean_hold_loss", dec=0)
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
