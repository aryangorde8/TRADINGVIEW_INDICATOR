# results/ — committed figures, and what is wrong with the old ones

*Last correction pass: 2026-07-14, driven by `docs/STAGE2_BACKTEST_RECON.md`.
Everything here is regenerated from the **pinned** price snapshot
(`data_cache/*.parquet`, hashed in `data_cache/MANIFEST.md`) and is
reproducible from a fresh clone with no network.*

---

## 0. WITHDRAWN FIGURES — read this before citing anything

**Every rupee-denominated statistic previously published from the pooled
backtests is withdrawn.** Cause (`tools/research/replicate_stage2.py:61-62`):
`equity` is reset to `START` **inside the per-name loop**, so each of the 39
names compounds an independent ₹10,00,000 account. Pooling the resulting
`Profit INR` column mixes trades taken at wildly different equity levels — a
name that compounded 50× emits rupee P&Ls two orders of magnitude larger than
an early trade elsewhere.

Consequently the pooled **profit factor, expectancy, bootstrap CI, and
drawdown in rupees are size-weighted and are not per-trade edge measures.**
They are replaced by percentage-space figures below, which are size-invariant.

**Unaffected** (count-based, not size-based): win rate, max consecutive
losses, holding periods, trade counts.

---

## 1. THE CORRECTED RESULT — percent space

Per-trade return recomputed from the committed Entry/Exit prices:
`r = Exit·(1 − 0.0025) / (Entry·(1 + 0.0025)) − 1`.
Reproduce: `python3 tools/research/percent_audit.py`
(full output: `backtests/stage2_percent_audit.txt`).

| | U1 (383 trades) | U2 (355 trades) |
|---|---|---|
| **Profit factor (percent)** | **6.43** | **5.12** |
| bootstrap 95% CI (seed 7) | 4.28 – 9.66 | 3.51 – 7.55 |
| PF excl. top-1 / top-3 / top-5 | 5.43 / 4.67 / 4.20 | 4.63 / 4.01 / 3.73 |
| PF first half → second half | 7.70 → 4.87 (−37%) | 6.30 → 3.55 (−44%) |
| mean return per trade | +26.3% | +22.0% |
| **median return per trade** | **+0.3%** | **−1.0%** |
| stdev of returns | 118.9% | 79.9% |
| top-1 / top-3 share of gross gain | 15.7% / 27.4% | 9.6% / 21.8% |
| return distribution (p10/p25/p50/p75/p90) | −12.8 / −7.8 / +0.3 / +26.7 / +74.8 % | −13.7 / −9.2 / −1.0 / +25.2 / +79.8 % |
| worst / best single trade | −91.3% / +1864.9% | −76.4% / +934.4% |
| win rate *(unaffected)* | 50.7% | 48.5% |
| max consecutive losses *(unaffected)* | 14 | 8 |
| mean hold, winners / losers *(unaffected)* | 321d / 86d | 317d / 97d |

### Which conclusions change

1. **The "fragile edge" alarm was largely a measurement artifact.** In rupees,
   U2's PF collapsed 3.77 → 1.57 on removing 3 of 355 trades, and the top 3
   trades looked like **58.3%** of gross profit. In percent space the same
   three trades are **21.8%** of gross gain and PF falls only 5.12 → 4.01
   (−22%). The apparent concentration was mostly *when* those trades occurred
   (late, in a large compounded account), not *how extreme* they were.
2. **The published PF understated the size-invariant PF.** 3.53 / 3.77 (rupee)
   vs **6.43 / 5.12** (percent). Neither is "the" number to trade on — but the
   percent figure is the one that means anything per-trade.
3. **Time decay is real and survives the correction.** Both universes lose
   ~37–44% of their profit factor from first half to second. This is the one
   fragility signal that is *not* an artifact.
4. **The median trade is ≈ 0%.** Half of all trades do essentially nothing;
   the entire expectancy sits in the right tail (p90 ≈ +75-80%, max +934% to
   +1865%). This is normal for trend following and is the honest character of
   the system — not a smooth edge.
5. **Nothing changes about win rate (~50%), max consecutive losses (8–14), or
   the hold asymmetry** (winners ~320d, losers ~90d). Those never depended on
   position size.

---

## 2. THE PORTFOLIO RUN — one consistent pinned run

`backtests/stage2_portfolio_equity.csv` (**date, nav** — 1,593 weekly rows) is
the equity curve, committed for the first time. Summary:
`backtests/stage2_portfolio_snapshot.txt`.
Reproduce: `python3 tools/research/stage2_portfolio.py`.

