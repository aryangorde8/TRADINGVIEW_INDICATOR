# CLAUDE.md — Project Constitution
# NIFTY 5-min Intraday Option-Buying Strategy (Pine Script v6)

## 0. Read order
Before writing ANY code, read these in order:
1. CLAUDE.md          (this file — rules, behavior, definition of done)
2. STRATEGY_SPEC.md   (what to build: entry/exit logic)
3. PINE_STANDARDS.md  (how to write it: v6 + anti-repaint + structure)
4. COMMANDS.md        (workflow: git, validation, variant comparison)
Then restate your understanding and ask clarifying questions BEFORE coding.

## 1. Goal (read literally — do not inflate it)
Build a non-repainting Pine Script v6 `strategy()` for NIFTY (spot/index) on the
5-minute timeframe that issues directional intraday signals:
  BUY CE   (open long-delta / call-buy bias)
  BUY PE   (open short-delta / put-buy bias)
  EXIT CE / EXIT PE  (close the corresponding position)
with ATR-defined stops and a minimum 1:2 reward:risk, instrumented so the
TradingView Strategy Tester reports honest performance metrics.

## 2. Hard truths baked into this project (DO NOT violate to chase numbers)
- This script runs on the NIFTY underlying, NOT on option premium. It cannot and
  must not claim option P&L. Strategy-Tester win rate is an UPPER BOUND on real
  CE/PE results, never a prediction. Theta/IV are out of scope.
- "80% accuracy" is NOT a target and must NOT be engineered toward. Any parameter
  set that hits an extreme win rate on one date window is overfit. Reject it.
- Target = POSITIVE EXPECTANCY with >=1:2 R:R, validated across >=3 distinct
  market regimes (trend up / trend down / chop) and >=3 separate months.
- A 40-trade sample cannot establish a win rate. Always report trade count next
  to every metric. Distrust any win rate from < ~100 trades.
- Repainting is an automatic FAIL (see PINE_STANDARDS.md).

## 3. How you (Claude Code) must work
- Iterative, phase by phase (see KICKOFF_PROMPT.md). One concern per phase.
- `git commit` BEFORE starting each change, and after each phase, using
  conventional-commit messages. Never batch unrelated changes.
- You cannot compile or unit-test Pine locally. Substitute = the self-review
  checklist in COMMANDS.md. Run it against your own code before every commit and
  paste the filled checklist in your message. Never claim you ran the backtest.
- When asked for variants, produce genuinely DIFFERENT strategy families, not the
  same logic with tweaked numbers. Then fill the comparison table in COMMANDS.md.
- Do not pad. Terse, technical, correct. If a requested thing is impossible in
  Pine, say so and propose the closest real alternative.

## 4. Tech constraints
- `//@version=6` only. One self-contained `.pine` file per variant.
- Script type: `strategy()` (so the tester yields win rate / profit factor / DD).
- Instrument: NIFTY index/spot, 5-min chart. No multi-symbol security leakage.
- All tunables exposed as `input.*` with groups + tooltips. Zero magic numbers.

## 5. SOLID, adapted to Pine
- Single responsibility: separate, clearly-named functions for
  (a) indicators/data, (b) entry-signal logic, (c) exit/risk logic, (d) plotting.
- Open/closed: behavior changes via inputs, not by editing hardcoded literals.
- No global mutable spaghetti; keep state in named `var` with clear scope.
- Pure functions where possible (same bar inputs -> same outputs, no hidden side
  effects), so logic is reviewable in isolation.

## 6. Global parameters (defaults — all overridable via inputs)
- Session: 09:20–15:10 IST; no NEW entries after 14:45; force-flat by 15:15.
- Timeframe: warn if chart TF != 5m.
- ATR length: 14. Stop = atrMult * ATR (default atrMult = 1.2).
- Reward:Risk: rrTarget = 2.0 (min). Trail arms at +1R.
- Risk filters: skip if ATR < minAtr (dead market); skip first `skipOpenBars`.
(Exact rule semantics live in STRATEGY_SPEC.md.)

## 7. Definition of Done (a variant is "done" only when ALL hold)
- Compiles in the Pine Editor with zero errors/warnings.
- Confirmed non-repainting (signals evaluated on bar close; no lookahead).
- Plots BUY CE / BUY PE / EXIT CE / EXIT PE labels + stop & target lines.
- `alertcondition()`/`alert()` present for all four events.
- Strategy Tester run over the 3 mandated regimes; metrics + trade counts
  recorded in the comparison table with screenshots referenced.
- Self-review checklist filled and pasted alongside the diff.
