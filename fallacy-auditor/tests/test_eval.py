"""Live precision/recall harness against the hand-labeled JSONL.

Run with:  pytest -m eval -s
(plain `pytest` skips this module — it needs Anthropic credentials and
spends tokens).

Environment knobs:
    FALLACY_AUDITOR_EVAL_ENGINE   ollama (default, free) | fable | opus
    FALLACY_AUDITOR_EVAL_VERIFY   1 -> also score the two-pass (verified)
                                  pipeline; single audit pass is reused, so
                                  the extra cost is one verifier call per
                                  example with findings
    FALLACY_AUDITOR_EVAL_WORKERS  parallel requests (default 4; use 1 for
                                  a local Ollama model to avoid thrashing)

Metric definition (deliberate):
    Scoring unit = (example_id, fallacy_type) pair, micro-averaged.
    Span text is NOT scored: exact span boundaries are subjective, so scoring
    them would inject labeling noise. Span *grounding* is not a statistical
    question — it is enforced structurally by the gate, which has its own
    deterministic tests.

Every run appends its numbers to eval_report.json so regressions across
prompt/rubric/model changes are visible over time.
"""

from __future__ import annotations

import datetime
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from fallacy_auditor import FallacyType, audit_text, verify_findings
from fallacy_auditor.llm import ollama_base_url

pytestmark = pytest.mark.eval

ROOT = Path(__file__).parent.parent
DATASET = ROOT / "data" / "labeled_examples.jsonl"
REPORT = ROOT / "eval_report.json"


def _have_credentials() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    # An `ant auth login` profile also works; the SDK picks it up itself.
    return (Path.home() / ".config" / "anthropic").exists()


def _ollama_reachable() -> bool:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(ollama_base_url() + "/api/tags", timeout=3):
            return True
    except (urllib.error.URLError, TimeoutError):
        return False


def _make_client(engine: str):
    if engine == "ollama":
        if not _ollama_reachable():
            pytest.skip(f"Ollama server not reachable at {ollama_base_url()}")
        from fallacy_auditor import OllamaClient

        return OllamaClient()
    if not _have_credentials():
        pytest.skip("No Anthropic credentials (ANTHROPIC_API_KEY or ant profile)")
    if engine == "fable":
        from fallacy_auditor import FableClient

        return FableClient()
    from fallacy_auditor import AnthropicClient

    return AnthropicClient()


def _load_examples() -> list[dict]:
    with DATASET.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _score(rows: list[tuple[set[str], set[str]]]) -> dict:
    """Micro + per-fallacy P/R over (gold, predicted) type-set pairs."""
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    for gold, predicted in rows:
        for t in predicted & gold:
            tp[t] += 1
        for t in predicted - gold:
            fp[t] += 1
        for t in gold - predicted:
            fn[t] += 1

    def prf(t: int, p: int, n: int) -> dict:
        return {
            "precision": round(t / (t + p), 3) if (t + p) else None,
            "recall": round(t / (t + n), 3) if (t + n) else None,
            "tp": t, "fp": p, "fn": n,
        }

    per_fallacy = {
        f.value: prf(tp[f.value], fp[f.value], fn[f.value])
        for f in FallacyType
        if tp[f.value] + fp[f.value] + fn[f.value] > 0
    }
    micro = prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))
    return {"micro": micro, "per_fallacy": per_fallacy}


def _print_metrics(title: str, metrics: dict) -> None:
    print(f"\n{title}")
    for name, m in metrics["per_fallacy"].items():
        print(
            f"  {name:<20} P={m['precision']} R={m['recall']} "
            f"(tp={m['tp']} fp={m['fp']} fn={m['fn']})"
        )
    m = metrics["micro"]
    print(
        f"  {'micro':<20} P={m['precision']} R={m['recall']} "
        f"(tp={m['tp']} fp={m['fp']} fn={m['fn']})"
    )


def test_precision_recall():
    engine = os.environ.get("FALLACY_AUDITOR_EVAL_ENGINE", "ollama")
    with_verify = os.environ.get("FALLACY_AUDITOR_EVAL_VERIFY") == "1"
    default_workers = "1" if engine == "ollama" else "4"
    workers = int(os.environ.get("FALLACY_AUDITOR_EVAL_WORKERS", default_workers))

    examples = _load_examples()
    assert examples, "dataset is empty"
    client = _make_client(engine)

    def run_one(ex: dict) -> dict:
        report = audit_text(ex["text"], client)
        row = {
            "id": ex["id"],
            "gold": sorted({label["fallacy"] for label in ex["labels"]}),
            "raw": sorted({f.fallacy.value for f in report.findings}),
        }
        if with_verify:
            confirmed, rejected = verify_findings(ex["text"], report.findings, client)
            row["verified"] = sorted({f.fallacy.value for f in confirmed})
            row["verifier_rejected"] = [
                {"fallacy": v.fallacy.value, "reason": v.reason} for v in rejected
            ]
        return row

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(run_one, examples))

    print(f"\n\nEngine: {engine} | examples: {len(rows)} | verified pass: {with_verify}")
    print("Per-example results:")
    for row in rows:
        mark = "OK " if row["raw"] == row["gold"] else "DIFF"
        line = f"  [{mark}] {row['id']:<18} gold={row['gold'] or ['-']} raw={row['raw'] or ['-']}"
        if with_verify:
            line += f" verified={row['verified'] or ['-']}"
        print(line)

    raw_metrics = _score([(set(r["gold"]), set(r["raw"])) for r in rows])
    _print_metrics("Single-pass (audit only):", raw_metrics)
    result = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "engine": engine,
        "examples": len(rows),
        "raw": raw_metrics,
        "rows": rows,
    }

    if with_verify:
        verified_metrics = _score([(set(r["gold"]), set(r["verified"])) for r in rows])
        _print_metrics("Two-pass (audit + verifier):", verified_metrics)
        result["verified"] = verified_metrics

    history = json.loads(REPORT.read_text()) if REPORT.exists() else []
    history.append(result)
    REPORT.write_text(json.dumps(history, indent=2))
    print(f"\nAppended run to {REPORT}")

    # Sanity floor only — this harness reports quality, it does not gate on
    # an arbitrary threshold that would itself be a form of overfitting.
    total_gold = sum(len(ex["labels"]) for ex in examples)
    m = raw_metrics["micro"]
    assert m["tp"] + m["fn"] == total_gold, "scoring bookkeeping is broken"
