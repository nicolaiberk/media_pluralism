# Building `outlets_dnr_<country>.csv` — end to end

Operating instructions for an agent collecting the outlet registry for **any** country. Every
trap below was hit for real — on Switzerland 2016–2026, and on a Sweden run done from this
document alone. None of it is anticipated.

Authority: **Berk's `RA_instructions_outlets.md` wins**, then this file, then judgement.
Columns marked *added* were agreed with him beyond that spec.

**Scope: 2016 onward.** CC-NEWS begins September 2016 and Berk ruled out pre-2016 backfill.
This matters more than it looks — §14c explains why the best domain-discovery tool stops
working at exactly 2016.

---

## 0. Runbook

```
1.  Ensure the 11 PDFs are present               → §1
2.  Locate the country's pages in each report    → §2    scripts/find_country_pages.py
3.  Read the essay, capture year-level facts     → §3, §4
4.  Render, crop, transcribe the charts          → §5–§8
5.  Classify brand_type, assign outlet_id        → §9, §10
6.  Write notes                                  → §11
7.  Validate structure                           → §12   scripts/validate_outlets.py
8a. Domains — liveness, every domain-year        → §13   scripts/wayback_liveness.py
8b. Domains — identity + article-bearing, every  → §15–16 scripts/wayback_identity.py
    domain-year                                            (mandatory, not optional)
8c. Domains — hand the needs-human / shared      → §16–17 tier process, human confirms
    rows to the user with proposed verdicts
8d. Common Crawl acceptance                      → §18   (open question 11)
9.  Record evidence, re-validate                 → §19
10. Branch, commit, pull request                 → collaboration_guide.md
```

**A domain is not verified until 8a and 8b have both run for it.** Liveness alone proves a
host existed; it says nothing about whose host it was or whether it carried articles. Every
domain-year needs all three signals — that is the triangulation Part B is built around.

**Timing.** Berk's estimate for manual work is 45–60 min per country-year page. An agent doing
all eleven years takes roughly 1½–2 hours for Part A, plus 30+ minutes for the Part B liveness
sweep, which is bound by Archive.org's rate limit rather than by thinking.

**Layout of this folder.** Run every command below from `data_collection/outlet_urls/`.

```
data_collection/
  documentation-and-issues/        for humans: PROCESS_OVERVIEW.md (how it all works),
                                   WORKING_MANUAL.md (what a person does), OPEN_QUESTIONS.md
                                   (Berk's decisions), Failure_Modes_Register.docx (open risks),
                                   Fixed_Issues.docx (the record)
outlet_urls/
  CLAUDE.md                        this file
  RA_instructions_outlets.md       Berk's spec — the authority
  outlets_dnr_<country>.csv        one data file per country: the 18 agreed columns plus
                                   human_checked (see below)
  wb_years_<country>.tsv           liveness evidence, one row per domain-year      (8a)
                                   columns: domain, year, live, used_in_csv, first_capture
  domain_evidence_<country>.tsv    identity + article-bearing evidence, per domain-year (8b);
                                   ends in human_checked, human_verdict, human_note
  scripts/
    find_country_pages.py          §2   locate a country's pages in every report
    validate_outlets.py            §12  structural checks on a data file
    wayback_liveness.py            §13  liveness sweep
    wayback_identity.py            §15–16  masthead (A3) + article-shape check
    dnr_fetch.py                   host-restricted GET; the only network tool the
                                        permission allowlist grants
```

**Human-review columns.** Both data files carry columns that belong to the person, not the
agent. In the CSV, `human_checked` — an `x` once someone has read that row against the printed
page. In the evidence file, `human_checked`, `human_verdict`, `human_note` — the person's
decision on a row the script could not settle, and why. **The agent never writes to these**, and
every script that rewrites a file carries them through unchanged. They are the row-level audit
trail; a row with an `x` has been looked at by a human, and one without has not.

**One file per country**, named `outlets_dnr_<country>.csv` with the country in lowercase
English. Berk's `RA_instructions_outlets.md` names a single `outlets_dnr.csv`; it predates the
multi-country split. Concatenate at analysis time; the `country` column carries the join.

---

# Part A — Transcription

## 1. Source PDFs

Not in the repo (~165 MB). They live at `ETH Media Pluralism/dnr_pdfs/`, one level above the
repo root; `dnr_pdfs/urls.txt` re-downloads all eleven:

```bash
cd dnr_pdfs && while read -r y u; do curl -sL -o "dnr$y.pdf" "$u"; done < urls.txt
```

URLs verified 12 September 2026. Reuters has changed the URL pattern several times — expect rot
and re-derive from the report landing pages if a fetch 404s.

## 2. Locating the country's pages

```bash
python scripts/find_country_pages.py Sweden
python scripts/find_country_pages.py Germany --dir /path/to/dnr_pdfs
```

Prints, per report year, the **PDF page** of the essay, the **PDF page** of the charts, and the
**printed folio** (what goes in `source`). Verified against Switzerland, Sweden and Germany,
all eleven years each.

Four traps it handles, every one of which produced a wrong answer during development:

- On some editions (2019, 2021) the chart page **carries no country name at all** — only a
  `112 / 113` spread marker. The name is on the essay page before it.
- Matching the name anywhere on a page lands on **another country's** profile, whose essay
  mentions yours and which also has a statistics box and charts. The name must be in the title area.
