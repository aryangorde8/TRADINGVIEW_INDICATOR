"""Typed failures. The auditor never fails silently and never returns partial results."""

from __future__ import annotations


class AuditError(Exception):
    """Base class for all auditor failures."""


class MalformedResponseError(AuditError):
    """The LLM failed schema validation on every attempt (initial + retries)."""

    def __init__(self, attempts: int, last_error: Exception | None) -> None:
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"LLM returned invalid audit JSON on all {attempts} attempts; "
            f"last error: {last_error!r}"
        )


class LLMRefusalError(AuditError):
    """The provider's safety layer declined the request (not retried: the
    same input would be declined again)."""


class LLMUnavailableError(AuditError):
    """The LLM backend cannot be reached or cannot serve the model at all
    (server down, model not pulled). Infrastructure, not a bad response —
    so it is not retried by the validation loop."""
