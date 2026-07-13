# fallacy-auditor

A strictly grounded auditor for trading reasoning — **free to run**. Give it
a block of text; it returns a schema-validated list of findings, each
flagging one of exactly five reasoning fallacies together with the
**verbatim substring** of the input that triggered it. Any finding whose
cited span is not a literal substring of the input is discarded — never
repaired — which is the primary defense against the auditor itself
hallucinating critiques.

The default engine is a **local open-weights model via
[Ollama](https://ollama.com)**: no API key, no per-token cost, nothing paid.
The paid Claude engines are an optional extra for when quality matters more
than cost. The pipeline — grounding gate, verification pass, red-team loop —
is identical either way, because everything sits behind a one-method
provider seam.

Three complementary surfaces, because a strategy lies in three places:

- **Reasoning audit (LLM):** prose in, grounded findings out.
- **Pine Script lint (deterministic):** strategy code in, mechanical bias
  red flags out — rule-based, offline, instant, no model involved.
- **Profit-factor audit (deterministic):** the backtest's exported trade
  list in, fragility report out — is the headline profit factor real, or
  three lucky trades in a small sample?

**Scope (and nothing past it):** text, a Pine file, or a trade CSV in — one
report out. No UI, no live market data, no portfolio scoring, no trade
recommendations, no HTTP API.

## Install (free path)

```bash
# 1. The package (core dependency: pydantic only)
cd fallacy-auditor
pip install -e ".[dev]"

# 2. Ollama + a model (one-time, free)
#    https://ollama.com/download
ollama pull qwen2.5:7b        # ≈4.7 GB download, wants ~5.5 GB free RAM (default)
# fast / low-RAM alternative (fine with an IDE open on 8 GB):
#   ollama pull qwen3:4b
#   export FALLACY_AUDITOR_OLLAMA_MODEL=qwen3:4b
```

The default is the model that *measured* best on the gold set, not the
newest one — see "Measured results" below. On an 8 GB machine it wants
other heavy apps closed; `qwen3:4b` is the interactive/low-RAM option
(~20 s per audit).

## Measured results (8 GB RAM laptop, CPU-only, all free)

Full per-run detail accumulates in `eval_report.json`.

### Model bake-off (original 18-example set, 2026-07-03)

Three free local models, identical pipeline. Two-pass = audit +
fresh-context verifier.

| Model | Single-pass P / R | Two-pass P / R | Two-pass wall time |
|---|---|---|---|
| qwen3:4b | 0.64 / 0.94 | 0.76 / 0.94 | ~13 min |
| **qwen2.5:7b (default)** | 0.81 / **1.00** | **1.00** / 0.88 | ~20 min |
| qwen3:8b | 0.71 / 1.00 | 0.79 / 0.88 | ~31 min |

Takeaways: **qwen2.5:7b won outright**; **newer ≠ better** (qwen3:8b — a
generation newer and larger — over-flagged `base_rate_neglect` and cost 50%
more time, which is exactly why the default is chosen by eval, not release
date); **the verifier raised precision on all three models**.

### Current baseline (expanded 44-example set, qwen2.5:7b, 2026-07-03)

The dataset was then expanded 18 → 44 with deliberately harder examples
(subtler fallacies, more multi-fallacy texts, 10 trap-cleans) and the
verifier's rejection bar was retuned. New numbers on the harder exam:

| Pipeline | Precision | Recall | Wall time |
|---|---|---|---|
| Single-pass | 0.71 | 0.76 | — |
| **Two-pass** | **0.87** | 0.71 | ~25 min |

What the harder exam revealed:

- The retuned verifier now removes **8 of 12 false positives at the cost of
  a single real finding** — the earlier over-pruning is fixed.
- The scores are lower than on the original set **because the exam got
  harder, not because the tool got worse** — on the original 18 examples
  this same run still scores near the old numbers. A harder denominator is
  the point of growing the dataset.
- The model's measured blind spot is **subtle lookahead bias** (recall 0.43
  on the new lookahead examples: month-scoped universe selection, full-day
  feature normalization, dropping 2020 "because COVID"). Multi-fallacy
  texts also usually yield only one of two findings. These are now the
  documented targets for prompt work or a stronger model.
