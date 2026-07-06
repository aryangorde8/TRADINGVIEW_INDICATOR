"""Profit-factor auditor: exact math, fragility checks, CSV parsing, CLI."""

from __future__ import annotations

import json

import pytest

from fallacy_auditor.__main__ import main
from fallacy_auditor.profit import audit_trades, parse_trades_csv

# TradingView-style export: entry rows have a blank profit cell.
TV_CSV = """\
Trade #,Type,Signal,Date/Time,Price,Profit INR,Profit %,Cum. Profit INR
1,Entry long,L,2026-01-02,100.0,,,
1,Exit long,TP,2026-01-05,110.0,100.00,10.0,100.00
2,Entry long,L,2026-01-08,105.0,,,
2,Exit long,SL,2026-01-09,100.0,-50.00,-4.8,50.00
3,Entry long,L,2026-01-12,102.0,,,
3,Exit long,TP,2026-01-20,112.0,100.00,9.8,150.00
"""


def test_parse_tradingview_export_skips_entry_rows_and_percent_columns():
    profits = parse_trades_csv(TV_CSV)
    assert profits == [100.0, -50.0, 100.0]  # absolute column, not % or cum


def test_missing_profit_column_is_loud():
    with pytest.raises(ValueError, match="no profit column"):
        parse_trades_csv("a,b\n1,2\n")


def test_tab_separated_paste_with_currency_symbols():
    """TradingView's List of Trades pastes as TSV with formatted numbers —
    the free-plan copy-paste path must parse as-is."""
    tsv = (
        "Trade #\tType\tProfit INR\n"
        "1\tExit long\t₹1,250.50\n"
        "2\tExit long\t−400.25\n"  # unicode minus, as rendered in the UI
    )
    assert parse_trades_csv(tsv) == [1250.50, -400.25]


def test_profit_factor_math():
    stats = audit_trades([100.0, -50.0, 100.0])
    assert stats.profit_factor == pytest.approx(4.0)  # 200 / 50
    assert stats.wins == 2 and stats.losses == 1
    assert stats.expectancy == pytest.approx(50.0)


def test_no_losses_gives_none_pf_and_warning():
    stats = audit_trades([10.0, 20.0])
    assert stats.profit_factor is None
    assert any("no losing trades" in w for w in stats.warnings)


def test_fragile_edge_flagged_when_top_winners_carry_it():
    # PF = 130/50 = 2.6, but without the top 3 winners it collapses.
    profits = [100.0, 15.0, 10.0, 5.0, -25.0, -25.0]
    stats = audit_trades(profits)
    assert stats.profit_factor == pytest.approx(2.6)
    assert stats.pf_excl_top3 == pytest.approx(5.0 / 50.0)
    assert any("fragile edge" in w for w in stats.warnings)
    assert any("single trade contributes" in w for w in stats.warnings)


def test_half_split_instability_flagged():
    profits = [50.0, 40.0, 30.0, -20.0, -20.0, -25.0]  # strong half, losing half
    stats = audit_trades(profits)
    assert stats.pf_first_half is None  # no losses in first half
    assert stats.pf_second_half == pytest.approx(0.0)
    assert any("unstable across time" in w for w in stats.warnings)


def test_small_sample_always_warned():
    stats = audit_trades([10.0, -5.0] * 5)  # 10 trades
    assert any("dominated by luck" in w for w in stats.warnings)


def test_max_consecutive_losses_and_drawdown():
    stats = audit_trades([10.0, -5.0, -5.0, -5.0, 20.0])
    assert stats.max_consecutive_losses == 3
    assert stats.max_drawdown == pytest.approx(15.0)


def test_bootstrap_ci_is_deterministic_and_ordered():
    profits = [10.0, -5.0, 8.0, -4.0, 12.0, -6.0] * 10  # 60 trades
    a = audit_trades(profits)
    b = audit_trades(profits)
    assert (a.pf_ci_low, a.pf_ci_high) == (b.pf_ci_low, b.pf_ci_high)
    assert a.pf_ci_low <= a.profit_factor <= a.pf_ci_high


# ---- CLI (.csv implies trade-audit mode; offline) ----


def test_cli_audits_csv_and_reports(tmp_path, capsys):
    path = tmp_path / "trades.csv"
    path.write_text(TV_CSV)
    rc = main([str(path)])
    out = capsys.readouterr().out
    assert "PROFIT FACTOR: 4.00" in out
    assert rc == 1  # small-sample warning => nonzero, gateable


def test_cli_csv_json_mode(tmp_path, capsys):
    path = tmp_path / "trades.csv"
    path.write_text(TV_CSV)
    main([str(path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["profit_factor"] == pytest.approx(4.0)


def test_cli_bad_csv_exits_2(tmp_path, capsys):
    path = tmp_path / "trades.csv"
    path.write_text("a,b\n1,2\n")
    assert main([str(path)]) == 2