- The essay page matches every chart marker too. DNR 2018 Switzerland resolves to 106, the
  essay; the charts are on **107**.
- **One-page profiles.** DNR 2020 puts stats box, charts and essay on a single page, so a
  "charts are on page *i* or *i+1*" rule hands you **the next country**. Sweden 2020 resolved to
  page 84 — which is Switzerland.

> **Confirm the chart page names your country**, via its heading or its statistics box. Merely
> confirming that the page *has charts* is not enough: the wrong country's page has charts too,
> and everything downstream — bar counts, monotonic reach, the validator — passes on it. This is
> the only failure mode that yields a complete, self-consistent dataset for the wrong country.

Where `printed` comes back `?` (2016 and 2020 use `50 / 51` spread markers), read the folio off
the page corner yourself.

## 3. Year-level facts

| Fact | Where | Notes |
|---|---|---|
| Fieldwork dates | Methodology, **PDF page 5** (sometimes 6) | Prose, so extracted text is safe |
| Sample size | Market table, **PDF page 6** — position varies | **Verify visually**, see §6 |
| Representativity | Methodology bullets, same pages | Copy any caveat **verbatim into `notes`** |

The table is on page 6 in every edition, but not always in the same part of it:

```bash
pdftoppm -r 200 -f 6 -l 6 -png -x 0 -y 1380 -W 1654 -H 780 dnr2025.pdf tbl   # lower half
```

- **2018–2025** — lower half, as above.
- **2026** — **upper** half; the lower half is author biographies.
- **2017** — two columns with ISO codes, countries higher up. Crop `-x 820 -y 850 -W 834 -H 600`.
- **2016** — two-column layout with full population counts; render the whole page.

If the crop shows no market table, **render the full page before concluding anything.** Never
fall back to extracted text — that is the source known to return the adjacent country's row.

**Cheap self-check:** every country sits in the same table, so verify your crop by reading
Switzerland's sample against Appendix A. If that matches, your crop and your reading are sound.

**Record only the precision the report gives.** "End of January/beginning of February" becomes
`YYYY-01` and `YYYY-02`. Never invent day precision. Every edition 2016–2026 used that phrasing
or "middle of January to the end of February", so month precision is always correct.

`sample_type` is `national` unless the report flags the market urban- or online-representative
only (Turkey is the standing example). Check the country's own asterisk — DNR 2018's
desktop-only caveat applies to a **named list of countries**, not to everyone.

## 4. Read the essay first

Three minutes on the country essay before touching charts. It is the **only** source for
rebrands, closures and ownership changes, which belong in `notes` — it told us nau.ch launched
in late 2017 and 20 Minuten went digital-only in late 2025. It usually names the author and
their institution, your Tier B source for that country (§20).

## 5. Chart layout — what varies

**Number of charts.** A country with language submarkets (Switzerland, Belgium, Canada) has
**four**: offline and online × each submarket. A single-market country (Germany, Sweden) has
**two**, side by side in one band.

**`submarket`:** multi-market countries use their market names (`german-speaking`,
`french-speaking`); single-market countries write **`single-market`** on every row. Never leave
it empty and never invent another placeholder — one convention everywhere, so the column groups
and joins cleanly once ~26 country files are concatenated.

**Brands per list varies by country and by year, and the two lists in a year need not match.**
Switzerland: 8 (2016), 10 (2017), 12 (2018+). Germany 2026: 16. Sweden 2023: 15 offline but 16
online; 2025 and 2026: 14 offline, 16 online. **Count each chart separately**, before and after.

**Chart order flips.** For Switzerland the German pair is on top 2016–2022; from 2023 it
reverses. Read the chart heading — but see the next point.

**Chart headings are not always present.** DNR 2020's single-market pages have **no chart
headings at all**, just two colour-coded columns and a legend. Where a heading exists, use it;
where none does, take `list_type` from the legend's colour coding and record that you did so in
`notes`.

**Bar series.** Some editions draw two series per bar:

| Edition | Series | Which number is printed |
|---|---|---|
| 2016 | weekly use + *main source* | weekly use |
| 2017–2025 | weekly use + *more than 3 days per week* | weekly use |
| 2026 | weekly use only (solid bars) | weekly use |

**Read the legend on the page rather than trusting this table** — the boundary was wrong here
once already. In every case the number printed **at the end of the full bar** is the weekly
reach figure the RA instructions ask for. Never read the inner segment: it also descends down
the chart, so a mis-read passes every structural check.

**The "ALSO" box.** DNR 2018–2020 print a boxed list of alternative/partisan brands with
weekly-reach percentages beside the ONLINE chart — for Sweden: Fria Tider, Nyheter Idag,
Samhällsnytt, Ledarsidorna, Samtiden, Nya Tider, Det Goda Samhället. They are not bars, and
their values do **not** continue the chart's descending order, so appending them breaks the
validator's monotonicity check. From 2021 the same titles appear as ordinary bars. These are
exactly the ideologically distinctive outlets a pluralism measure needs, so excluding them
leaves a visible hole. **Currently excluded; values captured in the run report.** Open question 9 in `OPEN_QUESTIONS.md`.

## 6. Never trust extracted text

**`pdftotext` silently corrupts this data.** Two distinct failures, both observed repeatedly:

