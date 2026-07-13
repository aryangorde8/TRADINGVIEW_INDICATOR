# Stage-2 Backtest — Recon (post-correction)

*Original recon: 2026-07-09, read-only, on `edfdc3e`.
Correction pass applied and re-verified: **2026-07-14**, on `638b422`.*

Repo: `aryangorde8/TRADINGVIEW_INDICATOR`. Every claim cites file + line
against the **current** tree. "NOT IN REPO" is used literally.

**How to read this document.** Each finding carries a status:

| | |
|---|---|
| ✅ **FIXED** | the defect is gone; the fix is committed and cited |
| 📌 **DISCLOSED** | not fixable without changing the strategy or buying data; now stated plainly wherever the numbers appear |
| ❌ **OPEN** | still broken, still live, deliberately not papered over |

---

## 0. THE HEADLINE — what the correction pass actually established

**Every rupee-denominated statistic from the pooled backtests is WITHDRAWN.**
`tools/research/replicate_stage2.py:73` resets `equity = START` **inside the
per-name loop**, so each of the 39 names compounds an independent ₹10,00,000
account. Pooling the resulting `Profit INR` column mixes trades taken at wildly
different equity levels — a name that compounded 50× emits rupee P&Ls two orders
of magnitude larger than an early trade elsewhere. Pooled PF, expectancy,
bootstrap CI and drawdown **in rupees are size-weighted and are not per-trade
edge measures.**

❌ **OPEN — the root cause is still in the code.** The per-name equity reset was
*not* removed (removing it changes the simulation, which this pass was forbidden
from doing). The `Profit INR` column in the committed pooled CSVs therefore
remains size-weighted and **must not be used**. The correction is a
*measurement* workaround, not a simulator fix: `tools/research/percent_audit.py`
recomputes everything in percentage space from the committed Entry/Exit prices,
which is size-invariant.

### Recomputed in percent space (the figures that replace the rupee ones)

`r = Exit·(1 − 0.0025) / (Entry·(1 + 0.0025)) − 1`
Full output: `results/backtests/stage2_percent_audit.txt`

| | U1 (383 trades) | U2 (355 trades) |
|---|---|---|
| PF — **rupee (withdrawn)** | 3.53 | 3.77 |
| **PF — percent (correct)** | **6.43** | **5.12** |
| PF excl. top-3 — rupee | 2.60 | **1.57** |
| **PF excl. top-3 — percent** | **4.67** | **4.01** |
| top-3 share of gross gain — rupee | — | **58.3%** |
| **top-3 share — percent** | **27.4%** | **21.8%** |
| bootstrap 95% CI (percent, seed 7) | 4.28 – 9.66 | 3.51 – 7.55 |
| PF first half → second half (percent) | 7.70 → 4.87 (**−37%**) | 6.30 → 3.55 (**−44%**) |
| median return per trade | **+0.3%** | **−1.0%** |
| mean / stdev per trade | +26.3% / 118.9% | +22.0% / 79.9% |
| win rate *(size-independent)* | 50.7% | 48.5% |
| max consecutive losses *(size-independent)* | 14 | 8 |
| mean hold winners / losers *(size-independent)* | 321d / 86d | 317d / 97d |

**Three conclusions changed:**

1. **The "fragile edge" alarm was largely an artifact of the bug it was
   measuring.** U2's top-3 trades are **21.8%** of gross gain in percent space,
   not 58.3%; PF falls 5.12 → 4.01 (−22%), not 3.77 → 1.57 (−58%). Those trades
   looked enormous because they occurred *late in a compounded account*, not
   because their returns were extreme.
2. **The published PF understated the size-invariant PF** (3.53/3.77 → 6.43/5.12).
   Neither number is tradeable; only the percent one is interpretable per-trade.
3. **Time decay is real and survives the correction** (−37% / −44% across
   halves). It is the only fragility signal that is *not* an artifact.

And one characterisation that was never visible before: **the median trade is
≈ 0%** (U1 +0.3%, U2 −1.0%). Half of all trades do essentially nothing; the
entire expectancy sits in the right tail (p90 ≈ +75-80%, max +934% to +1865%).

---

## 1. ARTIFACT INVENTORY

