"""Deterministic Pine Script linter — every rule proven on real patterns,
plus the CLI lint mode end-to-end (offline, no model)."""

from __future__ import annotations

import json

import pytest

from fallacy_auditor.__main__ import main
from fallacy_auditor.pinelint import lint_pine

LOOKAHEAD_BAD = (
    '//@version=5\nindicator("x")\n'
    'htf = request.security(syminfo.tickerid, "D", close, '
    "lookahead=barmerge.lookahead_on)\n"
)
LOOKAHEAD_SAFE_IDIOM = (
    'htf = request.security(syminfo.tickerid, "D", close[1], '
    "lookahead=barmerge.lookahead_on)\n"
)
CLEAN_STRATEGY = """\
//@version=5
strategy("clean", overlay=true, calc_on_every_tick=false)
htf = request.security(syminfo.tickerid, "D", close[1], lookahead=barmerge.lookahead_off)
longCond = ta.crossover(ta.ema(close, 9), ta.ema(close, 21))
if longCond
    strategy.entry("L", strategy.long)
"""


def _rules(source: str) -> list[str]:
    return [f.rule for f in lint_pine(source)]


def test_lookahead_on_without_offset_is_flagged():
    findings = lint_pine(LOOKAHEAD_BAD)
    assert [f.rule for f in findings] == ["pine-lookahead-on"]
    assert findings[0].line == 3
    # the source line is quoted verbatim — same grounding discipline as the LLM side
    assert "lookahead=barmerge.lookahead_on" in findings[0].source
    assert "[1]" in findings[0].message  # message teaches the safe idiom


def test_lookahead_on_with_offset_is_review_not_violation():
    assert _rules(LOOKAHEAD_SAFE_IDIOM) == ["pine-lookahead-review"]


def test_lookahead_off_is_clean():
    assert lint_pine(CLEAN_STRATEGY) == []


def test_commented_out_lookahead_is_ignored():
    source = "// htf = request.security(t, 'D', close, lookahead=barmerge.lookahead_on)\n"
    assert lint_pine(source) == []


def test_multiline_security_call_is_scanned():
    source = (
        "htf = request.security(syminfo.tickerid,\n"
        '     "D",\n'
        "     close,\n"
        "     lookahead=barmerge.lookahead_on)\n"
    )
    findings = lint_pine(source)
    assert [f.rule for f in findings] == ["pine-lookahead-on"]
    assert findings[0].line == 1  # anchored at the call site


def test_lookahead_on_outside_security_call_is_still_flagged():
    source = "mode = barmerge.lookahead_on\n"
    assert _rules(source) == ["pine-lookahead-on"]


def test_calc_on_every_tick_true_flagged_false_clean():
    assert _rules('strategy("s", calc_on_every_tick=true)') == [
        "pine-calc-on-every-tick"
    ]
    assert _rules('strategy("s", calc_on_every_tick=false)') == []


def test_timenow_flagged():
    assert _rules("if timenow - time < 60000\n    strategy.close_all()") == [
        "pine-timenow"
    ]


def test_isrealtime_flagged():
    assert _rules("entrySize = barstate.isrealtime ? 1 : 2") == ["pine-isrealtime"]


def test_findings_sorted_by_line():
    source = (
        "x = barstate.isrealtime\n"
        "y = timenow\n"
        'h = request.security(t, "D", close, lookahead=barmerge.lookahead_on)\n'
    )
    assert [f.line for f in lint_pine(source)] == [1, 2, 3]


# ---- CLI lint mode (no model, no network) ----


def test_cli_lints_pine_file_and_exits_nonzero(tmp_path, capsys):
    path = tmp_path / "strategy.pine"
    path.write_text(LOOKAHEAD_BAD)
    rc = main([str(path)])  # .pine extension implies lint mode
    out = capsys.readouterr().out
    assert rc == 1
    assert "pine-lookahead-on" in out


def test_cli_clean_pine_exits_zero(tmp_path, capsys):
    path = tmp_path / "clean.pine"
    path.write_text(CLEAN_STRATEGY)
    rc = main([str(path)])
    assert rc == 0
    assert "clean" in capsys.readouterr().out


def test_cli_pine_json_output(tmp_path, capsys):
    path = tmp_path / "strategy.pine"
    path.write_text(LOOKAHEAD_BAD)
    rc = main([str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["findings"][0]["rule"] == "pine-lookahead-on"
    assert payload["findings"][0]["line"] == 3


def test_cli_pine_flag_for_stdin(monkeypatch, capsys):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(LOOKAHEAD_BAD))
    rc = main(["--pine"])
    assert rc == 1
