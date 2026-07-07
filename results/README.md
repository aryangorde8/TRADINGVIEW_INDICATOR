# results/ — committed result snapshots (so numbers are verifiable, not asserted)

These are point-in-time artifacts committed so the performance figures cited
in the docs can be inspected without re-running anything. **Read the caveats.**

## What's here

### `backtests/`
- `stage2_universe1_pooled.csv` / `stage2_universe2_oos_pooled.csv` — the
  per-trade lists (entry/exit dates, days held, P&L after costs) for the two
  39-name test universes of the Stage-2 weekly strategy.
- `*_audit.txt` — the output of `python3 -m fallacy_auditor <csv>` on each:
  profit factor, bootstrap 95% CI, luck-concentration (PF without top winners),
  time-stability (half vs half), drawdown, warnings.

Headline figures in these snapshots: **universe 1 pooled PF 3.53** (CI
2.11-5.82, 383 trades); **universe 2 (out-of-sample) pooled PF 3.78** (CI
1.17-10.25, 354 trades). Regenerate with:
`python3 tools/research/replicate_stage2.py` (creates the pooled CSVs), then
`python3 -m fallacy_auditor <pooled.csv>`.

### `../fallacy-auditor/results/`
- `eval_report_snapshot.json` — one run of the two-pass precision/recall
  harness on the 44-example gold set using the local `qwen2.5:7b` model.
  Regenerate with `FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s`.

## CAVEATS (mandatory reading before citing any number)

1. **Survivorship bias.** The universes are *today's* liquid NSE names tested
   backwards; delisted/failed companies are absent. This inflates a trend
   system's results. The pooled PF is an **upper bound**, not an unbiased
   estimate. The more robust readouts are breadth (% of names profitable) and
   the stripped ~15-16% CAGR floor.
2. **Backtest, not track record.** Nothing has traded. The system is at the
   forward paper-trading gate.
3. **Data drift.** The scripts pull live Yahoo Finance data; re-running later
   yields slightly different numbers as history is extended/adjusted. These
   CSVs are the snapshot as of the commit date.
4. **Cost basis.** These Python results model 0.25%/side all-in. The Pine
   strategy models 0.25% commission + a small slippage separately (marginally
   more conservative) — see `src/stock_stage2_trend_weekly.pine` header.

See `TRADING_SYSTEM_RECON.md` (repo root) §3 for the full backtest-integrity
analysis.