1. **Chart labels separate from their values.** On DNR 2026's German online chart the numbers
   drifted off their brands and `GMX` lost its value entirely. Adjacent values also glue into
   one token (`1565` for 15 and 65). Layouts from ~2022 are worst; 2016-era ones extract cleanly.
2. **Table columns shift by a row.** Extracted text gave the wrong sample size in three of
   eleven Swiss years (2018, 2025, 2026) and two Swedish ones (2025, 2026), each time picking up
   the adjacent country's row. Swiss 2026 came out as 2,052 — that is Sweden's. The truth is
   2,051. The tell was a population of 10.7m for a country of 9m.

**Transcribe from the rendered page image.** Use extracted text as an independent second opinion.

**When they disagree, re-render at higher dpi and look again — do not simply assume the image
read was right.** DNR 2021 prints "Helsings**b**orgs Dagblad", a typo in the report; a 300 dpi
crop read as "Helsingborgs" and only the extraction's disagreement prompted a 400 dpi re-render
where the extra *s* is plain. The extraction was right and the eye was wrong.

Sanity-check every number from a table against something you already know.

## 7. Rendering and cropping

A whole page at once is too small to read bar values. Render at 300 dpi and crop to one chart
block. `-x -y -W -H` are pixels at the chosen dpi; A4 at 300 dpi is **2482 × 3508**.

```bash
pdftoppm -r 300 -f <page> -l <page> -png -x 620 -y 150 -W 1880 -H 560 dnr2025.pdf out
```

> **Bands are starting points, not settled geometry, and they do not transfer between
> countries.** The table below is Switzerland's four-chart layout. A single-market country has a
> different geometry entirely, and an independent Sweden run needed custom bands for every year.
> Even within Switzerland, 2016, 2017, 2019, 2020 and 2021 needed adjustment.
>
> **Always: render the full page first, count the bars, then crop, then compare row counts.**
> If a chart looks clipped at the bottom, it is — re-crop; never guess the missing rows.

Switzerland (four charts):

| Edition | Upper pair | Lower pair |
|---|---|---|
| 2025–2026 | `-x 620 -y 150 -W 1880 -H 560` | `-x 620 -y 710 -W 1880 -H 600` |
| 2023–2024 | `-x 500 -y 120 -W 2000 -H 620` | `-x 500 -y 720 -W 2000 -H 640` |
| 2022 | `-x 500 -y 120 -W 2000 -H 620` | `-x 500 -y 780 -W 2000 -H 700` |
| 2021 | `-x 0 -y 150 -W 2482 -H 800` | `-x 600 -y 800 -W 1900 -H 620` |
| 2020 | `-x 0 -y 200 -W 2482 -H 780` | `-x 0 -y 950 -W 2482 -H 780` (+ tail `-x 700 -y 1380 -W 1700 -H 420`) |
| 2019 | `-x 0 -y 200 -W 2482 -H 800` | `-x 0 -y 980 -W 2482 -H 800` |
| 2017–2018 | `-x 0 -y 180 -W 2482 -H 820` | `-x 0 -y 980 -W 2482 -H 820` |
| 2016 | `-x 0 -y 300 -W 2482 -H 580` | `-x 0 -y 820 -W 2482 -H 680` |

Sweden (two charts, one band) — included to show how far single-market geometry differs:

| Edition | Band |
|---|---|
| 2026 | `-x 500 -y 150 -W 2000 -H 800` **plus** `-x 600 -y 600 -W 2000 -H 500` for the tail |
| 2021–2025 | `-x 700 -y 165 -W 1600 -H 800` |
| 2020 | `-x 700 -y 500 -W 1400 -H 800` — one-page profile, band starts far down |
| 2017–2019 | `-x 700 -y 170..200 -W 1800 -H 800` |
| 2016 | `-x 500 -y 180 -W 2000 -H 800` |

## 8. Transcription

Work **top to bottom, in printed order, one chart at a time. Take every bar** — not the top ten,
not the ones you recognise. Filtering happens downstream; your job is completeness.

Record the brand **exactly as printed**: accents, parentheticals, stray spaces and typos. DNR
2025 prints "French commerical TV news"; DNR 2016 prints "Le Journa"; DNR 2017 prints
"Le Matin ( incl Sunday Edition)" with the space inside the bracket. All stay. Join downstream
on `outlet_id`, never on `brand`.

**Do not carry a label across years.** The single transcription error found by an independent
re-read was DNR 2016's `Blick (inc. evening and Sunday editions)` written into the 2017 rows,
where the page actually prints `Blick (incl. evening and Sunday)`. It maps to the right
`outlet_id`, so nothing structural catches it.

Reach descends down a chart — a value that rises means you misread a bar.

Write rows in page order so a human can check straight down the page.

## 9. `brand_type`

*Can this be fetched from Common Crawl, and if so, whose editorial voice is it?*

| Value | Fetchable | Voice | Examples |
|---|---|---|---|
| `outlet` | yes | its own, domestic | `NZZ online`, `Le Temps`, `nau.ch` |
| `category` | **no — no domain exists** | n/a | `Other regional or local newspapers`, `Commercial radio news` |
| `aggregator` | yes | **other outlets'** | `Blue News`, `GMX`, `Yahoo! News`, `Teletext online` |
| `foreign` | yes | its own, not domestic | `CNN`, `BBC News` |

`is_aggregator` is `TRUE` exactly when `brand_type == aggregator`; the validator enforces it.

