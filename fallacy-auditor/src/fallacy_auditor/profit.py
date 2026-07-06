"""Profit-factor audit for exported trade lists (deterministic, offline).

The LLM audits the *story*, the Pine linter audits the *code*, and this
module audits the *evidence*: the trade list a backtest produced. It does
not judge whether a strategy is good — it measures whether the headline
profit factor is fragile:

- luck concentration: PF recomputed without the top 1 / top 3 winners
- temporal stability: PF of the first half vs the second half of trades
- sample size: small trade counts make PF a lottery ticket
- bootstrap 95% CI: the range of PFs that pure resampling luck produces

Input: any CSV with a per-trade profit column (TradingView's "List of
Trades" export works as-is — entry rows with a blank profit cell are
skipped). Rows are assumed chronological; sort by date first if they are
not. Everything is standard library + pydantic; no network, no model.
"""

from __future__ import annotations

import csv
import io
import random

from pydantic import BaseModel, ConfigDict

SMALL_SAMPLE = 30
BOOTSTRAP_ROUNDS = 1000
BOOTSTRAP_SEED = 7  # fixed: the report must be reproducible


class TradeStats(BaseModel):
    """The profit-factor audit report."""

    model_config = ConfigDict(extra="forbid")

    trades: int
    wins: int
    losses: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None  # None when there are no losing trades
    expectancy: float  # mean profit per trade
    max_consecutive_losses: int
    max_drawdown: float  # worst peak-to-trough on the cumulative curve
    pf_first_half: float | None
    pf_second_half: float | None
    pf_excl_top1: float | None
    pf_excl_top3: float | None
    pf_ci_low: float | None  # bootstrap 95% CI over resampled trade lists
    pf_ci_high: float | None
    warnings: list[str]


def parse_trades_csv(text: str) -> list[float]:
    """Extract per-trade profits from a CSV/TSV, preserving row order.

    The delimiter is sniffed (comma, semicolon, or tab), so both a real CSV
    export and a table copy-pasted from TradingView's "List of Trades"
    (which pastes tab-separated) parse directly. The profit column is
    auto-detected: the first header containing "profit", "pnl", "p&l", or
    "net" that is not a percentage or a cumulative column. Blank /
    non-numeric cells (e.g. TradingView entry rows) are skipped; currency
    symbols and thousands separators are stripped.
    """
    try:
        dialect: csv.Dialect | type[csv.Dialect] = csv.Sniffer().sniff(
            text[:2048], delimiters=",;\t"
        )
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    def is_profit_column(name: str) -> bool:
        lower = name.lower()
        if "%" in lower or "cum" in lower:
            return False
        return any(key in lower for key in ("profit", "pnl", "p&l", "net"))

    column = next((n for n in reader.fieldnames if is_profit_column(n)), None)
    if column is None:
        raise ValueError(
            "no profit column found; headers are: "
            + ", ".join(reader.fieldnames)
        )

    strip_table = str.maketrans(
        {"−": "-", ",": None, " ": None, "₹": None, "$": None, "€": None, "£": None}
    )
    profits: list[float] = []
    for row in reader:
        cell = (row.get(column) or "").strip().translate(strip_table)
        if not cell:
            continue
        try:
            profits.append(float(cell))
        except ValueError:
            continue  # header repeats, stray text rows, etc.
    if not profits:
        raise ValueError(f"no numeric values in profit column {column!r}")
    return profits


def _profit_factor(profits: list[float]) -> float | None:
    gross_profit = sum(p for p in profits if p > 0)
    gross_loss = -sum(p for p in profits if p < 0)
    if gross_loss == 0:
        return None
    return gross_profit / gross_loss


def _excluding_top(profits: list[float], k: int) -> list[float]:
    return sorted(profits)[: len(profits) - k] if len(profits) > k else []


def _max_consecutive_losses(profits: list[float]) -> int:
    worst = streak = 0
    for p in profits:
        streak = streak + 1 if p < 0 else 0
        worst = max(worst, streak)
    return worst


def _max_drawdown(profits: list[float]) -> float:
    peak = cumulative = 0.0
    drawdown = 0.0
    for p in profits:
        cumulative += p
        peak = max(peak, cumulative)
        drawdown = max(drawdown, peak - cumulative)
    return drawdown


