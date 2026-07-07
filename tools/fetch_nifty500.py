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

INDICES = {
    "500": "ind_nifty500list.csv",
    "next50": "ind_niftynext50list.csv",
    "midcap150": "ind_niftymidcap150list.csv",
    "smallcap250": "ind_niftysmallcap250list.csv",
}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Fetch NSE index constituents")
    ap.add_argument("--index", choices=sorted(INDICES), default="500")
    args = ap.parse_args()
    csv_name = INDICES[args.index]
    sources = [
        f"https://archives.nseindia.com/content/indices/{csv_name}",
        f"https://www.niftyindices.com/IndexConstituent/{csv_name}",
    ]
    out = Path(__file__).parent / f"watchlist_nifty{args.index}.txt"

    text = None
    for url in sources:
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
    min_expected = {"500": 400, "next50": 45, "midcap150": 130,
                    "smallcap250": 220}[args.index]
    if len(symbols) < min_expected:
        print(f"only {len(symbols)} symbols parsed — source format may have "
              "changed; not overwriting", file=sys.stderr)
        return 1

    out.write_text("\n".join(symbols) + "\n")
    print(f"wrote {len(symbols)} symbols -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
