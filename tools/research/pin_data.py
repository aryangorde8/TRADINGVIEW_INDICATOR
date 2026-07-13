#!/usr/bin/env python3
"""Pin the Stage-2 price data: convert data_cache/*.csv -> *.parquet, hash it.

The backtest previously re-fetched from Yahoo on every run with
`period="max", auto_adjust=True`. That makes results non-reproducible twice
over: new bars append, AND auto_adjust restates the entire historical series
whenever a split or dividend occurs. Committing a hashed parquet snapshot
freezes the exact inputs the published figures were computed from.

Usage:
    python3 tools/research/pin_data.py            # convert + hash + manifest
    python3 tools/research/pin_data.py --verify   # re-hash and check drift
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data_cache"
MANIFEST = CACHE / "MANIFEST.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def convert() -> int:
    csvs = sorted(CACHE.glob("*.csv"))
    if not csvs:
        print(f"no CSVs in {CACHE} — nothing to pin", file=sys.stderr)
        return 1

    rows = []
    for csv in csvs:
        df = pd.read_csv(csv, index_col=0, parse_dates=True)
        df = df.dropna(subset=["Close"]).sort_index()
        pq = csv.with_suffix(".parquet")
        df.to_parquet(pq, compression="snappy")
        rows.append(
            {
                "name": pq.stem,
                "rows": len(df),
                "first": df.index[0].date(),
                "last": df.index[-1].date(),
                "sha256": sha256(pq),
            }
        )
        csv.unlink()  # parquet is now the pinned artifact; drop the CSV

    today = datetime.date.today().isoformat()
    lines = [
        "# data_cache — PINNED price snapshot",
        "",
        f"**Fetched: {today}** from Yahoo Finance "
        "(`yfinance`, `period=max`, `interval=1d`, `auto_adjust=True`).",
        "",
        "These parquet files are the **exact inputs** the committed Stage-2",
        "figures were computed from. They are committed (not gitignored) so a",
        "fresh clone reproduces the published numbers byte-for-byte.",
        "",
        "**Why pinning matters:** `auto_adjust=True` restates the *entire*",
        "historical series on every split/dividend — past prices change, not",
        "just recent ones. Re-fetching therefore silently moves old results.",
        "Do not regenerate these files to 'refresh' them; a refresh is a new",
        "dataset and requires republishing every dependent figure.",
        "",
        f"{len(rows)} series. Verify integrity with "
        "`python3 tools/research/pin_data.py --verify`.",
        "",
        "| Series | Rows | First bar | Last bar | SHA256 |",
        "|---|---:|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: x["name"]):
        lines.append(
            f"| {r['name']} | {r['rows']} | {r['first']} | {r['last']} "
            f"| `{r['sha256']}` |"
        )
    MANIFEST.write_text("\n".join(lines) + "\n")

    total_mb = sum(p.stat().st_size for p in CACHE.glob("*.parquet")) / 1e6
    print(f"pinned {len(rows)} series -> {CACHE} ({total_mb:.1f} MB parquet)")
    print(f"manifest -> {MANIFEST}")
    return 0


def verify() -> int:
    if not MANIFEST.exists():
        print("no MANIFEST.md — run without --verify first", file=sys.stderr)
        return 1
    expected = {}
    for line in MANIFEST.read_text().splitlines():
        if line.startswith("| ") and "`" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            expected[cells[0]] = cells[4].strip("`")

    bad = 0
    for name, want in sorted(expected.items()):
        pq = CACHE / f"{name}.parquet"
        if not pq.exists():
            print(f"MISSING  {name}")
            bad += 1
            continue
        got = sha256(pq)
        if got != want:
            print(f"DRIFTED  {name}\n  expected {want}\n  got      {got}")
            bad += 1
    if bad:
        print(f"\n{bad} of {len(expected)} series failed verification")
        return 1
    print(f"OK: all {len(expected)} pinned series match their manifest hashes")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="re-hash the parquet files and check against MANIFEST.md")
    args = ap.parse_args()
    return verify() if args.verify else convert()


if __name__ == "__main__":
    raise SystemExit(main())