- The deterministic Pine linter exists precisely because of that blind
  spot: *mechanical* lookahead in code is caught exactly, without the LLM.

Optional paid engines (Claude): `pip install -e ".[anthropic,dev]"` and set
`ANTHROPIC_API_KEY`.

## Usage

```python
from fallacy_auditor import OllamaClient, audit_text_verified

result = audit_text_verified(
    "Every trader I follow got rich with this system, so the edge is real.",
    OllamaClient(),                      # free, local
)
for finding in result.findings:          # grounded AND verifier-confirmed
    print(finding.fallacy.value, "->", finding.span)
for verdict in result.rejected:          # auditable: what was filtered, and why
    print("rejected:", verdict.fallacy.value, "-", verdict.reason)
```

Single pass (faster, no verification): `audit_text(text, client)`.
Paid engines when you want them: `FableClient()` (Claude Fable 5 with an
Opus 4.8 refusal fallback) or `AnthropicClient()` (Opus 4.8).

| Engine | Cost | Client | Notes |
|---|---|---|---|
| `ollama` (default) | **free** | `OllamaClient` | local; model via `FALLACY_AUDITOR_OLLAMA_MODEL`, server via `FALLACY_AUDITOR_OLLAMA_URL` |
| `fable` | paid | `FableClient` | strongest quality; `effort` lever, refusal fallback |
| `opus` | paid | `AnthropicClient` | cheaper Claude option |

Expectation-setting: local-model quality is whatever the eval says it is —
measure, don't assume (see "Measured results" above; current baseline for
the free default is P=0.87/R=0.71 two-pass on the hard 44-example set —
committed snapshot in `results/eval_report_snapshot.json`; runs vary a few
points). The
retry-then-fail-fast loop and the grounding gate were built for weaker
models' failure modes (malformed JSON, near-miss quotes), so the guarantees
hold on every engine; only the hit-rate differs.

### CLI (linter for reasoning)

```bash
python -m fallacy_auditor reasoning.txt --verify        # free local engine
echo "text..." | python -m fallacy_auditor --json
python -m fallacy_auditor reasoning.txt --engine fable  # paid, if configured
```

Exit codes: `0` clean, `1` findings flagged, `2` error — so it gates
LLM-generated trading reasoning in a pipeline exactly like a linter gates
code.

### Pine Script linter (deterministic, no model)

```bash
python -m fallacy_auditor strategy.pine        # .pine implies lint mode
cat strategy.pine | python -m fallacy_auditor --pine --json
```

Flags mechanical bias patterns in strategy code with exact line numbers and
the verbatim source line — the code-side counterpart of the grounding gate:

| Rule | What it catches |
|---|---|
| `pine-lookahead-on` | `lookahead=barmerge.lookahead_on` without the `[1]` offset idiom — the backtest reads future bars (classic repainting lookahead bias) |
| `pine-lookahead-review` | `lookahead_on` *with* a `[1]` offset — the standard safe idiom, surfaced for review |
| `pine-calc-on-every-tick` | live execution reacts to intrabar ticks the backtest never simulated |
| `pine-timenow` | wall-clock time in logic — behaves differently on historical vs live bars |
| `pine-isrealtime` | backtest and live take different code paths, so the backtest stops testing the live logic |

Only high-confidence mechanical patterns are flagged — anything requiring
*intent* belongs to the LLM auditor. Each rule's message explains the risk
and the safe idiom.

### Profit-factor auditor (deterministic, no model)

```bash
python -m fallacy_auditor trades.csv        # .csv implies trade-audit mode
python -m fallacy_auditor trades.csv --json
```

Feed it any CSV with a per-trade profit column — TradingView's Strategy
Tester → "List of Trades" → export works as-is (entry rows are skipped, the
absolute profit column is auto-detected). It reports profit factor, win
rate, expectancy, max drawdown and consecutive losses — then stress-tests
the profit factor:

- **without the top 1 / top 3 winners** — is the edge concentrated in a few
  lucky trades?
- **first half vs second half** — does the edge hold across time?
- **bootstrap 95% confidence interval** (seeded, reproducible) — can
  resampling luck alone erase the edge?
- **sample-size warning** below 30 trades — the base-rate problem in trade
  form.
- **relative degradation** — PF falling >40% when the top 3 trades are
  removed, or a second half worth <40% of the first.

Exit code 1 when any fragility warning fires, so a "great backtest" that is
three lucky trades in a trench coat fails the gate. It never judges whether
a profit factor is *good enough* — that threshold is yours; it judges
whether the number can be trusted at all. Rows are assumed chronological.

### The relative thresholds exist because this auditor failed its own audit

The first version of these checks were **all absolute floors at PF 1.0**: they
fired only if a profit factor *crossed below 1*. Auditing the auditor against a
real 355-trade backtest exposed the hole — that result's PF fell **3.77 → 1.57**
when 3 trades (0.85% of the sample) were removed, and its second half was worth
**13%** of its first, and it emitted **"no fragility warnings"**, because 1.57
and 1.99 are both above 1.0. *A number staying above the floor says nothing
about how far it fell to get there.*

The `PF_DROP_TOP3_WARN` / `HALF_DECAY_WARN` thresholds (both 0.40) close that
hole, and `tests/test_profit.py` pins the regression by feeding that exact
backtest and asserting the warnings now fire. The 0.40 values are a **judgment
call, not a derived constant** — they are flags for review, not verdicts.

A caution learned from the same exercise: these checks operate on whatever
P&L column you hand them. If your per-trade P&L is denominated in currency and
your backtest compounds, the column is **size-weighted** and the concentration
it reports may be an artifact of *when* trades happened, not how extreme they
were. Audit percentage returns when you can.

## Tests and eval

```bash
pytest                                     # 66 deterministic tests, no network, free
pytest -m eval -s                          # live P/R on the local Ollama model (free)
FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s      # also score the two-pass pipeline
FALLACY_AUDITOR_EVAL_ENGINE=fable pytest -m eval -s  # paid engines, if configured
```

The harness prints per-fallacy and micro precision/recall for the
single-pass pipeline and (with the flag) the two-pass pipeline side by side —
so the verifier's precision gain is measured, not assumed. Every run appends
to `eval_report.json`, which makes engine-vs-engine and prompt-change
regressions visible over time. It skips itself when the selected backend
isn't available. Ollama runs default to 1 worker (local models thrash under
parallel requests); paid engines default to 4.

The unit suite includes a stub Ollama server, so the free engine's wire
protocol (payload shape, schema-constrained `format`, error handling) is
verified offline on every `pytest` run.

### Red-teaming the eval set (free)

```bash
python3 scripts/redteam.py --fallacy overfitting --n 4
python3 scripts/redteam.py --fallacy all --n 2
```

Generates two adversarial classes per target fallacy: `subtle_fallacy`
(genuinely fallacious, no textbook giveaways — hunts false negatives) and
`trap_clean` (pattern-matches the fallacy but is methodologically sound —
hunts false positives). Candidates pass a machine gate (spans verbatim,
labels consistent) and land in `data/candidates_*.jsonl` marked
`"status": "unreviewed"`.

**Quarantine rule:** candidates are not gold data until a human reviews the
proposed labels. Promoting model-labeled examples unreviewed would make the
eval circular — the model grading its own homework. Promotion: review →
append to `labeled_examples.jsonl` → `python3 scripts/validate_dataset.py
data/labeled_examples.jsonl` → `pytest tests/test_dataset.py`.

## The five fallacies — labeling rubric

The rubric lives in one place — `RUBRIC` in
[`prompt.py`](src/fallacy_auditor/prompt.py) — and is embedded verbatim in
the auditor prompt, the verifier prompt, and the red-team prompt. This table
is its human-readable mirror; the eval set is labeled against it.