**`category` covers any aggregate survey label, not only newspapers** — 8 of 10 category rows in
Swiss 2026 were TV or radio. Tells: starts with "Other", "A regional", "Websites of a"; contains
"e.g."; names a medium rather than a brand. Keep the reach figure, assign a `cat_` id, **no
domain**. Never delete them: their reach is real audience mass the weighting needs.

**`aggregator` vs `outlet`** — is there a newsroom behind the domain? Read bylines (national
agency, Reuters, AFP, dpa credits mean republishing); check the imprint (a newsroom lists an
editor-in-chief, a portal lists a parent company and an ad contact); ask whether news is the
business or an add-on to email/telecom/search; follow `rel=canonical`. For historical years run
these **through the Wayback Machine at that year**.

**`foreign`** — is there a newsroom producing news for this country's audience? Ownership abroad
does not make an outlet foreign. **The TLD proves nothing**: `GMX` sits on `gmx.ch` and is
German with no Swiss newsroom.

**Overlaps:**
- *foreign × aggregator* (`Yahoo! News`) → **`aggregator`**. Contaminating the corpus is worse
  than being out of scope.
- *foreign × category* — labels like "Broadcasters/papers from outside Sweden", "Media from
  outside country" → **`category`**. No domain exists, and that dominates; the validator enforces
  category ⇒ no domain. Use ids like `cat_foreign_media` / `cat_foreign_media_online`.

**Category and foreign rows are kept**, never dropped.

## 10. `outlet_id`

`<iso3>_<shortname>`, lowercase, no spaces or punctuation. Foreign outlets take **their own**
country prefix (`usa_cnn`, `gbr_bbc`, `deu_gmx`) so they are shared across national registries.
Categories take `cat_`.

**An ID never changes once assigned, even when the brand renames.** `Bluewin news` (2016) and
`Blue News` (2026) are both `che_bluenews`. `brand` holds the printed name; `outlet_id` holds
the identity.

**A one-year rendering variant is not a new outlet.** DNR 2018 prints "Tv4.se" and "Sr.se" where
every other year prints the brand — same `swe_tv4`, `swe_sr`. Split only when the source treats
them as genuinely distinct titles with separate reach figures, as DNR 2017 did by listing
`Blick and Blick am Abend online` and `Blick am Abend online` as two bars.

Before inventing an ID, grep the file. The Swiss registry is in **Appendix A**.

## 11. `notes`

Per the RA instructions: *anything odd — representativity issues, rebrands, domain changes,
regional editions*. Plus, from Berk: sample caveats **verbatim**, and approximate domain-change
timing in prose.

Test: *would a stranger reading this row in three years be confused without it?*

**Year-level facts repeated on every row of that year are correct** — that is what `sample_size`
and `fieldwork_*` already do. **A country-level fact on one arbitrarily chosen row is not.** If
it does not belong on every row of its group, report it to the user instead of putting it in the
CSV.

**Notes must be time-consistent.** A note written from looking at a site *today* silently
applies to every year of that outlet's rows. The SonntagsZeitung note says `sonntagszeitung.ch`
"serves an e-paper portal only" — true in 2026, false earlier, where the anchor index shows
73,106 archived pages. Any present-tense claim about site structure (*serves*, *redirects to*,
*is a portal*) needs a **year qualifier**, or must be split per era.

## 12. Validation

```bash
python scripts/validate_outlets.py               # defaults to outlets_dnr_switzerland.csv
python scripts/validate_outlets.py outlets_dnr_sweden.csv
```

Checks header, descending reach within each chart, category-rows-have-no-domain,
`brand_type`/`is_aggregator` agreement, bare domains, `outlet_id` collisions, encoding damage,
and chart coverage. Coverage derives countries and submarkets **from the data** — it must never
hardcode a country's submarkets, which once made it fail for every non-Swiss file.

**It validates structure, not truth.** It cannot know whether `Blick 19` is what the page says.
Always also count bars against rows, and re-read the page against the rows once.

CSV mechanics: UTF-8 **without BOM**; quote any field containing a comma; never reorder or
rename the first ten columns. `human_checked` is the last column and is the human's — leave it.

---

# Part B — Domain verification

**The question:** was domain `D` the place outlet `O`'s articles were published in year `Y`?

That is one question with three independent parts, and **all three must hold for every
domain-year** before the domain counts as verified. Conflating them, or checking only the
first, is what made the first pass weak:

| Signal | Test | How | Section |
|---|---|---|---|
| **Liveness** | Did `D` serve content in `Y`? | `wayback_liveness.py`, per domain-year | §13 |
| **Article-bearing** | Did articles live at `D`, or was it a portal / e-paper / redirect? | `wayback_identity.py`, article-shape count | §15 |
| **Identity** | Was `D` branded as `O` in `Y`? | `wayback_identity.py`, masthead (A3) — plus A1/A2 by hand where it fails | §16 |

**Triangulation, not a checklist.** Each signal fails in a way the others catch:

- A host can be live and branded as the outlet yet carry no articles — an e-paper portal
  (`sonntagszeitung.ch` today), a landing page, a redirect (`bluenews.ch` every year).
- A host can be live and full of articles yet belong to someone else — `20minuten.ch` is not
  where 20 Minuten publishes; `blickamabend.ch` outlived the paper by years.
- A host can be branded and article-bearing in 2024 and something else entirely in 2017.

