# COMMANDS.md — Workflow, validation, comparison

## The honest constraint
There is NO local Pine compiler and NO Pine unit-test framework. You (Claude Code)
cannot execute or compile this code. "Testing" = (1) a disciplined self-review
checklist, then (2) the human pastes it into TradingView's Pine Editor and runs
the Strategy Tester. Plan around that. Do not pretend to have run it.

## Git (this IS supported — do it)
git init                              # once
git checkout -b feat/strategy-core    # work on a branch, not main
# BEFORE each change:
git add -A && git commit -m "chore: checkpoint before <change>"
# AFTER each phase, conventional commits, e.g.:
#   feat: add gate-1 bias logic
#   feat: add atr stop + 2R target + trail
#   fix: prevent same-bar lookahead on breakout trigger
#   docs: update STRATEGY_SPEC with variant C

## Optional: worktrees for parallel variants (overkill for one file — your call)
git worktree add ../nifty-variant-b feat/variant-b-pullback
git worktree add ../nifty-variant-c feat/variant-c-momentum
# Only useful if you want all three open simultaneously. For a single .pine file,
# plain branches are enough. Don't cargo-cult worktrees here.

## "Compile" step (human, in TradingView)
1. Paste a variant into the Pine Editor.
2. Confirm zero errors/warnings.
3. Add it to a NIFTY 5-min chart.
4. Open the Strategy Tester; set the date range; record metrics.

## Self-review checklist (Claude Code fills this BEFORE every commit)
[ ] //@version=6 and strategy() with commission + slippage set
[ ] No request.security lookahead_on; no same-bar omniscient entry
[ ] All entries/exits gated on confirmed bars
[ ] Every parameter is an input with group + tooltip (no magic numbers)
[ ] Sections 1–8 present and single-responsibility
[ ] BUY CE / BUY PE / EXIT CE / EXIT PE labels implemented
[ ] Stop & target lines drawn while in position; stale objects deleted
[ ] alertcondition()/alert() for all 4 events
[ ] R computed from |entry-stop|; target = rrTarget*R; trail arms at +1R
[ ] Force-flat at 15:15; no new entries after 14:45
[ ] Divide-by-zero / na guarded
Paste the filled checklist in your message with the diff.

## Validation date sets (test ALL — no cherry-picking)
- Trending-up month:   <Aryan picks a clearly bullish month>
- Trending-down month: <Aryan picks a clearly bearish/correction month>
- Choppy/range month:  <Aryan picks a sideways month>
Use the SAME three across every variant.

## Variant comparison table (fill from Strategy Tester)
| Metric            | A breakout | B pullback | C momentum |
|-------------------|------------|------------|------------|
| Net P&L (R)       |            |            |            |
| Win rate %        |            |            |            |
| # trades          |            |            |            |
| Profit factor     |            |            |            |
| Max drawdown      |            |            |            |
| Avg R / trade     |            |            |            |
| Worst losing run  |            |            |            |
Decision rule: prefer the variant with the most CONSISTENT positive expectancy
ACROSS all three regimes — not the highest single-window win rate. Take the best
sub-ideas from each, fold into a final candidate, then RE-VALIDATE that candidate.
