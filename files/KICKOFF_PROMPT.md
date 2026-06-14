# KICKOFF_PROMPT.md — Paste this into Claude Code first

You are building a NIFTY 5-minute intraday option-buying STRATEGY in Pine Script
v6 for TradingView. Work as a rigorous quant engineer, not a yes-man. Be terse,
technical, and brutally honest. If something I asked for is impossible in Pine or
statistically unsound, say so and give the closest sound alternative.

CONTEXT FILES (read in this exact order before writing any code):
1. CLAUDE.md  2. STRATEGY_SPEC.md  3. PINE_STANDARDS.md  4. COMMANDS.md
These define the goal, the trading logic, coding standards, and workflow. Treat
CLAUDE.md section 2 ("Hard truths") and the non-repainting rules as inviolable.

NON-NEGOTIABLES:
- Do NOT engineer toward "80% accuracy." Target positive expectancy at >=1:2 R:R,
  robust across the 3 regimes in COMMANDS.md. Reject overfit parameter sets.
- Non-repainting is mandatory. Repainting = fail.
- You cannot compile/run Pine. Use the COMMANDS.md self-review checklist instead
  and paste it filled before every commit. Never claim you ran the backtest.

WORK IN PHASES. Stop at the end of each phase, commit, and wait for my go-ahead.

PHASE 0 — Alignment
- Read all four context files. Restate the goal, the constraints, and the gate
  architecture IN YOUR OWN WORDS. List anything ambiguous and ask me. Run
  `git init` + create the working branch. Do NOT write strategy code yet.

PHASE 1 — Scaffold + data layer
- Create the .pine skeleton with all 8 sections, the full input block (groups +
  tooltips, zero magic numbers), and the indicator/data layer (EMAs, ATR, VWAP,
  session detection). Fill the applicable checklist items, commit.

PHASE 2 — Signal gates (Variant A: breakout)
- Implement GATE 1/2/3 for the breakout family per STRATEGY_SPEC. Confirmed-bar
  evaluation only. No orders yet — just the boolean signals + debug plots.
  Justify in comments why each signal is non-repainting. Checklist, commit.

PHASE 3 — Risk, exits, orders, rendering
- ATR stop, 2R target, trail-at-1R, time stop, opposite-flip exit. Wire
  strategy.entry/close. Plot BUY CE / BUY PE / EXIT CE / EXIT PE labels + stop &
  target lines (delete stale objects). Add alertcondition()/alert() for all 4
  events. Full checklist, commit. Variant A is now complete.

PHASE 4 — Variants B and C
- Produce Variant B (pullback) and Variant C (momentum-only), each as its own
  .pine, sharing the identical risk model. Genuinely different logic, not renamed
  numbers. Checklist + commit per variant.

PHASE 5 — Validation pack
- Output the COMMANDS.md comparison table (I'll paste in the Strategy-Tester
  numbers after I run each over the 3 date sets), plus a short written read on
  each variant's failure modes and which sub-ideas to merge into a final
  candidate. Then build that final candidate and mark it for re-validation.

Begin with PHASE 0 now. Do not skip ahead.
