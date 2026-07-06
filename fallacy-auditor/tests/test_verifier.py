"""The verification pass: strict 1:1 reconciliation, filtering, and the
two-pass pipeline end-to-end with scripted fakes."""

import json

import pytest
from fallacy_auditor.testing import FakeLLM

from fallacy_auditor.audit import MAX_ATTEMPTS, audit_text_verified
from fallacy_auditor.errors import MalformedResponseError
from fallacy_auditor.schemas import FallacyType, Finding
from fallacy_auditor.verifier import verify_findings

TEXT = (
    "Every trader I follow got rich with this system, so the edge is real.\n"
    "I tuned 12 parameters until the backtest Sharpe hit 3.4."
)

SURVIVORSHIP = Finding(
    fallacy=FallacyType.SURVIVORSHIP_BIAS,
    span="Every trader I follow got rich with this system",
)
OVERFIT = Finding(
    fallacy=FallacyType.OVERFITTING,
    span="I tuned 12 parameters until the backtest Sharpe hit 3.4",
)


def _verdict(finding: Finding, verdict: str, reason: str = "per rubric") -> dict:
    return {
        "fallacy": finding.fallacy.value,
        "span": finding.span,
        "verdict": verdict,
        "reason": reason,
    }


def test_all_confirmed_pass_through_in_order():
    fake = FakeLLM(
        [json.dumps({"verdicts": [
            _verdict(OVERFIT, "confirmed"),      # verifier may reorder...
            _verdict(SURVIVORSHIP, "confirmed"),
        ]})]
    )
    confirmed, rejected = verify_findings(TEXT, [SURVIVORSHIP, OVERFIT], fake)
    assert confirmed == [SURVIVORSHIP, OVERFIT]  # ...but original order is kept
    assert rejected == []


def test_rejected_finding_is_filtered_with_reason():
    fake = FakeLLM(
        [json.dumps({"verdicts": [
            _verdict(SURVIVORSHIP, "confirmed"),
            _verdict(OVERFIT, "rejected", reason="validated out of sample"),
        ]})]
    )
    confirmed, rejected = verify_findings(TEXT, [SURVIVORSHIP, OVERFIT], fake)
    assert confirmed == [SURVIVORSHIP]
    assert len(rejected) == 1
    assert rejected[0].reason == "validated out of sample"


def test_no_findings_makes_no_llm_call():
    fake = FakeLLM([])
    assert verify_findings(TEXT, [], fake) == ([], [])
    assert fake.calls == 0


def test_edited_span_is_a_malformed_response():
    """A verifier that 'corrects' a span breaks reconciliation — retried,
    then fail-fast. Verdicts never launder near-miss quotes."""
    edited = dict(_verdict(SURVIVORSHIP, "confirmed"))
    edited["span"] = "Every trader I follow got rich"  # trimmed
    fake = FakeLLM([json.dumps({"verdicts": [edited]})] * MAX_ATTEMPTS)
    with pytest.raises(MalformedResponseError):
        verify_findings(TEXT, [SURVIVORSHIP], fake)
    assert fake.calls == MAX_ATTEMPTS


def test_dropped_verdict_is_a_malformed_response():
    fake = FakeLLM(
        [json.dumps({"verdicts": [_verdict(SURVIVORSHIP, "confirmed")]})]
        * MAX_ATTEMPTS
    )
    with pytest.raises(MalformedResponseError):
        verify_findings(TEXT, [SURVIVORSHIP, OVERFIT], fake)


def test_invented_verdict_is_a_malformed_response():
    invented = Finding(fallacy=FallacyType.UNFALSIFIABLE, span="the edge is real")
    fake = FakeLLM(
        [json.dumps({"verdicts": [
            _verdict(SURVIVORSHIP, "confirmed"),
            _verdict(invented, "confirmed"),
        ]})]
        * MAX_ATTEMPTS
    )
    with pytest.raises(MalformedResponseError):
        verify_findings(TEXT, [SURVIVORSHIP], fake)


def test_malformed_then_valid_verdicts_succeed_on_retry():
    fake = FakeLLM(
        ["not json", json.dumps({"verdicts": [_verdict(SURVIVORSHIP, "confirmed")]})]
    )
    confirmed, _ = verify_findings(TEXT, [SURVIVORSHIP], fake)
    assert confirmed == [SURVIVORSHIP]
    assert fake.calls == 2


def test_two_pass_pipeline_end_to_end():
    """audit_text_verified: audit response, then verdicts, on one fake."""
    audit_response = json.dumps(
        {"findings": [
            {"fallacy": SURVIVORSHIP.fallacy.value, "span": SURVIVORSHIP.span},
            {"fallacy": OVERFIT.fallacy.value, "span": OVERFIT.span},
            {"fallacy": "unfalsifiable", "span": "not in the text at all"},  # ungrounded
        ]}
    )
    verdicts_response = json.dumps(
        {"verdicts": [
            _verdict(SURVIVORSHIP, "confirmed"),
            _verdict(OVERFIT, "rejected", reason="wrong type"),
        ]}
    )
    fake = FakeLLM([audit_response, verdicts_response])
    result = audit_text_verified(TEXT, fake)

    # ungrounded finding never reached the verifier; rejected one is auditable
    assert fake.calls == 2
    assert result.findings == [SURVIVORSHIP]
    assert len(result.rejected) == 1
    assert result.rejected[0].fallacy is FallacyType.OVERFITTING


def test_two_pass_with_clean_text_makes_single_call():
    fake = FakeLLM(['{"findings": []}'])
    result = audit_text_verified(TEXT, fake)
    assert result.findings == []
    assert result.rejected == []
    assert fake.calls == 1  # nothing to verify, no second call
