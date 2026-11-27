# Outlet domains: project overview

*Workstream: assign to every DNR "top brand" the registered domain under which it published news in the DNR year, and verify that domain. Output feeds the domain lists that drive CC-NEWS retrieval. Status as of 2026-11-27.*

## Starting point

- **Scope: DNR years 2016–2026 only.** These are covered by CC-NEWS (from Aug 2016), so CC-MAIN is used only as an index for the existence check in milestone 3, not as a page or text source. The 2012–2015 tables stay in the repo but are not processed for now.

- `outlets_<year>.csv` (one per DNR year 2012–2026, all extracted and checked against the reports) lists every brand printed in the DNR offline and online lists, with a stable `outlet_id` across years. The `domain` column is empty except where the printed brand is itself a domain (plus a few hand-researched 2016 rows): 259 of 1,029 outlets.
- RA conventions for the table are in `RA_instructions_outlets.md`. Progress is tracked in `data_collection/data_checks/checks_dnr_<year>.csv`.
- Two things have to hold for every outlet × year: (a) the domain belongs to that outlet, and (b) the domain carries news pages at that time. Milestones 1–3 settle (a), milestone 4 settles (b).

## Milestones

### 1. Candidate domains from Wikidata (done 2026-11-27)

- **What**: for each outlet, the Wikidata item, its official website (property P856) and earlier websites from the item and its edit history. Scripts `scripts/wikidata_prefill.py` and `scripts/wikidata_history.py`; outputs `wikidata_candidates.csv` and `wikidata_domain_history.csv`. Nothing is written to the yearly tables: the domains are candidates for milestone 2.
- **Result**: website for 796 of 887 outlets; results and limits are in `extraction_report.md`, section 2.

### 2. Agent search: all domains of each outlet, 2016–2026

- **What**: an LLM agent with web search establishes, for every outlet, **every registered domain under which it published news between 2016 and 2026**, with the years each one applied. One current domain per outlet is not enough: where it can be checked, about one in five Wikidata domains differs from the one the DNR printed, mostly because of rebrands and domain moves (`n24.de` → `welt.de`, `b.dk` → `berlingske.dk`, `rtvs.sk` → `stvr.sk`).
- **Input per outlet**: brand names as printed, country, submarket, years listed in the DNR; the domains the DNR printed, by year; the Wikidata candidate (`wikidata_candidates.csv`: item, website, name similarity, country match, dissolution year); earlier websites from the item and its edit history (`wikidata_domain_history.csv`).
- **How**: the agent (a) confirms or replaces the current domain, applying the rules from `RA_instructions_outlets.md` (registered domain only; the domain where articles are published, not the corporate or brand portal; empty + note if no news website exists); (b) searches for predecessors and successors: rebrands, mergers, closures and domain moves in the outlet's Wikipedia articles (local-language version first), the Wikidata history, and the Wayback Machine's capture history of each candidate domain; (c) returns one row per domain with first and last year of use, the URL it relied on and a confidence level (`high` / `low`).
- **Output**: a registry `outlet_domains.csv` with one row per outlet × domain: `outlet_id`, `domain`, `valid_from`, `valid_to` (years, empty = open-ended), `domain_source` (`printed` / `wikidata` / `agent`), `domain_evidence` (URL), `confidence`, `notes`. The yearly `outlets_<year>.csv` get their `domain` column filled from this registry by year. Retrieval (milestone 5) uses every domain in the registry, each within its years plus a margin.
- **Human review**: all `low`-confidence rows and all outlets where agent and Wikidata disagree on the current domain; a random 10% of the rest once, as an error-rate estimate.

### 3. Check domain existence per year via the Common Crawl columnar index

- **What**: for each registry domain × year, confirm that the domain was crawled as a live site in that year and did not redirect elsewhere. This also tests the agent's `valid_from` / `valid_to`: a domain that starts redirecting to another registered domain marks a move, and the target is a successor the registry must contain.
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

Domains themselves live in the registry `outlet_domains.csv` (see milestone 2); the yearly tables carry the per-year result.

| Column | Filled by | Values |
|---|---|---|
| `domain` | M2 | filled per year from the registry `outlet_domains.csv` (outlet × domain × years) |
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
