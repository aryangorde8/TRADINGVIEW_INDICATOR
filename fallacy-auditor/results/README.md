# fallacy-auditor/results/ — committed eval snapshot

`eval_report_snapshot.json` is one full run of the two-pass precision/recall
harness on the 44-example gold set (`data/labeled_examples.jsonl` — 38 labelled
spans, 10 deliberately clean examples), using the free local **qwen2.5:7b**
model via Ollama.

## Results, with confidence intervals

Micro-averaged over (example, fallacy_type) pairs. **Wilson 95% intervals** —
mandatory at this sample size:

| Pipeline | Precision | Recall |
|---|---|---|
| Single-pass (audit only) | 0.690 (29/42) **[0.54, 0.81]** | 0.763 (29/38) [0.61, 0.87] |
| Two-pass (audit + verifier) | 0.871 (27/31) **[0.71, 0.95]** | 0.711 (27/38) [0.55, 0.83] |

**The precision intervals OVERLAP on [0.71, 0.81].** At n=44 the verifier's
precision gain is **directional, not statistically established**. Report it as
an observation, never as a proven improvement. A larger gold set is the only
fix — nothing about the pipeline can make n=44 say more than it does.

Mechanically the verifier removed **9 false positives and 2 true positives**
(tp 29→27, fp 13→4, fn 9→11). That single trade-off is the whole
precision-up / recall-down story.

## Reproducibility

```bash
FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s   # Ollama + qwen2.5:7b, ~25 min CPU
```

The Ollama sampler is now **seed-pinned** (`llm.py`, `seed: 7`): temperature 0
alone does **not** make Ollama deterministic, and eval numbers moved between
runs on identical inputs. **This snapshot predates the seed fix**, so a re-run
may land slightly differently; from the fix onward, runs are reproducible.

Still unpinned (known, stated): the `qwen2.5:7b` Ollama tag can be re-pulled
with different weights, and `FALLACY_AUDITOR_EVAL_WORKERS` changes scheduling.
The live `eval_report.json` accumulates a run history and is gitignored; this
file is the committed point-in-time record.
