# -*- coding: utf-8 -*-
"""Stages 3 and 4 (A3), per domain-year: does the archived site carry this outlet's name, and
does it carry articles?

For every (outlet_id, domain, year) in the CSV with a non-empty domain:

  A3 masthead   fetch the archived homepage nearest mid-year via Wayback (raw, id_ mode) and
                check whether the outlet's name appears in its <title> or masthead text.
                A hit is documentary, per-year, Tier A3 evidence (CLAUDE.md section 16).
  article-bearing  CDX count of captures under the domain that year whose path looks like an
                article (a /20xx/ date segment). Section 15.

Writes domain_evidence_<country>.tsv beside the CSV, incrementally. Verdicts:
  A3            masthead matched, articles present         -> identity + article-bearing OK
  A3-noarticles masthead matched, no article-shaped URLs   -> portal / e-paper? human check
  A3-arts?      masthead matched, article query failed     -> re-run the article check
  needs-human   a title was found and it is not this outlet -> tier process by hand
  no-title      page returned but no title extracted       -> retryable, not evidence
  no-page       403/500/empty body from Wayback            -> retryable
  ?             no response after retries                  -> retryable
  shared        domain carries >1 outlet_id: masthead confirms the DOMAIN, not which outlet's
                articles live there (rule 3) - always needs a human decision

This confirms that a host presented itself as the outlet in that year. It does not, on its
own, distinguish a rebrand from a domain sale - that is the A2 redirect check, still manual.

Usage (from data_collection/outlet_urls/):
    python scripts/wayback_identity.py outlets_dnr_switzerland.csv
    python scripts/wayback_identity.py outlets_dnr_sweden.csv --delay 1.0
    python scripts/wayback_identity.py outlets_dnr_switzerland.csv --retry   # redo only ? rows
"""
import argparse
import collections
import csv
import datetime as dt
import html
import io
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

STOP = {"news", "online", "public", "broadcaster", "the", "and", "incl", "inc", "edition",
        "editions", "sunday", "evening", "tv", "radio", "print", "website", "websites", "ch",
        "com", "net", "de", "fr", "se", "nyheter", "nyheterna", "e", "eg", "etc", "journal",
        "tagesschau", "heute", "aktuell", "dagblad", "tidning", "tidningen"}
UA = "ETH-media-pluralism-registry/1.0 (academic research; identity check)"


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def keywords(outlet_id, brands):
    """Distinctive tokens for this outlet: the id shortname plus brand words >= 4 chars."""
    short = outlet_id.split("_", 1)[1] if "_" in outlet_id else outlet_id
    short = re.sub(r"_(de|fr|it|en|se)$", "", short)
    kws = {norm(short)}
    for b in brands:
        for tok in re.findall(r"[A-Za-zÀ-ÿ0-9]+", b):
            t = norm(tok)
            if len(t) >= 4 and t not in STOP:
                kws.add(t)
    return {k for k in kws if len(k) >= 3}


REFUSED = 0          # consecutive connection refusals; Archive.org blocks on sustained load
REFUSED_LIMIT = 6


def fetch(url, timeout=45, tries=3, max_bytes=600_000):
    """Returns (status, final_url, body). status None = no response after retries.

    max_bytes is generous on purpose: 2026-era homepages carry more than 60 KB of <head>
    before the <title>, and reading only 60 KB produced ten false 'needs-human' verdicts with
    status 200 and an empty title.
    """
    global REFUSED
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                REFUSED = 0
                return r.status, r.geturl(), r.read(max_bytes).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            REFUSED = 0
            return e.code, url, ""
        except Exception as e:
            if "refused" in str(e).lower() or "10061" in str(e):
                REFUSED += 1
                if REFUSED >= REFUSED_LIMIT:
                    sys.exit(f"\nArchive.org has refused {REFUSED} connections in a row - we are "
                             f"being throttled. Stop, wait an hour or more, then re-run with "
                             f"--retry and a larger --delay. Rows already written are kept.")
            if a == tries - 1:
                return None, url, ""
            time.sleep(3 + 3 * a)


