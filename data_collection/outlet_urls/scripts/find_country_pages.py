"""Locate a country's essay and chart pages in every DNR report PDF.

Country pages are templated, so this works for any country in any edition.

Returns, per report year:
  pdf_essay  - PDF page index of the country essay
  pdf_charts - PDF page index of the "Top brands" charts  <- the one you transcribe
  printed    - the folio printed on the chart page, which is what goes in `source`

pdf_charts and printed are NOT always equal (DNR 2026: PDF 120 = printed 117).

Why it does not simply search for the country name: on several editions (2019, 2021) the
chart page carries no country name at all - only a "112 / 113" spread marker - while the
essay page before it does. And matching the name alone puts DNR 2018 on page 106, which is
the essay; the charts are on 107.

Usage (from data_collection/outlet_urls/):
    python scripts/find_country_pages.py Switzerland
    python scripts/find_country_pages.py Germany --dir /path/to/dnr_pdfs

The default --dir resolves to ETH Media Pluralism/dnr_pdfs, i.e. one level above the git repo,
by walking up from this file's own location. If the script moves, update REPO_DEPTH.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

CHART_MARKERS = ("TV, RADIO AND PRINT", "TV, RADIO, AND PRINT",
                 "WEEKLY REACH", "TOP BRANDS", "ONLINE (")


def page_texts(pdf):
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True, errors="replace").stdout
    return txt.split("\f")


def chart_score(p):
    """How chart-like is this page? Marker hits plus rows that end in a small number."""
    up = p.upper()
    markers = sum(1 for m in CHART_MARKERS if m in up)
    bars = len(re.findall(r"[A-Za-z)à-ÿ]\s+\d{1,2}\s*$", p, re.M))
    return markers * 10 + bars


def printed_folio(p, country=""):
    """Read the folio printed on the page. Layouts vary, and in recent editions the running
    header extracts as mangled overlapping text, so match loosely on '| <Country> <n>'."""
    pats = [r"Digital News Report \d{4}\s*\|\s*[A-Za-z à-ÿ]+?\s+(\d{1,3})\b"]
    if country:
        pats.append(r"\|\s*" + re.escape(country) + r"\s+(\d{1,3})\b")
    pats += [r"^\s*(\d{1,3})\s*/\s*(\d{1,3})\s*$",
             r"^\s*(\d{1,3})\s+Reuters Institute"]
    for pat in pats:
        m = re.search(pat, p, re.M | re.I)
        if m:
            return m.groups()[-1]
    return ""


def find(pdf, country):
    ps = page_texts(pdf)
    name = re.compile(r"\b" + re.escape(country) + r"\b", re.I)

    # 1. candidate essay pages. A country PROFILE page always carries the statistics box
    #    ("Internet penetration") or prints the country name as a standalone heading.
    #    Requiring one of those is what stops the search landing on a comparative chart
    #    elsewhere in the report that merely mentions the country.
    #    The name must be in the page's TITLE AREA, not merely somewhere on the page -
    #    otherwise Austria's profile page, whose essay mentions Switzerland and which also
    #    carries a statistics box and charts, outscores the real one.
    upper = re.compile(r"^\s*" + re.escape(country.upper()) + r"\b", re.M)
    runhead = re.compile(r"Digital News Report\s+\d{4}\s*\|\s*" + re.escape(country),
                         re.I)
    essays = []
    for i, p in enumerate(ps, 1):
        if not name.search(p):
            continue
        titled = bool(upper.search(p)) or bool(runhead.search(p)) \
            or bool(name.search(p[:400]))
        if not titled:
            continue
        is_profile = bool(re.search(r"Internet\s+penetration", p, re.I))
        essays.append((i, 20 if is_profile else 10))
    if not essays:                      # fall back to any page naming the country
        essays = [(i, len(name.findall(p)))
                  for i, p in enumerate(ps, 1) if name.search(p)]
    if not essays:
        return None

    # 2. for each candidate, the charts are on that page or the next one.
    #
    #    Two guards, both learned the hard way:
    #    (a) ONE-PAGE PROFILES. Some editions (DNR 2020) put stats box, charts and essay on a
    #        single page. If the essay page itself has charts, that IS the chart page - do not
    #        look at i+1, which is the NEXT COUNTRY. Without this, Sweden 2020 resolved to
    #        page 84, which is Switzerland, and the documented safeguard ("confirm the page has
    #        charts") passes happily on the wrong country's charts.
    #    (b) Never accept an i+1 page whose title area announces a different country.
    #        A page belongs to ANOTHER country only if it looks like a country profile in its
    #        own right - a statistics box - while not naming ours. Matching bare uppercase
    #        headings is not enough: section titles like "WEEKLY REACH OFFLINE" look identical
    #        to a country heading and wrongly rejected the real chart pages for 2019 and 2021.
    def names_another_country(p):
        if not re.search(r"Internet\s+penetration", p, re.I):
            return False
        return not name.search(p)

    best = None
    for i, weight in essays:
        if i <= len(ps) and chart_score(ps[i - 1]) >= 20:
            cands = [i]                       # guard (a): one-page profile
        else:
            cands = [i + 1]
        for cand in cands:
            if cand > len(ps):
                continue
            s = chart_score(ps[cand - 1])
            if s < 20:
                continue
            if cand != i and names_another_country(ps[cand - 1]):
                continue                      # guard (b)
            total = s + weight
            if best is None or total > best[0]:
                best = (total, i, cand, printed_folio(ps[cand - 1], country))
    if not best:
        return None
    _, essay, charts, printed = best
    return essay, charts, printed


# this file lives at <repo>/data_collection/outlet_urls/scripts/; the PDFs live at
# <repo>/../dnr_pdfs. parents[0]=scripts, [1]=outlet_urls, [2]=data_collection, [3]=repo,
# [4]=the folder holding the repo.
REPO_DEPTH = 4
DEFAULT_PDF_DIR = Path(__file__).resolve().parents[REPO_DEPTH] / "dnr_pdfs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("country")
    ap.add_argument("--dir", default=str(DEFAULT_PDF_DIR))
    ap.add_argument("--from-year", type=int, default=2016)
    ap.add_argument("--to-year", type=int, default=2026)
    a = ap.parse_args()

    d = Path(a.dir)
    if not d.is_dir():
        sys.exit(f"no such directory: {d}\nPass --dir pointing at the folder holding dnrYYYY.pdf")

    print(f"{a.country}\n")
    print(f"{'report':<8}{'pdf essay':<11}{'pdf charts':<12}{'printed':<9}")
    for y in range(a.from_year, a.to_year + 1):
        pdf = d / f"dnr{y}.pdf"
        if not pdf.exists():
            print(f"{y:<8}-- pdf missing --")
            continue
        r = find(pdf, a.country)
        if not r:
            print(f"{y:<8}-- not found; check the country's spelling in that edition --")
            continue
        essay, charts, printed = r
        print(f"{y:<8}{essay:<11}{charts:<12}{printed or '?':<9}")
    print("\nOpen the chart page and confirm it has charts before transcribing.")
    print("If `printed` shows ?, read the folio off the page corner yourself.")


if __name__ == "__main__":
    main()
