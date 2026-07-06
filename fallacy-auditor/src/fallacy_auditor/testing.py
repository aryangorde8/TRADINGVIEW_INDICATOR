"""Public test double for the ``LLMClient`` protocol.

Shipped in the package (rather than hidden in the test tree) so downstream
users who swap in their own provider can test their pipelines the same way
this project tests its own: scripted responses, no network.
"""

from __future__ import annotations


class FakeLLM:
    """Scripted LLMClient: returns responses in order and counts calls."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)
        self.calls = 0
        self.last_system: str | None = None
        self.last_user_prompt: str | None = None
        self.last_output_schema: dict | None = None

    def complete(self, system: str, user: str, output_schema: dict) -> str:
        self.calls += 1
        self.last_system = system
        self.last_user_prompt = user
        self.last_output_schema = output_schema
        return next(self._responses)
