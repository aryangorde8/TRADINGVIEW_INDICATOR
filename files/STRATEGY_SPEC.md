# STRATEGY_SPEC.md — What to build (trading logic)

## Scope
NIFTY index, 5-min, intraday only, directional via options (CE for up, PE for
down). No overnight. No averaging. One position at a time.

## Realistic target (restated)
Positive expectancy, >=1:2 R:R, robust across regimes. NOT a fixed win rate.

## CE/PE <-> long/short mapping (read this once, get it right everywhere)
In the strategy script, a "long" entry models a CE buy (profit when spot rises)
and a "short" entry models a PE buy (profit when spot falls). The Strategy Tester
measures DIRECTIONAL accuracy on spot. It does NOT model premium, theta, or IV.

## Layered gate architecture (keep it few-parameter and robust)
Reject the trade if any HARD gate fails.

GATE 1 — Bias (hard): direction must be unambiguous.
  Long-bias (enables CE) when: close > VWAP AND emaFast > emaSlow.
  Short-bias (enables PE) when: close < VWAP AND emaFast < emaSlow.
  Defaults: emaFast=9, emaSlow=21. Neutral/conflict => no trade.

GATE 2 — Trigger (hard): a momentum event in the bias direction.
  Selectable input `triggerMode`, exactly one active per run:
    "breakout" = close breaks prior N-bar high (CE) / low (PE), N default 10.
    "pullback" = price pulls back to emaFast then resumes in bias direction.

GATE 3 — Context (hard block): block if ANY are true.
  - Outside session window, or after the no-new-entry cutoff.
  - ATR < minAtr (dead range) OR ATR > maxAtr (news whipsaw) [maxAtr optional].
  - Within first `skipOpenBars` bars (default 2 -> skips 09:15–09:25 noise).
  - A trade already open.

(Optional SOFT score: any discretionary confluence — RSI slope, range position —
may only DELAY or SIZE a trade, never override a failed hard gate.)

## Entry
On the CONFIRMED close of a bar passing all gates:
  CE: `strategy.entry` long; print "BUY CE" label below the bar.
  PE: `strategy.entry` short; print "BUY PE" label above the bar.
Record entryPrice; compute initial stop and target immediately.

## Risk / exits (this defines R)
- Initial stop:
    CE: entry - atrMult*ATR (or below trigger-bar low, whichever is wider/structural).
    PE: entry + atrMult*ATR (mirror).
  R = |entry - stop|.
- Target: entry +/- rrTarget*R  (default 2R).
- Trailing: once price reaches +1R, move stop to breakeven; then trail by atrMult*ATR.
- Time stop: force-exit at 15:15 regardless.
- Opposite signal: if a valid opposite-bias entry triggers, exit current first.

## Exit signals (must render on chart)
EXIT CE fires on: CE stop hit OR target hit OR time stop OR opposite trigger.
EXIT PE fires symmetrically. Print "EXIT CE"/"EXIT PE" at the exit bar.
Put the exit reason (stop/target/time/flip) in the label tooltip.

## Plotting requirements
- Labels: BUY CE, BUY PE, EXIT CE, EXIT PE (distinct colors/shapes).
- Lines: live stop and target while a position is open.
- Optional toggle: VWAP + the two EMAs for visual context.

## Alerts
`alertcondition()`/`alert()` for each of the four events with descriptive messages
(symbol, price, reason) so they can be wired to automation/webhooks.

## Anti-overfitting rules (NON-NEGOTIABLE)
- Keep total tunable parameters small (<= ~8 core). More knobs = more curve-fit.
- Do NOT optimize defaults to maximize one date window.
- Validate over >=3 regimes and >=3 months (date sets in COMMANDS.md).
- Report trade count with every metric. Distrust win rates from < ~100 trades.

## Variants to generate for comparison (3 distinct families)
A. Trend-continuation breakout   (GATE2="breakout").
B. Trend-continuation pullback    (GATE2="pullback").
C. Momentum-only / no-counter-trend (bias + trigger, fewer higher-conviction entries).
Identical risk model across all three so comparison is apples-to-apples.