| # | Artifact | Then (2026-07-09) | Now |
|---|---|---|---|
| a | Per-trade log | PARTIAL | ✅ **IN REPO** — `results/backtests/stage2_universe{1,2}_*_pooled.csv` (383 / 355 rows), regenerated from pinned data |
| b | Equity curve / NAV series | **NOT IN REPO** | ✅ **IN REPO** — `results/backtests/stage2_portfolio_equity.csv` (date, nav; **1,593 weekly rows**), written at `stage2_portfolio.py:140` |
| c | Pinned price snapshot | **NOT IN REPO** | ✅ **IN REPO** — `data_cache/*.parquet` (**39 series**, 12.9 MB) + `data_cache/MANIFEST.md` (fetch date + SHA256 each) |
| d | 44-example gold set | IN REPO | unchanged — 44 examples, 38 labelled spans, 10 clean |
| e | Per-example model outputs | IN REPO | unchanged — `fallacy-auditor/results/eval_report_snapshot.json` |
| f | Config / parameter file | **NOT IN REPO** | ❌ **OPEN** — parameters remain module-level constants (`replicate_stage2.py:22-31`, `stage2_portfolio.py:41-58`) and Pine `input.int`. No single config file. |

📌 Still missing from the per-trade log: **symbol, qty, initial stop**. Symbol is
dropped at pooling; qty is not recorded; **no stop exists to record** (§3b).

---

## 2. DEFINITIONS AND THE 25.3% / ₹96.4cr RECONCILIATION

✅ **FIXED — and the original hypothesis was wrong.** The recon suspected the
CAGR and the terminal NAV "came from different runs on drifting auto_adjust
data." They did not. **They always reconciled.** The period is **30.5 years**,
not the ~29 the script claimed:

```
period: 1996-01-05 -> 2026-07-10  (30.5 years)
start NAV: 1,000,000   end NAV: 964,313,477  (964.3x, 96.4 cr)
FULL PERIOD : CAGR 25.3%   maxDD 38.3%
```

964.3× over 30.5 years **is** 25.3%. The `"FULL ~29y"` in the old print
statement was a **hardcoded string literal**, not a computed duration — the only
defect was the label. `stage2_portfolio.py:135-170` now prints the exact start
and end dates and both NAVs, so the CAGR reconciles by construction.

(The curve starts in 1996, well before the first trade, because week-1 NAV is
recorded pre-entry — so the denominator includes warm-up years. Stated, not
silently corrected.)

### Partial year and one-year dependence — ✅ FIXED (now reported separately)

| | |
|---|---|
| Modern (2013+) — **includes partial 2026** | 23.9%, maxDD 23.6% |
| **Complete years only, 2013-2025 (13 yrs)** | **26.6%** |
| **… excluding 2020 (12 yrs)** | **19.7%** |
| **2020 alone contributes** | **+6.9pp** (2020 returned **+147%**) |
| Partial 2026 (to 2026-07-10) | −14.4% — **not comparable to complete years** |

Any forward expectation should be set from the **ex-2020** figure.

**Max drawdown** remains two different quantities and both are labelled as such:
`stage2_portfolio.py` computes a **% drawdown on weekly mark-to-market NAV
including open positions**; `profit.py` reports a **rupee drawdown on the
closed-trade cumulative curve** (and, per §0, that rupee figure is withdrawn).

---

## 3. EXPECTANCY, STOPS, SIZING

**a. Expectancy** — `profit.py` still reports the arithmetic mean of whatever
P&L column it is handed. On the pooled CSVs that column is rupees, so **the
rupee expectancy is withdrawn** (§0). The size-invariant replacements are mean
percent return **+26.3% (U1) / +22.0% (U2)**, against a **median of ≈0%**.

**b. Initial stop: NONE EXISTS.** 📌 **DISCLOSED.** The only exit is a trend
break (`replicate_stage2.py:70`-equivalent; `stage2_portfolio.py:99`). `grep -n
"stop"` over `src/stock_stage2_trend_weekly.pine` still returns **no matches**.
This is a property of the strategy, not a defect — but it means:

**c. Initial risk (entry − stop) × shares: NOT RECORDED and NOT RECOMPUTABLE.**
There is no stop, and no `qty` column.

**d. Position sizing is NOT risk-based.** 📌 **DISCLOSED.** Two rules coexist:
all-in on per-name equity (`replicate_stage2.py`), and `mtm / MAX_SLOTS`
cash-capped (`stage2_portfolio.py:120`). Neither sizes against a stop, because
there is no stop.

---

## 4. THE 10-SLOT MECHANIC

**a. Ranking is ALPHABETICAL.** ❌ **OPEN — flagged as a known risk, not fixed.**
`stage2_portfolio.py:111` iterates `for n in NAMES:` where `NAMES = sorted([...])`
(`:51`). When more than 10 names signal in the same week, slots go to the
**alphabetically first tickers**. There is no strength, momentum, or liquidity
ranking. This is an **arbitrary, untested choice**, and the reported portfolio
CAGR is conditional on it. It is now stated in `results/README.md` §3 and in the
script docstring; **it has not been tested against alternatives** (doing so would
be a new experiment, out of scope for a correction pass).

