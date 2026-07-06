"""Deterministic integrity checks for the gold dataset — runs in the normal
unit suite so a bad label can never silently corrupt the eval numbers."""

import json
from pathlib import Path

from fallacy_auditor.schemas import FallacyType

DATASET = Path(__file__).parent.parent / "data" / "labeled_examples.jsonl"
VALID_FALLACIES = {f.value for f in FallacyType}


def _examples() -> list[dict]:
    with DATASET.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def test_dataset_is_nonempty():
    assert len(_examples()) >= 10


def test_ids_unique():
    ids = [ex["id"] for ex in _examples()]
    assert len(ids) == len(set(ids))


def test_texts_nonempty():
    assert all(ex["text"].strip() for ex in _examples())


def test_labels_use_valid_fallacies():
    for ex in _examples():
        for label in ex["labels"]:
            assert label["fallacy"] in VALID_FALLACIES, ex["id"]


def test_gold_spans_are_verbatim():
    """The dataset must satisfy the same grounding invariant as the model."""
    for ex in _examples():
        for label in ex["labels"]:
            assert label["span"] in ex["text"], (
                f"{ex['id']}: gold span is not a verbatim substring"
            )


def test_has_clean_examples():
    """False-positive resistance is only measurable with clean examples."""
    assert any(not ex["labels"] for ex in _examples())


def test_every_fallacy_is_represented():
    covered = {
        label["fallacy"] for ex in _examples() for label in ex["labels"]
    }
    assert covered == VALID_FALLACIES
