# Outlet domains: project overview

*Workstream: assign to every DNR "top brand" the registered domain under which it published news in the DNR year, and verify that domain. Output feeds the domain lists that drive CC-NEWS retrieval. Status as of 2026-11-27.*

## Starting point

- **Scope: DNR years 2016–2026 only.** These are covered by CC-NEWS (from Aug 2016), so CC-MAIN is used only as an index for the existence check in milestone 3, not as a page or text source. The 2012–2015 tables stay in the repo but are not processed for now.

- `outlets_<year>.csv` (one per DNR year 2012–2026, all extracted and checked against the reports) lists every brand printed in the DNR offline and online lists, with a stable `outlet_id` across years. The `domain` column is empty except where the printed brand is itself a domain (plus a few hand-researched 2016 rows): 259 of 1,029 outlets.
- RA conventions for the table are in `RA_instructions_outlets.md`. Progress is tracked in `data_collection/data_checks/checks_dnr_<year>.csv`.
- Two things have to hold for every outlet × year: (a) the domain belongs to that outlet, and (b) the domain carries news pages at that time. Milestones 1–3 settle (a), milestone 4 settles (b).

## Milestones

### 1. Pre-fill domains from Wikidata

- **What**: for each distinct `outlet_id`, find the Wikidata item and its official website (property P856). Store the item ID in a new `wikidata_qid` column and the website's registered domain in `domain` for *all* years of that outlet, marked as `domain_source = wikidata` so it is known to be unverified.
- **How**: name search (`wbsearchentities`) per brand → keep candidates whose country (P17) matches and whose class is a media class (newspaper, news website, broadcaster, TV channel, radio station, magazine, periodical) → take P856, preferred rank first.
- **Known limits** (tested 2026-10-27): about half of newspaper items have a website at all (Swiss newspapers: 44 of 100; worldwide: 11.6k of 52.7k). Dates on website statements are essentially absent (99 of 11.6k statements worldwide), so Wikidata only gives the *current* domain. Class labels are inconsistent (20 Minuten is "periodical literature"), and name matches are ambiguous ("Le Temps", "Blick", "Watson"), so the country filter is mandatory and matches still need a check in milestone 2. Generic categories ("local newspaper") get no item.
- **Output**: `domain` and `wikidata_qid` pre-filled for roughly half the outlets; a list of unmatched outlets for milestone 2.

### 2. Agent search for the remaining outlets

