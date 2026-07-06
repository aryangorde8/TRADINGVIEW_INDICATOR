"""OllamaClient wire protocol, verified against a real (stub) HTTP server.

These tests run a tiny in-process HTTP server that speaks Ollama's
``/api/show`` and ``/api/chat`` shapes, so the client's request payloads and
response handling are exercised over an actual socket — deterministically,
offline, and free.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from fallacy_auditor import LLMUnavailableError, OllamaClient, audit_text
from fallacy_auditor.prompt import AUDIT_OUTPUT_SCHEMA

TEXT = "Every trader I follow got rich with this system, so the edge is real."
FINDING_JSON = json.dumps(
    {"findings": [
        {"fallacy": "survivorship_bias", "span": "Every trader I follow got rich"}
    ]}
)


class _StubOllama(BaseHTTPRequestHandler):
    """Speaks just enough of Ollama's native API for the tests.

    Model-name conventions: "missing-model" 404s (as a real server does for
    an un-pulled model); names containing "thinker" advertise the thinking
    capability on /api/show.
    """

    requests: list[tuple[str, dict]] = []
    reply_content = FINDING_JSON

    def do_POST(self):  # noqa: N802 (http.server API)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        type(self).requests.append((self.path, body))

        if body.get("model") == "missing-model":
            payload = json.dumps({"error": "model 'missing-model' not found"}).encode()
            self.send_response(404)
        elif self.path == "/api/show":
            caps = ["completion"]
            if "thinker" in body.get("model", ""):
                caps.append("thinking")
            payload = json.dumps({"capabilities": caps}).encode()
            self.send_response(200)
        else:  # /api/chat
            payload = json.dumps(
                {"message": {"role": "assistant", "content": type(self).reply_content},
                 "done": True}
            ).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # keep test output clean
        pass


@pytest.fixture()
def stub_server():
    _StubOllama.requests = []
    _StubOllama.reply_content = FINDING_JSON
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    thread.join(timeout=5)


def _chat_bodies() -> list[dict]:
    return [body for path, body in _StubOllama.requests if path == "/api/chat"]


def test_request_payload_shape(stub_server):
    client = OllamaClient(model="test-model", base_url=stub_server)
    raw = client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)

    assert raw == FINDING_JSON
    body = _chat_bodies()[0]
    assert body["model"] == "test-model"
    assert body["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    assert body["format"] == AUDIT_OUTPUT_SCHEMA  # schema-constrained output
    assert body["stream"] is False
    assert body["options"] == {"temperature": 0, "num_ctx": 8192}
    # non-thinking model: the think parameter must not be sent at all
    # (Ollama rejects it for models without the capability)
    assert "think" not in body


def test_truncation_guard_rejects_oversized_input(stub_server):
    """Ollama silently truncates past num_ctx; the client must refuse loudly
    instead — before any HTTP request is made."""
    client = OllamaClient(model="test-model", base_url=stub_server, num_ctx=2048)
    huge = "x" * (2048 * 4)  # comfortably past the guard at ~3 chars/token
    calls_before = len(_StubOllama.requests)
    with pytest.raises(ValueError, match="silently truncate"):
        client.complete("SYS", huge, AUDIT_OUTPUT_SCHEMA)
    assert len(_StubOllama.requests) == calls_before  # zero requests sent


def test_thinking_model_gets_think_false(stub_server):
    """Thinking-capable models get think:false by default — unconstrained
    thinking tokens turn a 1-minute CPU audit into a 7-minute one."""
    client = OllamaClient(model="thinker-model", base_url=stub_server)
    client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)
    assert _chat_bodies()[0]["think"] is False


def test_think_opt_in(stub_server):
    client = OllamaClient(model="thinker-model", base_url=stub_server, think=True)
    client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)
    assert _chat_bodies()[0]["think"] is True


def test_capability_lookup_is_cached(stub_server):
    client = OllamaClient(model="thinker-model", base_url=stub_server)
    client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)
    client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)
    show_calls = [p for p, _ in _StubOllama.requests if p == "/api/show"]
    assert len(show_calls) == 1  # one capability query per client, not per call


def test_full_pipeline_over_http(stub_server):
    """audit_text through a real socket: prompt out, grounded finding back."""
    client = OllamaClient(model="test-model", base_url=stub_server)
    report = audit_text(TEXT, client)
    assert len(report.findings) == 1
    assert report.findings[0].span == "Every trader I follow got rich"


def test_missing_model_raises_unavailable(stub_server):
    client = OllamaClient(model="missing-model", base_url=stub_server)
    with pytest.raises(LLMUnavailableError, match="ollama pull missing-model"):
        client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)


def test_unreachable_server_raises_unavailable():
    # Port 9 (discard) is never running an HTTP server locally.
    client = OllamaClient(model="x", base_url="http://127.0.0.1:9", timeout=2)
    with pytest.raises(LLMUnavailableError, match="not reachable"):
        client.complete("SYS", "USER", AUDIT_OUTPUT_SCHEMA)


def test_unavailable_is_not_retried(stub_server):
    """Infrastructure failures must fail immediately, not burn retries."""
    calls_before = len(_StubOllama.requests)
    client = OllamaClient(model="missing-model", base_url=stub_server)
    with pytest.raises(LLMUnavailableError):
        audit_text(TEXT, client)
    assert len(_StubOllama.requests) == calls_before + 1  # exactly one attempt
