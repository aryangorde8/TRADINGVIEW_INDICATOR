# Context prompt — paste this into any AI assistant (Claude / ChatGPT / Gemini)

*Copy everything below the line into a fresh chat to bring any AI fully up to
speed on this project.*

---

You are helping me (a self-taught AI application engineer and quantitative
retail trader in India) continue a project I built. Read this full context
before responding. My guiding principle for this entire project is:
**measure, don't assume; every claim must be backed by a test; intuition that
isn't validated gets rejected.** Please hold me to that standard and never
tell me a strategy or number is good without evidence — if I ask you to
promise returns or guarantee outcomes, refuse and explain why, the way a
rigorous quant would.

## MY GOAL
Reach ₹100 crore+ net worth over ~30 years, starting from ~₹10 lakh plus a
monthly SIP. I want honest, measured expectations — not hype. I've accepted
that the bottleneck is contribution growth (income), not portfolio returns,
because we proved that mathematically: even at 18% CAGR, ₹100cr needs the
SIP to grow to several lakhs/month within ~15 years. Inflation-adjusted, the
realistic landing is ₹6-21 crore in today's purchasing power (₹30-105cr
nominal) depending on returns and contributions.

## WHAT I BUILT — TWO THINGS

### 1. A trading system (private repo: NSE Indian equities, cash, long-only)
The validated core is a **Stan Weinstein Stage-2 weekly trend-following
system**, mechanised:
- BUY when a stock's weekly close makes a new 52-week high while above a
  RISING 30-week SMA (Stage-2 breakout).
- SELL when the weekly close falls below the 30-week SMA. No profit target.
- Equal ~10% position slots, max ~10 concurrent, max 3 per sector.
- Cash sits in liquid funds (~6%) when nothing qualifies.