| Fallacy | Counts | Does NOT count |
|---|---|---|
| `survivorship_bias` | A conclusion generalized from a sample containing only survivors/winners (traders still posting, funds still alive, *current* index constituents). | Citing one winner as an illustration while the full population, including failures, is explicitly accounted for. |
| `lookahead_bias` | Using data values unknowable at the moment the decision applies: future/same-bar prices in a rule, intraday extremes known only in hindsight, choosing a test period because its outcome was already known. | Explicit use of lagged or point-in-time data. |
| `overfitting` | Treating a strategy as validated because it fits historical data, especially after many parameters/filters/iterations were tuned on that same data, with no out-of-sample evidence. | In-sample tuning explicitly validated on held-out or walk-forward data. |
| `base_rate_neglect` | A striking conditional statistic or outcome implying an edge while the underlying base rate is omitted (how often the signal fires, how often the outcome happens anyway, how many attempts the result was drawn from). | A claim quoted together with the relevant base rate or full-sample frequency. |
| `unfalsifiable` | A claim no outcome could disprove: opposite outcomes both confirm it, losses are attributed to unobservable forces (manipulation, "smart money"), or no condition is named under which it would be wrong. | A probabilistic claim with an explicit invalidation level or testable condition. |

Boundary rule used to keep labels consistent: **sample composition** problems
(only survivors in the universe) are `survivorship_bias`; **data timing**
problems (values not knowable yet) are `lookahead_bias`.

## Dataset format

`data/labeled_examples.jsonl`, one JSON object per line:

```json
{"id": "overfitting-1", "text": "...", "labels": [{"fallacy": "overfitting", "span": "..."}]}
```

- `labels` may be empty (clean example) or contain multiple entries.
- Every gold `span` is a verbatim substring of `text` — the same grounding
  invariant the model is held to, enforced three ways: at generation time
  (`scripts/make_dataset.py`), on demand (`scripts/validate_dataset.py`),
  and in every CI run (`tests/test_dataset.py`).
- Spans document *why* a label was given but are not scored.
- Current size: 44 examples / 38 gold labels, including 10 trap-clean
  examples and 4 multi-fallacy texts. **Label provenance rule:** gold labels
  are authored by a human or an independent frontier-model reviewer — never
  by the local model under evaluation, which would make the eval circular.

## Architecture

```
input text ─▶ prompt.py ─▶ llm.py (LLMClient protocol) ─▶ raw text
                                │  OllamaClient (free, stdlib HTTP) or
                                │  FableClient/AnthropicClient (paid, lazy
                                │  import of the optional SDK)
                                ▼
          calling.py: json.loads ▶ strict Pydantic validation
                      │ invalid → retry (≤2) → MalformedResponseError
                      ▼
          grounding.py: span in input_text ? keep : discard
                      ▼
          verifier.py (optional 2nd pass, fresh context):
             confirmed/rejected per finding, 1:1 reconciliation —
             the verifier cannot add, drop, or edit a finding
                      ▼
          VerifiedAuditReport(findings=confirmed, rejected=with reasons)
```

| Module | Responsibility |
|---|---|
| `schemas.py` | `FallacyType`, `Finding` (exactly two fields), `AuditReport`, verdict models. `extra="forbid"` everywhere. |
| `prompt.py` | The shared `RUBRIC`, auditor system prompt, wire-level output schema, delimited user prompt. |
| `llm.py` | `LLMClient` protocol (`complete(system, user, output_schema) -> str`); `OllamaClient` (free default), `FableClient`, `AnthropicClient`. |
| `calling.py` | The one call-validate-retry-fail loop every LLM interaction uses. |
| `grounding.py` | The gate: exact, case-sensitive `span in input_text`. Discards are logged, never repaired. |
| `verifier.py` | Fresh-context cross-examination with strict 1:1 verdict reconciliation. |
| `audit.py` | `audit_text` (single pass) and `audit_text_verified` (two pass). |
| `pinelint.py` | Deterministic Pine Script linter — 5 mechanical rules, exact line numbers, verbatim source quotes, no model. |
| `testing.py` | `FakeLLM` — public scripted test double for the protocol. |

## Design decisions (the ones I'd have to defend)

