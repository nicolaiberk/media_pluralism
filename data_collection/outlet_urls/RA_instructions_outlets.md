# RA Instructions: Outlet List from the Reuters Digital News Reports

*Goal: a table of the most-consumed news outlets per country and year, with their web domains. This table defines which outlets we collect from the Common Crawl web archive, so completeness and correct domains matter more than speed.*

## Country scope

Include all countries from Europe and North America which are covered in a given Reuters Digital News Report (DNR). The DNR country pages are in the annual reports: https://reutersinstitute.politics.ox.ac.uk/digital-news-report.


## Task

The "Top brands" lists of the DNR country pages have already been transcribed into `data_collection/outlet_urls/outlets_<year>.csv` (one file per DNR year, e.g. `outlets_2016.csv`). For **each country × each DNR year** in scope, open the country page of that year's DNR and:

1. **Check the transcribed rows** against the country page: all brands present, percentages correct, brand names as printed, sensible `outlet_id` merges of offline/online variants. Fix errors directly in the CSV and mention them in `notes`.
2. **Add the domains** (see "Domain research" below). The `domain` column is pre-filled only where the printed brand name is itself a domain.
3. **Mark your progress** in `data_collection/data_checks/checks_dnr_<year>.csv`. Each file has one row per country (or language market, e.g. "Switzerland (german)") and market type (`print` = the offline "TV, radio and print" list, `digital` = the online list). Put `x` in `checked_content` once the content check is complete and `x` in `added_domain` once all domains for that row are added. Update as you go — this is how we see what is done.

Note:

- The DNR reports **two lists**: *offline* brands (TV, radio, print combined — there is no print-only list) and *online* brands. Both lists are recorded with **all brands shown** (usually ~12–16 per list, i.e. more than 10 — everything printed, we filter later).
- The DNR figure is **weekly reach in %** ("used in the last week"), not market share.
- Some countries (e.g. Switzerland) have several lists. These are recorded as separate markets in the `submarket` column.
- Samples for some markets (e.g. Turkey) are **urban/online-representative only** — any such sample caveat from the country page belongs in `notes`.

## Output table (`outlets_<year>.csv`)

One row per country × year × list × brand:

| Column | Content | Example |
|---|---|---|
| `country` | ISO-3 code | `CHE` |
| `submarket` | Optional, for countries with several news markets | `german-speaking` |
| `year` | DNR report year | `2022` |
| `list_type` | `online` or `offline` | `online` |
| `brand` | Brand name exactly as printed in the DNR | `20 Minuten` |
| `weekly_reach_pct` | Weekly reach in % as printed | `28` |
| `outlet_id` | Stable ID, same across years/lists/spellings | `che_20min` |
| `domain` | Registered domain of the brand's news website **at that time**, | `20min.ch` |
| `notes` | Anything odd: representativity issues, rebrands, domain changes, regional editions | |
| `source` | DNR report + page where information was found | DNR 2023, p. 111 |

## Domain research

1. `domain` = the registered domain only (`20min.ch`, not `https://www.20min.ch/`); language/regional editions on subdomains stay one domain.
2. Check the Wayback Machine (web.archive.org) to see what the domain was in earlier years.
3. If a brand publishes under a **different domain than its name suggests** (e.g. print brand whose site lives under a portal), record the domain where its *articles* live, and note it.
4. Offline-list brands (TV/radio/print) still get their news-website domain — that's what we can observe.
5. If no news website exists (or articles are only on a shared portal), record the domain as empty and explain in `notes`.
