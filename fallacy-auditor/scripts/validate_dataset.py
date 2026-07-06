#!/usr/bin/env python3
"""Validate a labeled-examples JSONL against the dataset invariants.

    python3 scripts/validate_dataset.py data/labeled_examples.jsonl

Checks per line: unique id, non-empty text, labels use the five known
fallacy values, and every gold span is a verbatim substring of its text
(the same grounding invariant the model is held to). Exit 1 on violation.

Run this before promoting red-team candidates into the gold set. Full-set
checks (every fallacy represented, clean examples present) live in
tests/test_dataset.py and run in the normal pytest suite.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fallacy_auditor.schemas import FallacyType  # noqa: E402

VALID_FALLACIES = {f.value for f in FallacyType}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()

    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            ex = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: invalid JSON ({exc})")
            continue

        ex_id = ex.get("id", f"<line {lineno}>")
        if ex_id in seen_ids:
            errors.append(f"{ex_id}: duplicate id")
        seen_ids.add(ex_id)

        text = ex.get("text", "")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{ex_id}: empty text")
            continue

        for label in ex.get("labels", []):
            if label.get("fallacy") not in VALID_FALLACIES:
                errors.append(f"{ex_id}: unknown fallacy {label.get('fallacy')!r}")
            span = label.get("span", "")
            if span not in text:
                errors.append(f"{ex_id}: span not a verbatim substring: {span!r}")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        print("\n".join(errors))
        print(f"\nFAILED: {len(errors)} violation(s) in {path}")
        return 1
    print(f"OK: {path} satisfies all dataset invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