**Free-by-default is a dependency-architecture decision, not a mode.** Core
`dependencies` are pydantic plus the standard library; `OllamaClient` speaks
raw HTTP via `urllib`. The `anthropic` SDK moved to an optional extra with a
lazy import, so the free path never even imports paid-provider code. Nothing
in the pipeline branches on the engine — the guarantees are engine-agnostic
by construction.

**The riskiest assumption is grounding.** The failure mode most likely to
sink this tool is the model citing spans that are *near-misses* — a
paraphrase, normalized whitespace, a "fixed" typo — rather than exact
substrings. The grounding gate addresses it structurally: `span in input_text`
or the finding is discarded. Discarding (not repairing) is deliberate — a
near-miss quote is evidence the model is quoting from imagination, and
patching it into a match would launder exactly the failure the gate exists
to catch. Local models make near-misses *more* often, which makes the gate
more load-bearing, not less.

**Coverage-then-verify, not self-filtering.** The audit pass is instructed to
report everything; the verifier — a separate call with fresh context and an
adversarial system prompt — filters. Two passes let recall and precision be
tuned independently, and the eval harness scores both pipelines so the
verifier earns its cost with numbers. On a free local engine that cost is
CPU time, not money.

**The verifier is held to the same strictness as the auditor.** It must echo
each finding character-for-character and return exactly one verdict per
finding; anything else fails reconciliation and counts as a malformed
response. A verifier that could edit spans would be a repair channel around
the grounding gate.

**Grounding failures are not retried; schema failures are; infrastructure
failures are neither.** Retrying a schema-invalid response recovers from a
formatting accident. Retrying an ungrounded finding is re-rolling the dice
until a fabricated quote happens to match. An unreachable backend
(`LLMUnavailableError`) fails immediately with instructions — burning
retries on a down server helps no one.

**Long inputs fail loudly, never silently.** Ollama truncates prompts past
the model's context window without telling you — which would mean returning
an "audit" of text the model never read. The client estimates input size
conservatively and refuses over-long inputs with instructions (split the
text, or raise `FALLACY_AUDITOR_OLLAMA_NUM_CTX` if you have the RAM)
before any request is sent.

**The Pine linter flags only mechanical certainties.** Five rules, each a
pattern whose risk is a property of the code itself (e.g.
`lookahead=barmerge.lookahead_on` without the `[1]` offset). Judgment calls
belong to the LLM auditor — a linter that guessed would break the same
no-hallucinated-findings promise the grounding gate enforces.

**Red-team candidates are quarantined.** The generator proposes labels, but a
model-labeled example promoted straight to gold would make the eval circular.
A human sign-off is the label of record.

**No confidence score.** An uncalibrated confidence is a liability the caller
will inevitably treat as calibrated. The verifier's categorical
confirmed/rejected with a rubric-based reason is the honest substitute.

**Eval metric is type-level, not span-level.** Scoring unit is the
`(example, fallacy_type)` pair, micro-averaged. Exact span boundaries are
subjective, so scoring them would inject label noise. Span *grounding* is
enforced deterministically and tested deterministically.

**No output massaging at all.** `json.loads` on the raw response — no
markdown-fence stripping, no bracket balancing. A response that isn't plain
JSON is malformed and gets retried. Strictness is the product.

**Determinism knobs differ per engine, deliberately.** Ollama gets
`temperature: 0` (supported, aids repeatability). The Claude 4.8+ family
rejects `temperature` (HTTP 400), so the paid clients rely on the prompt
contract plus schema-constrained output.

## Known limitations / future work

- Local-model quality is unmeasured until you run `pytest -m eval -s` on
  your machine; expect meaningfully lower recall than Claude and choose the
  largest model your RAM allows.
- 18-example gold set: the red-team loop is the scaling mechanism, but the
  human-review step is the bottleneck by design.
- Other free backends (e.g. Gemini's free API tier) are one `LLMClient`
  implementation away if a local model is not an option.
- Span-level scoring (overlap-based) once span boundary conventions are
  settled in the rubric.

## License

MIT
