# PINE_STANDARDS.md — Code quality, Pine v6, anti-repaint

## Version & type
- First line: `//@version=6`. Use `strategy(...)` with `overlay=true`,
  `calc_on_every_tick=false`, `process_orders_on_close=true`, an `initial_capital`,
  a `default_qty_type`, and realistic `commission_*` + `slippage`.

## NON-REPAINTING — automatic FAIL if violated
- Evaluate all entry/exit conditions on CONFIRMED bars only
  (`barstate.isconfirmed`) or reference completed values with `[1]`.
- NEVER use `request.security(... lookahead=barmerge.lookahead_on)` on a
  real-time series. If you must pull HTF data, use `lookahead_off` and offset.
- Do NOT use the still-forming bar's high/low/close to decide an entry that is
  then plotted on that same bar as if it were known.
- A printed signal must NEVER move or disappear on the next tick. State in a code
  comment why each signal is fixed.

## Structure (so errors are locatable without spelunking)
Order the file in clearly headered sections:
  // === 1. INPUTS ===
  // === 2. INDICATORS / DATA ===
  // === 3. SESSION & FILTERS ===
  // === 4. SIGNAL LOGIC (GATES) ===
  // === 5. RISK & EXITS ===
  // === 6. ORDERS ===
  // === 7. PLOTTING ===
  // === 8. ALERTS ===
One responsibility per section. Helper logic in named functions, not inline.

## Naming
- camelCase for variables/functions; UPPER_SNAKE for true constants.
- Prefix by domain: `inAtrLen`, `sigLongTrigger`, `riskStopPrice`, `plotBuyCe`.
- Booleans read as predicates: `isLongBias`, `canEnter`, `inSession`.

## Inputs
- Every tunable is `input.*` with `group=` and `tooltip=`. No magic numbers.
- Group logically: Session / Bias / Trigger / Risk / Display / Alerts.

## Pine v6 specifics to get right
- `na` in boolean context is stricter in v6 — handle explicitly with `na()`/`nz()`.
- Use `switch`/`if` as expressions for `triggerMode` selection.
- Use v6-idiomatic built-ins; avoid deprecated v5 forms.
- Namespaced TA functions: `ta.ema`, `ta.atr`, `ta.vwap`, `ta.highest`, etc.
- Manage drawing-object limits: cap labels/lines and delete stale ones
  (`label.delete`, `line.delete`) to avoid the ~500-object ceiling.

## Performance
- One ATR/EMA/VWAP computation each; no redundant `request.security`.
- Don't loop unnecessarily; Pine recomputes per bar already.

## What NOT to do
- No future leakage, no lookahead, no HTF leak, no same-bar omniscience.
- No hardcoded literals scattered in logic.
- No silent failure: guard divide-by-zero and `na` with explicit checks.