A domain-year with all three signals is verified with a documentary artefact behind each one.
A domain-year missing any signal goes to the user as `needs-human` or `shared` with the
evidence attached (§19) — never silently recorded as verified.

Then one acceptance test against the system the data feeds (§18).

**Live resolution today proves nothing about any earlier year.** Common Crawl indexes by the URL
**as crawled at the time**, so a 2017 row must hold the 2017 domain. In `CC-MAIN-2017-13`,
`blickamabend.ch` has 400+ captures and `blick.ch` has 17 — pointing 2017 at today's domain
retrieves essentially nothing.

**One domain can carry several outlets.** `20 Minuten` and `20 Minutes` share `20min.ch`;
`SonntagsBlick` resolves to `blick.ch`. Since the pipeline fetches by domain, those outlets are
indistinguishable at fetch time and their corpora merge unless something downstream splits by
path or language. Flag every such case (open question 10).

## 13. Stage 1 — Liveness sweep

One query per (domain, year). Never batch years.

```
http://web.archive.org/cdx/search/cdx?url=D&matchType=domain
  &from=Y0101&to=Y1231&limit=1&fl=timestamp,original,statuscode
```

- **2xx and 3xx both count as live.** A redirect is a live host.
- **Never use `collapse=timestamp:N` with a row limit.** Collapse merges only *adjacent* rows and
  results group by URL variant, so a limit truncates mid-group and invents gaps. This produced a
  confident report that `blick.ch` was unarchived in five years.
- **A timeout is not a negative.** Keep `?` distinct from `NO` and retry. Ten of the first 279
  Swiss checks were timeouts; all ten were live on retry.
- **`matchType` changes the answer.** `domain` times out on very large hosts; retry with `exact`.
  `host` can return 0 where `exact` returns captures — never read that as a gap.
- **Large foreign hosts dominate the runtime.** `bbc.co.uk`, `cnn.com`, `buzzfeed.com`,
  `huffpost.com` and `yahoo.com` take 20–25s each under `matchType=domain` and consumed most of
  the Sweden sweep. Use `exact` for them, and **cache foreign-domain liveness across countries** —
  the answer does not change per country, and these hosts appear in every country's list.
- **Record capture counts, not just yes/no.** Wayback archives small outlets far more thinly, so
  "no captures in year Y" is ambiguous between *did not exist* and *was not crawled*.
- Archive.org goes down for hours, and rate-limits to roughly 4–11 queries a minute under load.
  Budget for it; never record an outage as data.

**Output columns:** `domain, year, live, used_in_csv, first_capture`. `first_capture` is the
raw CDX hit — timestamp, URL, status — the artefact that proves liveness. A bare yes/no
records no evidence; the status code is also a free redirect signal (§15). This column was
added by the Sweden run, which had re-implemented the sweep and kept the artefact; the
Swiss file predates it and lacks the column until re-run.

Results so far: Switzerland 279 checks / 31 domains / zero gaps; Sweden 246 checks / 29 domains /
zero gaps.

## 14. Stage 2 — Discovery: find the historical domain

**Do not start by guessing domain names.**

**14a. Trigger — free, from our own data.** Whenever one `outlet_id` maps to a *different*
`brand` string in a new year, that is a rebrand signal. `Bluewin news` → `Blue News` is visible
in the registry without touching the web.

**14b. Discontinuity — also free.** If the recorded domain's Wayback or Common Crawl captures
begin later than the brand first appears, something else published the earlier years.

**14c. Name search — Wayback anchor index.**

```
https://web.archive.org/__wb/search/anchor?q=<brand+name>
```

Returns hosts with `name`, `first_captured`, `last_captured`, `webpage` (page count) and
`snippet`. Rank by page count. Query the brand **exactly as the DNR printed it that year**, in
the market's language.

> **Hard limitation: this index stops at 2016.** Every result caps at `last_captured: 2016`.
> Since scope is 2016 onward it helps only at the very start of the range and **cannot** resolve
> later rebrands. Do not build a workflow that depends on it.

**14d. Post-2016 fallbacks**, in order:
1. **DNR country essays** — they document rebrands and closures, and you have already read them.
2. **The national media-research institute** (§20).
3. **Wikidata** — `Special:EntityData/<QID>.json`, `P856` (official website), `P127` (owned by).
   **Tested: usually carries no `P580`/`P582` date qualifiers**, so it is a candidate-and-ownership
   pointer, *not* a dated history source. Do not cite it as one.
4. **Outbound links** in the successor domain's archived pages.
5. **Web search** — to *locate a primary source*, never as the source.
6. **Name guessing** — last resort, Tier C only.

## 15. Stage 3 — Article-bearing test

Run **independently of identity**, for every domain-year. A domain can be unambiguously the
outlet's and still not be where articles live.

```bash
python scripts/wayback_identity.py outlets_dnr_<country>.csv    # does §15 and §16 together
```

