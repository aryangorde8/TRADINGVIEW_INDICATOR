"""Pydantic schemas for the trading-reasoning fallacy auditor.

``AuditReport`` is used twice on purpose:

1. To strictly validate the raw JSON the LLM returns (unknown keys, unknown
   fallacy values, and empty spans are all rejected — they count as a
   malformed response and trigger a retry).
2. As the final return type handed to the caller, after the grounding gate
   has discarded any finding whose span is not a verbatim substring of the
   input.

A ``Finding`` carries exactly two fields. There is deliberately no confidence
score in v1: an uncalibrated confidence is a liability, not information. The
verifier pass (``verifier.py``) is the calibrated substitute — a categorical
confirmed/rejected judgment from a fresh-context second call, with a reason.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FallacyType(str, Enum):
    """The five (and only five) fallacies this auditor flags."""

    SURVIVORSHIP_BIAS = "survivorship_bias"
    LOOKAHEAD_BIAS = "lookahead_bias"
    OVERFITTING = "overfitting"
    BASE_RATE_NEGLECT = "base_rate_neglect"
    UNFALSIFIABLE = "unfalsifiable"


class Finding(BaseModel):
    """One flagged instance: the fallacy type and the verbatim trigger span."""

    # frozen=True makes findings hashable so exact duplicates can be
    # collapsed with a set; extra="forbid" rejects any additional keys the
    # model invents (and emits additionalProperties:false in the JSON schema).
    model_config = ConfigDict(extra="forbid", frozen=True)

    fallacy: FallacyType
    span: str = Field(min_length=1)


class AuditReport(BaseModel):
    """The audit result. An empty ``findings`` list is a first-class outcome."""

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]


class Verdict(str, Enum):
    """The verifier's categorical judgment on one proposed finding."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FindingVerdict(BaseModel):
    """One verifier judgment: the echoed finding plus verdict and reason.

    ``fallacy`` and ``span`` must echo the proposed finding exactly — the
    reconciliation check in ``verifier.py`` enforces a 1:1 match, so the
    verifier can neither invent findings nor quietly drop them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    fallacy: FallacyType
    span: str = Field(min_length=1)
    verdict: Verdict
    reason: str = Field(min_length=1)


class VerdictReport(BaseModel):
    """Raw verifier output: exactly one verdict per proposed finding."""

    model_config = ConfigDict(extra="forbid")

    verdicts: list[FindingVerdict]


class VerifiedAuditReport(BaseModel):
    """Audit result after the verification pass.

    ``findings`` are grounded AND confirmed; ``rejected`` preserves what the
    verifier threw out, with its reasons, so the filtering is auditable.
    """

    model_config = ConfigDict(extra="forbid")

    findings: list[Finding]
    rejected: list[FindingVerdict]
