"""Shared call-validate-retry loop for every LLM interaction.

Extracted once the verifier became the second concrete caller (audit pass +
verification pass share the exact same failure policy):

- A response that fails ``parse`` is retried at most ``MAX_RETRIES`` times.
- After the initial attempt plus retries all fail, ``MalformedResponseError``
  is raised. No partial results, no repair, no silent fallback.
"""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from pydantic import ValidationError

from .errors import MalformedResponseError
from .llm import LLMClient

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
MAX_ATTEMPTS = 1 + MAX_RETRIES

T = TypeVar("T")


def complete_validated(
    client: LLMClient,
    system: str,
    user: str,
    output_schema: dict,
    parse: Callable[[str], T],
) -> T:
    """Call the LLM and return ``parse(raw)``, retrying on validation failure.

    ``parse`` must raise ``ValueError`` (``json.JSONDecodeError`` is one) or
    pydantic ``ValidationError`` to signal a malformed response; any other
    exception propagates immediately (it is a bug, not a bad response).
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = client.complete(system, user, output_schema)
        try:
            return parse(raw)
        except (ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Attempt %d/%d: LLM output failed validation: %s",
                attempt,
                MAX_ATTEMPTS,
                exc,
            )

    raise MalformedResponseError(attempts=MAX_ATTEMPTS, last_error=last_error)
