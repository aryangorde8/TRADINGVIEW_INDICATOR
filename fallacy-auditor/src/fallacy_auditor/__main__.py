"""Linter-style CLI: audit a file (or stdin) and exit non-zero on findings.

    python -m fallacy_auditor reasoning.txt --verify      # LLM reasoning audit
    echo "..." | python -m fallacy_auditor --json
    python -m fallacy_auditor strategy.pine               # deterministic Pine lint

Exit codes: 0 = clean, 1 = findings flagged, 2 = usage/audit error.
The non-zero-on-findings convention lets this gate LLM-generated trading
reasoning (and strategy code) in a pipeline exactly like a linter gates code.

Files ending in .pine (or any input with --pine) are checked by the
deterministic Pine Script linter — offline, no model, instant. Everything
else goes through the LLM reasoning auditor; the default engine is a free
local model via Ollama, while --engine fable/opus use the paid Claude API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import AuditError, audit_text, audit_text_verified
from .schemas import VerifiedAuditReport


def _have_credentials() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    # An `ant auth login` profile also works; the SDK picks it up itself.
    return (Path.home() / ".config" / "anthropic").exists()


def _make_client(engine: str):
    # Imported lazily so `--engine ollama` (the free default) never touches
    # the optional anthropic dependency.
    if engine == "ollama":
        from .llm import OllamaClient

        return OllamaClient()
    if engine == "fable":
        from .llm import FableClient

        return FableClient()
    from .llm import AnthropicClient

    return AnthropicClient()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m fallacy_auditor",
        description="Audit trading reasoning for five specific fallacies.",
    )
    parser.add_argument(
        "path", nargs="?", help="text file to audit; omit to read stdin"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="run the fresh-context verification pass (second LLM call)",
    )
    parser.add_argument(
        "--engine",
        choices=["ollama", "fable", "opus"],
        default="ollama",
        help="ollama = free local model (default); fable/opus = paid Claude API",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json", help="emit JSON"
    )
    parser.add_argument(
        "--pine",
        action="store_true",
        help="lint input as Pine Script for mechanical bias red flags "
        "(deterministic, offline, no model); implied by a .pine path",
    )
    parser.add_argument(
        "--trades",
        action="store_true",
        help="audit a trade-list CSV (e.g. TradingView 'List of Trades' "
        "export): profit factor + fragility checks, offline, no model; "
        "implied by a .csv path",
    )
    args = parser.parse_args(argv)

    if args.trades or (args.path or "").endswith(".csv"):
        if args.path:
            with open(args.path, encoding="utf-8") as f:
                csv_text = f.read()
        else:
            csv_text = sys.stdin.read()
        from .profit import audit_trades, format_report, parse_trades_csv

        try:
            stats = audit_trades(parse_trades_csv(csv_text))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.as_json:
            print(stats.model_dump_json(indent=2))
        else:
            print(format_report(stats))
        return 1 if stats.warnings else 0

    if args.pine or (args.path or "").endswith(".pine"):
        if args.path:
            with open(args.path, encoding="utf-8") as f:
                source = f.read()
        else:
            source = sys.stdin.read()
        from .pinelint import lint_pine

        pine_findings = lint_pine(source)
        if args.as_json:
            print(
                json.dumps(
                    {"findings": [f.model_dump() for f in pine_findings]},
                    indent=2,
                )
            )
        else:
            if not pine_findings:
                print("clean: no mechanical red flags")
            for f in pine_findings:
                print(f"{args.path or '<stdin>'}:{f.line}: [{f.rule}] {f.message}")
                print(f"    {f.source}")
        return 1 if pine_findings else 0

    if args.engine != "ollama" and not _have_credentials():
        print(
            "error: no Anthropic credentials found "
            "(set ANTHROPIC_API_KEY or run `ant auth login`) — "
            "or use the free default: --engine ollama",
            file=sys.stderr,
        )
        return 2

    if args.path:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    client = _make_client(args.engine)

    try:
        if args.verify:
            result: VerifiedAuditReport = audit_text_verified(text, client)
        else:
            report = audit_text(text, client)
            result = VerifiedAuditReport(findings=report.findings, rejected=[])
    except (AuditError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(result.model_dump_json(indent=2))
    else:
        if not result.findings:
            print("clean: no fallacies found")
        for finding in result.findings:
            print(f"[{finding.fallacy.value}] {finding.span!r}")
        for verdict in result.rejected:
            print(
                f"(verifier rejected {verdict.fallacy.value}: {verdict.reason})",
                file=sys.stderr,
            )

    return 1 if result.findings else 0


if __name__ == "__main__":
    sys.exit(main())