def masthead(domain, year):
    """Archived homepage nearest 1 July of that year, raw. Returns (status, final_url, title, text).

    Title comes from <title>, else og:site_name, else og:title - some sites put the brand only
    in the Open Graph tags.
    """
    url = f"https://web.archive.org/web/{year}0701000000id_/http://{domain}/"
    status, final, body = fetch(url)
    if status is None:
        return None, url, "", ""
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    title = html.unescape(m.group(1)).strip() if m else ""
    if not title:
        for prop in ("og:site_name", "og:title"):
            m = re.search(r'property=["\']' + prop + r'["\']\s+content=["\']([^"\']+)', body, re.I)
            if m:
                title = html.unescape(m.group(1)).strip()
                break
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return status, final, title, text[:8000]


def article_count(domain, year):
    """Distinct article-shaped URLs captured under the domain that year (capped at 300).

    article-shaped = a /2019/-style date segment OR a run of 5+ digits (an article id).
    Date-only missed tdg.ch (/titre-123456789) and bluewin.ch (/titel-123456.html).

    collapse=urlkey is essential: CDX returns rows in URL-key order, so without it the
    hundreds of homepage captures fill the result window and articles never appear. It also
    makes the count mean "distinct URLs", which is the quantity we actually want.
    Only the regex braces are percent-encoded - encoding the slashes and pipes as well
    silently broke the filter and returned 0 for every domain.
    """
    filt = "original:.*(/(19|20)[0-9][0-9]/|[0-9]%7B5,%7D).*"
    url = (f"http://web.archive.org/cdx/search/cdx?url={domain}&matchType=domain"
           f"&from={year}0101&to={year}1231&limit=300&fl=original"
           f"&collapse=urlkey&filter={filt}")
    status, _, body = fetch(url, timeout=90)
    # A 504 or timeout is NOT zero articles - the same mistake section 13 warns about.
    # Only a clean 200 with an empty body means "no article-shaped URLs captured".
    if status != 200:
        return None
    return len([ln for ln in body.splitlines() if ln.strip()])


HEADER = ("outlet_id\tdomain\tyear\tbrand_type\tverdict\ttier\tartefact_url\t"
          "http_status\ttitle\tmatched_keyword\tarticle_urls\tshared_domain\tchecked_on\t"
          "human_checked\thuman_verdict\thuman_note\n")
