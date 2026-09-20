# How the collection works — step by step

*The whole pipeline from PDF to verified registry, in order, with what each script does, what
each file is, and where every open failure mode sits. Companion to `CLAUDE.md` (the method) and
the `Failure_Modes_Register` (the risks). Last updated 15 September 2026.*

Section numbers (§) refer to `../outlet_urls/CLAUDE.md`. Failure IDs (A1, B3 …) refer to
`Failure_Modes_Register.docx` in this folder.

---

## The shape of it

```
 PDFs ──► find pages ──► transcribe charts ──► classify ──► validate ──► outlets_dnr_<country>.csv
                                                                              │
                              ┌───────────────────────────────────────────────┘
                              ▼
           liveness ──► identity + articles ──► human review ──► (Common Crawl gate)
              │                 │                     │
         wb_years_*.tsv   domain_evidence_*.tsv   verdicts appended
```

Part A turns a report into rows. Part B establishes, for every row's domain and year, that it
really was that outlet's publishing site. Part A is done for Switzerland and Sweden. Part B is
done for liveness on both, and two-thirds done for identity on Switzerland (Archive.org
throttling has left 78 domain-years to re-run).

---

## Part A — from PDF to CSV

### Step 1 · Get the reports  (§1)

Eleven DNR PDFs, 2016–2026, ~165 MB, kept in `dnr_pdfs/` **outside the repo**. The repo holds
`dnr_pdfs/urls.txt` so anyone can re-download the identical set.

| Failure | What can go wrong |
|---|---|
| **E1** | Reuters changes URLs — links rot. Re-verify before each new edition. |
| **E4** | The DNR only surveys some language regions — no Italian-speaking Swiss list exists. Structural gap from the source. |

### Step 2 · Find the country's pages  (§2)

```
python scripts/find_country_pages.py Sweden
```

**`find_country_pages.py`** — for each PDF, finds the country's essay page, its chart page, and
the printed page number for the `source` column. It scores pages on chart markers and requires
the country name in the page's title area. Verified on Switzerland, Sweden, Germany.

| Failure | What can go wrong |
|---|---|
| **F1** | It's a heuristic. It once returned Switzerland's page for Sweden 2020. Guard: **confirm the page names your country**, not just that it has charts. |
| **F7** | It uses `pdftotext`, which we distrust elsewhere. Acceptable — it only locates; numbers are read from images. |
| **F8** | Country names change between editions. "Not found" for one year may mean a spelling change. |

### Step 3 · Year-level facts and the essay  (§3–§4)

By hand, per year: fieldwork dates (methodology, PDF p. 5), sample size (market table, PDF p. 6,
**read visually** — extracted text gives the wrong row), representativity caveat, and a read of
the country essay for rebrands and closures. These become `fieldwork_*`, `sample_size`,
`sample_type`, and material for `notes`.

### Step 4 · Render, crop, transcribe  (§5–§8)

Render the chart page at 300 dpi, crop to one chart, read the image, write one row per bar.
Never from extracted text — it separates labels from values and glues numbers together.

`submarket` is the market name where a country has several (`german-speaking`,
`french-speaking`) and `single-market` otherwise — never empty.

| Failure | What can go wrong |
|---|---|
| **F2** | Crop bands are starting points. They don't transfer between countries and clipped lists look complete. Count bars before and after. |
| **D5** | A clipped crop drops rows silently. Same guard. |
| **D2** | Some editions draw two series per bar. Read the legend; the printed number at the end of the full bar is the one. |
| **D3** | Chart order flips between editions (German on top to 2022, French from 2023). Read the heading; where there is none (2020), the legend colour. |
| **D7** | Typos are kept on purpose — "commerical", "Le Journa". Join on `outlet_id`, never on `brand`. |
| **E7** | Public-broadcaster sub-figures (TV 48% / radio 32%) overlap and exceed the headline. Never summed; kept in `notes`. **Open question 8 for Berk:** *extra rows for the sub-splits, or headline only (current)?* |
| **H6** | DNR 2018–2020 print an "ALSO" box of partisan brands outside the chart — Fria Tider, Nyheter Idag, Samhällsnytt and others. Currently excluded, which leaves them with rows from 2021 but none before. **Open question 9 for Berk:** *include them? If yes, the validator's descending-reach check needs an exemption, since they don't continue the chart's order.* |