| | Value |
|---|---|
| Period | **1996-01-05 → 2026-07-10 (30.5 years)** |
| Start NAV → End NAV | ₹10,00,000 → ₹96,43,13,477 (**964.3×**) |
| Full-period CAGR | **25.3%**, max drawdown **38.3%** |
| Modern (2013+, *includes partial 2026*) | 23.9%, maxDD 23.6% |
| **Complete years only (2013-2025, 13 yrs)** | **26.6%** |
| **… excluding 2020** (12 yrs) | **19.7%** — 2020 alone is **+6.9pp** |
| Partial 2026 (to 2026-07-10) | −14.4% — **not comparable to complete years** |

### Why the old "25.3% / ₹96.4cr / ~29 years" trio did not reconcile

964× at 25.3% requires **30.5 years**, not 29. The figures were always from
the same run — the **"~29y" label was hardcoded in the print statement** and
was simply wrong. The period is 30.5 years (the curve starts in 1996, well
before the first trade, because week-1 NAV is recorded pre-entry). Corrected
above; the CAGR is now derived from the printed start/end dates and NAVs, so
it reconciles by construction.

**One year carries the modern record.** 2020 returned **+147%**. Remove it and
the complete-year CAGR drops from 26.6% to **19.7%**. Any forward expectation
should be set from the ex-2020 figure, not the headline.

---

## 3. WHAT THIS BACKTEST IS NOT

State these before quoting any number above.

- **No stops exist.** The only exit is a 30-week MA break
  (`replicate_stage2.py:70`, `stage2_portfolio.py`). `grep -n "stop"` over the
  Pine strategy returns nothing. Position sizing is therefore **not
  risk-based** — it is equity/10 (portfolio) or all-in (per-name). There is no
  initial risk per trade to size against, and none is recorded.
- **Fills are not executable.** Both the entry and the exit fill at the
  **signal bar's own weekly close** — the very close that generates the
  signal. No future bar is read (so this is *not* lookahead), but you cannot
  transact at a price you only observe when the bar closes. Live, you would
  fill at the **next open**. Every return here is optimistic by one gap.
- **There is NO temporal out-of-sample test. Anywhere.** U1 and U2 are
  **disjoint tickers over the same 1997–2026 span**. That is a
  **cross-sectional** split: it controls for parameter reuse across names, and
  nothing else. It does **not** test a later regime. There is no walk-forward,
  no train/test time boundary, no holdout period. The `2013+` cutoff is a
  *reporting* segmentation applied after the fact, not a validation split.
- **Both universes are current large-cap NSE survivors.** The 39 names are
  hardcoded (`replicate_stage2.py:20-26`) and were chosen because they exist
  today. Delisted and failed companies are absent. **Survivorship-biased by
  construction**, and trend systems are the most inflated by this.
- **Slot allocation is ALPHABETICAL.** When more than 10 names signal in the
  same week, `stage2_portfolio.py` fills slots in sorted-ticker order — there
  is no strength, momentum, or liquidity ranking. This is an **arbitrary,
  untested choice** and a **known open risk**: the reported portfolio result is
  conditional on it. Skipped signals are dropped, not queued.
- **Slippage and gaps are unmodelled** beyond the flat 0.25%/side. No partial
  fills, no volume constraint, no gap-through handling.
- **Data:** pinned parquet, `auto_adjust=True` (splits/dividends restate the
  whole series — which is exactly why it is now pinned rather than re-fetched).

---

## 4. Fallacy-auditor eval — with confidence intervals

From `../fallacy-auditor/results/eval_report_snapshot.json` (44 gold examples,
38 labelled spans, local `qwen2.5:7b`). Wilson 95% intervals:

| Pipeline | Precision | Recall |
|---|---|---|
| Single-pass | 0.690 (29/42) **[0.54, 0.81]** | 0.763 (29/38) [0.61, 0.87] |
| Two-pass (verifier) | 0.871 (27/31) **[0.71, 0.95]** | 0.711 (27/38) [0.55, 0.83] |

**The two precision intervals OVERLAP on [0.71, 0.81].** At n=44 the verifier's
precision gain is **directional, not statistically established**. It is
reported as an observation, not a result. (Mechanically, the verifier removed
9 false positives *and* 2 true positives: tp 29→27, fp 13→4, fn 9→11.)

The Ollama sampler is now **seed-pinned** (`llm.py`, `seed: 7`) — temperature 0
alone did not make runs reproducible. Figures above predate the seed fix and
may move slightly on re-run; the snapshot is the record of that run.

---

## 5. Reproducing everything (no network)

```bash
python3 tools/research/pin_data.py --verify     # confirm the 39 hashes match
python3 tools/research/percent_audit.py         # §1 (committed CSVs only)
python3 tools/research/stage2_portfolio.py      # §2 (equity curve + summary)
python3 -m fallacy_auditor results/backtests/stage2_universe2_oos_pooled.csv
cd fallacy-auditor && pytest -q                 # 82 tests
```

The pooled per-trade CSVs, the equity curve, the percent audit, the price
snapshot and its hashes are all committed. The only thing that still needs a
live dependency is the LLM eval (Ollama + `qwen2.5:7b`).
