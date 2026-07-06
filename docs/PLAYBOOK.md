# TRADING SYSTEM PLAYBOOK — every tool, every command

*Everything runs free, on this laptop. All commands are typed in the
**Terminal** app (Ctrl+Alt+T on Ubuntu), starting from the project folder:*

```bash
cd ~/TRADINGVIEW_INDICATOR
```

---

## 0. One-time setup (already done on this machine — re-run only after a reinstall)

```bash
pip install --user --break-system-packages pydantic pytest yfinance
pip install --user --break-system-packages -e ./fallacy-auditor
systemctl --user enable --now ollama          # local LLM server autostart
~/.local/bin/ollama pull qwen2.5:7b           # audit model (winner of the bake-off)
~/.local/bin/ollama pull qwen3:4b             # fast low-RAM alternative
```

Health check any time:

```bash
systemctl --user is-active ollama             # -> active
python3 -m fallacy_auditor --help             # -> help text
```

---

## 1. THE WEEKEND RITUAL (Saturday, ~10 minutes) — the monster net

### 1a. Run the Stage-2 scanner

```bash
cd ~/TRADINGVIEW_INDICATOR
python3 tools/stage2_scan.py
```

Scans ~160 liquid NSE names (needs internet; takes a few minutes) and prints
three groups:

| Group | Meaning | Your action |
|---|---|---|
| `NEW BREAKOUT` | Fired a Stage-2 entry this week: new 52-week-high weekly close above a rising 30-week SMA | Verify on the 1W chart (see 1b), then buy an equal slot Monday |
| `EXIT` | Weekly close fell below the 30-week SMA this week | If you hold it: sell Monday. No debate. |
| `IN STAGE-2` | Trend intact, already riding | Hold if owned; do nothing otherwise |

Custom universe (e.g. paste Nifty 500 symbols, one per line, no `.NS`):

```bash
python3 tools/stage2_scan.py --watchlist mylist.txt
```

Built-in liquidity gate: names trading under ~5 cr/day turnover are skipped.

### 1b. Verify a breakout on TradingView

Open tradingview.com → chart → the symbol → timeframe **1W** → Pine Editor →
paste `src/stock_stage2_trend_weekly.pine` → Add to chart. The status table
confirms STAGE 2; the label shows the entry; the teal line (SMA30w) is your
exit for as long as you hold.

### 1c. Position rules (from the tested portfolio simulation)

- Equal slots: ~10% of trading capital per name, max ~10 names.
- More breakouts than free slots? Prefer names that also pass the value
  screen (section 3).
- Never skip a signal because the last one lost; never hold below the
  30-week SMA; never drop a name from the watchlist for performing badly.

---

## 2. STRATEGY FILES (what to paste into TradingView, and when)

All in `src/`, all long-only NSE cash equity, all lint-clean:

| File | Chart timeframe | Status | What it is |
|---|---|---|---|
| `stock_stage2_trend_weekly.pine` | **1W** | **CHAMPION** — passed its pre-registered bar (pooled PF 3.53 / 3.78 both universes) | Weinstein Stage-2 trend rider; holds winners for months-years; the core engine and the monster-catcher |
| `stock_swing_ribbon_pullback.pine` | 1D | validated earlier (11/15 names; replication OOS PF 1.39) | Buys pullbacks to EMA20 inside an uptrend; fixed 2R |
| `stock_swing_dual_edge.pine` | 1D | assembled from tested parts | Ribbon pullback + 52wk breakout in one script (they share only 11% of trades) |
| `stock_swing_52wk_breakout.pine` | 1D | real edge, missed its PF≥1.5 bar (OOS 1.41) | Kept as research; superseded by the weekly Stage-2 version |
| `stock_swing_rsi2_dip.pine` | 1D | REJECTED (mean reversion fails in this universe) | Research artifact — do not trade, do not tune |

Measured portfolio expectations (honest, survivorship-caveated): Stage-2
portfolio ~15–16% CAGR floor (ex-moonshots) to ~24% ceiling (with a
moonshot decade), max drawdowns ~23–38%. Plan on the floor.

---

## 3. QUARTERLY — the value screen (undervalued-quality watchlist)

```bash
python3 tools/value_screen.py
```