### Step 5 · Classify and assign IDs  (§9–§10)

Each row gets a `brand_type` — `outlet`, `category` (a survey label like "Other regional
newspapers", no domain), `aggregator` (a portal republishing others), or `foreign` — and an
`outlet_id` that stays the same across years and spellings.

**Open question 4:** *20 Minuten and 20 Minutes have separate ids (`che_20min_de`,
`che_20min_fr`) though they share `20min.ch` — separate (current) or one shared id?*

| Failure | What can go wrong |
|---|---|
| **C4** | Aggregator vs outlet is a judgement at the edges. Overlaps resolve by rule: foreign × aggregator → `aggregator`; foreign × category → `category`. |
| **C5** | Merging two outlets under one id is irreversible — the corpus blends. Rule: prefer the reversible error, keep ids separate when unsure. |
| **D6** | The DNR rewords one item four ways over the years. Currently split across **two** ids (2016–18 vs 2019–26) with a note claiming they're one — inconsistent. **Open question 5:** *merge under `cat_commercial_tv`?* Rows shown in `OPEN_QUESTIONS.md`. |
| **E3** | Foreign ids (`usa_cnn`) recur across country files. A collision rule is needed before country three. |
| **E5** | Category rows carry real reach but can never be fetched. Kept, with `brand_type=category` and no domain, so the weighting sees them. |

### Step 6 · Notes  (§11)

Anything odd, per Berk: rebrands, caveats, regional editions. Year-level facts go on every row
of that year; a fact about one row goes on that row only.

| Failure | What can go wrong |
|---|---|
| **A1** | A note written from today's site gets applied to eleven years. SonntagsZeitung's was rewritten 15 Sep with per-era evidence; the rule stands for every new note. |

### Step 7 · Validate  (§12)

```
python scripts/validate_outlets.py outlets_dnr_switzerland.csv
```

**`validate_outlets.py`** — header, descending reach within each chart, category rows have no
domain, `brand_type`/`is_aggregator` agree, bare domains, id collisions, encoding, every chart
present. **Structure only** — it cannot know whether a number matches the page.

**Output of Part A:** `outlets_dnr_<country>.csv` — 18 columns, one row per country × year ×
list × brand. Switzerland 504 rows; Sweden 338.

One file per country. The RA instructions' single `outlets_dnr.csv` predates the multi-country
split.

---

## Part B — is the domain really the outlet's, that year?

One question with three independent parts. All three must hold for a domain-year to count as
verified; each catches what the others miss.

| Signal | Asks | Catches |
|---|---|---|
| **Liveness** | Was the host archived that year? | domains that didn't exist yet, or had died |
| **Article-bearing** | Did it carry article-shaped URLs? | portals, e-papers, redirects |
| **Identity** | Was the outlet's name in the masthead? | live hosts that belong to someone else |

### Step 8a · Liveness  (§13)

```
python scripts/wayback_liveness.py outlets_dnr_switzerland.csv
```

**`wayback_liveness.py`** — one Wayback CDX query per (domain, year): was anything captured?
Writes **`wb_years_<country>.tsv`**: `domain, year, live, used_in_csv, first_capture`. The
last column is the actual capture (timestamp, URL, status) — the artefact.

Result: Switzerland 279 checks, Sweden 246 — **zero used domains missing in any year**.

| Failure | What can go wrong |
|---|---|
| **B3** | `matchType` changes the answer; big hosts time out under `domain`. Large hosts use `exact`. |
| **B8** | Archive.org goes down, and refuses connections after sustained load. Never record an outage as data; scripts stop after six refusals. |
| **F5** | Throughput: 4–11 queries/min. About an hour per country before any human time. |

### Step 8b · Identity and article-bearing  (§15–§16)

```
python scripts/wayback_identity.py outlets_dnr_switzerland.csv
python scripts/wayback_identity.py outlets_dnr_switzerland.csv --retry   # redo only failures
```

**`wayback_identity.py`** — for each (outlet, domain, year): fetches the archived homepage
nearest mid-year, checks the outlet's name is in the title (**Tier A3**), and counts distinct
article-shaped URLs under the domain that year. Writes **`domain_evidence_<country>.tsv`** with
a verdict per row and a Wayback link to the page it looked at.

**Verdicts.** For each outlet-domain-year the script asks two questions of the archived
homepage from that year — *is the outlet's name in the page title?* and *are there
article-looking URLs under this domain that year?* — and the verdict is just the combination
of answers. Each row also carries `artefact_url`, a Wayback link to the exact page it looked at,
so you can see what it saw.

**`A3` — both yes. Verified.**
The archived page's title carries the outlet's name (e.g. *"24 heures, l'actualité en direct…"*
for `24heures.ch` in 2016) and hundreds of article URLs were captured that year. This host was
that outlet, publishing, in that year. Evidence tier A3. **You do nothing.** If you want to
sample-check the automation, these are the rows to open.

**`shared` — name yes, but the domain has more than one outlet on it.**
`20min.ch` in 2016: title *"20 Minuten - News von jetzt!"*, clearly the publisher's. But the
registry has both `che_20min_de` and `che_20min_fr` pointing at this domain. The script has
proved the domain belongs to the publisher; it *cannot* say whether the French edition's
articles are on the same host as the German ones, or somewhere else. That is a judgement.
**You decide** — and it's open question 10 for Berk, so until he answers, note it and move on.

**`A3-noarticles` — name yes, articles no.**
The page is branded as the outlet, but the article-URL search found nothing that year. Two
possibilities: the site changed its URL pattern so the search missed them (a false alarm), or it
genuinely was a landing page / e-paper portal that year with no articles to fetch. **You open
the link and look.** If there are articles, note it and treat as `A3`. If there aren't, find
where the articles were actually published (Berk's rule 3), else blank the domain for that year
and say why (rule 5).

**`needs-human` — the name was *not* in the title.**
A page came back with a real title, and it isn't this outlet's. This is the case the whole
check exists for: a live host that may belong to someone else, or a year in which the outlet
used a different domain. **You apply the evidence tiers by hand** — look for an archived imprint
(A1), a redirect to a domain already confirmed (A2), or two independent sources (B). Twenty
minutes; if nothing settles it, blank the domain for that year and note what you tried.

**`A3-arts?` — name yes, article query failed.**
Identity is confirmed; the article count is unknown because Archive.org didn't answer that
query. Not a finding about the outlet. **Re-run** with `--retry`; it becomes `A3` or
`A3-noarticles`.

**`no-title`, `no-page`, `?` — Archive.org didn't answer.**
No page, an empty page, or a page cut off before the title. Not evidence of anything. **Re-run**
with `--retry`. These pile up when Archive.org is throttling; wait an hour first.

So the file sorts into three piles: **settled** (`A3`), **yours to judge** (`shared`,
`A3-noarticles`, `needs-human`), and **not yet answered** (the rest — re-run, don't interpret).

Switzerland after the first retry: 93 `A3`, 56 `shared`, 8 `A3-noarticles`, 4 `needs-human`,
78 still unanswered (Archive.org throttling). One more `--retry` clears those.

| Failure | What can go wrong |
|---|---|
| **I3** | The name match is a keyword heuristic; its false-positive rate is unmeasured. Hand-check 30 `A3` rows before trusting it. |
| **C1** | A domain outlives its paper (`blickamabend.ch` to 2026). Existence proves nothing — identity is checked per year. |
| **C2** | Two live domains, one real (`20min.ch` vs `20minuten.ch`). The article count separates them. |
| **B1** | The only name-to-domain search stops at 2016. Post-2016 rebrands are found by brand-string change and capture discontinuity (§14). |

### Step 8c · Human review  (§16–§17)

The rows the script routes to a person: `needs-human`, `shared`, `A3-noarticles`. Grouped by
outlet — Switzerland: 17 outlets.

**Evidence tiers** — how strong a piece of evidence is:

| Tier | Evidence | Sufficient? |
|---|---|---|
| **A1** | archived imprint naming the outlet or publisher | alone |
| **A2** | archived redirect to a domain already confirmed | alone, only if the target is confirmed |
| **A3** | outlet's name in the archived masthead — *what the script checks* | alone |
| **B** | DNR essay, national media institute, trade press, Wikidata with citation, successor site linking back | two, independently |
| **C** | name resemblance, the domain existed, looks like news | never |

**Decision rule:** Tier A or 2×B *and* article-bearing → record the domain. Identity confirmed
but no articles → find where articles live, else blank. Identity not confirmed → blank, note
why, keep ids separate. Twenty minutes per outlet, then stop.

| Failure | What can go wrong |
|---|---|
| **A3** | Six Swiss outlets still carry `UNVERIFIED` notes. Resolve from the evidence file. |
| **A4** | Shared domains — `20min.ch` carries both language editions; SonntagsBlick resolves to `blick.ch`; Le Matin Dimanche to `lematin.ch`. The pipeline fetches by domain, so their corpora would merge. **Open question 10 for Berk:** *split by path/language at extraction, or accept the merge and document it?* |
| **B6** | The imprint path varies by site and country. Try the country's variants; find the link on the homepage. |
| **C3** | A redirect isn't proof of a rebrand — could be a domain sale. A2 alone only when the target is already confirmed. |
| **F6 / I4** | This step is deliberately not automated. Rebrand-vs-sale and shared-domain attribution need a person. |
| **K1** | Language editions sit at a *path* on a shared domain — `20min.ch/ro/`, `bluewin.ch/fr/`. The registry records only the domain, so extraction gets both editions mixed. Proposed `edition_path` column (question 10). |
| **K2** | `teletext.ch` renders German only; where the French teletext lives is unverified. If it's another host, the French rows have the wrong domain. |
| **K3** | `lematin.ch`'s Dec 2016 capture looks like an e-paper. Check a mid-year capture before concluding — could be SonntagsZeitung's pattern, could be a holiday page. |
| **K4** | One capture is not the year. Look at two or three spread across it before recording a verdict; the script uses 1 July for this reason. |

### Step 8d · Common Crawl acceptance  (§18)

Query the CC index for the domain in that year's crawl. The definitive fetchability test — but
it tests fetchability only. `sonntagszeitung.ch` passes it and the articles were elsewhere.
**Open question 11 for Berk:** *keep the Common Crawl check in the registry pipeline (current), or hold it for the extraction stage, since it's milestone-4 work?*

| Failure | What can go wrong |
|---|---|
| **E2** | The test ran against CC-MAIN; the project's source is CC-NEWS. Counts are directional. |

### Step 9 · Record  (§19)

Human verdicts are **appended** to `domain_evidence_<country>.tsv`, never overwriting the
script's row. Contested cases get a `domain_research/<outlet_id>.md` dossier. The CSV `notes`
column gets a one-line verdict.

### Step 10 · Branch, commit, PR

Nothing is committed yet. **E8** — the longest-standing open item.

---

## Verification re-runs

Twice, a fresh agent with no access to the data has redone a step blind:

- **Switzerland re-transcription** — all 504 reach values and 11 sample sizes matched; three
  brand strings were wrong in the original and fixed.
- **Sweden from `CLAUDE.md` alone** — produced 338 valid rows and a list of twelve gaps in the
  method, all since fixed; also found the finder returning the wrong country's page.

| Failure | What can go wrong |
|---|---|
| **F9** | `CLAUDE.md`'s appendix holds the verified Swiss answers. A re-run that reads it confirms rather than tests. Blind runs get the method without the appendix and say so. |

---

## Every file, and what it is

| File | Made by | Holds |
|---|---|---|
| `outlets_dnr_<country>.csv` | Part A, by hand/agent | the registry — the deliverable |
| `wb_years_<country>.tsv` | `wayback_liveness.py` | one row per domain-year: archived or not, with the capture |
| `domain_evidence_<country>.tsv` | `wayback_identity.py` + human | one row per outlet-domain-year: verdict, tier, link, title, article count |
| `domain_research/<outlet_id>.md` | human | dossier for a contested outlet |
| `OPEN_QUESTIONS.md` | — | the decisions still Berk's (six) — this folder |
| `CLAUDE.md` | — | the method, for an agent |
| `RA_instructions_outlets.md` | Berk | the spec — the authority |
| `dnr_pdfs/urls.txt` | — | re-download the eleven PDFs |
| `Failure_Modes_Register.docx` | — | live risks — this folder |
| `Fixed_Issues.docx` | — | fixed defects and settled decisions, kept as the record — this folder |

## Every script

| Script | Step | In one line |
|---|---|---|
| `find_country_pages.py` | 2 | which PDF page has this country's charts, per year |
| `validate_outlets.py` | 7 | is the CSV structurally sound |
| `wayback_liveness.py` | 8a | was each domain archived in each year it's used |
| `wayback_identity.py` | 8b | was each domain branded as the outlet and carrying articles, per year |
| `dnr_fetch.py` | any | host-restricted GET — the only network tool the permission allowlist grants |
