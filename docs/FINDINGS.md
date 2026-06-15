# FINDINGS — NIFTY Intraday Options-Directional Strategy (FINAL)

**Status: CLOSED — terminal negative result.** This is the real deliverable of the
project. Every file (5m A/B/C, 5m B-RUNNER, 15m runner) is final; no further work on
intraday directional.

Instrument: `NSE:NIFTY1!` (continuous NIFTY futures). Tested on 5m and 15m.
All numbers were produced by the human in TradingView's Strategy Tester; there is no
local Pine compiler. Strategy-Tester win rate is a directional **upper bound** on
real CE/PE option P&L — premium, theta and IV are not modelled.

---

## 0. Goal — stated, then corrected
The project opened wanting high directional accuracy ("80%") at ≥1:2 reward:risk.
That was corrected to a sound objective early and held throughout: **positive
expectancy at ≥1:2 R:R, judged on profit factor / expectancy / MFE — never a win
rate.**

**Why 80% is impossible (not just hard):** at 1:2 (win +2R, lose −1R), an 80% hit
rate implies expectancy `0.8·(+2) + 0.2·(−1) = +1.4R per trade`. A +1.4R/trade
edge on a liquid index would be the best public strategy in existence. It does not
exist at any timeframe. We never engineered toward a win rate, and we explicitly
refused to stack confluence gates to inflate one (that path manufactures overfit,
not edge).

---

## 1. Entries tested (5m) — three different triggers, one clean harness
Identical GATE-1 bias (VWAP/SessionAvg + EMA cross), GATE-3 context, fixed −1R ATR
stop / +2R target (trail off, `minAtr=0`); only the GATE-2 trigger differs.

| Entry | Trigger | Clean-bracket win rate | Profit factor |
|---|---|---|---|
| A | Breakout (close > prior-N high, `[1]`-offset) | ~34.5% | 0.69 |
| B | Pullback to fast-EMA, then resume | 36.5% (101/277) | 0.67 |
| C | Supertrend flip (`ta.supertrend` crossover) | 34.4% | 0.75 |

The 1:2 breakeven is ~35%. **All three sit on the breakeven line, CIs straddling
it — a directional coin flip, three ways.** Exit-reason counters confirmed no leak:
winners reached +2R (avg ≈ +1.7 to +1.9R), losers ≈ −1R. `minAtr` cannot help —
chop-bar ATR and PE-trade ATR fully overlap (no volatility gap to filter on).

---

## 2. Exits tested (5m) — fixed target vs partial + runner (on the B entry)
The MFE study showed moves *exist* past 2R, so the second axis was the exit.

| Exit | Profit factor | Result |
|---|---|---|
| Fixed 2R bracket | 0.673 | loses |
| Partial book @2R + loose chandelier runner | 0.63 | loses |

The runner trimmed the net loss (it stops dumping every winner at 2R) but **PF did
not improve — it fell.** Both lose.

---

## 3. MFE (5m) and why the runner still failed
Max favorable excursion of every B entry (277 trades), measured **ignoring** the 2R
target (shadow-tracked to the −1R stop or 15:15):

| Reached | ≥1R | ≥2R | ≥3R | ≥4R | ≥5R |
|---|---|---|---|---|---|
| % of trades | 53.1% | 33.6% | **20.6%** | **11.9%** | **5.4%** |

The tail is **reachable but not harvestable.** ~47% never reach +1R; only ~21%
reach ≥3R. To give that ~20% tail a chance, the runner must hold every trade — and
the ~80% that round-trip (give back to breakeven / the −1R stop / the time-stop)
**cost more than the ~20% tail pays.** The loose chandelier hands back a slice of
each runner on exit, and half the position is already capped at the 2R book. A ~35%
hit rate is simply too low for any exit scheme to monetize. **Fixing the payoff side
cannot fix a coin-flip entry.**

---

## 4. 15m re-test — the higher-timeframe hypothesis, falsified
Hypothesis: 15m trends sustain longer than 5m, so the runner's tail might be fatter
and harvestable. Same harness, only TF + sessions re-tuned. Window: **Aug 2025 –
Jun 2026.**

| Reached | ≥3R | ≥4R | ≥5R |
|---|---|---|---|
| 5m  | 20.6% | 11.9% | 5.4% |
| 15m | **18.5%** | **4.4%** | **1.3%** |

The 15m tail is **THINNER, not fatter.** PF **0.714**, net −4.36 L. The hypothesis
is falsified — the runner has *less* to capture on 15m than on 5m.

---

## 5. Verdict
**NIFTY intraday directional trading on simple price/trend signals has no
recoverable edge — across 3 entries, 2 exits, and 2 timeframes (5m, 15m).** Every
combination loses by a consistent margin, confirmed by measurement (exit-reason
counters + MFE shadow-tracking), not assumed. We stop here.

---

## 6. Method note — these numbers are an optimistic ceiling
All results are on **futures**, which is an **upper bound** on real CE/PE option
performance. Buying options adds theta decay and IV moves that tax a directional
position further. So actual option results from these signals would be **worse than
the already-negative numbers above.** There is no hidden upside being missed.

---

## 7. Where edge might actually live — NEXT PROJECTS (each its own honest harness)
Not continued here. Each is a *new* project with the same discipline (clean
fixed-bracket baseline, exit-reason + MFE instrumentation, ≥~100 trades, reject
single-window flukes, no win-rate engineering):

- **Daily / swing timeframe.** Intraday noise dominates 5m/15m; trends persist over
  days/weeks. Re-test the same harness there before anything fancy.
- **Mean-reversion, not continuation.** Price *reverts*: fade the 2R extension
  rather than chase it. This is the opposite hypothesis to everything tested here
  and deserves a clean test of its own.
- **Non-directional / volatility structures.** This was always *for* options — the
  edge may be in the payoff instrument: defined-risk spreads, premium selling
  (theta), IV-crush/event setups — where a directional coin flip is irrelevant.

Carried-forward discipline: 80% accuracy was never the goal and is mathematically
out of reach; the goal is positive expectancy at ≥1:2 — which NIFTY intraday simple
directional does not provide on either axis at either timeframe tested.

---

## Files (all CLOSED)
- `src/nifty_fut_5m_A_breakout.pine` — Variant A (breakout entry)
- `src/nifty_fut_5m_B_pullback.pine` — Variant B (pullback entry)
- `src/nifty_fut_5m_C_supertrend.pine` — Variant C (supertrend-flip entry)
- `src/nifty_fut_5m_B_runner.pine` — B entry + partial/runner exit (5m)
- `src/nifty_15m_runner.pine` — same harness, 15m
- `src/version 6 NIFTY 5M v12.c` — external idea source (pullback/supertrend); never adopted wholesale
