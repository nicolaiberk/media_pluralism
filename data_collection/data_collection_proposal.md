# Proposal: Media Data Collection & Storage Process

*Draft, Sep 2026 — pipeline design for the pilot (Switzerland, validated against Swissdox@LiRI), built to scale to ~26 countries.*

## Design principles

1. **Country-agnostic, config-driven.** One pipeline; each country is a config (outlet list, domains, language, reach data). Adding a country must not require new code.
2. **Targeted retrieval, not TLD filtering.** Unlike Kriesch & Losacker (who kept all `.de` content), we retrieve by **outlet domain list**. This captures outlets on generic TLDs (e.g. `telex.hu` vs. outlets on `.com`) and drastically cuts processing volume.
3. **Raw data kept once, immutable; everything downstream reproducible.** Each processing layer is derivable from the layer below via versioned code.
4. **Copyright-aware from day one.** Full texts stored privately; public releases contain derived measures, metadata, and Common Crawl record IDs/URLs so others can re-retrieve texts (Kriesch & Losacker model).

## Stage 0 — Outlet registry (the spine of both datasets)

A curated table, one row per outlet × country, maintained as versioned CSV/YAML:

- `outlet_id`, `outlet_name`, `country`
- `domains`: list of domains **with validity periods** (domains change: e.g. Origo pre/post takeover; print vs. online brands)
- `reach_{year}`: weekly reach from Reuters DNR (extraction via existing DNR workflow); defines inclusion (threshold, e.g. ≥3%)
- outlet characteristics for dataset 1: ownership, public/private, print/online/broadcast origin, founding/closure dates, known ownership changes (sources: DNR, EJC Media Landscapes, CMPF MPM, national sources; RA-researched)

**QA**: every domain manually verified (resolves to the outlet); registry reviewed by a country expert / RA. Then run the full domain list against the **CC-MAIN index** (cc-index parquet via Athena/DuckDB — costs cents): per-domain URL counts per crawl verify each domain exists in Common Crawl, catch typos and domain migrations, and give a first coverage preview per outlet — all *before* the expensive CC-NEWS scan.

## Stage 1 — Retrieval from web archives

**Primary: CC-NEWS** (Aug 2016 →). CC-NEWS has **no URL index** — retrieval requires a full scan: iterate WARC files from `s3://commoncrawl/crawl-data/CC-NEWS/`, stream-parse record headers, and keep records whose target URI host matches the registry domains. Because one scan costs the same regardless of how many domains we match, **scan once against the union domain list of all target countries** (not just the pilot) and store matched raw records partitioned by country — downstream stages then process Switzerland first without ever rescanning.

**Secondary: CC-MAIN** (2013 →, for pre-2016 and gap-filling). CC-MAIN *does* have a columnar index (**cc-index parquet, queryable via AWS Athena / DuckDB**): query by domain to locate records, then fetch only the matching byte ranges from S3. Assess per-outlet coverage before committing. *Note: the index does not make CC-MAIN a substitute for CC-NEWS — CC-MAIN samples pages per domain under crawl budgets (homepage-skewed, capture often long after publication), while CC-NEWS polls RSS/sitemaps daily and systematically captures articles near publication. CC-MAIN's role is gap-filling (outlets without feeds, CC-NEWS dropouts, pre-2016).*

**Fallback: Internet Archive CDX API** per domain, for outlets/periods with poor CC coverage. Log provenance (`source_corpus`, `crawl_id`) on every record.

**Compute**: see Infrastructure section below. Jobs are embarrassingly parallel over WARC files; a monthly CC-NEWS slice is independent, so backfill and incremental updates use the same job.

## Stage 2 — Extraction & cleaning

