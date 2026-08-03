# MASTER GUIDE — the complete system: analysis, decisions, and every command

*This is the consolidated record of the entire research campaign (July 2026):
what to invest in, when, how much to expect, what was rejected and why, and a
detailed reference for every command. The short operating version is
[PLAYBOOK.md](PLAYBOOK.md); this file is the full picture.*

---

# PART 1 — THE OVERALL ANALYSIS

## 1.1 Where the money goes (the capital structure)

Money flows through four layers, in this order — never skip a layer:

| Layer | What | Why |
|---|---|---|
| **0. Emergency reserve** | ~6 months of expenses in a fixed deposit, untouchable | So no life event ever forces selling mid-drawdown — the one failure no backtest can price |
| **1. Core (buy & hold)** | Recurring contributions into Nifty 50 + Nifty Next 50 index funds | The no-skill compounding floor (~12-13% historical); Next 50 is the nursery of future giants (~2-3% more, deeper drawdowns) |
| **2. Satellite (the edge)** | The Stage-2 weekly trend system across the Nifty 500 | The measured edge: floor ~15-16% CAGR, ceiling ~24% in moonshot decades |
| **3. Strategy cash** | Idle satellite capital in liquid/overnight funds (~6-6.5%, T+1) | Dry powder for recovery breakouts; adds ~1.5-2.5%/yr vs idle cash |

**Never:** F&O (measured: worse than a savings account — see 1.6), leverage or
margin funding (~11% cost ≈ the entire edge), "9-12% fixed" credit platforms
(credit risk + 1-3yr lockups that strand capital exactly when recovery
breakouts appear), single-stock concentration, tips.

## 1.2 When to BUY (mechanical, no judgment)

A stock qualifies when its **weekly close makes a new 52-week high while
above a rising 30-week SMA** (a Weinstein Stage-2 breakout).

Operationally: Saturday scan → NEW BREAKOUT list → verify on the 1W
TradingView chart with `src/stock_stage2_trend_weekly.pine` → buy Monday.

- **Equal slots:** ~10% of satellite capital per name, max ~10 positions.
- **Sector cap:** max 3 positions from one sector/theme.
- **Tie-breaker** when breakouts exceed free slots: prefer names that also
  pass the quarterly value screen (cheap + quality + market agreeing).
- Never skip a signal because the last one lost. You cannot know which
  breakout is the next 100-bagger; boarding all of them is the only
  guarantee of being on the right one.

## 1.3 When to SELL (one rule)

**Weekly close below the 30-week SMA → sell Monday.** No targets, no
"it'll come back", no selling winners early because they're up a lot.
The exit rule is the entire risk management AND the entire monster-riding
mechanism: losers leave in ~3 months (median 84 days), winners stay ~10
months (median 266 days), monsters stay years (longest: 4.7 years, and
single trades of +742% to +1,086% in the midcap tests).

## 1.4 When to AVOID investing

- **Stock level:** anything below its 30-week line — however cheap it looks.
  "Cheap and falling" is bought only after it turns (enters Stage 2).
- **Market level:** when the scanner's NEW BREAKOUT column is empty and
  breadth is falling, cash (earning 6%+) is a position. The system re-enters
  automatically when breadth returns — 2020-style recoveries are where the
  backtest made its biggest years.
- **Breadth context:** the breadth log (% of universe in Stage-2) is the
  regime gauge. >90% = extended market (stay disciplined, sector caps
  matter most); rising from low = the best hunting season; collapsing =
  expect exits, honor them without anxiety.

## 1.5 What to expect (all measured, survivorship-caveated)

**The champion — Stage-2 weekly trend system:**

| Test | Result |
|---|---|
| 39 NSE large caps, 2 universes | pooled PF 3.53 / 3.77 — passed its pre-registered bar |
| Full Nifty 500 (441 names, 5,048 trades) | pooled PF 6.29 (upper bound), **breadth 87% of names profitable** |
| 64 US large caps incl. 9 famous duds | PF 2.44 (CI 1.97-3.06), **98% breadth** — the edge travels |
| Portfolio (10 slots, 39 names) | committed snapshot (2026-07-09): full 25.3% CAGR (₹10L→₹96cr/29y); modern 23.9% at 23.6% maxDD — `results/backtests/stage2_portfolio_snapshot.txt` |
| Ex-moonshot floor (honest planning number) | **~15-16% CAGR, maxDD ~25-35%, 3-4 losing years per decade** |
| Holding periods | winners median 266d (29% >1yr → LTCG), losers median 84d |