- **CDX URL shape** (any year) — what the script does: count **distinct** captured URLs under
  the domain that year whose path looks like an article: a `/2019/`-style date segment **or** a
  run of five or more digits (an article id — `tdg.ch/titre-123456789`, `bluewin.ch/titel-123456.html`).
  ```
  ...cdx?url=D&matchType=domain&from=Y0101&to=Y1231&limit=300&fl=original
     &collapse=urlkey&filter=original:.*(/(19|20)[0-9][0-9]/|[0-9]%7B5,%7D).*
  ```
  Three things in that query were each learned by getting them wrong:
  - **`collapse=urlkey` is essential.** CDX returns rows in URL-key order, so the hundreds of
    homepage captures fill any result window and the articles never appear. With it, the count
    means *distinct URLs* — the quantity actually wanted.
  - **Encode only the regex braces.** Percent-encoding the slashes and pipes too silently
    broke the filter and returned 0 for every domain.
  - **A 504 is not zero articles.** Archive.org returns 504 on heavy domains (`tdg.ch`). Only a
    clean 200 with an empty body means none were captured; anything else is `?`, re-run it.
- **Page count** (anchor search, ≤2016 only): thousands ⇒ publishing; dozens ⇒ vestigial, parked
  or redirect. `20min.ch` 1,522,669 vs `20minuten.ch` 45 settles that pair with no judgement.
- **Status codes — check the scheme first.** A domain whose captures are all 301 *may* be a pure
  redirect, but the commonest 301 is the ordinary http→https hop. `http://samnytt.se/` is 301
  every year while `https://samnytt.se/` returns 200 with dated article paths. Compare http and
  https separately before calling anything a redirect domain.
- **Archived homepage**: headlines with datelines.

Fails ⇒ locate the real article home (rule 3), else blank the domain and explain (rule 5).

**A domain existing proves nothing.** `20minuten.ch` is live all eleven years and is not the
publishing domain. `blickamabend.ch` is live all eleven years including after the paper folded in
2018. Existence is a candidate generator, nothing more.

## 16. Stage 4 — Identity, tiered

**Tier A — documentary, self-proving. One item suffices.**

- **A1 Imprint.** Archived imprint on `D` in `Y` naming `O` or its publisher. Legally mandatory
  in CH/DE/AT and (as *ansvarig utgivare*) in Sweden, which makes it the strongest single artefact.
  ```
  https://web.archive.org/web/{ts}/https://www.D/impressum
  ```
  **The path varies by site and country** (§20). `20min.ch/impressum` works; `blick.ch/impressum`
  has no captures. Try the country's variants, or find the link on the archived homepage.
  Absence of one path is not absence of an imprint.
- **A2 Redirect.** A capture of `D` in `Y` returning 301/302 to a domain already confirmed for `O`.
  ```bash
  ts=$(curl -s "http://web.archive.org/cdx/search/cdx?url=D&matchType=exact\
&from=Y0101&to=Y1231&limit=1&fl=timestamp")
  curl -sI "https://web.archive.org/web/${ts}id_/http://D/"
  ```
  `id_` returns the capture unmodified. **Wayback rewrites the `location` header** to
  `https://web.archive.org/web/{ts}id_/<real target>` — strip that prefix. Upstream headers
  survive as `x-archive-orig-*`.
  Sufficient alone **only when the target is already confirmed for `O`**; otherwise a domain sale
  is indistinguishable from a rebrand, so treat as Tier B.
- **A3 Masthead.** Archived homepage nearest mid-year whose `<title>` or masthead carries `O`'s
  name. **Automated by `wayback_identity.py`** for every domain-year: it fetches
  `https://web.archive.org/web/{Y}0701000000id_/http://D/`, reads the `<title>` (falling back
  to visible text), and matches the outlet's id shortname or any distinctive brand token. A hit
  is a per-year documentary artefact; the URL is recorded so a human can open it.
  What it establishes: *that host presented itself as `O` in `Y`*. What it does not: whether a
  change of host was a rebrand or a domain sale — that is A2, still by hand.

**Which of these the script does, and which stay manual.** A3 and the §15 article count run
unattended for every domain-year. A1 (imprint) and A2 (redirect) are applied by hand to the
rows the script returns as `needs-human` or `shared`. The script's job is to shrink the human
work to the cases that genuinely need judgement — for Switzerland, a handful of outlets out of
forty — not to make the call.

**Tier B — corroborating. Two independent items required.**

B1 DNR country essay · B2 national media-research institute · B3 contemporary trade reporting or
the outlet's own announcement · B4 Wikidata/Wikipedia **with the citation followed** ·
B5 successor domain's archived pages linking to `D`.

**Tier C — never sufficient, alone or stacked.** Name resemblance · the domain existed · it looks
like a news site.

## 17. Stage 5 — Decision rule

```
identity confirmed (Tier A, or 2 × Tier B)  AND  article-bearing
    → record D for that year; set domain_valid_from / domain_valid_to

identity confirmed, NOT article-bearing
    → locate the article home; else blank + note (rule 5)

identity NOT confirmed
    → blank + note the candidate and why it was rejected
    → keep outlet_ids SEPARATE
```

**Prefer the reversible error.** Two IDs that should be one is a one-line fix later. One ID that
should be two is a contaminated corpus nobody can unpick — the outlet's measured position
silently becomes a blend of two newsrooms, and nothing downstream flags it.

## 18. Stage 6 — Acceptance test against Common Crawl

The criterion that actually matters. Wayback is a proxy; this is the target system.

```
https://index.commoncrawl.org/collinfo.json          # 127 crawls, 2008 → present
https://index.commoncrawl.org/<CRAWL-ID>-index?url=D/*&output=json&limit=1000
```

Record captures per outlet-year. Caveats: `CC-MAIN` coverage is uneven per domain, and from 2016
the project's real source is **CC-NEWS**, a separate dataset — treat counts as directional. The
output doubles as milestone 4 coverage evidence.

