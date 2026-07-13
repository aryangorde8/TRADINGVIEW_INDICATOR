"""The LLM boundary.

Everything else in this package depends only on the ``LLMClient`` protocol:
prompts and a JSON output schema in, raw text out. Swapping providers means
implementing one method; no other module imports a provider SDK. The
``output_schema`` argument is advisory — a provider that cannot enforce it
may ignore it, because ``calling.py`` re-validates every response with
Pydantic as if no enforcement existed.

Three implementations ship:

- ``OllamaClient`` (default engine, **free**) — any open-weights model served
  by a local Ollama instance (https://ollama.com). Talks to Ollama's native
  API with the standard library only, so the core package needs no provider
  SDK and no API key. Ollama enforces the JSON schema via its ``format``
  parameter (Ollama >= 0.5).
- ``FableClient`` (optional, paid) — Claude Fable 5 with a server-side
  fallback to Claude Opus 4.8 on safety-classifier refusals.
- ``AnthropicClient`` (optional, paid) — Claude Opus 4.8 directly.

The paid clients require the optional extra:
``pip install "fallacy-auditor[anthropic]"``. The ``anthropic`` import is
lazy so the free path works without it installed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from .errors import LLMRefusalError, LLMUnavailableError

FABLE_MODEL = "claude-fable-5"
DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_FALLBACK_MODEL = "claude-opus-4-8"
MODEL_ENV_VAR = "FALLACY_AUDITOR_MODEL"
EFFORT_ENV_VAR = "FALLACY_AUDITOR_EFFORT"

# Default = best measured two-pass F1 on the gold set (see README's
# "Measured results"): qwen2.5:7b beat both qwen3:4b and qwen3:8b. It wants
# ~5.5 GB free RAM — on an 8 GB machine, close heavy apps, or switch to the
# fast low-RAM option via FALLACY_AUDITOR_OLLAMA_MODEL=qwen3:4b.
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_MODEL_ENV_VAR = "FALLACY_AUDITOR_OLLAMA_MODEL"
OLLAMA_URL_ENV_VAR = "FALLACY_AUDITOR_OLLAMA_URL"
OLLAMA_THINK_ENV_VAR = "FALLACY_AUDITOR_OLLAMA_THINK"
OLLAMA_NUM_CTX_ENV_VAR = "FALLACY_AUDITOR_OLLAMA_NUM_CTX"
DEFAULT_OLLAMA_NUM_CTX = 8192
OLLAMA_SEED = 7  # fixed: temperature 0 is not sufficient for reproducibility
# Conservative sizing for the truncation guard: ~3 chars/token overestimates
# the token count for English, which is the safe direction here.
_CHARS_PER_TOKEN = 3
_OUTPUT_RESERVE_TOKENS = 1024


def ollama_base_url() -> str:
    """Resolve the Ollama server URL (shared with the eval harness)."""
    return os.environ.get(OLLAMA_URL_ENV_VAR, "http://localhost:11434").rstrip("/")


class LLMClient(Protocol):
    """The single seam between the auditor and any LLM provider."""

    def complete(self, system: str, user: str, output_schema: dict) -> str:
        """Return the model's raw text response for one prompt pair.

        ``output_schema`` is the JSON Schema the response should satisfy;
        enforcing it is optional (validation happens upstream regardless).
        """
        ...


class OllamaClient:
    """Free local inference through Ollama's native chat API.

    Setup (once):
        1. Install Ollama: https://ollama.com/download
        2. ``ollama pull qwen2.5:7b``   (≈4.7 GB; wants ~5.5 GB free RAM —
           the default: best measured accuracy on the gold set)
           Fast/low-RAM alternative: ``ollama pull qwen3:4b`` (~20 s/audit,
           fine with an IDE open on 8 GB).

    Notes:
    - ``format=<schema>`` makes Ollama constrain the output to the JSON
      schema; models that ignore it on old Ollama versions are caught by the
      validation-retry loop upstream.
    - ``temperature: 0`` is supported here (unlike the Claude 4.8+ family)
      and used for repeatability.
    - Thinking is disabled by default on thinking-capable models (qwen3,
      deepseek-r1, ...): thinking tokens are not schema-constrained and on
      CPU they turn a 1-minute audit into a 7-minute one. Set
      ``FALLACY_AUDITOR_OLLAMA_THINK=1`` (or ``think=True``) to re-enable
      if you have the hardware for it. The capability is queried from the
      server once per client, so non-thinking models never receive the
      parameter (Ollama rejects it for them).
    - Small local models fail schema validation more often than frontier
      models; that is exactly the case the retry-then-fail-fast loop exists
      for, and quality must be read off the eval harness, not assumed.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 600.0,
        think: bool | None = None,
        num_ctx: int | None = None,
    ) -> None:
        self._model = model or os.environ.get(
            OLLAMA_MODEL_ENV_VAR, DEFAULT_OLLAMA_MODEL
        )
        self._base_url = (base_url or ollama_base_url()).rstrip("/")
        self._timeout = timeout  # local CPU inference can be slow
        self._think = (
            think
            if think is not None
            else os.environ.get(OLLAMA_THINK_ENV_VAR) == "1"
        )
        # Context window requested from Ollama. Larger values cost RAM
        # (KV cache); the truncation guard below keeps inputs honest.
        self._num_ctx = num_ctx or int(
            os.environ.get(OLLAMA_NUM_CTX_ENV_VAR, str(DEFAULT_OLLAMA_NUM_CTX))
        )
        self._supports_thinking: bool | None = None  # queried lazily, cached

    def _model_supports_thinking(self) -> bool:
        if self._supports_thinking is None:
            data = self._post("/api/show", {"model": self._model})
            self._supports_thinking = "thinking" in (data.get("capabilities") or [])
        return self._supports_thinking

    def complete(self, system: str, user: str, output_schema: dict) -> str:
        # Fail-fast truncation guard: Ollama silently drops prompt tokens
        # beyond num_ctx, which would mean auditing text the model never
        # read. Refusing loudly is the only honest behavior.
        estimated = (len(system) + len(user)) // _CHARS_PER_TOKEN
        if estimated + _OUTPUT_RESERVE_TOKENS > self._num_ctx:
            raise ValueError(
                f"input too long for the model's context window "
                f"(~{estimated} tokens + output reserve > num_ctx="
                f"{self._num_ctx}); Ollama would silently truncate it. "
                f"Split the text into sections, or raise "
                f"{OLLAMA_NUM_CTX_ENV_VAR} if you have the RAM."
            )
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": output_schema,
            "stream": False,
            # temperature 0 alone does NOT make Ollama deterministic — the
            # sampler still needs a fixed seed. Without it the eval's
            # precision/recall moved between runs on identical inputs.
            "options": {
                "temperature": 0,
                "seed": OLLAMA_SEED,
                "num_ctx": self._num_ctx,
            },
        }
        if self._model_supports_thinking():
            payload["think"] = self._think
        data = self._post("/api/chat", payload)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMUnavailableError(
                f"Unexpected Ollama response shape: {data!r:.200}"
            ) from exc

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self._base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:  # server reached, request failed
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise LLMUnavailableError(
                f"Ollama rejected the request ({exc.code}): {detail} — "
                f"is the model pulled? Try: ollama pull {self._model}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMUnavailableError(
                f"Ollama not reachable at {self._base_url} — install it from "
                "https://ollama.com and make sure the server is running "
                "(`ollama serve` or the desktop app)"
            ) from exc