**b. Lookahead: NONE.** ✅ Confirmed again on the current tree. The anchor is
lagged (`w["c"].shift(1).rolling(52).max()`), `rising` compares trailing SMAs,
and the alphabetical rank uses no price data.

**c. Same-bar-close execution.** 📌 **DISCLOSED — this is the material
limitation, and it is not lookahead.** Fills are at `row.c`, the *same* weekly
close that generates the signal, and sizing uses `mtm` marked at that close. No
future bar is read, but **you cannot transact at a price you only observe once
the bar has closed.** Live, you fill at the **next open**. Every return in this
repo is optimistic by one gap, and the gap is not modelled. Now stated wherever
the figures appear.

**d. Skipped signals are DROPPED, not queued** — unchanged, and now stated.

**e. Avg open positions / % time in cash: still NOT IN REPO.** ❌ **OPEN.** The
committed equity curve (`b` above) now makes these computable by a reader, but
the script does not report them.

---

## 5. FRAGILITY CHECK — the auditor failed its own audit

✅ **FIXED.** Every original check was an **absolute floor at PF 1.0**. Nothing
tested *relative* degradation, so U2 could collapse **3.77 → 1.57** on removing
3 of 355 trades (0.85% of the sample), decay **15.00 → 1.99** across halves, and
still print **"no fragility warnings"** — because 1.57 and 1.99 are both above
1.0. *A number staying above the floor says nothing about how far it fell to get
there.*

Added (`fallacy-auditor/src/fallacy_auditor/profit.py:44-45`):

```python
PF_DROP_TOP3_WARN = 0.40  # warn if PF falls >40% when the top 3 are removed
HALF_DECAY_WARN   = 0.40  # warn if second-half PF < 40% of first-half PF
```

fired at `:212` ("concentrated edge") and `:243` ("decaying edge"). The
regression is pinned by a test that feeds **the actual U2 pooled CSV** and
asserts both warnings fire (`fallacy-auditor/tests/test_profit.py`), plus two
synthetic cases proving they fire *without* crossing the old 1.0 floor. 82 tests
pass.

The 0.40 values are a **judgment call, not a derived constant** — flags for
review, not verdicts. Documented as such in `fallacy-auditor/README.md`.

> **The honest catch, stated because it cuts against the fix.** The U2 *rupee*
> fragility these new checks now catch **is itself the §0 artifact**. In percent
> space U2 triggers **neither** warning (−22% top-3 drop, 56% half-retention —
> both inside the thresholds). So the checks are correctly signalling "this file
> cannot be trusted", but for a different reason than they name. The fix is still
> right in general — a P&L auditor must catch relative collapse — and
> `fallacy-auditor/README.md` now warns that currency P&L from a compounding
> backtest is size-weighted and its apparent concentration may be illusory.

---

## 6. PARAMETERS AND PROVENANCE

📌 **DISCLOSED — unchanged and unfixable retroactively.**

Values (52 / 30 / 4 weeks; `W-FRI`; 0.25%/side; 10 slots; 2013 cutoff; bootstrap
seed 7) are unchanged and hardcoded. **No parameter was tuned in this pass.**

**a priori or tuned? Git still cannot prove it.** The pre-registration claim
lives in a docstring (`replicate_stage2.py:1-9`) and a Pine comment, and the
spec, code and results all landed in a **single commit** (`2259bf4`). There is no
commit sequence showing the spec predating the results. Stage-2's parameters show
**no tuning commits**; the repo's *other* strategies (`stock_swing_*`) show
extensive iterative tuning. That distinction is real and remains the honest
statement — **the pre-registration is asserted, not proven by history.**

---

## 7. UNIVERSES

📌 **DISCLOSED — both defects remain, both are now stated wherever numbers appear.**

**a. There is NO temporal out-of-sample test. Anywhere.** U1 (19 names) and U2
(20 names) are **disjoint tickers over the same 1997-2026 span**. That is a
**cross-sectional** split: it controls for parameter reuse across names, and
**nothing else**. It does not test a later regime. There is no walk-forward, no
train/test boundary, no holdout period. The `2013+` cutoff is a *reporting*
segmentation applied after the fact, not a validation split. Calling U2
"out-of-sample" (as the filename `stage2_universe2_oos_pooled.csv` still does) is
**misleading and is now contradicted in the README** — the filename is retained
only to avoid breaking committed references.

