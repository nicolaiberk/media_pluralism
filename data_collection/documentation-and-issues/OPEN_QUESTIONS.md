# Open questions — outlet registry

Decisions still to be made. Each is cheap to change on the Swiss and Swedish files and expensive
across ~26 countries. Current behaviour is stated so a "no change" answer is easy. When one is
answered, the answer is written into `CLAUDE.md` as a rule, the entry is removed from here, and a
record goes to `Fixed_Issues.docx`.

### 4. `che_20min_de` / `che_20min_fr` — one id or two?

20 Minuten (German) and 20 Minutes (French) are separate bars with separate reach figures in
separate submarkets, but share `20min.ch`. Currently **two ids**. One shared id would treat them
as one outlet. Closely tied to question 10.

### 5. Swiss commercial-TV category — merge the two ids?

The DNR asks Swiss respondents about their regional private TV channels (Tele Züri, Tele Bärn,
TeleM1) every year, but prints a different label each time. Here are the actual rows,
German-speaking offline chart:

| year | brand as printed | reach | outlet_id |
|---|---|---|---|
| 2016 | Other commercial news (e.g. Tele Züri) | 23 | `cat_other_commercial` |
| 2017 | Other commercial TV (e.g. Tele Züri) | 24 | `cat_other_commercial` |
| 2018 | Other commercial TV | 19 | `cat_other_commercial` |
| 2019 | Private TV news | 24 | `cat_commercial_tv` |
| 2020 | Private TV news | 23 | `cat_commercial_tv` |
| 2021 | Private TV news | 22 | `cat_commercial_tv` |
| 2022 | Private TV news | 21 | `cat_commercial_tv` |
| 2023 | Private TV news | 17 | `cat_commercial_tv` |
| 2024 | Private TV news | 19 | `cat_commercial_tv` |
| 2025 | Commercial TV news (e.g. Tele Züri, Tele Bärn, TeleM1) | 18 | `cat_commercial_tv` |
| 2026 | Commercial TV news | 21 | `cat_commercial_tv` |

The reach series is continuous (23 → 24 → 19 → 24 → 23 → 22 → 21 → 17 → 19 → 18 → 21) and the
"e.g. Tele Züri" appears at both ends. It is plainly one survey item.

**The note on every one of these rows** reads: *"Aggregate category label for Swiss
commercial/private TV news. Wording varies by year ('Other commercial news (e.g. Tele Zuri)' →
'Other commercial TV' → 'Private TV news' → 'Commercial TV news'); treated as one item."*

**The honest state:** the note says "one item" but the rows are under **two different ids**
(2016–2018 vs 2019–2026). That's an inconsistency in the current file, not a design — the earlier
question text saying "merged under one id" was wrong. Not to be confused with
`cat_de_commercial_tv` ("German commercial TV news", i.e. RTL from Germany), which is a separate
item that exists alongside every year.

**Proposed:** merge everything under `cat_commercial_tv`. These are category rows — no domain,
never fetched — so the only effect is that the time series joins on one id. No risk.

### 8. Public-broadcaster sub-splits — extra rows or headline only?

Charts print e.g. "SRF TV News: 38% / SRF Radio News: 36%" beside a headline "SRF News 57".
Currently in `notes` only. The parts overlap and exceed the headline (RTS 48+32 vs 63) — they
are not a partition and must never be summed.

### 9. The "ALSO" box, DNR 2018–2020 — include?

Beside the Swedish online chart those years is a boxed list of alternative/partisan brands with
reach figures: Fria Tider, Nyheter Idag, Samhällsnytt, Ledarsidorna, Samtiden, Nya Tider, Det
Goda Samhället. Not bars, not in descending order with the chart. **Currently excluded**, so
those outlets have rows from 2021 but none for 2018–2020. Values preserved in the failure
register (H6). Including them means a per-source exemption in the validator's descending-reach
check.

### 10. Outlets sharing a domain — split or accept?

**What the problem is.** Common Crawl stores articles keyed by URL. Extraction says "give me
everything under `20min.ch`". That returns German *and* French articles mixed together, because
both editions live on that host. The registry says `20min.ch` belongs to `che_20min_de` **and**
`che_20min_fr` — but from the domain alone, extraction cannot tell which article belongs to
which outlet.

The same applies to `SonntagsBlick` on `blick.ch` (Sunday paper's articles interleaved with
daily Blick's) and `Le Matin Dimanche` on `lematin.ch`. The identity check marks all of these
`shared`: it can confirm the domain is the publisher's, not whose articles are on it.

**Option A — split at extraction.** Route articles to an outlet by URL path (if French articles
live under `20min.ch/fr/…`) or by language detection on the text. Keeps the German/French
distinction, which for a multilingual pilot is exactly what you'd want. Costs an extraction rule
per shared domain, and needs checking that the path structure held in every year. For the
Sunday papers there is probably no path to split on at all.

**Option B — accept the merge.** Treat `20min.ch` as one outlet with one measured position; let
SonntagsBlick's reach count toward Blick and its position be Blick's. Simpler, loses the
distinction.

**What the 2016 manual check found (15 Sep).** The editions are at *paths*, not separate
domains: the French 20 Minuten is `20min.ch/ro/` (Romandie); Bluewin has `bluewin.ch/de/…`
and `bluewin.ch/fr/…` with a language toggle. So the discriminator extraction needs is
knowable and recordable.

**Note on Berk's rule 1** ("language/regional editions on subdomains stay one domain"): that is
a rule about how to *write the domain column* — registered domain only — not a claim that the
editions carry the same content. They don't; different newsrooms, different articles,
plausibly different positions.

**Proposed answer:** add one column, `edition_path`, empty for outlets with their own domain
and the URL prefix otherwise — `/ro/` for `che_20min_fr`, `/fr/` for Blue News's French rows.
Keeps `domain` exactly as the spec says; gives extraction what it needs; and lets the identity
check fetch the French edition's masthead rather than calling the row `shared`.

**Current behaviour:** separate ids and rows (so nothing is lost), domain recorded as shared in
the evidence file, and no extraction rule yet.

### 11. Common Crawl acceptance test — keep in the registry, or defer?

**What it is.** Ask Common Crawl's own index directly: *"do you have any captures of this
domain in this year's crawl?"* It is the only check that speaks to the actual data source —
Wayback is a proxy for it. Example: `bluenews.ch` returned 0 captures in CC 2022 while
`bluewin.ch` returned 433, confirming the former is a pure redirect.

**Why keep it here.** It tells you *before* extraction which outlet-years will yield nothing.
That's early warning for the milestone-4 coverage assessment, and it flags a wrong domain
before anyone builds on it.

**Why defer it.** Milestone 2 is "define the outlet universe"; coverage is milestone 4. Also the
test so far ran against CC-MAIN (the general crawl), whereas the project's real source from
2016 is CC-NEWS — a different corpus — so the counts are directional only until re-run there.

**Cost either way:** one query per domain-year, comparable to the Wayback sweep.

**Proposed:** keep it as a per-country *report*, not a gate — run it, record the counts, don't
let it decide anything in the registry.