def _import_anthropic():
    try:
        import anthropic
    except ImportError as exc:  # the free path must not require the SDK
        raise ImportError(
            "The Claude engines need the optional extra: "
            'pip install "fallacy-auditor[anthropic]"'
        ) from exc
    return anthropic


def _text_of(response) -> str:
    # Thinking blocks may precede the text block; an empty string (no text
    # block at all) fails JSON parsing upstream and is retried there.
    return "".join(block.text for block in response.content if block.type == "text")


class FableClient:
    """Claude Fable 5 with a server-side Opus 4.8 refusal fallback (paid).

    Parameter notes:
    - Thinking is always on for Fable 5; ``{"type": "adaptive"}`` is the only
      accepted explicit setting and is also valid for the Opus 4.8 fallback.
    - ``effort`` is the intelligence/latency/cost lever ("high" default;
      "xhigh" for the hardest texts). Override via FALLACY_AUDITOR_EFFORT.
    - ``temperature`` is not sent — removed on this model family (HTTP 400).
    - A refusal on the final response means the whole fallback chain
      declined; that is surfaced as ``LLMRefusalError`` and never retried.
    """

    def __init__(
        self,
        effort: str | None = None,
        max_tokens: int = 16000,
        fallback_model: str = DEFAULT_FALLBACK_MODEL,
    ) -> None:
        # Credentials resolve from the environment (ANTHROPIC_API_KEY or an
        # `ant auth login` profile); never hardcode a key.
        self._client = _import_anthropic().Anthropic()
        self._effort = effort or os.environ.get(EFFORT_ENV_VAR, "high")
        self._max_tokens = max_tokens
        self._fallback_model = fallback_model

    def complete(self, system: str, user: str, output_schema: dict) -> str:
        response = self._client.beta.messages.create(
            model=FABLE_MODEL,
            max_tokens=self._max_tokens,
            system=system,
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": self._fallback_model}],
            thinking={"type": "adaptive"},
            output_config={
                "effort": self._effort,
                "format": {"type": "json_schema", "schema": output_schema},
            },
            messages=[{"role": "user", "content": user}],
        )
        if response.stop_reason == "refusal":
            raise LLMRefusalError(
                "Both Fable 5 and the fallback model declined this input"
                + (
                    f" (category: {response.stop_details.category})"
                    if response.stop_details
                    else ""
                )
            )
        return _text_of(response)


class AnthropicClient:
    """Claude Opus 4.8 via the non-beta Messages API (paid, no fallback chain)."""

    def __init__(self, model: str | None = None, max_tokens: int = 16000) -> None:
        self._client = _import_anthropic().Anthropic()
        self._model = model or os.environ.get(MODEL_ENV_VAR, DEFAULT_MODEL)
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str, output_schema: dict) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={
                "format": {"type": "json_schema", "schema": output_schema}
            },
            messages=[{"role": "user", "content": user}],
        )
        if response.stop_reason == "refusal":
            raise LLMRefusalError(
                "The model declined to process this input"
                + (
                    f" (category: {response.stop_details.category})"
                    if response.stop_details
                    else ""
                )
            )
        return _text_of(response)
