"""Orchestration: prompt -> LLM -> strict validation -> grounding gate
-> (optionally) independent verification.

Failure policy:
- Schema-invalid output (bad JSON, unknown keys, unknown fallacy, empty
  span) is retried at most twice, then fails fast with
  ``MalformedResponseError`` (see ``calling.py``). No partial results.
- Grounding failures are NOT retried. A schema-valid response with an
  ungrounded span is the model quoting from imagination; re-rolling until a
  span happens to match would be confirmation-seeking, so the finding is
  dropped and the rest of the report is returned.
- Verifier rejections are not silent: they are returned on
  ``VerifiedAuditReport.rejected`` with the verifier's reasons.
"""

from __future__ import annotations

import json
import logging

from .calling import MAX_ATTEMPTS, MAX_RETRIES, complete_validated
from .grounding import ground_findings
from .llm import LLMClient
from .prompt import AUDIT_OUTPUT_SCHEMA, SYSTEM_PROMPT, build_user_prompt
from .schemas import AuditReport, VerifiedAuditReport
from .verifier import verify_findings

__all__ = ["MAX_ATTEMPTS", "MAX_RETRIES", "audit_text", "audit_text_verified"]

logger = logging.getLogger(__name__)


def audit_text(input_text: str, client: LLMClient) -> AuditReport:
    """Audit one block of trading reasoning (single pass).

    Returns an ``AuditReport`` whose findings are all verbatim-grounded in
    ``input_text``. An empty report means no fallacy was found — a valid,
    first-class outcome.

    Raises:
        ValueError: if ``input_text`` is empty or whitespace-only.
        MalformedResponseError: if the LLM fails schema validation on the
            initial attempt and all retries.
        LLMRefusalError: if the provider declines the request.
    """
    if not input_text.strip():
        raise ValueError("input_text is empty; nothing to audit")

    def parse(raw: str) -> AuditReport:
        return AuditReport.model_validate(json.loads(raw))

    parsed = complete_validated(
        client, SYSTEM_PROMPT, build_user_prompt(input_text), AUDIT_OUTPUT_SCHEMA, parse
    )

    grounded, discarded = ground_findings(parsed.findings, input_text)
    if discarded:
        logger.warning(
            "Discarded %d ungrounded finding(s); returning %d grounded",
            len(discarded),
            len(grounded),
        )
    return AuditReport(findings=grounded)


def audit_text_verified(
    input_text: str,
    client: LLMClient,
    verifier_client: LLMClient | None = None,
) -> VerifiedAuditReport:
    """Two-pass audit: coverage-tuned audit, then fresh-context verification.

    Pass order is deliberate: schema validation -> grounding gate ->
    verifier. Only grounded findings are verified (no tokens are spent
    cross-examining a hallucinated quote), and confirmed findings remain
    verbatim-grounded by construction because the verifier must echo spans
    exactly.

    ``verifier_client`` defaults to ``client``; independence comes from the
    fresh context and adversarial system prompt, not from a different model —
    though passing a different model here is supported.
    """
    report = audit_text(input_text, client)
    confirmed, rejected = verify_findings(
        input_text, report.findings, verifier_client or client
    )
    return VerifiedAuditReport(findings=confirmed, rejected=rejected)
