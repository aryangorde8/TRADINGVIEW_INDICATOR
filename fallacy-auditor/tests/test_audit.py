"""Orchestrator behavior with a scripted fake LLM: retries, fail-fast,
clean-input handling, and the grounding gate wired end-to-end."""

import json

import pytest
from fallacy_auditor.testing import FakeLLM

from fallacy_auditor.audit import MAX_ATTEMPTS, audit_text
from fallacy_auditor.errors import MalformedResponseError
from fallacy_auditor.prompt import AUDIT_OUTPUT_SCHEMA
from fallacy_auditor.schemas import FallacyType

TEXT = "Every trader I follow got rich with this system, so the edge is real."


def _valid_response(span: str = "Every trader I follow got rich") -> str:
    return json.dumps(
        {"findings": [{"fallacy": "survivorship_bias", "span": span}]}
    )


def test_happy_path():
    fake = FakeLLM([_valid_response()])
    report = audit_text(TEXT, fake)
    assert fake.calls == 1
    assert len(report.findings) == 1
    assert report.findings[0].fallacy is FallacyType.SURVIVORSHIP_BIAS


def test_clean_input_returns_empty_report():
    fake = FakeLLM(['{"findings": []}'])
    report = audit_text(TEXT, fake)
    assert report.findings == []
    assert fake.calls == 1


def test_hallucinated_span_is_dropped_without_retry():
    """Grounding failures are not retried — a schema-valid response with a
    fabricated quote is answered by dropping the finding, not re-rolling."""
    fake = FakeLLM([_valid_response(span="a quote that appears nowhere")])
    report = audit_text(TEXT, fake)
    assert report.findings == []
    assert fake.calls == 1


def test_malformed_then_valid_succeeds_on_retry():
    fake = FakeLLM(["this is not json", _valid_response()])
    report = audit_text(TEXT, fake)
    assert fake.calls == 2
    assert len(report.findings) == 1


def test_schema_invalid_json_counts_as_malformed():
    """Valid JSON with an out-of-enum fallacy must be retried, not accepted."""
    bad = json.dumps({"findings": [{"fallacy": "recency_bias", "span": "x"}]})
    fake = FakeLLM([bad, _valid_response()])
    report = audit_text(TEXT, fake)
    assert fake.calls == 2
    assert len(report.findings) == 1


def test_exhausted_retries_fail_fast():
    fake = FakeLLM(["garbage"] * MAX_ATTEMPTS)
    with pytest.raises(MalformedResponseError) as excinfo:
        audit_text(TEXT, fake)
    assert fake.calls == MAX_ATTEMPTS  # 1 initial + 2 retries, then stop
    assert excinfo.value.attempts == MAX_ATTEMPTS
    assert excinfo.value.last_error is not None


def test_no_partial_results_on_failure():
    """A response that fails validation contributes nothing — even if it
    contained a plausible-looking finding fragment."""
    almost = '{"findings": [{"fallacy": "survivorship_bias", "span": "Every trader"}'  # truncated
    fake = FakeLLM([almost] * MAX_ATTEMPTS)
    with pytest.raises(MalformedResponseError):
        audit_text(TEXT, fake)


def test_empty_input_rejected():
    fake = FakeLLM([])
    with pytest.raises(ValueError):
        audit_text("   \n", fake)
    assert fake.calls == 0


def test_user_prompt_embeds_input_verbatim():
    fake = FakeLLM(['{"findings": []}'])
    audit_text(TEXT, fake)
    assert TEXT in fake.last_user_prompt


def test_audit_pass_uses_audit_schema():
    fake = FakeLLM(['{"findings": []}'])
    audit_text(TEXT, fake)
    assert fake.last_output_schema is AUDIT_OUTPUT_SCHEMA