**Wealth math (normalised — multiples, not amounts):**

For a monthly contribution stream that itself grows 10-12%/yr, compounded
over 30 years:

| Return assumption | Nominal terminal corpus | In today's purchasing power |
|---|---|---|
| 15% CAGR, contributions +10%/yr | ~1,500x the *initial monthly* contribution | ÷~5 at 5.5% inflation |
| 16% CAGR, contributions +12%/yr | ~2,000x | ÷~5 |
| 18% CAGR, contributions +12%/yr | ~2,600x | ÷~5 |

The structural conclusion is what matters, and it is independent of the
starting amount: **the binding constraint is contribution growth, not
portfolio return.** Inflation divides the nominal outcome by roughly five
over 30 years, so any "target corpus" stated in today's rupees is an income
question, not a stock-picking question. The biggest lever after year 1 is
contribution growth; the biggest risk is quitting during a drawdown year.

## 1.6 The rejection log (equal in value to the champion)

Every one of these was tested against a pre-registered bar and failed —
they are CLOSED, not to be retried or tuned:

1. **Intraday NIFTY systems** — no edge (pre-campaign).
2. **Short selling** — 2/5 weakly profitable, structurally weak.
3. **Runner/level-based exits** — fixed exits beat them.
4. **RSI-2 dip buying (mean reversion)** — rejected; this universe pays
   continuation, not dip-catching. ("RSI<30 wins 80%" measured: 53% vs a
   55.6% base rate — worse than nothing.)
5. **52wk daily breakout at fixed 2R** — real edge (PF 1.41 OOS) but below
   bar; superseded by the weekly version.
6. **Pyramiding** — halved terminal wealth; in a no-leverage cash account
   the plain system is already fully invested from the first breakout.
7. **NIFTY futures trend (the only testable F&O)** — 15 trades/19yrs,
   CI 0.46-9.95, PF-without-top-3 = 0.38, CAGR 6.5-7.6% at every capital
   level: worse than liquid fund + index SIP. The edge lives in BREADTH;
   one leveraged index amputates it. Options: untestable with free data —
   never ship untested. **F&O is permanently closed** (SEBI: ~9/10 retail
   F&O accounts lose).

Meta-lesson, proven seven times: intuitive "improvements" usually destroy
measured edges. Nothing changes without a pre-registered bar passing first.

---

# PART 2 — EVERY COMMAND, EXPLAINED IN DETAIL

All commands run in the **Terminal** (Ctrl+Alt+T), starting from:

```bash
cd ~/TRADINGVIEW_INDICATOR
```

## 2.1 One-time setup / recovery (after a reinstall only)

```bash
pip install --user --break-system-packages -r requirements.txt   # pandas, numpy, yfinance, pyarrow
pip install --user --break-system-packages pytest                # fallacy-auditor test runner
```
The first line installs the trading tools' libraries (`requirements.txt` at
the repo root) — including **pyarrow**, which is required to read the pinned
`data_cache/*.parquet` snapshot; without it the replication scripts cannot
reproduce the committed figures. The second adds pytest for the auditor's
suite (pydantic itself is pulled in by the editable install below). `--user`
keeps them in your home folder; `--break-system-packages` is Ubuntu's
required override for user-level installs (safe — touches nothing
system-owned).

```bash
pip install --user --break-system-packages -e ./fallacy-auditor
```
Installs the fallacy-auditor package in "editable" mode so
`python3 -m fallacy_auditor` works from anywhere and picks up code changes.

```bash
systemctl --user enable --now ollama
```
Registers the local LLM server to start automatically at every login and
starts it now. Ollama lives at `~/.local/bin/ollama` (user-level install,
no sudo).

```bash
~/.local/bin/ollama pull qwen2.5:7b     # main audit model (bake-off winner)
~/.local/bin/ollama pull qwen3:4b       # fast low-RAM alternative
```
Downloads the free local models. qwen2.5:7b won the three-way accuracy
bake-off; qwen3:4b (~20s/audit) is for when RAM is tight.