- **What**: an LLM agent with web search fills `domain` for outlets without a Wikidata website and sanity-checks the pre-filled ones (brand name vs. site name). A human only reviews what the agent flags and a random sample.
- **How**: one agent task per outlet (brand, country, submarket, years listed, Wikidata candidate if any). The agent finds the current news website, applies the rules from `RA_instructions_outlets.md` (registered domain only, articles' domain not the brand portal, empty + note if no news website exists), and returns domain, the URL it relied on, a confidence level (`high` / `low`) and any hint of rebrands or domain changes. Mark `domain_source = agent`.
- **Human review**: all `low`-confidence rows, all disagreements between agent and Wikidata, and a random 10% of the rest. If the error rate in the sample exceeds a few percent, review the country in full.
- **Output**: `domain` filled (or deliberately empty with a note) for every outlet × year, `domain_evidence` URL per outlet; `added_domain` ticked in the checks file after review.

### 3. Check domain existence per year via the Common Crawl columnar index

- **What**: for each outlet × DNR year, confirm that the domain was crawled as a live site in that year and did not redirect elsewhere.
- **Source**: the CC-MAIN URL index in Parquet, `s3://commoncrawl/cc-index/table/cc-main/warc/` (us-east-1), partitioned by `crawl` and `subset`; about 110 crawls for 2016–2026. It is queried with Athena (or DuckDB/Spark on an EC2 instance) and needs an AWS account. The CDX API at `index.commoncrawl.org` is not used: it works one crawl at a time and timed out in tests (2026-11-27).
- **How**: one query per crawl over the full domain registry: `WHERE url_host_registered_domain IN (<registry>)`, grouped by domain and `subset`, returning number of captures, number with `fetch_status = 200`, the most frequent `fetch_redirect` target outside the domain, and the most frequent `content_languages`. The `warc` subset holds successful fetches, `crawldiagnostics` holds redirects and errors. Results are stacked into `data_collection/data_checks/domain_crawl_index.csv` (domain × crawl) and aggregated to the calendar year of each DNR edition.
- **Rules**: ≥1 capture with status 200 in the year → `exists`. Only redirects to another registered domain → `redirect`, and the target is recorded as candidate domain for that year. No captures in any crawl of the year → `missing`.
- **Cost**: a full scan of one crawl's index is at most about $1.50 on Athena; the query reads only a few columns, so the whole run stays far below 110 × $1.50.
- **Limits**: CC-MAIN is a sample of the web, so `missing` is not proof that the domain did not exist. `missing` rows are therefore looked up by hand in the Wayback Machine before a domain is changed. CC-NEWS is not part of this index (see milestone 4).
- **Output**: columns `ccmain_status` (`exists` / `redirect` / `missing`), `ccmain_redirect_to` and `ccmain_captures`; `redirect` and `missing` rows go back to milestone 2, resolved cases are documented in `notes`.

### 4. One page per domain-year, verified by an agent

- **What**: save one archived page per outlet × year as HTML and have an LLM agent confirm that the domain is a news site of that brand at that time.
- **How**: scan one month of CC-NEWS per DNR year (February of the DNR year; September for 2016) for the full domain registry with `data_collection/scan_ccnews.py`. Per domain, keep the first matched record whose URL is the homepage if present, otherwise the first article page, and write it to `data_collection/data_checks/pages/<year>/<outlet_id>.html` (CC-NEWS text is for internal verification only, not for redistribution). Scan cost: a month is 30–700 WARC files of ~1 GiB, i.e. minutes on an EC2 instance in us-east-1, up to an hour on a laptop per month; the full set (11 months, ~3.5 TB) is ~2 h on a 32-vCPU instance for under $5. The same scan yields `domain × month → article count`, the input to the coverage assessment (README milestone 4).
- **Agent check**: the agent gets the page text (title, headline, visible text, site name in the footer/imprint) together with brand, country and year, and returns `page_check` plus a one-line reason. A human looks only at `not_news`, `wrong_outlet` and `no_page` rows.
- **Output**: HTML file per outlet × year; `page_check` set to `news` / `not_news` / `wrong_outlet` / `no_page`. Zero matches in the month plus `ccmain_status = exists` usually means a paywall or a site CC-NEWS cannot pick up (no RSS/sitemap); note it, it is a coverage finding, not an error.

## Columns added to `outlets_<year>.csv` by this workstream

| Column | Filled by | Values |
|---|---|---|
| `wikidata_qid` | M1 | QID or empty |
| `domain_source` | M1/M2 | `wikidata`, `agent`, `manual`, `printed` |
| `domain_evidence` | M2 | URL the agent relied on |
| `ccmain_status` | M3 | `exists`, `redirect`, `missing` |
| `ccmain_redirect_to` | M3 | registered domain or empty |
| `ccmain_captures` | M3 | integer, status-200 captures in the DNR year |
| `page_check` | M4 (agent) | `news`, `not_news`, `wrong_outlet`, `no_page` |
| `ccnews_articles_month` | M4 | integer, articles matched in the scanned month |

## Other sources considered

- **No historical Google search API exists.** Custom Search queries only the current index.
- **GDELT GKG** (BigQuery, 2015+): articles per domain per month for most news domains, free; useful later as an independent coverage benchmark, not needed for the checks above.
- **GDELT Web News NGrams 3.0** (2020+): same information, newer and bulkier; no advantage here.
- **GDELT Global Frontpage Graph** (2018+): hourly homepage outlinks; could catch brands whose articles live on another host, but the redirect check in milestone 3 covers the common cases.
- **Wayback CDX**: denser than CC-MAIN for single domains but rate-limited (about 1 request/s, throttling on longer runs); kept only as a manual lookup for `missing` rows.