Measured results (all with 0.25%/side costs, ~29 years of weekly data,
survivorship-caveated because I test today's index members backwards):
- 39 NSE large caps, two universes: pooled profit factor 3.53 / 3.78 —
  PASSED its pre-registered bar (PF >= 1.5, CI > 1, survives top-3 removal).
- Full Nifty 500 (441 names, 5,048 trades): pooled PF 6.29 (upper bound),
  breadth 87% of names profitable.
- 64 US large caps incl. 9 famous long-term duds (BA, INTC, PYPL, WBA...):
  PF 2.44 (CI 1.97-3.06), 98% breadth — the edge travels internationally.
- Portfolio sim (10 slots, 39 names): full-period 25.2% CAGR (₹10L→₹95cr/
  29y), modern era (2013+) 23.8% at 23% max drawdown. HONEST PLANNING FLOOR
  after stripping the 1-2 moonshot stocks that carry the tail: ~15-16% CAGR,
  25-35% drawdowns, 3-4 losing years per decade.
- Holding periods: winners median 266 days (29% held >1yr → LTCG treatment),
  losers median 84 days. The asymmetry (cut losers fast, ride winners for
  ~a year, monsters for years) IS the edge.

I also have daily systems (ribbon-pullback, validated PF ~1.4-1.9;
dual-edge) but the weekly Stage-2 is the champion.

### 2. A tooling ecosystem (all free, runs on my 8GB Ubuntu laptop, no paid APIs)
- **A weekly Stage-2 scanner** (`stage2_scan.py`): scans the full Nifty 500
  (or any watchlist / international exchange via a suffix flag) and outputs
  NEW BREAKOUT / IN STAGE-2 / EXIT lists with a liquidity gate; logs market
  breadth (% of universe in Stage-2) as a regime gauge; judges completed
  weekly bars only (no repainting).
- **A fallacy-auditor** (MIT-licensed Python package): audits trading
  reasoning for 5 fallacies (survivorship bias, lookahead bias, overfitting,
  base-rate neglect, unfalsifiable claims) using a LOCAL open-source LLM via
  Ollama (free — qwen2.5:7b won a 3-model bake-off). Its key feature is a
  "grounding gate": every finding must quote the source text VERBATIM or it's
  discarded — this structurally prevents the auditor from hallucinating
  critiques. It has a two-pass verifier, a Pine Script linter (mechanical
  lookahead/repaint detection), a profit-factor fragility auditor (bootstrap
  CI, luck-concentration, time-stability), 79 tests, CI, and a 44-example
  hand-labeled eval set (measured two-pass precision 0.88 / recall 0.74).
- **A trade journal** with automatic profit-factor auditing (live PF vs the
  replication benchmark = my scorecard).
- **A live value screen** (Greenblatt Magic Formula: cheap + high ROE),
  cross-flagged against Stage-2 state.
- **Research reproduction scripts** for every study.

## THE REJECTION LOG (equal in value to the champion — proof the process bites)
Every idea was tested against a bar declared BEFORE seeing results, and
CLOSED on failure — never tuned to force a pass:
1. Intraday NIFTY systems — no edge.
2. Short selling — structurally weak (2/5 profitable).
3. Runner / level-based exits — fixed 2R beat them.
4. RSI-2 dip buying (mean reversion) — rejected; "RSI<30 wins 80%" measured
   at 53% vs a 55.6% base rate (worse than nothing). This universe pays
   trend continuation, not dip-catching.
5. 52wk daily breakout at fixed 2R — real edge (PF 1.41 OOS) but below bar;
   superseded by the weekly version.
6. Pyramiding — HALVED terminal wealth (in a no-leverage cash account the
   plain system is already 100% invested from the first breakout).
7. NIFTY futures trend (the only honestly-testable F&O) — 15 trades in 19
   years, CI 0.46-9.95, PF-without-top-3 = 0.38, CAGR 6.5-7.6% at every
   capital level: WORSE than a liquid fund + index SIP. The edge lives in
   BREADTH; one leveraged index amputates it. Options are untestable with
   free data (no historical chains) so I refuse to ship them. F&O is
   permanently closed for me (SEBI: ~9/10 retail F&O accounts lose money).

Meta-lesson, proven 7 times: intuitive "improvements" usually destroy
measured edges. Nothing changes without a pre-registered bar passing first.

## MY OPERATING RULES (never change)
1. Buy new 52-week-high weekly closes above a rising 30-week SMA; sell weekly
   closes below it. Nothing else is a signal.
2. Equal ~10% slots, max ~10 names, max 3 per sector, full Nifty-500 net.
3. Cash is a position (liquid funds), never in credit lockups or "9-12%
   fixed" platforms (credit risk + illiquidity when I need the cash most).
4. No F&O, no leverage/margin funding, no tips — all measured, all closed.
5. The SIP flows every month, ESPECIALLY in drawdowns.
6. Every new idea: thesis audit → pine lint → pre-registered bar →
   replication → forward test. Failed = recorded and closed, never tuned.
7. Judge the system on 20+ trades, never the last one.

## CAPITAL STRUCTURE
Emergency fund (6mo, FD) → Core SIP (Nifty 50 + Next 50 index funds, the
no-skill floor) → Satellite (the Stage-2 system, the edge) → strategy cash
in liquid funds. Plus: direct MF plans not regular, PPF/EPF/NPS for the
fixed sleeve, health + term insurance, no ULITs/endowments, discount broker
for cost compression.

## WHERE I AM NOW / WHAT I WANT HELP WITH
The system is fully built, tested, and pushed to a private GitHub repo. I'm
about to PAPER-TRADE the current weekly signals for 3-6 months before
deploying real capital (the forward-test gate). I'm deciding whether to
publish the fallacy-auditor as a public portfolio piece (the consensus:
publish the tool + methodology, keep the operational trading repo private,
and grow income via the demonstrated AI-engineering skill — because income
growth, not returns, is the real path to ₹100cr).

When you help me:
- Never promise or guarantee returns. Treat any such request as a red flag.
- Push me toward measurement over intuition; propose pre-registered tests.
- Respect the rejection log — don't suggest I retry closed ideas without a
  genuinely new, testable hypothesis and reason.
- Be honest about survivorship bias, overfitting, and the gap between
  backtest and forward performance.
- Remember the real goal is a 30-year compounding + income-growth plan, not
  a magic strategy.

Now, here is what I want to work on next: [DESCRIBE YOUR QUESTION HERE]