Live Magic-Formula screen (cheap = high earnings yield, good = high ROE) on
~90 NSE non-financials, and flags which candidates are ALSO in Stage-2.
Use it to (a) prioritise breakouts when slots are scarce, (b) build the
watch-for-Stage-2-turn list. **Verify every name on screener.in** (10-yr
ROCE, promoter pledging, FCF) — Yahoo data occasionally lies (a VEDL
demerger artifact appeared in our first run). Not SEBI advice.

---

## 4. AFTER ANY BACKTEST — audit the profit factor

Export/copy TradingView's List of Trades (free plan: select table → Ctrl+C →
paste into a file saved as `trades.csv` — tab-separated is fine), then:

```bash
python3 -m fallacy_auditor trades.csv
```

Reads any CSV/TSV with a profit column and prints: PF, bootstrap 95% CI,
PF-without-top-winners (luck concentration), first/second-half stability,
max drawdown, and WARNING lines. Exit code 0 = no fragility warnings,
1 = warnings, 2 = error. Rule of thumb: don't trust a PF whose CI dips
below 1.0 or that collapses without its top 3 trades.

---

## 5. BEFORE CODING AN IDEA — audit the reasoning and the code

```bash
# audit a written trading thesis for 5 fallacies (local LLM, ~1-3 min):
python3 -m fallacy_auditor idea.txt --verify

# lint any Pine strategy for mechanical bias (instant, no model):
python3 -m fallacy_auditor src/mystrategy.pine
```

The reasoning audit flags: survivorship bias, lookahead bias, overfitting,
base-rate neglect, unfalsifiable claims — each with a verbatim quote (a
grounding gate discards anything the model can't quote exactly). The Pine
lint catches `lookahead_on` repainting, `calc_on_every_tick`, `timenow`,
`barstate.isrealtime`. Both exit 1 when something is flagged (usable in
scripts/CI).

---

## 6. RESEARCH REPRODUCTION (`tools/research/`) — rerun any study

Each script re-downloads its own data (creates a `data_cache/` folder
wherever you run it):

| Script | Reproduces |
|---|---|
| `replicate_stage2.py` | Stage-2 per-name PFs, both universes (the champion's evidence) |
| `stage2_portfolio.py` | Stage-2 10-slot portfolio: ~25% CAGR full period / 23.8% modern, ₹10L→₹95cr backtest |
| `replicate_ribbon.py` | Ribbon-pullback replication (both universes) |
| `replicate_52wk.py` | 52wk daily breakout replication |
| `replicate_stage2_pyramid.py` | The pyramiding variant (REJECTED — halved terminal equity; kept as proof) |
| `portfolio_sim.py` | Daily dual-edge portfolio ARR study (8–15% modern era) |
| `rsi30_claim_test.py` | "RSI<30 wins 80%" debunk (measured 53% vs 55.6% base rate) |
| `value_screen.py` | The quarterly value screen |

Run any of them:

```bash
cd ~/TRADINGVIEW_INDICATOR/tools/research
python3 replicate_stage2.py
```

---

## 7. FALLACY-AUDITOR MAINTENANCE (occasional)

```bash
cd ~/TRADINGVIEW_INDICATOR/fallacy-auditor
python3 -m pytest -q                                  # 79 offline tests
pytest -m eval -s                                      # live accuracy eval on local model
FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s        # two-pass eval (P .88 / R .74 baseline)
python3 scripts/redteam.py --fallacy all --n 2         # generate hard eval candidates (review before promoting)
python3 scripts/validate_dataset.py data/labeled_examples.jsonl
```

Env knobs: `FALLACY_AUDITOR_OLLAMA_MODEL` (default qwen2.5:7b),
`FALLACY_AUDITOR_OLLAMA_NUM_CTX` (default 8192; long inputs are refused
loudly rather than silently truncated).

---

## 8. THE CADENCE (the whole system on one line each)

- **Saturday (10 min):** scanner → verify breakouts on 1W chart → Monday orders (buys and exits). SIP continues regardless of market mood.
- **Quarterly (30 min):** value screen → refresh watchlist priorities → run `pytest -q` in fallacy-auditor to confirm tools healthy.
- **Yearly (1 hr):** re-run `stage2_portfolio.py`; compare live results vs replication; log the year in `docs/`; adjust nothing unless a pre-registered test says so.
- **Always:** new strategy ideas go through thesis audit → pine lint → pre-registered bar → replication → forward test. Failed tests are recorded and closed, never tuned.