**Health check (run any time something seems off):**
```bash
systemctl --user is-active ollama       # expect: active
python3 -m fallacy_auditor --help       # expect: help text
```

## 2.2 The scanner — `tools/stage2_scan.py` (THE Saturday command)

```bash
python3 tools/stage2_scan.py
```
Scans the built-in ~160-name watchlist. For each symbol it downloads 2 years
of daily data, builds weekly bars (completed weeks only — a mid-week run
never judges the still-forming week), computes the 30-week SMA and the
52-week-high anchor, applies a liquidity gate, and prints three groups:
- **NEW BREAKOUT** — fired the Stage-2 entry this week → your buy candidates
- **EXIT** — weekly close crossed below the 30-week SMA → sell if held
- **IN STAGE-2** — trend intact → hold if owned
Each line shows close, SMA30w level, and daily turnover. Every run appends
one row (date, counts, breadth %) to `tools/breadth_log.csv` — the market
regime gauge.

```bash
python3 tools/stage2_scan.py --watchlist tools/watchlist_nifty500.txt
```
Same scan over the full Nifty 500 (the recommended wide net — takes
~10-15 min). `--watchlist` accepts any text file with one symbol per line,
no exchange suffix, `#` for comments.

```bash
python3 tools/stage2_scan.py --watchlist us.txt --suffix "" --min-turnover 5
```
International mode. `--suffix` is Yahoo's exchange suffix: `.NS` NSE
(default), `""` for US tickers, `.L` London. `--min-turnover` is the
liquidity gate in units of 1e7 local currency (5 = 5cr INR ≈ $50M/day for
US names).

## 2.3 The index fetcher — `tools/fetch_nifty500.py` (monthly)

```bash
python3 tools/fetch_nifty500.py                     # Nifty 500 (default)
python3 tools/fetch_nifty500.py --index next50      # Nifty Next 50
python3 tools/fetch_nifty500.py --index midcap150   # Nifty Midcap 150
python3 tools/fetch_nifty500.py --index smallcap250 # Nifty Smallcap 250
```
Downloads the OFFICIAL current constituents from NSE (two mirror URLs) and
writes `tools/watchlist_nifty<index>.txt`. Refresh monthly-ish: the index
reconstitutes twice a year, and scanning today's members today is exactly
how live operation avoids survivorship bias. Refuses to overwrite if the
download looks malformed.

## 2.4 The journal — `tools/journal.py` (after every closed trade)

```bash
python3 tools/journal.py add RELIANCE 2026-07-14 1425.50 2026-11-20 1710.00 70
```
Logs one closed trade: symbol, entry date, entry price, exit date, exit
price, quantity. P&L is computed automatically with the same 0.25%/side
costs as every replication, and appended to `tools/journal.csv`. Add
`--note "PAPER"` during the paper-trading phase, or any note you like.

```bash
python3 tools/journal.py list
```
Prints the whole journal.

```bash
python3 tools/journal.py audit
```
Runs your REAL trades through the full profit-factor fragility audit
(PF, bootstrap confidence interval, PF-without-top-winners, half-vs-half
stability, drawdown, warnings). Run monthly. Benchmark: the replication's
pooled PF ranged 2.0 (recent era) to 3.8. Live PF far below that over 20+
trades = STOP and investigate before sizing up — the cause is usually
rule-breaking, occasionally edge decay; both must be caught early.

## 2.5 The value screen — `tools/value_screen.py` (quarterly)

```bash
python3 tools/value_screen.py
```
Live Magic-Formula screen (Greenblatt): ranks ~90 liquid NSE non-financials
by cheap (high earnings yield = 1/PE) + good (high ROE), filters out
small/overleveraged names, and flags which candidates are ALSO currently in
Stage-2. Uses: prioritising breakouts when slots are scarce; building the
watch-for-the-turn list. Every name needs manual verification on
screener.in (10-yr ROCE consistency, promoter pledging ~0, positive FCF
8/10 yrs) — Yahoo fundamentals occasionally glitch (a VEDL demerger
artifact appeared in our first run, kept as the standing reminder).
Educational output, not SEBI-registered advice.

