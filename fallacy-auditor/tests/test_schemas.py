"""Schema strictness: anything outside the contract is rejected, loudly."""

import pytest
from pydantic import ValidationError

from fallacy_auditor.schemas import AuditReport, FallacyType, Finding


def test_valid_report_parses():
    report = AuditReport.model_validate(
        {"findings": [{"fallacy": "overfitting", "span": "tuned 12 parameters"}]}
    )
    assert report.findings[0].fallacy is FallacyType.OVERFITTING
    assert report.findings[0].span == "tuned 12 parameters"


def test_empty_findings_is_valid():
    """'Found nothing' must be a first-class, schema-valid result."""
    report = AuditReport.model_validate({"findings": []})
    assert report.findings == []


def test_unknown_fallacy_value_rejected():
    with pytest.raises(ValidationError):
        AuditReport.model_validate(
            {"findings": [{"fallacy": "confirmation_bias", "span": "x"}]}
        )


def test_extra_keys_rejected():
    """No invented fields — e.g. a confidence score the schema never asked for."""
    with pytest.raises(ValidationError):
        AuditReport.model_validate(
            {"findings": [{"fallacy": "overfitting", "span": "x", "confidence": 0.9}]}
        )
    with pytest.raises(ValidationError):
        AuditReport.model_validate({"findings": [], "summary": "looks fine"})


def test_empty_span_rejected():
    with pytest.raises(ValidationError):
        AuditReport.model_validate({"findings": [{"fallacy": "overfitting", "span": ""}]})


def test_missing_field_rejected():
    with pytest.raises(ValidationError):
        AuditReport.model_validate({"findings": [{"fallacy": "overfitting"}]})


def test_finding_is_hashable():
    """frozen=True is load-bearing: the grounding gate dedupes via a set."""
    a = Finding(fallacy=FallacyType.OVERFITTING, span="x")
    b = Finding(fallacy=FallacyType.OVERFITTING, span="x")
    assert a == b
    assert len({a, b}) == 1