**b. Survivorship-biased by construction.** The 39 names are hardcoded
(`replicate_stage2.py:22-28`) and were selected because they **exist today**.
Delisted and failed companies are absent. Trend systems are the most inflated by
this bias. Free data offers no point-in-time membership feed, so this is not
fixable here — only disclosable.

---

## 8. COSTS AND FILLS

✅ Costs verified again on the current tree: `COST = 0.0025`
(`replicate_stage2.py:30`), applied on **both** sides — `proceeds = row.c * qty *
(1 - COST)` (`:82`) and `cost_basis = entry_px * qty * (1 + COST)` (`:84`).

📌 **Fills: signal bar's own weekly close** (§4c). Not next-bar open.
📌 **Slippage / gap model: NONE** beyond the flat 0.25%. No partial fills, no
volume constraint, no gap-through handling.

---

## 9. FALLACY-AUDITOR EVAL — now with confidence intervals

✅ **FIXED (reporting).** Wilson 95% intervals, n=44 (38 labelled spans):

| Pipeline | Precision | Recall |
|---|---|---|
| Single-pass | 0.690 (29/42) **[0.54, 0.81]** | 0.763 (29/38) [0.61, 0.87] |
| Two-pass (verifier) | 0.871 (27/31) **[0.71, 0.95]** | 0.711 (27/38) [0.55, 0.83] |

**The precision intervals OVERLAP on [0.71, 0.81].** The verifier's precision
gain is **directional, not statistically established** at this sample size. It is
now reported as an observation, never as a proven improvement. Mechanically the
verifier removed **9 false positives and 2 true positives** (tp 29→27, fp 13→4,
fn 9→11).

✅ **Seed pinned.** `llm.py:52` `OLLAMA_SEED = 7`, sent at `:161`. Temperature 0
alone does **not** make Ollama deterministic. **The committed snapshot predates
this fix** and says so.

❌ **OPEN:** the `qwen2.5:7b` Ollama tag can be re-pulled with different weights;
`FALLACY_AUDITOR_EVAL_WORKERS` alters scheduling. TN remains undefined (span
detection, not binary classification).

---

## 10. REPRODUCIBILITY

✅ **A fresh clone now reproduces every backtest figure with no network.**

| Source of drift (2026-07-09) | Status |
|---|---|
| No pinned price data; `period="max"` re-fetch; `auto_adjust` restates history | ✅ **FIXED** — 39 series pinned as parquet + SHA256 manifest; `pin_data.py --verify` detects drift |
| In-progress week included (`W-FRI`, no completed-week filter) | ✅ **FIXED** — filter backported from `stage2_scan.py:84` to `replicate_stage2.py:48` and `stage2_portfolio.py:74` |
| 2026 partial year mixed with complete years | ✅ **FIXED** — reported separately; complete-years and ex-2020 CAGR published |
| Equity curve existed only in memory | ✅ **FIXED** — committed (1,593 rows) |
| LLM eval not seed-pinned | ✅ **FIXED** going forward (snapshot predates it) |
| Ollama tag / weights not pinned | ❌ **OPEN** |

```bash
python3 tools/research/pin_data.py --verify     # 39 hashes match
python3 tools/research/percent_audit.py         # §0 (committed CSVs only, no network)
python3 tools/research/stage2_portfolio.py      # §2 (equity curve + summary)
python3 -m fallacy_auditor results/backtests/stage2_universe2_oos_pooled.csv
cd fallacy-auditor && pytest -q                 # 82 tests
```

Everything above is offline. The **only** figure still requiring a live
dependency is the LLM eval (Ollama + `qwen2.5:7b`).

---

## 11. WHAT IS STILL WRONG (the short list)

1. ❌ **The per-name equity reset is still in the simulator**
   (`replicate_stage2.py:73`). The `Profit INR` column in the committed pooled
   CSVs is size-weighted and must not be used. Percent space is the workaround,
   not a fix.
2. ❌ **Alphabetical slot allocation** is arbitrary and untested; the portfolio
   CAGR is conditional on it.
3. ❌ **No temporal out-of-sample test exists** — and the `_oos_` filename
   actively misleads.
4. 📌 **Fills are not executable** (signal-bar close); live returns will be worse
   by the open gap.
5. 📌 **Survivorship-biased universe**; **no stops**; **sizing not risk-based**.
6. ❌ **Pre-registration is asserted in docstrings, not provable from git.**
7. 📌 **The strategy has never traded.** Every number in this repo is a backtest.