# The last three columns belong to the human. The script writes them empty for a new row and
# never overwrites them on --retry (kept rows are written back field-for-field): a person puts
# an x in human_checked once they have looked, their decision in human_verdict, and why in
# human_note. That is the row-level audit trail.
RETRYABLE = {"?", "A3-arts?", "no-title", "no-page"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="seconds between rows; 0.6 got us throttled, 2.0 is the floor")
    ap.add_argument("--retry", action="store_true",
                    help="re-run only rows whose verdict is '?' or 'A3-arts?' in the existing "
                         "evidence file; keep every other row as it is")
    a = ap.parse_args()

    csv_path = Path(a.csv)
    rows = list(csv.DictReader(io.open(csv_path, encoding="utf-8")))
    m = re.search(r"outlets_dnr_(\w+)\.csv$", csv_path.name)
    tag = m.group(1) if m else csv_path.stem
    out_path = csv_path.with_name(f"domain_evidence_{tag}.tsv")

    # --retry: keep settled rows, redo only the ones Archive.org failed on. Failures are
    # transient load, not data - roughly 40% of raw id_ page fetches failed on the first Swiss
    # pass while the CDX queries beside them succeeded.
    keep = []
    if a.retry:
        if not out_path.exists():
            sys.exit(f"--retry needs an existing {out_path.name}")
        prev = list(csv.DictReader(io.open(out_path, encoding="utf-8"), delimiter="\t"))

        def retryable(r):
            # 'needs-human' with an EMPTY title is the 60 KB truncation artefact from the first
            # pass, not a real mismatch - redo it. needs-human with a title present is genuine.
            return r["verdict"] in RETRYABLE or (r["verdict"] == "needs-human" and not r["title"])

        keep = [r for r in prev if not retryable(r)]
        redo = {(r["outlet_id"], r["domain"], int(r["year"])) for r in prev if retryable(r)}
        print(f"--retry: keeping {len(keep)} settled rows, redoing {len(redo)}\n")

    # work units: one per (outlet_id, domain, year)
    units = {}
    brands_of = collections.defaultdict(set)
    outlets_on = collections.defaultdict(set)
    for r in rows:
        d = r["domain"].strip()
        if not d or r["brand_type"] == "category":
            continue
        key = (r["outlet_id"], d, int(r["year"]))
        units.setdefault(key, r["brand_type"])
        brands_of[r["outlet_id"]].add(r["brand"])
        outlets_on[d].add(r["outlet_id"])

    if a.retry:
        units = {k: v for k, v in units.items() if k in redo}

    today = dt.date.today().isoformat()
    out = io.open(out_path, "w", encoding="utf-8", newline="")
    out.write(HEADER)
    cols = HEADER.strip().split("\t")
    for r in keep:                                   # settled rows first, unchanged
        out.write("\t".join(r.get(c, "") for c in cols) + "\n")
    out.flush()

    total = len(units)
    print(f"{csv_path.name}: {total} outlet-domain-years -> {out_path.name}\n")
    tally = collections.Counter(r["verdict"] for r in keep)
    for i, ((oid, d, y), btype) in enumerate(sorted(units.items()), 1):
        kws = keywords(oid, brands_of[oid])
        status, url, title, text = masthead(d, y)
        hay_title, hay_text = norm(title), norm(text)
        hit = next((k for k in sorted(kws, key=len, reverse=True) if k in hay_title), "")
        if not hit:
            hit = next((k for k in sorted(kws, key=len, reverse=True) if k in hay_text), "")
            hit = f"(body) {hit}" if hit else ""
        arts = article_count(d, y)
        shared = "yes" if len(outlets_on[d]) > 1 else "no"

        if status is None:
            verdict, tier = "?", ""
        elif status != 200 or (not title and not text.strip()):
            # got a response but not a page: 403/500 from Wayback, or an empty body. Not a
            # mismatch - retry it.
            verdict, tier = "no-page", ""
        elif shared == "yes":
            verdict, tier = "shared", ("A3" if hit else "")
        elif hit and arts is None:
            verdict, tier = "A3-arts?", "A3"        # identity confirmed; article query failed
        elif hit and arts > 0:
            verdict, tier = "A3", "A3"
        elif hit:
            verdict, tier = "A3-noarticles", "A3"
        elif not title:
            # a page came back but carried no title at all - almost always a fetch that was cut
            # short, not evidence about the outlet. Retryable, and distinct from a real mismatch.
            verdict, tier = "no-title", ""
        else:
            verdict, tier = "needs-human", ""       # a title was found and it is not this outlet
        tally[verdict] += 1

        out.write("\t".join([oid, d, str(y), btype, verdict, tier, url, str(status or ""),
                             title.replace("\t", " ")[:120], hit,
                             "" if arts is None else str(arts), shared, today,
                             "", "", ""]) + "\n")            # human columns start empty
        out.flush()
        print(f"[{i}/{total}] {oid:<24} {d:<22} {y}  {verdict:<14} "
              f"kw={hit or '-':<20} arts={'?' if arts is None else arts}", flush=True)
        time.sleep(a.delay)
    out.close()

    print("\n=== SUMMARY ===")
    for k, v in sorted(tally.items()):
        print(f"  {k:<14}{v}")
    print(f"\nDONE -> {out_path}")
    print("Re-run rows marked '?'. Rows marked needs-human or shared go through the tier process "
          "in CLAUDE.md sections 16-17 by hand.")


if __name__ == "__main__":
    main()
