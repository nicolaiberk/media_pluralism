# RA Instructions: Outlet List from the Reuters Digital News Reports

*Goal: a table of the most-consumed news outlets per country and year, with their web domains. This table defines which outlets we collect from the Common Crawl web archive, so completeness and correct domains matter more than speed.*

## Country scope

Include all countries from Europe and North America which are covered in a given Reuters Digital News Report (DNR). The DNR country pages are in the annual reports: https://reutersinstitute.politics.ox.ac.uk/digital-news-report.


## Task

For **each country × each DNR year** in scope, open the country page of that year's DNR and record the **"Top brands" lists**. Note:

- The DNR reports **two lists**: *offline* brands (TV, radio, print combined — there is no print-only list) and *online* brands. Record **both lists, all brands shown** (usually ~12–16 per list, i.e. more than 10 — record everything printed, we filter later).
- The DNR figure is **weekly reach in %** ("used in the last week"), not market share.

Notes:

- Some countries (e.g. Switzerland) might have a several lists. Record these as separate markets in the `submarket` column.
- Samples for some markets (e.g. Turkey) are **urban/online-representative only** — copy any such sample caveat from the country page into `notes`.

## Output table (`outlets_dnr.csv`)

One row per country × year × list × brand:

| Column | Content | Example |
|---|---|---|
| `country` | ISO-3 code | `CHE` |
| `submarket` | Optional, for countries with several news markets | `german-speaking` |
| `year` | DNR report year | `2022` |
| `list_type` | `online` or `offline` | `online` |
| `brand` | Brand name exactly as printed in the DNR | `20 Minuten` |
| `weekly_reach_pct` | Weekly reach in % as printed | `28` |
| `outlet_id` | Stable ID you assign, same across years/lists/spellings | `che_20min` |
| `domain` | Registered domain of the brand's news website **at that time**, | `20min.ch` |
| `notes` | Anything odd: representativity issues, rebrands, domain changes, regional editions | |
| `source` | Report year + page / URL of country page | |

## Domain research

1. `domain` = the registered domain only (`20min.ch`, not `https://www.20min.ch/`); language/regional editions on subdomains stay one domain.
2. Check the Wayback Machine (web.archive.org) to see what the domain was in earlier years.
3. If a brand publishes under a **different domain than its name suggests** (e.g. print brand whose site lives under a portal), record the domain where its *articles* live, and note it.
4. Offline-list brands (TV/radio/print) still get their news-website domain — that's what we can observe.
5. If no news website exists (or articles are only on a shared portal), record the domain as empty and explain in `notes`.
