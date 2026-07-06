#!/usr/bin/env python3
"""Fetch the current Nifty 500 constituents and write the scanner watchlist.

    python3 tools/fetch_nifty500.py
    python3 tools/stage2_scan.py --watchlist tools/watchlist_nifty500.txt

Run monthly-ish: the index reconstitutes twice a year, and using the CURRENT
constituents forward-looking is exactly how survivorship bias is avoided in
live operation (you scan today's index today — no hindsight involved).
"""

from __future__ import annotations

import csv
import io
import sys
import urllib.request
from pathlib import Path

SOURCES = [
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
]
OUT = Path(__file__).parent / "watchlist_nifty500.txt"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def main() -> int:
    text = None
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            break
        except Exception as exc:  # noqa: BLE001 — try the next mirror
            print(f"{url}: {exc}", file=sys.stderr)
    if not text:
        print("all sources failed — download the CSV manually from "
              "niftyindices.com and extract the Symbol column", file=sys.stderr)
        return 1

    symbols = []
    for row in csv.DictReader(io.StringIO(text)):
        sym = (row.get("Symbol") or "").strip().upper()
        if sym and row.get("Series", "EQ").strip() == "EQ":
            symbols.append(sym)
    if len(symbols) < 400:
        print(f"only {len(symbols)} symbols parsed — source format may have "
              "changed; not overwriting", file=sys.stderr)
        return 1

    OUT.write_text("\n".join(symbols) + "\n")
    print(f"wrote {len(symbols)} symbols -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
