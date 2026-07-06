#!/usr/bin/env python3
"""Trade journal with built-in fragility audit — the live scorecard.

    # after closing a trade:
    python3 tools/journal.py add RELIANCE 2026-07-14 1425.50 2026-11-20 1710.00 70
    python3 tools/journal.py add SUZLON 2026-08-01 55.20 2026-09-05 49.80 1800 --note "SMA30w exit"

    # monthly review (profit factor + fragility checks on YOUR real trades):
    python3 tools/journal.py audit

    # show the log:
    python3 tools/journal.py list

Why this exists: the replication's pooled PF for the Stage-2 system was
2.0-3.8 depending on era. Your LIVE pooled PF versus that range is the only
scorecard that matters once real money moves — it detects both a decaying
edge and (more commonly) rule-breaking by the human. Audit monthly; if live
PF sits far below the replication for 20+ trades, stop and investigate
before sizing up.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

DEFAULT_FILE = Path(__file__).parent / "journal.csv"
HEADER = ["Symbol", "Entry Date", "Entry", "Exit Date", "Exit", "Qty",
          "Profit INR", "Note"]
COST_PER_SIDE = 0.0025  # keep identical to the replications


def cmd_add(args: argparse.Namespace) -> int:
    gross = (args.exit_price - args.entry_price) * args.qty
    costs = (args.entry_price + args.exit_price) * args.qty * COST_PER_SIDE
    pnl = round(gross - costs, 2)
    new_file = not args.file.exists()
    with args.file.open("a", newline="") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(HEADER)
        w.writerow([args.symbol.upper(), args.entry_date, args.entry_price,
                    args.exit_date, args.exit_price, args.qty, pnl,
                    args.note or ""])
    print(f"logged {args.symbol.upper()}: qty {args.qty}, "
          f"P&L after costs {pnl:+,.2f} INR -> {args.file}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not args.file.exists():
        print("journal is empty — log closed trades with: journal.py add ...")
        return 0
    print(args.file.read_text().rstrip())
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    if not args.file.exists():
        print("journal is empty — nothing to audit yet")
        return 0
    try:
        from fallacy_auditor.profit import (audit_trades, format_report,
                                            parse_trades_csv)
    except ImportError:
        print("fallacy-auditor not installed: "
              'pip install --user --break-system-packages -e ./fallacy-auditor',
              file=sys.stderr)
        return 2
    stats = audit_trades(parse_trades_csv(args.file.read_text()))
    print(format_report(stats))
    print("\nContext: Stage-2 replication pooled PF ranged 2.0 (recent era) "
          "to 3.8 (full period). Live PF far below that over 20+ trades = "
          "stop and investigate (usually rule-breaking, sometimes decay).")
    return 1 if stats.warnings else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Trade journal + audit")
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    sub = ap.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="log a closed trade")
    add.add_argument("symbol")
    add.add_argument("entry_date", help="YYYY-MM-DD")
    add.add_argument("entry_price", type=float)
    add.add_argument("exit_date", help="YYYY-MM-DD")
    add.add_argument("exit_price", type=float)
    add.add_argument("qty", type=int)
    add.add_argument("--note", default="")
    add.set_defaults(fn=cmd_add)

    lst = sub.add_parser("list", help="print the journal")
    lst.set_defaults(fn=cmd_list)

    aud = sub.add_parser("audit", help="profit-factor + fragility audit")
    aud.set_defaults(fn=cmd_audit)

    args = ap.parse_args()
    for d in ("entry_date", "exit_date"):
        if hasattr(args, d):
            date.fromisoformat(getattr(args, d))  # loud failure on bad dates
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
