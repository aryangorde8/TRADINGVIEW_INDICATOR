"""Deterministic Pine Script linter for mechanical bias red flags.

The LLM auditor judges *reasoning*; this module inspects *implementation*.
It is rule-based — no model, no network, no cost — so its findings are exact
and repeatable, and it runs in milliseconds. Together they cover the two
places a trading strategy lies to its author: the story told about it and
the code that computes it.

Scope discipline: only high-confidence mechanical patterns are flagged, each
with the reasoning and the safe idiom in the message. Anything that requires
understanding *intent* belongs to the LLM auditor, not here — a linter that
guesses would break the same no-hallucinated-findings promise the grounding
gate enforces on the LLM side.

Rules:
    pine-lookahead-on        request.security(..., lookahead=barmerge.lookahead_on)
                             without the [1] offset idiom — reads future bars
                             in backtests (classic repainting lookahead bias).
    pine-lookahead-review    lookahead_on together with a [1] offset — the
                             standard non-repainting idiom, flagged for review.
    pine-calc-on-every-tick  strategy(..., calc_on_every_tick=true) — live
                             execution reacts to intrabar ticks the backtest
                             never simulated; results diverge.
    pine-timenow             `timenow` is wall-clock "now" even on historical
                             bars; logic conditioned on it differs between
                             backtest and live.
    pine-isrealtime          `barstate.isrealtime` branches mean the backtest
                             exercises different code than live trading runs.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict


class PineFinding(BaseModel):
    """One mechanical red flag: rule id, 1-indexed line, verbatim source line."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str
    line: int
    source: str
    message: str


_LOOKAHEAD_ON = re.compile(r"lookahead\s*=\s*barmerge\.lookahead_on")
_LOOKAHEAD_CONST = re.compile(r"barmerge\.lookahead_on")
_SECURITY_CALL = re.compile(r"(?:request\.)?security\s*\(")
_CALC_EVERY_TICK = re.compile(r"calc_on_every_tick\s*=\s*true")
_TIMENOW = re.compile(r"\btimenow\b")
_ISREALTIME = re.compile(r"\bbarstate\.isrealtime\b")

_MSG_LOOKAHEAD = (
    "lookahead=barmerge.lookahead_on without a [1] offset reads future bars "
    "during backtests (repainting lookahead bias). Safe idiom: "
    "request.security(sym, tf, expr[1], lookahead=barmerge.lookahead_on)."
)
_MSG_LOOKAHEAD_REVIEW = (
    "lookahead_on used together with a [1] offset — the standard "
    "non-repainting idiom. Verify the [1] applies to the requested "
    "expression itself, not to something else in the call."
)
_MSG_CALC_TICK = (
    "calc_on_every_tick=true makes live execution react to intrabar ticks "
    "the backtest never simulated; backtest and live results will diverge."
)
_MSG_TIMENOW = (
    "timenow is wall-clock 'now' even when evaluating historical bars; any "
    "logic conditioned on it behaves differently in backtest and live."
)
_MSG_ISREALTIME = (
    "barstate.isrealtime branches make backtest and live take different "
    "code paths, so the backtest no longer tests the logic that trades."
)


def _strip_comment(line: str) -> str:
    # Pine line comments start with //. The rare `//` inside a string literal
    # is accepted as a false strip — it can only suppress a finding on that
    # line, never invent one.
    idx = line.find("//")
    return line if idx == -1 else line[:idx]


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _balanced_call(text: str, open_paren: int) -> str:
    """Return the call text from the opening paren to its matching close."""
    depth = 0
    for i in range(open_paren, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren : i + 1]
    return text[open_paren:]  # unbalanced (truncated source): scan to end


def lint_pine(source: str) -> list[PineFinding]:
    """Lint Pine Script source; returns findings in line order."""
    raw_lines = source.splitlines()
    stripped = [_strip_comment(line) for line in raw_lines]
    text = "\n".join(stripped)

    findings: list[PineFinding] = []
    lookahead_lines: set[int] = set()

    def add(rule: str, line: int, message: str) -> None:
        findings.append(
            PineFinding(
                rule=rule,
                line=line,
                source=raw_lines[line - 1].strip(),
                message=message,
            )
        )

    # Rule 1: lookahead_on inside security() calls (balanced-paren scan so
    # multi-line calls are handled).
    for match in _SECURITY_CALL.finditer(text):
        call = _balanced_call(text, match.end() - 1)
        if not _LOOKAHEAD_ON.search(call):
            continue
        line = _line_of(text, match.start())
        lookahead_lines.update(
            range(line, line + call.count("\n") + 1)
        )
        if "[1]" in call:
            add("pine-lookahead-review", line, _MSG_LOOKAHEAD_REVIEW)
        else:
            add("pine-lookahead-on", line, _MSG_LOOKAHEAD)

    # Catch-all: the bare constant outside any scanned security call (e.g.
    # stored in a variable and passed indirectly).
    for match in _LOOKAHEAD_CONST.finditer(text):
        line = _line_of(text, match.start())
        if line not in lookahead_lines:
            lookahead_lines.add(line)
            add("pine-lookahead-on", line, _MSG_LOOKAHEAD)

    # Simple per-line rules.
    for lineno, line in enumerate(stripped, start=1):
        if _CALC_EVERY_TICK.search(line):
            add("pine-calc-on-every-tick", lineno, _MSG_CALC_TICK)
        if _TIMENOW.search(line):
            add("pine-timenow", lineno, _MSG_TIMENOW)
        if _ISREALTIME.search(line):
            add("pine-isrealtime", lineno, _MSG_ISREALTIME)

    findings.sort(key=lambda f: f.line)
    return findings