def _bootstrap_ci(profits: list[float]) -> tuple[float | None, float | None]:
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_ROUNDS):
        pf = _profit_factor(rng.choices(profits, k=len(profits)))
        if pf is not None:
            samples.append(pf)
    if len(samples) < BOOTSTRAP_ROUNDS // 2:
        return None, None  # too many all-win resamples to trust the CI
    samples.sort()
    return (
        samples[int(0.025 * len(samples))],
        samples[int(0.975 * len(samples)) - 1],
    )


def audit_trades(profits: list[float]) -> TradeStats:
    """Compute the profit factor and stress-test its fragility."""
    if not profits:
        raise ValueError("no trades to audit")

    n = len(profits)
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    gross_profit = sum(p for p in profits if p > 0)
    gross_loss = -sum(p for p in profits if p < 0)
    pf = _profit_factor(profits)
    half = n // 2
    pf_first = _profit_factor(profits[:half]) if half else None
    pf_second = _profit_factor(profits[half:]) if half else None
    pf_top1 = _profit_factor(_excluding_top(profits, 1))
    pf_top3 = _profit_factor(_excluding_top(profits, 3))
    ci_low, ci_high = _bootstrap_ci(profits)

    warnings: list[str] = []
    if n < SMALL_SAMPLE:
        warnings.append(
            f"only {n} trades — a profit factor on a sample this small is "
            "dominated by luck (the base-rate problem in trade form)"
        )
    if pf is None:
        warnings.append(
            "no losing trades at all — either the sample is tiny or the "
            "backtest is broken; treat the result as unverified"
        )
    elif pf < 1.0:
        warnings.append("profit factor below 1.0 — gross losses exceed gross profits")
    if pf is not None and pf >= 1.0 and pf_top3 is not None and pf_top3 < 1.0:
        warnings.append(
            "fragile edge: removing the top 3 winners drops the profit "
            "factor below 1.0 — the result is concentrated in a few trades"
        )
    if profits and gross_profit > 0 and max(profits) > 0.5 * gross_profit:
        warnings.append(
            "a single trade contributes more than half of all gross profit"
        )
    if (
        pf is not None
        and pf >= 1.0
        and (
            (pf_first is not None and pf_first < 1.0)
            or (pf_second is not None and pf_second < 1.0)
        )
    ):
        warnings.append(
            "unstable across time: one half of the trade history has a "
            "profit factor below 1.0 despite the overall result"
        )
    if ci_low is not None and ci_low < 1.0 <= (pf or 0):
        warnings.append(
            "the bootstrap 95% confidence interval reaches below 1.0 — "
            "resampling luck alone can erase this edge"
        )

    return TradeStats(
        trades=n,
        wins=wins,
        losses=losses,
        win_rate=wins / n,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=pf,
        expectancy=sum(profits) / n,
        max_consecutive_losses=_max_consecutive_losses(profits),
        max_drawdown=_max_drawdown(profits),
        pf_first_half=pf_first,
        pf_second_half=pf_second,
        pf_excl_top1=pf_top1,
        pf_excl_top3=pf_top3,
        pf_ci_low=ci_low,
        pf_ci_high=ci_high,
        warnings=warnings,
    )


def format_report(stats: TradeStats) -> str:
    """Human-readable report."""

    def fmt(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.2f}"

    lines = [
        f"trades: {stats.trades}  wins: {stats.wins}  losses: {stats.losses}  "
        f"win rate: {stats.win_rate:.1%}",
        f"gross profit: {stats.gross_profit:.2f}  gross loss: {stats.gross_loss:.2f}",
        f"PROFIT FACTOR: {fmt(stats.profit_factor)}   "
        f"(bootstrap 95% CI: {fmt(stats.pf_ci_low)} .. {fmt(stats.pf_ci_high)})",
        f"expectancy/trade: {stats.expectancy:.2f}  "
        f"max consecutive losses: {stats.max_consecutive_losses}  "
        f"max drawdown: {stats.max_drawdown:.2f}",
        "robustness:",
        f"  PF first half: {fmt(stats.pf_first_half)}   "
        f"second half: {fmt(stats.pf_second_half)}",
        f"  PF without top winner: {fmt(stats.pf_excl_top1)}   "
        f"without top 3: {fmt(stats.pf_excl_top3)}",
    ]
    for warning in stats.warnings:
        lines.append(f"WARNING: {warning}")
    if not stats.warnings:
        lines.append("no fragility warnings")
    return "\n".join(lines)
