"""Dedicated tests for the grounding gate (the hard requirement).

Every discard case here is a near-miss a real model produces: paraphrase,
case drift, whitespace drift, punctuation drift. None of them may pass.
"""

from fallacy_auditor.grounding import ground_findings
from fallacy_auditor.schemas import FallacyType, Finding

TEXT = (
    "Every trader I follow got rich with this system, so the edge is real.\n"
    "I tuned 12 parameters until the backtest Sharpe hit 3.4."
)


def _finding(span: str, fallacy: FallacyType = FallacyType.OVERFITTING) -> Finding:
    return Finding(fallacy=fallacy, span=span)


def test_exact_substring_is_kept():
    grounded, discarded = ground_findings(
        [_finding("tuned 12 parameters until the backtest Sharpe hit 3.4")], TEXT
    )
    assert len(grounded) == 1
    assert discarded == []


def test_paraphrased_span_is_discarded():
    grounded, discarded = ground_findings(
        [_finding("adjusted a dozen parameters until Sharpe reached 3.4")], TEXT
    )
    assert grounded == []
    assert len(discarded) == 1


def test_case_mismatch_is_discarded():
    """The check is case-sensitive: 'Tuned' != 'tuned'."""
    grounded, discarded = ground_findings([_finding("Tuned 12 parameters")], TEXT)
    assert grounded == []
    assert len(discarded) == 1


def test_whitespace_mismatch_is_discarded():
    grounded, discarded = ground_findings([_finding("tuned  12 parameters")], TEXT)
    assert grounded == []
    assert len(discarded) == 1


def test_punctuation_mismatch_is_discarded():
    grounded, discarded = ground_findings(
        [_finding("backtest Sharpe hit 3.4!")], TEXT
    )
    assert grounded == []
    assert len(discarded) == 1


def test_discarded_finding_is_not_repaired():
    """The near-miss must not be mutated into a match — it is dropped as-is."""
    near_miss = _finding("tuned 12 parameters until sharpe hit 3.4")
    grounded, discarded = ground_findings([near_miss], TEXT)
    assert grounded == []
    assert discarded == [near_miss]  # identical object content, untouched


def test_mixed_findings_keep_only_grounded_preserving_order():
    survivorship = _finding(
        "Every trader I follow got rich", FallacyType.SURVIVORSHIP_BIAS
    )
    hallucinated = _finding("the strategy printed money in 2021")
    overfit = _finding("tuned 12 parameters")
    grounded, discarded = ground_findings([survivorship, hallucinated, overfit], TEXT)
    assert grounded == [survivorship, overfit]
    assert discarded == [hallucinated]


def test_exact_duplicates_collapse_to_one():
    f = _finding("tuned 12 parameters")
    grounded, discarded = ground_findings([f, f, f], TEXT)
    assert grounded == [f]
    assert discarded == []


def test_same_span_different_fallacy_both_kept():
    a = _finding("tuned 12 parameters", FallacyType.OVERFITTING)
    b = _finding("tuned 12 parameters", FallacyType.LOOKAHEAD_BIAS)
    grounded, _ = ground_findings([a, b], TEXT)
    assert grounded == [a, b]


def test_empty_input_list():
    assert ground_findings([], TEXT) == ([], [])
