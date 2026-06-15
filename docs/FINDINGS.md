# FINDINGS — NIFTY Intraday Directional/Reversion Strategy (FINAL)

**Status: CLOSED — terminal negative result, solution space exhausted.** This is the
real deliverable of the project. All files (5m A/B/C, 5m B-RUNNER, 15m runner, 5m
trend-pullback, 5m pure-reversion) are final. No further 5m/15m intraday entry work.

Instrument: `NSE:NIFTY1!` (continuous NIFTY futures), 5m and 15m, intraday only
(force-flat 15:15, no overnight). All numbers were produced by the human in
TradingView's Strategy Tester (no local Pine compiler). Tester win rate is a
directional **UPPER BOUND** on real CE/PE option P&L — premium, theta, IV and Indian
transaction costs (brokerage/STT) are not modelled and make real results worse.

---

## 0. Goal — stated, then corrected
The project opened wanting high directional accuracy ("80%") at ≥1:2 R:R. That was
corrected early to a sound objective and held throughout: **positive expectancy at
≥1:2, judged on profit factor / expectancy / MFE — never a win rate.**

**Why 80% is impossible (not merely hard):** at 1:2 (win +2R, lose −1R), an 80% hit
rate implies expectancy `0.8·(+2) + 0.2·(−1) = +1.4R per trade` — a magnitude of edge
that does not exist on a liquid index at any timeframe. We never engineered toward a
win rate and explicitly refused confluence-gate stacking (which manufactures overfit,
not edge).

---

## 1. Full results — every combination loses
**5 entries** (5m, clean fixed bracket unless noted) — win rate and profit factor:

| # | Entry | Family | Win rate | PF | Notes |
|---|---|---|---|---|---|
| 1 | Breakout (close > prior-N high) | trend-follow | ~34.5% | 0.69 | |
| 2 | Pullback to fast-EMA | trend-follow | 36.5% (101/277) | 0.67 | |
| 3 | Supertrend flip | trend-follow | 34.4% | 0.75 | |
| 4 | Trend-aligned reversion (buy-dip/sell-rip) | with-trend revert | 41% (41 trades) | 0.78 | best WR, still loses |
| 5 | Pure reversion (fade extension, no trend gate) | counter-trend | **0/11** | **0.00** | every exit a loss |

All sit at/under the ~35% breakeven for 1:2; the one that broke 40% (entry 4) still
had PF<0.8. The counter-trend opposite bet (entry 5) performed **worst** of all.

**3 exits** (tested on the pullback / trend-pullback entries) — none reach PF>1.0:

| Exit | PF | Result |
|---|---|---|
| Fixed 2R bracket | 0.67 | loses |
| Fixed 2.5R bracket | 0.80 | loses |
| Partial book + chandelier runner | 0.63 (5m) / <1.0 | loses |

**2 timeframes:** 5m (above) and **15m** (runner): PF **0.714**, and the MFE tail came
out **thinner** than 5m, not fatter — falsifying the "higher timeframe sustains" idea.

---

## 2. MFE — the tail exists but is not harvestable
Max favorable excursion (shadow-tracked, ignoring the target), % of trades reaching:

| Reached | 5m pullback | 5m trend-revert | 15m |
|---|---|---|---|
| ≥2R | 33.6% | 22% | — |
| ≥3R | 20.6% | 12.2% | 18.5% |
| ≥4R | 11.9% | 7.3% | 4.4% |
| ≥5R | 5.4% | 7.3% | 1.3% |

The 3R–5R tail is real but **too thin/infrequent**: to give the ~20% tail a chance the
runner must hold every trade, and the ~80% that round-trip (to breakeven / −1R / time)
cost more than the tail pays. Confirmed by the runner runs (PF fell, not rose).

---

## 3. Why it fails (mechanism)
NIFTY 5m moves ~2R and then reverts — but **the reversion is not tradeable at the bar
level with a stop**:
- **Trend-following** (entries 1–3) enters *after* the move is underway; on 5m the
  continuation doesn't sustain — price reverts before a 2R target, so a −1R stop or
  the reversion takes it out. ~35% hit rate, coin-flip.
- **Counter-trend** (entries 4–5) fades the extension, but **extensions carry through**
  on 5m — the fade keeps extending into the −1R stop. Pure reversion (entry 5) was
  0/11; even an ADX>30 guard didn't help, because "non-trending" extensions still
  don't revert enough to clear a stop before reversing.

Both directions of the bet fail for the same underlying reason: at the 5m bar level,
the move that exists is not capturable net of a protective stop.

---

## 4. Cost reality — the numbers are an optimistic ceiling
Everything is measured on **futures**, an **upper bound** on real CE/PE option results.
Buying options adds **theta decay + IV moves**; Indian costs add **brokerage + STT +
exchange/SEBI charges + slippage**. So actual option P&L from these signals would be
**materially worse than the already-negative numbers above.** There is no hidden upside.

---

## 5. Verdict
**NIFTY 5m/15m intraday directional + reversion on simple price/trend/oscillator
signals has no recoverable edge — across 5 entries, 3 exits, and 2 timeframes.**
Exhaustively and honestly tested with instrumentation (exit-reason counters, MFE
shadow-tracking, entry funnels), not assumed. There is no 6th entry variant worth
trying in this space; we stop.

---

## 6. Where to go next — NEW projects, NOT more 5m entries
- **Different INSTRUMENT that trends better intraday.** Reuse this exact harness on a
  high-intraday-momentum stock or a more directional index, and test whether the
  directional logic works where NIFTY's mean-reverting 5m chop killed it. (Cheapest
  next step — the harness is built and instrumented.)
- **NON-DIRECTIONAL option structures.** Spreads, premium-selling / theta, IV-crush
  and event setups — payoffs that don't depend on directional accuracy at all, which
  sidesteps this entire dead end. This was always *for* options; the edge may live in
  the instrument's payoff, not in calling direction.
- **Higher timeframe (daily/swing)** where trends genuinely sustain — but this needs
  overnight holding, which the project rules out, so it is **off-table unless that
  constraint changes.**

Carried-forward discipline: clean fixed-bracket baseline first; exit-reason + MFE
instrumentation; ≥~100 trades before trusting a rate; reject single-window flukes; no
win-rate engineering, no gate-stacking. 80% accuracy was never the goal and is out of
reach; positive expectancy at ≥1:2 is the goal — which NIFTY intraday simple
directional/reversion does not provide.

---

## Files (all CLOSED)
- `src/nifty_fut_5m_A_breakout.pine` — entry 1 (breakout)
- `src/nifty_fut_5m_B_pullback.pine` — entry 2 (pullback)
- `src/nifty_fut_5m_C_supertrend.pine` — entry 3 (supertrend flip)
- `src/nifty_fut_5m_B_runner.pine` — entry 2 + partial/runner exit (5m)
- `src/nifty_15m_runner.pine` — same harness, 15m
- `src/nifty_5m_trendpullback.pine` — entry 4 (trend-aligned reversion)
- `src/nifty_5m_pure_meanrev.pine` — entry 5 (pure reversion, ADX-guarded)
- `src/version 6 NIFTY 5M v12.c` — external idea source; never adopted wholesale
