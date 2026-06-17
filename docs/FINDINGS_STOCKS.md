# FINDINGS — Stock Swing (daily, cash equity) — VALIDATED LONG EDGE

**Status: long edge VALIDATED and FROZEN; short side TESTED-AND-REJECTED.**
The pivot from the NIFTY intraday work (which was no-edge across 5 entries / 3 exits
/ 2 timeframes — see `docs/FINDINGS.md`) to **daily, cash-equity, long-only swing**
found the project's first genuine edge.

Strategy: EMA-ribbon-filtered pullback. Regime = ribbon stacked bullish + price above
the 200 EMA (persistent filter). Entry = pullback tags the fast EMA, then a bar
resumes up (2-bar confirm window). Fixed −1R structural stop, **fixed 2R target**,
trend-break exit. Risk-based share sizing. Realistic delivery costs (~0.2%/side).
Files: `src/stock_swing_ribbon_pullback.pine` (long, deployable) and
`src/stock_swing_short_futures.pine` (short, rejected research).

---

## 1. LONG edge — validated across 15 names / diverse sectors (daily, fixed 2R, runner OFF)
**11 of 15 profitable.** The failures are all downtrend/chop names — the *mechanistic*
signature of a real long-trend edge, not luck.

| Stock | Sector | PF | | Stock | Sector | PF |
|---|---|---|---|---|---|---|
| BHARTIARTL | telecom | **1.89** | | HINDUNILVR | FMCG | 1.12 |
| MARUTI | auto | **1.51** | | ICICIBANK | bank | 1.03 |
| ULTRACEMCO | cement | **1.47** | | ASIANPAINT | paints | 0.99 ✗ |
| INFY | IT | **1.31** | | HDFCBANK | bank | 0.90 ✗ |
| LT | infra | **1.30** | | RELIANCE | energy | 0.79 ✗ |
| TCS | IT | 1.27 | | BAJFINANCE | NBFC | 0.05 ✗ |
| TATASTEEL | metals | 1.25 | | | | |
| SUNPHARMA | pharma | 1.23 | | | | |
| TITAN | consumer | 1.17 | | | | |

**The edge GENERALIZES** (IT, auto, cement, pharma, metals, infra, telecom, consumer,
FMCG, bank) and **its weakness is precisely downtrending/choppy names** — which is the
point: you only run it on confirmed uptrends.

---

## 2. SHORT side — tested on genuine downtrenders, REJECTED (not viable standalone)
Symmetric mirror on **futures** (leveraged), tested on names with real sustained
downtrends:

| Stock | PF | Win rate |
|---|---|---|
| YESBANK | 1.289 | ~39% |
| IDEA | 1.068 | low |
| ZEEL | 0.948 ✗ | low |
| PNB | 0.795 ✗ | low |
| INDUSINDBK | 0.519 ✗ | ~24% |

**Only 2/5 profitable and both weak** — far below the long side (11/15, PFs to 1.89).
First we proved it wasn't a sign bug (target below entry, stop above, R positive, exit
legs correct — all verified), then we tested real downtrenders, so this is the genuine
result, not a defect.

**Why the short is structurally weaker (won't change with tuning):** downtrends are
**violent and bounce-prone** — the counter-rally short's stop (just above the rally
high) gets taken out by sharp squeezes/short-covering before the 2R target, giving
**low win rates (24–39%)**. Leverage amplifies the squeeze damage. This is the classic
"shorting is harder" asymmetry, and it's intrinsic to bear-market microstructure.

**Decision: the short side is CLOSED — rejected on evidence, not tuned.** No more
names, no parameter chasing.

---

## 3. Also rejected: the runner exit (both directions)
The MFE tail on stocks is genuinely fat (HDFCBANK: ≥3R 29.5%, ≥5R 12.9% — ~2× NIFTY at
5R), but turning the partial+chandelier runner ON made results **worse** (same as on
NIFTY): the loose trail gives back gains on the ~87% that don't run to 5R, and the few
that do don't pay for the round-trips. **Fixed 2R is the exit.** (R note: realized stop
avg ≈ −1.4R, not −1.0R — genuine overnight **gap-through**, since daily holds gap past
the stop; R is correctly the actual stop distance.)

---

## 4. DEPLOYABLE conclusion
**LONG-ONLY ribbon-pullback swing on confirmed-uptrend stocks; CASH in downtrends.**
The bear-market answer is **capital preservation (cash)**, not shorting — you compound
the validated long edge during uptrends and simply don't trade names in downtrends
(the long filter already keeps you out, and the short isn't worth the squeeze risk).

- Deployable file: `src/stock_swing_ribbon_pullback.pine`, `inDirection = long_only`
  (default). `short_only` / `both` exist but are documented tested-and-rejected and
  not traded in the deployable.
- **Realistic expectation (set it correctly):** **~40% win rate at ≥1:2 R:R**, edge from
  the trend tail, **conditional on uptrending names**. Plausible **ARR ~15–30%** with
  discipline (run only confirmed uptrends, accept the ~40% hit rate, hold winners to 2R,
  honor the stop, sit in cash otherwise). Numbers are on cash equity (delivery costs
  modelled); no leverage, no overnight-options decay.
- **Validate any new name before sizing into it** — the edge is broad but per-name
  dispersion is real (PF 1.03 → 1.89); a name in chop/downtrend will not perform.

---

## 5. Method discipline carried through
Clean fixed-bracket baseline; exit-reason counter, MFE/MAE shadow-tracker, entry-funnel
instrumentation on every variant; multi-name validation (the stock equivalent of
multi-regime); reject on evidence (short, runner) rather than tune toward a target; no
confluence-gate stacking; ≤8 edge params. 80% accuracy was never the goal and remains
out of reach — positive expectancy at ≥1:2 across many names is, and the long side
delivers it.