## 19. Recording, and validator additions still to build

CSV schema stays frozen. Evidence lives alongside, one row per **domain-year**:

- **`wb_years_<country>.tsv`** — liveness (§13). Written by `wayback_liveness.py`.
- **`domain_evidence_<country>.tsv`** — identity + article-bearing (§15–16). Written by
  `wayback_identity.py`, one row per (outlet_id, domain, year), with the verdict, the tier, the
  artefact URL, the matched title, the article count, and whether the domain is shared. Verdicts:

  | verdict | meaning | who acts |
  |---|---|---|
  | `A3` | masthead matched, articles present | nobody — verified |
  | `A3-noarticles` | branded as the outlet but no article-shaped URLs — portal / e-paper? | human, rule 3 |
  | `A3-arts?` | masthead matched, article query failed | re-run |
  | `needs-human` | masthead did not match | human, §16–17 by hand |
  | `shared` | domain carries several outlet_ids — confirms the domain, not whose articles | human, always |
  | `?` | fetch failed | re-run |

  The last three columns — `human_checked`, `human_verdict`, `human_note` — are the human's.
  The script writes them empty and carries them through unchanged on `--retry`. A person puts
  an `x`, a decision, and a reason there for every row they look at. The agent never fills them.
- **`domain_research/<outlet_id>.md`** — dossier for contested cases: candidates tried,
  artefacts, reasoning, rejections.
- **CSV `notes`** — one-line verdict and tier.

Not yet implemented: every non-empty domain has a liveness record for its year; any `outlet_id`
with more than one domain has non-overlapping `domain_valid_from`/`_to`; every `UNVERIFIED` note
has a dossier; every domain change has a Tier A or 2×Tier B record.

## 20. Country parameters

| Parameter | Switzerland | Sweden | Deriving it elsewhere |
|---|---|---|---|
| Imprint path | `/impressum`, `/ueber-uns`, `/kontakt` | `/om-oss`, `/kontakt`, `/redaktionen`, `/ansvarig-utgivare` | `mentions légales` (FR), `colofon` (NL), `about us` (EN), `chi siamo` (IT) |
| Tier B institute | foeg / UZH, *Jahrbuch Qualität der Medien* | Oscar Westlund — Gothenburg, later OsloMet | The DNR country essay's byline |
| Brand language | DE / FR | SV | The language the DNR printed |
| Submarkets | german-speaking, french-speaking | none (leave empty) | Check the chart headings |

**The byline rule is not self-maintaining.** DNR 2020 replaced signed country essays with
unsigned blurbs, so that edition names no author for any country. Where a byline is absent, take
the institution from an adjacent year for the same country.

## 21. Automation boundary and stopping rule

**Unattended:** liveness, anchor search, page counts, URL-shape probes, redirect detection,
fetching archived homepages and imprints, CC index queries, drafting dossiers with a proposed
verdict and tier.

**Never decided alone:** whether an imprint names "the same outlet"; whether a change is a
rebrand, an acquisition or a domain sale; whether two titles are one outlet. Bring the artefacts
and a proposed verdict to the user; they confirm before it is written as fact.

**Stopping rule: twenty minutes per case.** If Tier A and Tier B have not resolved it, the answer
is blank + note — a legitimate outcome. Berk was explicit about not sinking time here. *Pilot
exception:* Switzerland sets conventions for ~25 further countries.

**Decisions that are Berk's, not the agent's,** live in
`../documentation-and-issues/OPEN_QUESTIONS.md`. Where a rule above says "(open question N)",
the current behaviour is what the instruction states; apply it as written and do not re-decide it.

Live risks are in `../documentation-and-issues/Failure_Modes_Register.docx`; defects that have
been fixed are in `Fixed_Issues.docx` beside it, same IDs. Add an entry whenever something is found
wrong or a step turns out to rest on an assumption; move it to the fixed file when it is fixed,
never delete it. Several fixed entries describe results that looked entirely credible and were not.

---

# Appendix A — Switzerland reference data

Verified against rendered pages, and confirmed by an independent blind re-transcription
(13 Sep 2026) that matched all 504 reach values and all 11 sample sizes. Use to check a re-run,
not to skip one.

**Page index** (PDF page of charts / printed folio): 2016 61/61 · 2017 97/97 · 2018 107/107 ·
2019 113/113 · 2020 84/84 · 2021 107/107 · 2022 107/107 · 2023 103/103 · 2024 109/109 ·
2025 113/113 · 2026 **120/117**.

**Sample sizes:** 2016 2,004 · 2017 2,005 · 2018 2,120 · 2019 2,003 · 2020 2,012 · 2021 2,000 ·
2022 2,004 · 2023 2,037 · 2024 2,012 · 2025 2,023 · 2026 2,051.

**Fieldwork:** every year `YYYY-01` to `YYYY-02`.

**Chart order:** German pair on top 2016–2022; French pair on top 2023–2026.

**Coverage limit:** the DNR publishes Swiss lists for the German- and French-speaking markets
only. There is no Italian-speaking list in any year, so RSI and Italian-language outlets never
appear.

**2018 caveat (verbatim, on all 2018 rows):** respondents in Switzerland could only take the
survey on a desktop or laptop computer; device-use figures may be affected. Sweden is **not** on
that edition's affected list — check each country.

**Registry:**

