"""Structural checks for an outlets_dnr_<country>.csv file.

Catches the transcription errors that are easy to make and hard to spot by eye:
misread bars, skipped rows, inconsistent outlet_ids, broken encoding.

It cannot tell you whether a number matches the printed chart - only a human
reading the page can do that. Run it after each report year.

Usage (from data_collection/outlet_urls/):
    python scripts/validate_outlets.py                              # Switzerland
    python scripts/validate_outlets.py outlets_dnr_sweden.csv
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

COLUMNS = [
    "country", "submarket", "year", "list_type", "brand", "weekly_reach_pct",
    "outlet_id", "domain", "notes", "source", "brand_type", "is_aggregator",
    "domain_valid_from", "domain_valid_to", "sample_type",
    "fieldwork_start", "fieldwork_end", "sample_size",
]
BRAND_TYPES = {"outlet", "category", "aggregator", "foreign"}

problems = []
notes = []


def problem(msg):
    problems.append(msg)


def main(path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        problem("File starts with a UTF-8 BOM. Re-save as UTF-8 without BOM.")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        problem(f"File is not valid UTF-8 ({exc}). Something re-saved it in another encoding.")
        return

    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fh.seek(0)
        header = next(csv.reader(fh))

    # 18 agreed columns, optionally followed by human_checked - an x once a person has read
    # that row against the printed page. The row-level audit trail.
    if header not in (COLUMNS, COLUMNS + ["human_checked"]):
        problem(f"Header does not match the agreed schema.\n    expected: {COLUMNS}\n    found:    {header}")
        return

    if not rows:
        problem("No data rows.")
        return

    # 1. per-row field checks
    for i, r in enumerate(rows, start=2):
        where = f"row {i} ({r['year']} {r['submarket']} {r['list_type']} '{r['brand']}')"
        if "�" in "".join(r.values()):
            problem(f"{where}: contains a replacement character - encoding broke.")
        if not r["brand"].strip():
            problem(f"{where}: empty brand.")
        try:
            pct = int(r["weekly_reach_pct"])
            if not 0 <= pct <= 100:
                problem(f"{where}: weekly_reach_pct {pct} outside 0-100.")
        except ValueError:
            problem(f"{where}: weekly_reach_pct '{r['weekly_reach_pct']}' is not an integer.")
        if r["brand_type"] not in BRAND_TYPES:
            problem(f"{where}: brand_type '{r['brand_type']}' not one of {sorted(BRAND_TYPES)}.")
        if r["list_type"] not in {"online", "offline"}:
            problem(f"{where}: list_type '{r['list_type']}' not online/offline.")
        if r["is_aggregator"] not in {"TRUE", "FALSE"}:
            problem(f"{where}: is_aggregator '{r['is_aggregator']}' not TRUE/FALSE.")
        if (r["brand_type"] == "aggregator") != (r["is_aggregator"] == "TRUE"):
            problem(f"{where}: brand_type and is_aggregator disagree.")
        # domain rules
        if r["brand_type"] == "category" and r["domain"].strip():
            problem(f"{where}: category rows must have no domain, found '{r['domain']}'.")
        if r["brand_type"] != "category" and not r["domain"].strip() and not r["notes"].strip():
            problem(f"{where}: empty domain with no explanation in notes.")
        d = r["domain"].strip()
        if d and ("/" in d or d.startswith("www.") or d.startswith("http")):
            problem(f"{where}: domain '{d}' is not a bare registered domain.")

    # 2. reach must not increase down a chart
    charts = defaultdict(list)
    for i, r in enumerate(rows, start=2):
        charts[(r["year"], r["submarket"], r["list_type"])].append((i, r))
    for key, entries in sorted(charts.items()):
        prev = None
        for i, r in entries:
            try:
                pct = int(r["weekly_reach_pct"])
            except ValueError:
                continue
            if prev is not None and pct > prev:
                problem(
                    f"{key}: reach rises down the chart at row {i} "
                    f"('{r['brand']}' {pct} after {prev}) - likely a misread bar or a row out of order."
                )
            prev = pct

    # 3. outlet_id <-> brand consistency
    id_to_brands = defaultdict(set)
    brand_to_ids = defaultdict(set)
    for r in rows:
        id_to_brands[r["outlet_id"]].add(r["brand"])
        brand_to_ids[r["brand"]].add(r["outlet_id"])
    for brand, ids in sorted(brand_to_ids.items()):
        if len(ids) > 1:
            problem(f"Brand '{brand}' is mapped to several outlet_ids: {sorted(ids)}.")

    # 4. one domain per outlet_id unless date-bounded
    for oid in sorted(id_to_brands):
        rs = [r for r in rows if r["outlet_id"] == oid]
        domains = {r["domain"] for r in rs if r["domain"].strip()}
        if len(domains) > 1:
            dated = all(r["domain_valid_from"].strip() or r["domain_valid_to"].strip()
                        for r in rs if r["domain"].strip())
            if not dated:
                problem(f"outlet_id '{oid}' has several domains {sorted(domains)} with no valid-from/to dates.")

    # 5. chart coverage. Submarkets are derived from the data, not hardcoded - a single-market
    #    country has one empty submarket, and hardcoding Switzerland's two made this check emit
    #    a spurious failure for every year of any other country.
    years = sorted({r["year"] for r in rows})
    submarkets = sorted({r["submarket"] for r in rows})
    countries = sorted({r["country"] for r in rows})
    for c in countries:
        crows = [r for r in rows if r["country"] == c]
        cyears = sorted({r["year"] for r in crows})
        csubs = sorted({r["submarket"] for r in crows})
        for y in cyears:
            for sub in csubs:
                for lt in ("offline", "online"):
                    if not [r for r in crows
                            if r["year"] == y and r["submarket"] == sub and r["list_type"] == lt]:
                        label = f"{c} {y} {sub or '(no submarket)'} {lt}"
                        problem(f"{label}: no rows - a chart was skipped.")

    # summary
    print(f"Checked {len(rows)} rows across {len(charts)} charts, years {years[0]}-{years[-1]}.\n")
    for key in sorted(charts):
        print(f"  {key[0]}  {key[1]:<16} {key[2]:<8} {len(charts[key]):>3} rows")
    print()
    by_type = defaultdict(int)
    for r in rows:
        by_type[r["brand_type"]] += 1
    print("  brand_type:", dict(sorted(by_type.items())))
    if "human_checked" in header:
        n_hc = sum(1 for r in rows if r.get("human_checked", "").strip())
        print(f"  human_checked: {n_hc} / {len(rows)} rows")
    unverified = [r for r in rows if "UNVERIFIED" in r["notes"]]
    if unverified:
        print(f"\n  {len(unverified)} row(s) flagged UNVERIFIED - still need a human check:")
        for r in unverified:
            print(f"    - {r['brand']} ({r['outlet_id']})")

    print()
    if problems:
        print(f"FAIL - {len(problems)} problem(s):\n")
        for p in problems:
            print(f"  * {p}")
        return 1
    print("PASS - no structural problems found.")
    print("This does NOT confirm the numbers match the page. Check those against the PDF by eye.")
    return 0


if __name__ == "__main__":
    # data files live one level up from this scripts/ folder
    default = Path(__file__).resolve().parent.parent / "outlets_dnr_switzerland.csv"
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    sys.exit(main(target))
