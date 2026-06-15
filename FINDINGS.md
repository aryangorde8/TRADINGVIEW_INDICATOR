# FINDINGS — NIFTY 5m Intraday Options-Directional Strategy

**Status: CLOSED.** Variants A, B, C and the B-RUNNER exit are final. This is the
real deliverable: a negative result, honestly measured.

Instrument: `NSE:NIFTY1!` (continuous front-month NIFTY futures), 5-minute.
Primary test window: **2026-03-02 → 2026-06-15**. Strategy-Tester win rate is a
directional UPPER BOUND on real CE/PE P&L (no premium / theta / IV modelled).
All numbers below were produced by the human in TradingView; I cannot run Pine.

---

## 1. Entries tested — three structurally different triggers, identical clean harness
Same GATE-1 bias (VWAP/SessionAvg + EMA cross), GATE-3 context, fixed **−1R stop /
+2R target** (trail OFF, `minAtr=0`), so only GATE-2 (the trigger) differs.

| Variant | Trigger | Clean-bracket win rate | Profit factor | # trades |
|---|---|---|---|---|
| A | Breakout (close > prior-N high, `[1]`-offset) | ~34.5% (76 / 205 resolved) | 0.69 | ~235 |
| B | Pullback to fast-EMA, then resume | 36.5% (101 / 277) | 0.67 | 277 |
| C | Supertrend flip (`ta.supertrend`, crossover) | 34.4% (22 / 64) | 0.75 | 64 |

The 1:2 breakeven win rate is ~35% (after costs). **All three sit on the breakeven
line; their 95% CIs straddle it.** Three different ways of reading direction →
statistically indistinguishable from a coin flip. Exit-reason counters confirmed no
hidden leak: winners genuinely reached +2R (avg ≈ +1.74 to +1.88R), losers ≈ −1R.

Note: `minAtr` cannot rescue any of them — chop-bar ATR and PE-trade ATR fully
overlap (both ~25–30), so there is no volatility gap to filter on.

---

## 2. Exits tested — fixed target vs partial + runner (on the B pullback entry)
The MFE study showed the moves exist past 2R, so the second axis was the exit.

| Exit model | Profit factor | Net | Result |
|---|---|---|---|
| Fixed 2R bracket | ~0.65 | −4.58 L | loses |
| Partial book @2R + loose chandelier runner | 0.63 | −3.98 L | loses |

The runner cut the net loss slightly (it stops dumping the whole winner at 2R) but
**PF did not improve** — it actually fell. Both lose.

---

## 3. The MFE distribution, and why the runner still failed
Max-favorable-excursion of every B entry (277 trades), measured **ignoring** the 2R
target (shadow-tracked to the −1R stop or 15:15):

| Reached | % of trades |
|---|---|
| ≥ 1R | 53.1% |
| ≥ 2R | 33.6% |
| ≥ 3R | 20.6% |
| ≥ 4R | 11.9% |
| ≥ 5R | 5.4% |

The tail is **reachable but not harvestable.** ~47% of trades never even reach +1R;
only ~21% reach ≥3R. To give that 21% tail a chance, the runner must HOLD every
trade — and the ~80% that round-trip (give back to breakeven, the −1R stop, or the
time-stop) cost more than the ~20% tail pays. Compounding it: the loose chandelier
(≈2R behind the high) hands a large slice of each runner back on the way out, and
half the position is already capped at the 2R book. Net expectancy stays negative.
**A ~35% hit rate is simply too low for any exit to monetize — fixing the payoff
side cannot fix a coin-flip entry.**

---

## 4. Verdict
**NIFTY 5-minute simple directional intraday trading on price/trend signals has no
recoverable edge — on EITHER axis (entry or exit).** 3 entries × 2 exits, every
combination loses across the test window, by a consistent margin (not noise).
This was confirmed by measurement, not assumed; we did NOT chase win rate or stack
gates toward a target (that path is the overfit trap, not edge).

Closing cross-regime check (to confirm it is not a one-window artifact) — run by the
human, runner ON, same `NSE:NIFTY1!` 5m:

| Regime month | Profit factor | Net | (expectation) |
|---|---|---|---|
| Primary 2026-03-02→06-15 | 0.63 | −3.98 L | loses |
| Trending-DOWN month `<pick>` | _pending your run_ | _pending_ | lose |
| Choppy month `<pick>` | _pending your run_ | _pending_ | lose (likely worst) |

(The down/choppy months were never specified — fill these two rows after running;
the verdict already holds on the primary multi-month window.)

---

## 5. Where edge might actually live — NEXT-PROJECT notes (do NOT reopen this one)
- **Higher timeframe.** 5m is dominated by chop/noise; trends persist better on
  15m/1h/daily. Re-test the SAME clean harness there before anything fancy.
- **Different structure, not more filters.** On 5m, mean-reversion (fade stretched
  moves to VWAP/bands) is the opposite hypothesis to the trend-following tested here
  and deserves its own clean test. Trend-continuation on 5m is the disproven one.
- **Use the options structure, not just spot direction.** This was always *for*
  options — the edge may be in the payoff instrument itself: defined-risk spreads,
  premium selling (theta), or event/IV-crush setups, where a directional coin flip
  is irrelevant. Pure spot-direction throws away the option-specific edges.
- **Conditioning with a real prior.** Time-of-day / open-drive / event windows,
  validated as a statistical prior on their own — not bolted on as gate #7.
- **Order flow / microstructure.** OHLC-only may be insufficient at 5m; depth/flow
  is a different (harder) data axis.

**Discipline carried forward:** clean fixed-bracket baseline first, exit-reason +
MFE instrumentation, ≥~100 trades before trusting a win rate, reject any single
window that looks great. 80% accuracy was never the goal and remains impossible;
the goal is positive expectancy at ≥1:2 — which this market/timeframe/signal class
does not provide.
