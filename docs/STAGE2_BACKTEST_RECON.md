# Stage-2 Backtest — Read-Only Recon

*Factual inventory produced by reading the committed source only. Nothing was
run, modified, or fetched. Every claim cites file + line. "NOT IN REPO" is
used literally, not as shorthand for "probably somewhere."*

Repo: `aryangorde8/TRADINGVIEW_INDICATOR` @ `edfdc3e`. Working tree clean.
Recon date: 2026-07-09.

---

## 1. ARTIFACT INVENTORY

| # | Artifact | Status |
|---|---|---|
| a | Per-trade log | **PARTIAL** — see below |
| b | Equity curve / NAV series | **NOT IN REPO** |
| c | Pinned price snapshot | **NOT IN REPO** — fetched live |
| d | 44-example gold set with labels | **IN REPO** |
| e | Per-example model outputs | **IN REPO** |
| f | Config / parameter file | **NOT IN REPO** |

**a. Per-trade log** — `results/backtests/stage2_universe1_pooled.csv` (tracked,
**383 rows**) and `results/backtests/stage2_universe2_oos_pooled.csv` (tracked,
**354 rows**).

Columns (both): `Entry Date, Exit Date, Days Held, Entry, Exit, Profit INR` —
written at `tools/research/replicate_stage2.py:75-80`.

**Missing columns: symbol, size/qty, initial stop.** Symbol is dropped at
pooling (`replicate_stage2.py:103`); qty and stop are never recorded.

Date ranges:
- U1: entry `1997-01-03` → `2026-02-13`; exit `1997-03-14` → `2026-06-26`
- U2: entry `1997-01-03` → `2026-03-13`; exit `1997-08-29` → `2026-07-10`

Per-name trade CSVs are written to `stage2_r1/{name}.csv` / `stage2_oos/{name}.csv`
(`replicate_stage2.py:92`) — **NOT IN REPO** (absent from `git ls-files`).

The **portfolio** simulation (`tools/research/stage2_portfolio.py`) produces **no
per-trade log at all** — only an integer counter (`:53`, `:67`) and printed
summaries (`:103-107`).

**b. Equity curve** — `stage2_portfolio.py:92` builds `eq` in memory; never
written to disk. Only aggregate lines are printed. **NOT IN REPO.**

**c. Price data** — `data_cache/` is gitignored (`.gitignore:9`). Fetched live:

```python
# tools/research/portfolio_sim.py:55-57
df = yf.download(f"{name}.NS", period="max", interval="1d",
                 auto_adjust=True, progress=False,
                 multi_level_index=False)
```

**NOT IN REPO.**

**d. Gold set** — `fallacy-auditor/data/labeled_examples.jsonl` (tracked).
**44 lines.** 38 labeled spans; **10 examples carry zero labels** (negatives).
Per-class: overfitting 9, unfalsifiable 8, survivorship_bias 7,
lookahead_bias 7, base_rate_neglect 7.

**e. Per-example outputs** — `fallacy-auditor/results/eval_report_snapshot.json`
(tracked), key `rows`: 44 entries of shape
`{"id", "gold", "raw", "verified", "verifier_rejected"}`.

**f. Config file** — none. Parameters are module-level constants
(`stage2_portfolio.py:19-33`, `replicate_stage2.py:19-29`) and Pine `input.int`
(`src/stock_stage2_trend_weekly.pine:62-64`). **NOT IN REPO.**

---

## 2. DEFINITIONS

**a. CAGR** — `tools/research/stage2_portfolio.py:93-97`:

```python
yrs = (eq.index[-1] - eq.index[0]).days / 365.25
cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
mod = eq[eq.index >= MODERN]
myrs = (mod.index[-1] - mod.index[0]).days / 365.25
mcagr = (mod.iloc[-1] / mod.iloc[0]) ** (1 / myrs) - 1
```

Denominator is **calendar years elapsed** (first to last weekly bar), not years
invested.

Starting capital: `START = 1_000_000.0` (`:22`). `eq.iloc[0]` equals START
because `mtm` is computed *before* entries each week (`:69-73` precede `:74-89`),
so week 1 records pre-entry cash.
Ending capital: `eq.iloc[-1]` — snapshot reports **96.4 cr**.
Modern cutoff: `MODERN = pd.Timestamp("2013-01-01")` (`:23`).

**Exact start and end dates are NOT PRINTED** by the script and appear nowhere in
the committed snapshot — only `"FULL ~29y"`. **NOT IN REPO.**

**b. Max drawdown** — `stage2_portfolio.py:98-99`:

