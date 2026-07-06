"""The grounding gate — the primary defense against hallucinated findings.

A finding survives the gate iff its span is a *literal* substring of the
input text (exact, case-sensitive ``in`` check). Anything else is discarded:
no fuzzy matching, no whitespace normalization, no repair. A near-miss span
is evidence the model is quoting from imagination rather than from the text,
and "repairing" it into a match would launder exactly the failure mode this
gate exists to catch.
"""

from __future__ import annotations

import logging

from .schemas import Finding

logger = logging.getLogger(__name__)


def ground_findings(
    findings: list[Finding], input_text: str
) -> tuple[list[Finding], list[Finding]]:
    """Split ``findings`` into ``(grounded, discarded)``, preserving order.

    Exact duplicates (same fallacy + same span) are collapsed to their first
    occurrence so a repetitive model cannot inflate the report.
    """
    grounded: list[Finding] = []
    discarded: list[Finding] = []
    seen: set[Finding] = set()

    for finding in findings:
        if finding in seen:
            continue
        seen.add(finding)
        if finding.span in input_text:
            grounded.append(finding)
        else:
            discarded.append(finding)
            logger.warning(
                "Discarding ungrounded finding (%s): cited span is not a "
                "verbatim substring of the input",
                finding.fallacy.value,
            )

    return grounded, discarded
