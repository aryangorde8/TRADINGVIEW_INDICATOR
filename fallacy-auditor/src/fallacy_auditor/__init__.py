"""fallacy-auditor: strictly grounded auditing of trading reasoning.

Free by default — runs on any local open-weights model served by Ollama:

    from fallacy_auditor import OllamaClient, audit_text_verified

    result = audit_text_verified(
        "Every trader I follow got rich with this...", OllamaClient()
    )
    for finding in result.findings:          # grounded AND verifier-confirmed
        print(finding.fallacy.value, "->", finding.span)
    for verdict in result.rejected:          # what the verifier threw out, and why
        print("rejected:", verdict.reason)

Single-pass (cheaper, no verification): ``audit_text(text, client)``.
Optional paid engines (``pip install "fallacy-auditor[anthropic]"``):
``FableClient`` (Claude Fable 5 + Opus 4.8 fallback), ``AnthropicClient``.
"""

from .audit import audit_text, audit_text_verified
from .errors import (
    AuditError,
    LLMRefusalError,
    LLMUnavailableError,
    MalformedResponseError,
)
from .llm import AnthropicClient, FableClient, LLMClient, OllamaClient
from .schemas import (
    AuditReport,
    FallacyType,
    Finding,
    FindingVerdict,
    Verdict,
    VerifiedAuditReport,
)
from .verifier import verify_findings

__all__ = [
    "AnthropicClient",
    "AuditError",
    "AuditReport",
    "FableClient",
    "FallacyType",
    "Finding",
    "FindingVerdict",
    "LLMClient",
    "LLMRefusalError",
    "LLMUnavailableError",
    "MalformedResponseError",
    "OllamaClient",
    "Verdict",
    "VerifiedAuditReport",
    "audit_text",
    "audit_text_verified",
    "verify_findings",
]