| id | brands seen | domain |
|---|---|---|
| `che_srf` | SRF News (public broadcaster), SRF News online/Online | `srf.ch` |
| `che_rts` | RTS News, RTS News online | `rts.ch` |
| `che_20min_de` | 20 Minuten, 20 Minuten online | `20min.ch` |
| `che_20min_fr` | 20 Minutes, 20 Minutes online | `20min.ch` |
| `che_blick` | Blick, Blick online, Blick (incl. evening and Sunday), Blick and Blick am Abend online | `blick.ch` |
| `che_blickamabend` | Blick am Abend online (2017 only) | `blickamabend.ch` |
| `che_sonntagsblick` | Sonntagsblick, SonntagsBlick | `blick.ch` |
| `che_sonntagszeitung` | SonntagsZeitung | `sonntagszeitung.ch` |
| `che_tagesanzeiger` | Tages-Anzeiger, Tages Anzeiger, … online | `tagesanzeiger.ch` |
| `che_nzz` | NZZ online, Neue Zürcher Zeitung (NZZ) | `nzz.ch` |
| `che_watson` | Watson, Watson.ch | `watson.ch` |
| `che_nau` | nau.ch | `nau.ch` |
| `che_luzernerzeitung` | Luzerner Zeitung | `luzernerzeitung.ch` |
| `che_bluenews` | Bluewin news/News, Bluewin.ch, Blue News | `bluewin.ch` |
| `che_teletext` | Teletext online, Teletext.ch | `teletext.ch` |
| `che_24heures` | 24 heures, 24 heures online, 24 heures.ch | `24heures.ch` |
| `che_letemps` | Le Temps, Le Temps online | `letemps.ch` |
| `che_lematin` | Le Matin online, Le Matin ( incl Sunday Edition), … | `lematin.ch` |
| `che_lematindimanche` | Le Matin Dimanche | `lematin.ch` |
| `che_tdg` | Tribune de Genève, … online | `tdg.ch` |
| `che_nouvelliste` | Le Nouvelliste, … online, LeNouvelliste.ch | `lenouvelliste.ch` |
| `che_laliberte` | La Liberté | `laliberte.ch` |
| `che_arcinfo` | Arcinfo.ch | `arcinfo.ch` |
| `usa_cnn` | CNN, CNN.com | `cnn.com` |
| `gbr_bbc` | BBC News, BBC News online | `bbc.co.uk` |
| `fra_lemonde` | Le Monde online | `lemonde.fr` |
| `deu_spiegel` | Spiegel online | `spiegel.de` |
| `usa_yahoo` | Yahoo! News, Yahoo News | `yahoo.com` |
| `usa_msn` | MSN News | `msn.com` |
| `deu_gmx` | GMX, gmx | `gmx.ch` |

Categories: `cat_de_public_tv`, `cat_de_commercial_tv`, `cat_fr_public_tv`,
`cat_fr_commercial_tv`, `cat_commercial_tv`, `cat_other_commercial`, `cat_commercial_radio`,
`cat_regional_local_press`, `cat_regional_local_press_online`, `cat_private_broadcasters`.

`cat_commercial_tv` (2019–2026) and `cat_other_commercial` (2016–2018) both cover Swiss
commercial TV; the DNR reworded the item ("Other commercial news (e.g. Tele Züri)" → "Other
commercial TV" → "Private TV news" → "Commercial TV news"). Currently **two ids with a note
saying they are one item** — inconsistent. Open question 5: merge under `cat_commercial_tv`.

**Blue News, worked example (resolved).** Trigger: brand string changed. Liveness: `bluenews.ch`
absent 2016–19, live 2020–26; `bluewin.ch` throughout. Article-bearing: `bluenews.ch` captures
are 301 in 2020, 2022 and 2024 — a pure redirect. Identity (A2): location resolves to
`https://www.bluewin.ch/`. Acceptance: `CC-MAIN-2022-05` gives `bluewin.ch` 433 captures,
`bluenews.ch` 0. **Verdict:** `bluewin.ch` correct for all eleven years.

---

# Appendix B — Sweden

Collected 13 Sep 2026 from this document alone, as a reusability test. 338 rows in
`outlets_dnr_sweden.csv`; validator passes.

**Page index** (PDF/printed): 2016 51/51 · 2017 95/95 · 2018 105/105 · 2019 111/111 ·
2020 **83**/83 · 2021 105/105 · 2022 105/105 · 2023 101/101 · 2024 107/107 · 2025 111/111 ·
2026 118/**115**.

**Sample sizes:** 2016 2,030 · 2017 2,021 · 2018 2,016 · 2019 2,007 · 2020 2,091 · 2021 2,005 ·
2022 2,064 · 2023 2,034 · 2024 2,018 · 2025 2,000 · 2026 2,052.

Two charts per year; `submarket` = `single-market` on every row. Bars per chart (offline/online): 16/16 · 16/16 · 16/16 ·
14/14 · 16/16 · 16/16 · 15/15 · 15/16 · 14/15 · 14/16 · 14/16.

Liveness: 246 checks, 29 domains, zero gaps. Outlets still needing identity work: `swe_sr`,
`swe_tv4`, `swe_metro`, `swe_samhallsnytt` (avpixlat.info → samhallsnytt.se → samnytt.se), plus
`swe_etc`, `swe_nyheter24`, `swe_hd`, `usa_huffpost`, `usa_buzzfeed`.