```python
dd = ((eq.cummax() - eq) / eq.cummax()).max()
mdd = ((mod.cummax() - mod) / mod.cummax()).max()
```

Computed on `eq` = **weekly mark-to-market NAV including open positions**
(`mtm`, `:69-73`).

Separately, the auditor's `max drawdown: 28417983.56` in
`results/backtests/stage2_universe1_audit.txt` is a **different quantity**: a
rupee amount on the **closed-trade cumulative** curve
(`fallacy-auditor/src/fallacy_auditor/profit.py:127-134`) — not a percentage and
not mark-to-market.

**c. Yearly returns** — `stage2_portfolio.py:100-101`:

```python
yearly = eq.resample("YE").last().pct_change().dropna()
myearly = yearly[yearly.index >= MODERN]
```

**Calendar-year change in mark-to-market NAV.** Not a sum of trades closed that
year.

**d. Last bar / partial year** — Max exit label in the committed U2 pooled CSV is
**`2026-07-10`**. `replicate_stage2.py:37` resamples `.resample("W-FRI").last()`
**with no completed-week filter**, so the final bin is the *in-progress* week
labelled with its future Friday. Contrast `tools/stage2_scan.py:84`, which *does*
filter to completed weeks (commit `9e443c5`, "scanner judges completed weekly
bars only"). The research scripts do not carry that fix.

**2026 is a partial year.** The snapshot's `2026:-14%` is a partial-year figure.

---

## 3. EXPECTANCY

**a.** `fallacy-auditor/src/fallacy_auditor/profit.py:219`:

```python
expectancy=sum(profits) / n,
```

Yes — **simple arithmetic mean of the rupee `Profit INR` column** (U1:
1,588,028.37).

Material caveat from the source: `replicate_stage2.py:61-62` resets
`equity = START` **inside the per-name loop** — every one of the 19/20 names
trades its own fresh ₹10,00,000 account and compounds independently. The pooled
file therefore mixes trades taken at wildly different equity levels; a name that
compounded 50× produces rupee P&Ls two orders of magnitude larger than an early
trade. **Mean rupee P&L is not a per-trade edge measure on this file.**

**b. Initial stop at entry: NONE EXISTS.** The only exit is a trend break:

```python
# tools/research/replicate_stage2.py:70
if row.c < row.sma30:
```

```python
# tools/research/stage2_portfolio.py:64
if row.c < row.sma:
```

`grep -n "stop"` over `src/stock_stage2_trend_weekly.pine` returns **no matches**.
There is no stop rule to quote.

**c. Initial risk (entry − stop) × shares: NOT RECORDED and NOT RECOMPUTABLE.**
No stop exists, and the pooled CSV has no `qty` column — share count is not
recoverable from committed data either.

**d. Position sizing** — two different rules:

```python
# replicate_stage2.py:84  (per-name: all-in on full name equity)
q = int(equity / (row.c * (1 + COST)))
```

```python
# stage2_portfolio.py:84-85  (portfolio: equity/10, cash-capped)
alloc = min(mtm / MAX_SLOTS, cash)
qty = int(alloc / (row.c * (1 + COST)))
```

Neither is risk-based — there is no stop to size against.

---

## 4. THE 10-SLOT MECHANIC

**a. Ranking** — `tools/research/stage2_portfolio.py:75-83`:

```python
    for n in NAMES:
        if len(pos) >= MAX_SLOTS:
            break
        if n in pos or n not in data or wk not in data[n].index:
            continue
        row = data[n].loc[wk]
        if pd.isna(row.sma) or pd.isna(row.anchor) or not row.rising:
            continue
        if row.c > row.anchor and row.c > row.sma:
```

`NAMES = sorted([...])` (`:25`). The winner is the **alphabetically first
ticker**. There is no strength, momentum, or liquidity ranking.

**b. Lookahead check — no future-bar data is used anywhere.** Specifically:

- Anchor is correctly lagged: `w["anchor"] = w["c"].shift(1).rolling(52).max()`
  (`:45`) — the shift removes the current bar from its own 52-week high.
- `w["rising"] = w["sma"] > w["sma"].shift(4)` (`:46`) — both terms trailing.
- The alphabetical rank uses **no price data at all**.

**What is present is same-bar-close execution, not lookahead:** the fill price is
`row.c` (`:83-88`), the very weekly close that generates the signal, and sizing
uses `mtm` (`:84`) which was marked at that same close (`:72`). This assumes you
transact *at* a close you only observe *at* the close. It uses no future
information, but it is not executable as written.

**c. Skipped signals are DROPPED, not queued.** `:76-77` breaks the entry loop
when slots are full; no queue or pending-signal structure exists in the file. A
skipped name re-enters only if its entry condition re-fires on a later week
(conditions are re-evaluated fresh each iteration).

**d. Average open positions / % weeks fully invested / % time in cash: NOT IN
REPO.** `stage2_portfolio.py` tracks `pos` but records none of these statistics —
only `trades` (`:53`, `:67`) and `curve` (`:90`). The committed snapshot prints
none of them.
(The `avg concurrent=7.1` line printed by `portfolio_sim.py` belongs to a
**different strategy** — ribbon + 52wk breakout, `portfolio_sim.py:1-4` — not
Stage-2.)

---

## 5. FRAGILITY CHECK

**a.** `fallacy-auditor/src/fallacy_auditor/profit.py:171-209` — the warnings
block:

```python
    warnings: list[str] = []
    if n < SMALL_SAMPLE:
        ...
    if pf is None:
        ...
    elif pf < 1.0:
        warnings.append("profit factor below 1.0 — gross losses exceed gross profits")
    if pf is not None and pf >= 1.0 and pf_top3 is not None and pf_top3 < 1.0:
        warnings.append(
            "fragile edge: removing the top 3 winners drops the profit "
            "factor below 1.0 — the result is concentrated in a few trades"
        )
    if profits and gross_profit > 0 and max(profits) > 0.5 * gross_profit:
        warnings.append(
            "a single trade contributes more than half of all gross profit"
        )
    if (
        pf is not None
        and pf >= 1.0
        and (
            (pf_first is not None and pf_first < 1.0)
            or (pf_second is not None and pf_second < 1.0)
        )
    ):
        ...
    if ci_low is not None and ci_low < 1.0 <= (pf or 0):
        ...
```

Thresholds: sample `n < 30` (`SMALL_SAMPLE`, `:27`); `pf < 1.0`;
**`pf_excl_top3 < 1.0`**; `max(profits) > 0.5 × gross_profit`;
`pf_first_half < 1.0` **or** `pf_second_half < 1.0`; `ci_low < 1.0`.

**b. Why Universe 2 emitted "no fragility warnings" despite PF 3.78 → 1.57 on
removing 3 of 354 trades.**

Measured from the committed `stage2_universe2_oos_pooled.csv`:

| Test (`profit.py` line) | Threshold | U2 actual | Fired? |
|---|---|---|---|
| Luck concentration (`:184`) | `pf_excl_top3 < 1.0` | **1.57** | **No** |
| Single-trade dominance (`:189`) | `max > 50% of gross profit` | top-1 = **40.0%** | **No** |
| Time stability (`:193-204`) | either half `< 1.0` | 15.00 / **1.99** | **No** |
| Bootstrap CI (`:205`) | `ci_low < 1.0` | **1.17** | No |
| Small sample (`:172`) | `n < 30` | 354 | No |

**Every threshold is an absolute floor at 1.0. None tests relative degradation.**
A profit factor that collapses 58% (3.78 → 1.57), or a second half that decays
7.5× (15.00 → 1.99), passes silently — both land above the floor.

Underlying concentration (computed from the committed CSV): top-1 trade
**₹40.78 cr**, top-2 **₹9.61 cr**, top-3 **₹9.06 cr**; gross profit **₹102.0 cr**.
**The top 3 of 354 trades (0.85%) supply 58.3% of all gross profit; the single
largest supplies 40.0%** — 10 percentage points under the dominance trigger.

---

## 6. PARAMETERS AND PROVENANCE

**a. Every tunable parameter with its committed value:**

| Parameter | Value | Location |
|---|---|---|
| New-high lookback | 52 weeks | `replicate_stage2.py:41`, `stage2_portfolio.py:45`, Pine `:62` |
| Trend SMA | 30 weeks | `replicate_stage2.py:40`, `stage2_portfolio.py:44`, Pine `:63` |
| SMA-rising lookback | 4 weeks | `replicate_stage2.py:42`, `stage2_portfolio.py:46`, Pine `:64` |
| Bar resample | `W-FRI` | `replicate_stage2.py:37`, `stage2_portfolio.py:41` |
| Min history | 60 weeks | `replicate_stage2.py:38`, `stage2_portfolio.py:42` |
| Cost/side | 0.0025 | `replicate_stage2.py:28`, `stage2_portfolio.py:21` |
| Start capital | 1,000,000 | `replicate_stage2.py:29`, `stage2_portfolio.py:22` |
| Max slots | 10 | `stage2_portfolio.py:20` |
| Modern-era cutoff | 2013-01-01 | `stage2_portfolio.py:23` |
| Bootstrap seed / rounds | 7 / 1000 | `profit.py:28-29` |
| Small-sample threshold | 30 | `profit.py:27` |

**b. Parameter-change commits, from `git log`:**

```
092fd2b 2026-07-07 audit: recon report + fixes (cost reconcile, committed results, dead code, docstring)
2259bf4 2026-07-07 feat: fallacy-auditor v0.4 + stage-2 trend system + research replications
```

(`git log -- tools/research/replicate_stage2.py tools/research/stage2_portfolio.py src/stock_stage2_trend_weekly.pine`)

**Two commits total, both on 2026-07-07. Zero parameter-change commits. Zero
re-evaluation cycles are visible in git for the Stage-2 system.**

**c. A priori or tuned? — git evidence, stated precisely.**

The *claims* of pre-registration exist in the source:

```python
# tools/research/replicate_stage2.py:1-9
"""Stage-2 weekly trend rider — registered spec (decided before running):
...
- BAR:   pooled date-sorted PF >= 1.5 on BOTH universes separately,
         CI low > 1.0, survives top-3 removal. FAIL => REJECT, no re-tuning.
```

```pine
// src/stock_stage2_trend_weekly.pine:39
// DO NOT   : tune the 52/30/4 lengths — they are the literature-standard,
```

**Git cannot verify either claim.** The spec, the code, and the results all
landed in a **single commit** (`2259bf4`). There is no commit sequence showing
the spec existing before the results. The pre-registration is **asserted in a
docstring, not proven by history**.

**Counter-evidence of a tuning culture in the same repo, on *other* strategies**
(all pre-dating Stage-2):

```
22a2287 2026-06-16 fix: rsi dip level 40->50 (and rip 60->50) for trend-pullback
2fb3a38 2026-06-16 test: rrTarget 1.5->2.5 (fixed-target config) + firstTgtR 1.5->2.0 ... payoff test on same entry
0a1642c 2026-06-17 feat: 3tp variant — set TPs to 50%@1.8R / 30%@2.2R / 20%@2.5R
c6eaad3 2026-06-18 feat: 2r arm-stop -> -0.5R at 1R (configurable armToR), book@2R
```

These are the ribbon/swing strategies (`src/stock_swing_*.pine`), **not**
Stage-2. The distinction is real and should be stated as such: Stage-2's
parameters show no tuning in git; the repo's other strategies show extensive
iterative tuning against results.

**d. Fitted on one period, validated on a strictly later one? — NO.**

U1 and U2 are **different tickers over the same calendar span** (both pooled
files begin `1997-01-03` and run into 2026). This is a **cross-sectional** split,
not a temporal one. There is no walk-forward, no train/test time boundary, and no
out-of-time holdout anywhere in the Stage-2 code. The `MODERN = 2013-01-01`
cutoff (`stage2_portfolio.py:23`) is a *reporting* segmentation applied after the
fact, not a validation split.

---

## 7. UNIVERSES

**a.** `tools/research/replicate_stage2.py:20-26`:

**U1 (`R1`, 19 names):** RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS, SBIN,
BHARTIARTL, ITC, LT, HINDUNILVR, BAJFINANCE, MARUTI, SUNPHARMA, TITAN,
ULTRACEMCO, AXISBANK, KOTAKBANK, TATASTEEL, ADANIGREEN

**U2 (`OOS`, 20 names):** WIPRO, HCLTECH, TECHM, ASIANPAINT, NESTLEIND,
BAJAJFINSV, ADANIPORTS, POWERGRID, NTPC, ONGC, COALINDIA, JSWSTEEL, HINDALCO,
DRREDDY, CIPLA, EICHERMOT, HEROMOTOCO, BRITANNIA, DABUR, VEDL

**Disjoint: yes** (19 + 20 = 39 = the `NAMES` list in `stage2_portfolio.py:25-33`).

**Same date range: pooled, yes** (both 1997 → 2026). **Per-name, no** — several
U2 constituents listed far later than 1997 (e.g. POWERGRID, COALINDIA,
ADANIPORTS), and U1 contains ADANIGREEN (listed 2018). Per-name effective ranges
are not recorded in any committed artifact.

**b. Provenance of the lists: hardcoded literals** (`replicate_stage2.py:20-26`).
**NOT IN REPO:** any script, note, or index file documenting how these 39 were
selected, or any point-in-time membership source. They are large-cap NSE names
that exist today — **membership as of today, survivorship-biased by
construction.** (`tools/watchlist_*.txt` files exist but drive the scanner, not
the backtest, and are themselves current-membership lists.)

---

## 8. COSTS AND FILLS

**a.** `COST = 0.0025` (`replicate_stage2.py:28`, `stage2_portfolio.py:21`).
Applied on **both** sides:

```python
# replicate_stage2.py:71 (exit)   proceeds = row.c * qty * (1 - COST)
# replicate_stage2.py:73 (entry)  cost_basis = entry_px * qty * (1 + COST)
# stage2_portfolio.py:65 (exit)   cash += row.c * pos[n]["qty"] * (1 - COST)
# stage2_portfolio.py:88 (entry)  cash -= row.c * qty * (1 + COST)
```

**b. Fill price: the signal bar's own weekly close** (`row.c` at
`replicate_stage2.py:83-88`; `stage2_portfolio.py:83-88`). Not next-bar open, not
next-bar close.

