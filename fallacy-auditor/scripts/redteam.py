#!/usr/bin/env python3
"""Red-team generator: use the model to attack the eval set.

    python3 scripts/redteam.py --fallacy overfitting --n 4
    python3 scripts/redteam.py --fallacy all --n 2 --engine opus

For each target fallacy it asks the model for two adversarial classes:

- subtle_fallacy — realistic trading reasoning that genuinely commits the
  fallacy, but subtly (no textbook giveaway phrasing). Hunts false negatives.
- trap_clean    — reasoning that superficially pattern-matches the fallacy
  (backtests, win rates, streaks) but is methodologically sound, with an
  empty label list. Hunts false positives.

Every candidate passes a machine gate (spans verbatim, labels consistent
with its kind); invalid candidates are discarded, never repaired — the same
philosophy as the grounding gate.

IMPORTANT — quarantine: output goes to data/candidates_*.jsonl with
"status": "unreviewed". Candidates are NOT gold data until a human reviews
the proposed labels; promoting model-labeled examples unreviewed would make
the eval circular (the model grading its own homework). To promote:
  1. Review each candidate; fix or reject labels; delete the status/source keys.
  2. Append the approved lines to data/labeled_examples.jsonl.
  3. python3 scripts/validate_dataset.py data/labeled_examples.jsonl
  4. pytest tests/test_dataset.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pydantic import BaseModel, ConfigDict, Field  # noqa: E402

from fallacy_auditor import (  # noqa: E402
    AnthropicClient,
    FableClient,
    FallacyType,
    OllamaClient,
)
from fallacy_auditor.calling import complete_validated  # noqa: E402
from fallacy_auditor.prompt import RUBRIC  # noqa: E402
from fallacy_auditor.schemas import Finding  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(subtle_fallacy|trap_clean)$")
    text: str = Field(min_length=1)
    labels: list[Finding]


class CandidateBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[Candidate]


CANDIDATE_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["subtle_fallacy", "trap_clean"],
                    },
                    "text": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "fallacy": {
                                    "type": "string",
                                    "enum": [f.value for f in FallacyType],
                                },
                                "span": {"type": "string"},
                            },
                            "required": ["fallacy", "span"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["kind", "text", "labels"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["candidates"],
    "additionalProperties": False,
}

_SYSTEM = (
    """\
You are red-teaming an automated auditor that flags five reasoning fallacies
in trading text. Your job is to write eval examples the auditor is most
likely to get WRONG. The fallacy rubric the auditor is held to:

"""
    + RUBRIC
    + """

You will be asked for two kinds of candidates targeting one fallacy:

- "subtle_fallacy": 2-4 sentence trading reasoning, in a realistic retail or
  quant voice, that GENUINELY commits the target fallacy — but subtly. No
  textbook giveaway phrasing; bury the fallacious step among sound-sounding
  detail. Provide labels: the target fallacy plus the exact verbatim span
  (copied character-for-character from your own text) containing the
  fallacious step. Do not commit other fallacies from the rubric in the same
  text unless you also label them.

- "trap_clean": 2-4 sentence trading reasoning that superficially resembles
  the target fallacy — same vocabulary, same setting (backtests, win rates,
  streaks, gurus) — but is methodologically SOUND per the rubric's "NOT"
  clause. labels must be an empty array.

Vary instruments, markets, and voices across candidates. Spans must be exact
substrings of the text they label. Respond with JSON only.
"""
)


def _build_user(fallacy: str, n: int) -> str:
    return (
        f"Target fallacy: {fallacy}\n"
        f"Produce exactly {n} subtle_fallacy candidates and {n} trap_clean "
        f"candidates."
    )


def _gate(candidates: list[Candidate], fallacy: str) -> tuple[list[Candidate], list[str]]:
    """Machine gate: discard structurally invalid candidates (never repair)."""
    kept: list[Candidate] = []
    reasons: list[str] = []
    for i, cand in enumerate(candidates):
        if cand.kind == "trap_clean" and cand.labels:
            reasons.append(f"candidate {i}: trap_clean must have no labels")
            continue
        if cand.kind == "subtle_fallacy":
            if not cand.labels:
                reasons.append(f"candidate {i}: subtle_fallacy must be labeled")
                continue
            if fallacy not in {label.fallacy.value for label in cand.labels}:
                reasons.append(f"candidate {i}: target fallacy not in labels")
                continue
        if any(label.span not in cand.text for label in cand.labels):
            reasons.append(f"candidate {i}: span not a verbatim substring")
            continue
        kept.append(cand)
    return kept, reasons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    fallacies = [f.value for f in FallacyType]
    parser.add_argument("--fallacy", choices=fallacies + ["all"], required=True)
    parser.add_argument("--n", type=int, default=3, help="candidates per kind")
    parser.add_argument(
        "--engine",
        choices=["ollama", "fable", "opus"],
        default="ollama",
        help="ollama = free local model (default); fable/opus = paid Claude API",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if args.engine == "ollama":
        client = OllamaClient()
    elif args.engine == "fable":
        client = FableClient()
    else:
        client = AnthropicClient()
    targets = fallacies if args.fallacy == "all" else [args.fallacy]

    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or DATA_DIR / f"candidates_{stamp}.jsonl"

    total_kept = 0
    with out.open("w") as f:
        for fallacy in targets:
            def parse(raw: str) -> CandidateBatch:
                return CandidateBatch.model_validate(json.loads(raw))

            batch = complete_validated(
                client, _SYSTEM, _build_user(fallacy, args.n),
                CANDIDATE_OUTPUT_SCHEMA, parse,
            )
            kept, reasons = _gate(batch.candidates, fallacy)
            for reason in reasons:
                print(f"[{fallacy}] discarded {reason}", file=sys.stderr)

            for i, cand in enumerate(kept, start=1):
                record = {
                    "id": f"redteam-{fallacy}-{stamp}-{i}",
                    "text": cand.text,
                    "labels": [
                        {"fallacy": label.fallacy.value, "span": label.span}
                        for label in cand.labels
                    ],
                    "kind": cand.kind,
                    "status": "unreviewed",
                    "source": f"redteam-{args.engine}",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            total_kept += len(kept)
            print(f"[{fallacy}] kept {len(kept)}/{len(batch.candidates)} candidates")

    print(f"\nWrote {total_kept} UNREVIEWED candidates to {out}")
    print("These are not gold data until a human reviews the labels — see the "
          "promotion steps in this script's docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
