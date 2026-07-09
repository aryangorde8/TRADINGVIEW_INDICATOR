# Interrogation Question Bank — Trading System

Hostile questions grounded in this repo, in the order an interviewer who
actually read the code would ask them. **No answers exist for this file by
design** — you answer from memory, then verify against the cited source.
Grading protocol: answer in writing/aloud → Claude grades against the
implementation → misdescriptions get pointed at the exact file and line.

Rules of engagement: no opening the repo before answering; "I don't know,
I'd check X" is a valid answer and scores higher than a confident guess.

---

## A. The fallacy-auditor (your most defensible engineering)

1. The grounding gate discards any model finding not quoted verbatim from
   the input. Walk through what happens when the model paraphrases a real
   fallacy instead of quoting it. Is that a false negative, and which
   committed metric does it depress — precision (0.87) or recall (0.71)?
   (`fallacy-auditor/src/`, gate logic; `results/eval_report_snapshot.json`)
2. Two-pass verification moved precision 0.69 → 0.87 while recall *fell*
   0.76 → 0.71. Explain the mechanism. What is the verifier rejecting, and
   why is some of it true positives?
3. Your eval is 44 hand-labeled examples. An interviewer says n=44 makes
   the 0.87 meaningless. Defend the number — what's the binomial confidence
   interval on it, roughly, and why did you stop at 44?
4. Per-fallacy results are wildly uneven (lookahead_bias P=0.5, R=0.43 in
   the snapshot). Why is lookahead the hardest class for the model? What
   would you change first to fix it — prompt, examples, or gate?
5. Why a local 7B model instead of a frontier API? Give the real tradeoff
   you accepted, quantified by your own eval numbers.
6. The retry-then-fail-fast loop: what specific failure modes of weak
   models is it built for, what does it do after the retries, and why
   fail-fast instead of best-effort?
7. You license this MIT but the strategy code sits outside the package.
   Where exactly is the boundary and why there?

## B. Backtest methodology (where interviewers smell blood)

8. Universe 2 is labeled "out-of-sample" (PF 3.78). Defend the label —
   both 39-name universes are large-cap NSE *survivors chosen today*. What
   does the R1/OOS split actually control for, and what does it not touch?
9. Your PF confidence intervals come from bootstrap. Bootstrap over what —
   trades, weeks, or names? What correlation structure does that resampling
   silently assume away, and why does it matter for a trend system where
   trades cluster in bull phases?
10. The luck-concentration check recomputes PF without top winners. Your
    committed universe-1 audit: what happens to PF 3.53 when the top trades
    come out, and why is that the single most honest number in the repo?
11. The portfolio sim fills at **weekly close** on a signal computed from
    that same weekly close, with **alphabetical priority** for contested
    slots. Which of these is look-ahead, which is arbitrary, what would
    fixing each do to the 23.9%, and why did you ship it anyway?
    (`tools/research/stage2_portfolio.py`)
12. Costs are 0.25%/side. Reconstruct that number for NSE cash equities —
    brokerage, STT, impact — and say where it's too generous and where
    too harsh.
13. Full-period CAGR is 25.3% but modern-era (2013+) is 23.9% with maxDD
    23.6% vs 38.3% full. Why do you quote the *modern* number as the
    planning figure? What changed structurally around 2013 in your data?
14. Yahoo data drifts — your committed snapshot differs from the doc claims
    by ~0.1-0.5pp. An interviewer asks: "so which number is true?" Answer
    as you would in the room.

## C. The strategy itself (Weinstein Stage-2)

15. State the exact entry condition as coded — all three clauses — and the
    exit. Now: why weekly closes and not daily? What specifically breaks
    at daily granularity? (`src/stock_stage2_trend_weekly.pine:66-85`)
16. Why a *rising* 30-week SMA clause instead of just price-above-SMA?
    Construct the market scenario the rising filter exists to exclude.
17. Your scanner has a completed-weeks filter (`tools/stage2_scan.py:84`).
    What bug does it prevent, and what does the bug look like in P&L terms
    if you remove it?
18. The 52-week-high anchor uses `shift(1)` before the rolling max. One
    line — what look-ahead does the shift kill?
19. A stock gaps down 40% overnight on fraud news, Monday. Trace exactly
    what your system does, week by week, and what your realized loss is
    versus what a daily-stop system would have taken.
20. Defend long-only cash equities against "why no shorts, no futures,
    no options" — from your own 16 months of F&O experience, not theory.

## D. Live trading vs the backtest

21. The backtest caps at 10 slots, equity/10 sizing, no leverage. Your live
    F&O trading uses margin. Why does your backtest model *less* leverage
    than you trade with — and does that make 23.9% a floor, a ceiling, or
    incomparable to your live results?
22. Your journal applies costs per trade (`tools/journal.py:36-40`) and
    audits live PF against the backtest PF. What divergence threshold makes
    you stop trading the system, and where is that number written down?
23. 200+ live NSE trades: what's your live PF, how does it compare to 3.53,
    and what explains the gap in whichever direction it runs?
24. Weekly signals mean acting Monday open after Friday close. What's the
    realistic slippage between Friday's theoretical close fill and your
    actual Monday fill, and is it in the backtest?

## E. Meta (the questions that test honesty, not knowledge)

25. "Is this a verifiable track record?" — answer in one sentence, then
    justify it using the repo's own reproducible-vs-asserted distinction.
    (`TRADING_SYSTEM_RECON.md`)
26. What claim about this system did you *stop* making after the recon
    audit, and why? (`TRADING_SYSTEM_RECON.md`, "do not claim" list)
27. What's the single weakest part of this repo an interviewer could find
    in ten minutes, and what's your prepared, honest response to it?
28. If a fund handed you ₹50L tomorrow and said "run this," what would you
    fix first before deploying — and why hasn't it been fixed already?

---

*Grading sessions: answer ≥3 at a time. Confident wrong answers cost more
than honest gaps. After all sections pass, the Mnemos bank gets written.*

---

## Self-grading protocol (no Claude required)

The answer key for every question above already exists: it is the cited
source file. The repo's own recon rule applies — **the code wins.**

Per question:
1. Write your answer down first. Full sentences, from memory, repo closed.
   No written answer = no attempt; reading the code first is the cheat.
2. Open the cited file(s). Check every factual claim in your answer against
   the code — line by line, the way a skeptical interviewer would.
3. Mark each claim ✓ / ✗ / didn't-mention. Score the question PASS only if
   zero ✗. Confidently-wrong beats unmentioned in badness.
4. Re-attempt every failed question from scratch after 2+ days — not the
   same day (same-day retries test short-term memory, not understanding).

Optional local grader: you already run qwen2.5:7b via Ollama. Paste the
question, your written answer, and the cited source file into it and ask
only: "list every claim in this answer that the code contradicts, quoting
the code." Treat its output like your own auditor treats model findings —
verify each quote exists before believing it (your grounding-gate rule,
applied to your grader).

For the meta-questions (25-28) there is no code oracle: record yourself
answering aloud, wait a day, listen as a stranger. If you hear hedging or
recitation, rewrite.