**c. Slippage / gap model: NONE** beyond the flat 0.25%. No slippage term, no
gap-through handling, no liquidity or volume constraint, no partial fills, no
stop-vs-gap ambiguity. (`portfolio_sim.py:10-11` mentions "gap-at-open,
stop-first ambiguity" — that docstring belongs to the **ribbon/52wk** strategy,
not Stage-2.)

---

## 9. FALLACY-AUDITOR EVAL

**a. Confusion matrices** (`fallacy-auditor/results/eval_report_snapshot.json`,
run `2026-07-07`, engine `ollama`, 44 examples):

| Pipeline | tp | fp | fn | tn | Precision | Recall |
|---|---|---|---|---|---|---|
| Raw (single-pass) | 29 | 13 | 9 | **not reported** | 0.690 | 0.763 |
| Verified (two-pass) | 27 | 4 | 11 | **not reported** | 0.871 | 0.711 |

**TN is NOT IN REPO** — the task is span/label detection, not binary
classification, so true negatives are undefined in the report schema
(`raw.micro` / `verified.micro` carry only `precision, recall, tp, fp, fn`).

The two-pass verifier removed **9 false positives and 2 true positives**
(tp 29→27, fn 9→11). That is the mechanism behind the precision gain and the
recall loss.

**b. Total gold positives: 38 labeled spans across 44 examples** (10 examples
have zero labels). Confirmed internally: `tp + fn = 38` in both pipelines
(29+9, 27+11).