## 2.6 The auditor — `python3 -m fallacy_auditor` (three modes by input type)

**Mode A — reasoning audit (text file):**
```bash
python3 -m fallacy_auditor idea.txt --verify
```
Sends the text to your LOCAL model (free) with a strict rubric for exactly
five fallacies: survivorship bias, lookahead bias, overfitting, base-rate
neglect, unfalsifiable claims. Every finding must quote the text VERBATIM —
a grounding gate discards anything the model can't quote exactly (the
anti-hallucination guarantee; you've watched it discard fabricated findings
live). `--verify` adds a second fresh-context LLM pass that cross-examines
each finding (measured: removes most false positives at ~zero recall cost).
`--json` for machine-readable output; `--engine fable|opus` for paid Claude
models if ever configured. Exit codes: 0 clean, 1 findings, 2 error.
Takes 1-3 minutes on the 7B model.

**Mode B — Pine Script lint (.pine file):**
```bash
python3 -m fallacy_auditor src/mystrategy.pine
```
Instant, offline, no model. Five mechanical rules with exact line numbers
and verbatim source quotes: `lookahead_on` without the `[1]` offset
(repainting lookahead), lookahead-with-offset (flagged for review),
`calc_on_every_tick=true` (backtest/live divergence), `timenow`, and
`barstate.isrealtime`. Ran clean on all 18 original strategies. Note its
limit honestly: it catches textual certainty-patterns, not order-management
logic bugs (the "never-exits" bug was caught by reading the stats table:
PF 0 + Profitable trades "—" = no trade ever closed).

**Mode C — trade-list audit (.csv file):**
```bash
python3 -m fallacy_auditor trades.csv
```
Reads any CSV/TSV with a profit column (auto-detects delimiter and column;
handles TradingView copy-paste with ₹, commas, unicode minus). Prints:
trades/wins/losses/win-rate, gross P&L, PROFIT FACTOR with bootstrap 95%
CI, expectancy, max consecutive losses, max drawdown, PF first-half vs
second-half, PF without top-1/top-3 winners, and WARNING lines. Trust
rules: CI low above 1.0 = luck alone can't erase it; survives top-3
removal = not a few lucky trades; both halves >1 = stable in time.

**Pooling many exports into one cumulative PF:**
```bash
cd folder_with_csvs
head -1 first.csv > ../pooled.csv && tail -n +2 -q *.csv >> ../pooled.csv
python3 -m fallacy_auditor ../pooled.csv
```
(`head -1` takes one header; `tail -n +2 -q` strips headers from all files;
writing outside the folder stops the pooled file swallowing itself.)

## 2.7 TradingView (free plan) — charts and strategy files

Paste from `src/` into Pine Editor → Add to chart:

| File | Timeframe | Status |
|---|---|---|
| `stock_stage2_trend_weekly.pine` | **1W** | **CHAMPION** — the system you trade |
| `stock_swing_ribbon_pullback.pine` | 1D | validated daily alternative |
| `stock_swing_dual_edge.pine` | 1D | both daily edges in one script |
| `stock_swing_52wk_breakout.pine`, `stock_swing_rsi2_dip.pine` | 1D | research artifacts — do not trade |

The Stage-2 script shows: BUY labels (entry/SL context), regime background
tint (green = Stage 2, red = avoid), a status table (regime / distance to
52w high / position state), and alerts. Free-plan trade export: select the
List of Trades table → Ctrl+C → paste into a file saved as `.csv` — the
auditor parses it as-is.

## 2.8 Research reproduction — `tools/research/` (rerun any study)

Each script re-downloads its own data into a local `data_cache/`:

```bash
cd ~/TRADINGVIEW_INDICATOR/tools/research
python3 replicate_stage2.py            # champion's evidence, 2 universes
python3 replicate_stage2_universe.py ../watchlist_nifty500.txt out_dir        # any watchlist
python3 replicate_stage2_universe.py us_list.txt out_us ""                    # any exchange
python3 stage2_portfolio.py            # the 10-slot portfolio CAGR study
python3 replicate_ribbon.py            # ribbon-pullback replication
python3 replicate_52wk.py              # daily 52wk breakout replication
python3 replicate_stage2_pyramid.py    # pyramiding (REJECTED — the proof)
python3 nifty_fut_trend.py             # futures system (REJECTED — the proof)
python3 portfolio_sim.py               # daily dual-edge portfolio ARR study
python3 rsi30_claim_test.py            # the RSI<30 folklore debunk
python3 value_screen.py                # the quarterly value screen
```