Per raw HTML record (adopting Kriesch & Losacker's validated choices):

1. **Text extraction**: Trafilatura (main text, title, date, tags/categories, excerpt).
2. **Language detection**: keep target language(s) of the country config.
3. **Quality filters** (their thresholds as defaults, re-validated per language): ≥3 sentences, 50–10,000 words, ≤10% non-alphabetic words, >5 words/line, no JavaScript, mean word length 3–12.
4. **Article-type filtering**: heuristics + classifier to drop non-news (tag pages, live tickers, horoscopes, sports results) — *addition over K&L, needed because political-position measures assume news/opinion content*.
5. **Deduplication**: exact (text × outlet) and near-duplicate (MinHash) — syndication and republication matter for pluralism measures; keep dedup mapping rather than discarding silently.
6. **Date resolution**: publication date from Trafilatura/metadata; fall back to crawl date flagged as such (date quality flag column).

## Stage 3 — Storage

Three layers, mirroring the processing stages:

| Layer | Content | Format / location |
|---|---|---|
| **Raw** | Matched WARC records | Gzipped WARC on S3 (+ cold local backup), partitioned `country/source_corpus/crawl_id/` — immutable |
| **Articles** | Cleaned article table | **Parquet, partitioned by `country/year`**, queried via DuckDB; columns: `article_id` (UUID), `outlet_id`, `url`, `domain`, `title`, `text`, `lang`, `pub_date`, `date_quality`, `crawl_id`, `source_corpus`, `warc_offset`, quality-filter flags, `dedup_group` |
| **Derived** | Annotations, classifier predictions, outlet-year scores, country-year indices | Parquet/CSV; small enough for git/DVC |

- Parquet + DuckDB over Postgres for the article layer: cheaper, serverless, trivially parallel, works locally and on AWS. Postgres (budgeted) reserved for the annotation workflow if a labeling tool needs it.
- **Versioning**: pipeline code in git; data versioned with DVC (or dated snapshot prefixes on S3); every derived file records the code commit + config hash that produced it.
- **Public release**: derived layer + article metadata (IDs, URLs, dates, outlet) **without full text**; texts re-retrievable from Common Crawl via `crawl_id`/`warc_offset`.

## Stage 4 — Quality assessment (pilot gate)

Before scaling beyond the pilot, produce a standard per-country coverage report:

- articles per outlet × month (flag gaps, RSS-feed dropouts, domain migrations)
- **pilot benchmark: Swissdox@LiRI** — per outlet × month, compare CC-extracted article counts (and matched articles via URL/title/date) against the near-complete Swissdox archive; quantifies CC's coverage bias (paywalled outlets like NZZ/Tamedia, small outlets, feed dropouts). This comparison is a headline result for the methods paper. *License: Swissdox data stays on ETH infrastructure; only aggregate comparison statistics leave.*
- secondary benchmarks (comparative stage): Kriesch & Losacker counts (Germany), outlet self-reported output, Google Trends-style volume correlations
- text-quality distributions (length, boilerplate share); manual face-validity check of random samples (RA)
- CC-MAIN vs. CC-NEWS overlap for the same outlet-periods → decision rule for backfilling
- explicit **go/no-go criteria** per outlet-period (e.g. ≥N articles/month for inclusion in outlet-year estimates), so measurement never silently runs on thin data

## Stage 5 — Annotation & measurement layer (interface only)

Collection hands over a stable, versioned article table. Measurement (LLM annotation → NLI fine-tuning → prediction → DSL bias correction → outlet-year scores) reads from it and writes to the derived layer; annotation samples are drawn with stored seeds and stratification records so training/validation splits are reproducible.

## Infrastructure

### Extraction compute: AWS us-east-1

The CC-NEWS scan is I/O-bound over ~30–40 TiB of compressed WARC (2016–2026) sitting in `s3://commoncrawl` (us-east-1, free access from within AWS). Run the scan **next to the data**:

- **Why not Euler**: pulling tens of TiB from Common Crawl over public HTTPS is slow and now actively rate-limited by CC; in-region S3 reads are free and fast. Euler remains attractive for CPU-heavy *downstream* steps (Stage 2 on already-filtered data) and GPU work.
- **Setup**: AWS Batch (or a small spot-instance fleet) in us-east-1; one job per WARC file (or per month); container with `fastwarc` (much faster than `warcio`) doing header-level domain matching, writing matched raw records to our S3 bucket. Idempotent per-file jobs + a manifest table → trivial retry/resume.
- **Cost envelope (rough)**: scanning ~35 TiB compressed at realistic throughput ≈ a few hundred vCPU-hours → **low hundreds of CHF on spot instances** per full scan; in-region data transfer free; egress of the *filtered* output (est. 100–500 GB for the union domain list) ~ tens of CHF. Budget one full scan + margin for a re-run.
- **Stage 2 (Trafilatura etc.)** runs on the filtered corpus only — small enough for Euler or even a workstation; keep it off AWS to save cost.

### Hosting & storage

| Data | Where | Why |
|---|---|---|
| Raw matched WARC (immutable) | S3 (Standard-IA) **and** a synced copy on ETH group storage | S3 for pipeline proximity; ETH copy as the canonical long-term archive (no recurring cost, institutional backup) |
| Article layer (Parquet) | ETH group storage / Euler project space; working copies local | Queried via DuckDB — no server; a country-year partition fits on a laptop |
| Swissdox exports | **ETH infrastructure only** (group NAS), never AWS/cloud | License restriction; used only for the pilot benchmark |
| Derived layer (scores, indices) | git + DVC in the project repo | Small, versioned with code |
| Public release | Zenodo (DOI) + Hugging Face mirror | Metadata + derived measures only; texts re-retrievable from CC via record IDs |

After the scan and QA are complete, S3 can be emptied except for the raw matched WARC (or even that moved to Glacier/ETH-only) — steady-state cloud cost near zero.

### Later stages (for reference)

- **GPU (classifier fine-tuning/inference)**: Euler GPU nodes first (free); AWS (g4dn/p3-class, budgeted in Career Seed) as overflow.
- **Annotation workflow**: labeling tool (e.g. Argilla/Label Studio) on an ETH VM; Postgres only if the tool requires it.

## Open decisions

- [ ] AWS account setup: ETH central IT brokered account vs. project account (billing, IAM for RA access)
- [ ] Union domain list timing: full 26-country registry before the scan (delays pilot) vs. Switzerland + easily-researched majors now, second scan later — leaning: spend 2–3 RA weeks to get the union list first, scan once
- [ ] Reach threshold for outlet inclusion (3%? sensitivity band?) and handling of outlets entering/exiting DNR across years
- [ ] Near-dedup policy for syndicated wire content (drop, keep-with-flag, or attribute to agency)
- [ ] Whether to compute and store embeddings (useful for QA/search; K&L publish them, but not needed for the position measures)
