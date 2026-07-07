# fallacy-auditor/results/ — committed eval snapshot

`eval_report_snapshot.json` is one full run of the two-pass precision/recall
harness on the 44-example gold set (`data/labeled_examples.jsonl`), using the
free local **qwen2.5:7b** model via Ollama.

Headline (micro-averaged over (example, fallacy_type) pairs):

| Pipeline | Precision | Recall |
|---|---|---|
| Single-pass (audit only) | 0.69 | 0.76 |
| **Two-pass (audit + verifier)** | **0.87** | 0.71 |

The verifier's job is precision: it cut false positives from 13 to 4 (raising
precision 0.69 → 0.87) at the cost of 2 findings (recall 0.76 → 0.71). This is
the coverage-then-verify design working as intended.

Regenerate: `FALLACY_AUDITOR_EVAL_VERIFY=1 pytest -m eval -s` (needs Ollama +
`qwen2.5:7b`; ~25 min on CPU). The live `eval_report.json` accumulates a run
history and is gitignored; this snapshot is the committed point-in-time record.
Small run-to-run variance is expected even at temperature 0 (local sampling).