## 2.9 fallacy-auditor maintenance (occasional)

```bash
cd ~/TRADINGVIEW_INDICATOR/fallacy-auditor
python3 -m pytest -q                              # 82 offline tests, ~5s (83rd is the opt-in eval)
pytest -m eval -s                                  # live accuracy eval on the local model
FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s    # two-pass eval (committed snapshot P .87 / R .71; live runs vary)
python3 scripts/redteam.py --fallacy all --n 2     # generate hard eval candidates
python3 scripts/validate_dataset.py data/labeled_examples.jsonl   # dataset integrity
```
Red-team candidates are quarantined as "unreviewed" — human sign-off before
they join the gold set (the model must never grade its own homework).

Environment knobs: `FALLACY_AUDITOR_OLLAMA_MODEL` (default qwen2.5:7b),
`FALLACY_AUDITOR_OLLAMA_URL`, `FALLACY_AUDITOR_OLLAMA_NUM_CTX` (default
8192 — oversized inputs are refused loudly, never silently truncated),
`FALLACY_AUDITOR_OLLAMA_THINK=1` (re-enable thinking-model deliberation).

## 2.10 Git / GitHub (after any work session)

```bash
~/.gitportable/git add -A
~/.gitportable/git commit -m "your message"
~/.gitportable/git push
```
This machine uses the portable git at `~/.gitportable/git`. Credentials are
kept outside the repository in the local git credential store — never commit
a token. Journal and breadth logs are gitignored (personal trading records
stay local and are never published). Every push touching `fallacy-auditor/`
runs its 82-test offline suite automatically via GitHub Actions.

## 2.11 Ollama service management

```bash
systemctl --user status ollama          # is the LLM server running?
systemctl --user restart ollama         # restart it
~/.local/bin/ollama list                # installed models
~/.local/bin/ollama ps                  # what's loaded in RAM right now
~/.local/bin/ollama pull <model>        # add a model
~/.local/bin/ollama rm <model>          # remove one (frees disk)
```

---

# PART 3 — THE CADENCE (the whole life of the system)

| When | What | Commands |
|---|---|---|
| **Saturday (10 min)** | Scan → verify breakouts on 1W chart → write Monday's orders (buys AND exits) | `stage2_scan.py --watchlist tools/watchlist_nifty500.txt` |
| **Monday (5 min)** | Execute the orders; journal any closes | `journal.py add ...` |
| **Monthly** | Audit the journal vs the PF 2+ benchmark; refresh index list; SIP continues regardless of market | `journal.py audit`, `fetch_nifty500.py` |
| **Quarterly** | Value screen → watchlist priorities; tool health | `value_screen.py`, `pytest -q` |
| **Yearly** | Re-run the portfolio study; compare live vs replication; write the year up; change nothing without a pre-registered bar | `stage2_portfolio.py` |
| **Right now (phase gate)** | PAPER-trade the current signals for 3-6 months before real capital | journal with `--note "PAPER"` |

# PART 4 — THE RULES THAT NEVER CHANGE

1. Buy new 52-week-high weekly closes above a rising 30-week SMA; sell
   weekly closes below it. Nothing else is a signal.
2. Equal ~10% slots, max ~10 names, max 3 per sector, full Nifty-500 net.
3. Cash is a position; it lives in liquid funds, never in credit lockups.
4. No F&O, no leverage, no margin funding, no tips — all measured, all closed.
5. Contributions continue on schedule, especially in drawdowns.
6. Every new idea: thesis audit → pine lint → pre-registered bar →
   replication → forward test. Failed = recorded and closed, never tuned.
7. The journal gets audited monthly; the system gets judged on 20+ trades,
   never on the last one.
8. When in doubt, reread the rejection log (Part 1.6) — it is the tuition
   already paid.
