# -*- coding: utf-8 -*-
"""Stage 1 liveness sweep: was each domain archived in each year the CSV uses it?

One CDX query per (domain, year). Any capture at all - 2xx or 3xx - means the host was live.
See CLAUDE.md section 13 for why it is done this way; the short version:

  - never batch years with collapse=timestamp:N plus a row limit (it invents gaps)
  - a timeout is NOT a negative; output keeps '?' distinct from 'NO'
  - matchType=domain times out on very large hosts; those fall back to matchType=exact

Usage (from data_collection/outlet_urls/):
    python scripts/wayback_liveness.py outlets_dnr_switzerland.csv
    python scripts/wayback_liveness.py outlets_dnr_sweden.csv --extra bluenews.ch,20minuten.ch

--extra probes candidate historical domains across every year in the file, alongside the
domains actually recorded. Output: wb_years_<country>.tsv next to the CSV, written
incrementally so progress survives an interruption.
"""
import argparse
import collections
import csv
import io
import re
import sys
import time
import urllib.request
from pathlib import Path

# hosts known to be so large that matchType=domain times out; queried with exact instead
LARGE_HOSTS = {"yahoo.com", "bbc.co.uk", "cnn.com", "buzzfeed.com", "buzzfeednews.com",
               "huffpost.com", "huffingtonpost.com", "msn.com", "google.com"}


def live(domain, year, tries=3):
    """Returns (is_live, first_capture). first_capture is the raw CDX hit - timestamp, URL,
    status - i.e. the artefact that proves liveness. Keep it: a bare yes/no records no
    evidence, and the status code is a free redirect signal (a 301 on every capture is the
    section 15 tell). None means no response after retries, which is NOT a negative."""
    mt = "exact" if domain in LARGE_HOSTS else "domain"
    url = (f"http://web.archive.org/cdx/search/cdx?url={domain}&matchType={mt}"
           f"&from={year}0101&to={year}1231&limit=1&fl=timestamp,original,statuscode")
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as fh:
                hit = fh.read().decode("utf-8", "replace").strip().splitlines()
                return (bool(hit), hit[0] if hit else "")
        except Exception:
            if a == tries - 1:
                return (None, "")
            time.sleep(2 + 2 * a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="outlets_dnr_<country>.csv")
    ap.add_argument("--extra", default="",
                    help="comma-separated candidate domains to probe across all years")
    ap.add_argument("--delay", type=float, default=0.25, help="seconds between queries")
    a = ap.parse_args()

    csv_path = Path(a.csv)
    if not csv_path.exists():
        sys.exit(f"no such file: {csv_path}")
    rows = list(csv.DictReader(io.open(csv_path, encoding="utf-8")))
    years_in_file = {int(r["year"]) for r in rows}

    need = collections.defaultdict(set)
    for r in rows:
        d = r["domain"].strip()
        if d:
            need[d].add(int(r["year"]))
    for d in [x.strip() for x in a.extra.split(",") if x.strip()]:
        need[d] |= years_in_file

    m = re.search(r"outlets_dnr_(\w+)\.csv$", csv_path.name)
    tag = m.group(1) if m else csv_path.stem
    out_path = csv_path.with_name(f"wb_years_{tag}.tsv")

    out = io.open(out_path, "w", encoding="utf-8", newline="")
    out.write("domain\tyear\tlive\tused_in_csv\tfirst_capture\n")
    total = sum(len(v) for v in need.values())
    print(f"{csv_path.name}: {len(need)} domains, {total} checks -> {out_path.name}\n")

    i = 0
    summary = collections.defaultdict(dict)
    for d in sorted(need):
        for y in sorted(need[d]):
            i += 1
            r, cap = live(d, y)
            used = "yes" if any(x["domain"].strip() == d and int(x["year"]) == y for x in rows) else "no"
            summary[d][y] = r
            out.write(f"{d}\t{y}\t{'?' if r is None else ('yes' if r else 'NO')}\t{used}\t{cap}\n")
            out.flush()
            print(f"[{i}/{total}] {d} {y} live={r} used={used}", flush=True)
            time.sleep(a.delay)
    out.close()

    print("\n=== SUMMARY ===", flush=True)
    conflicts = 0
    for d in sorted(summary):
        yrs = summary[d]
        dead = sorted(y for y, v in yrs.items() if v is False)
        err = sorted(y for y, v in yrs.items() if v is None)
        used_years = {int(r["year"]) for r in rows if r["domain"].strip() == d}
        conflict = [y for y in dead if y in used_years]
        conflicts += len(conflict)
        tag_ = "CONFLICT" if conflict else ("errors" if err else "ok")
        print(f"{d:<28} {tag_:<9} not-archived={dead} used-but-not-archived={conflict} "
              f"timeouts={err}", flush=True)
    print(f"\nDONE - {conflicts} used-but-not-archived (domain, year) pair(s). "
          f"Re-run any timeouts before interpreting them.", flush=True)


if __name__ == "__main__":
    main()