**c. Temperature 0: YES.** `fallacy-auditor/src/fallacy_auditor/llm.py:155`:

```python
"options": {"temperature": 0, "num_ctx": self._num_ctx},
```

**Seed: NOT PINNED — NOT IN REPO.** No `seed` key is sent to Ollama in the
options dict. (Contrast `profit.py:29`,
`BOOTSTRAP_SEED = 7  # fixed: the report must be reproducible` — the bootstrap
*is* seeded.)

---

## 10. REPRODUCIBILITY

**A fresh clone cannot reproduce the README backtest numbers exactly.** Sources
of non-determinism, in order of severity:

1. **No pinned price data.** `data_cache/` is gitignored (`.gitignore:9`).
   `portfolio_sim.py:55` re-fetches from Yahoo with `period="max"`, so a later
   run sees additional bars. `auto_adjust=True` means splits/dividends
   **restate the entire historical series** — past prices change, not just
   recent ones.
2. **The in-progress week is included.** `replicate_stage2.py:37` /
   `stage2_portfolio.py:41` resample `W-FRI` with **no completed-week filter**
   (unlike `stage2_scan.py:84`). The final bar differs depending on the weekday
   you run it.
3. **2026 is a partial year.** The `2026: -14%` figure moves every week and is
   not comparable to complete years in the same table.
4. **LLM eval is not seed-pinned** (`llm.py:155` sends temperature 0 but no
   seed). Also variable: the `qwen2.5:7b` Ollama tag can be re-pulled with new
   weights, `num_ctx`, and worker parallelism (`test_eval.py:137`,
   `FALLACY_AUDITOR_EVAL_WORKERS`).
5. **Ollama must be running locally with the model pulled** — the eval cannot
   run at all otherwise.

**What IS deterministic and reproducible:** every number in
`results/backtests/*_audit.txt` is reproducible from the committed pooled CSVs,
because `profit.py` is pure stdlib with a fixed bootstrap seed (`:29`). The
committed pooled CSVs and the committed eval snapshot are the only fixed records
in the repo; the CAGR, max-drawdown, and yearly-return figures depend entirely on
uncommitted, drifting data.
