# CLAUDE.md — Media Pluralism Project

## What this project is

Nicolai Berk (postdoc, Public Policy Group, ETH Zurich) is building **media content datasets from large web archives** (Common Crawl, esp. CC-NEWS) to measure the ideological positions of news outlets and, aggregated, media pluralism across countries.

Two target datasets — both **comparative** from the start:

1. **Outlet-level dataset**: political positions (and other characteristics) of individual news outlets, per outlet-year, on four dimensions: government criticism, liberal democracy, economic left-right, cultural (GAL-TAN).
2. **Country-year dataset**: comparative indicators of media pluralism, aggregated from outlet positions weighted by audience reach (Reuters Digital News Report).

## Plan

1. **Pilot extraction: Switzerland** (decided Sep 2026). Validation benchmark: **Swissdox@LiRI** (~29M articles, 260+ Swiss outlets, print + online, near-complete except Italian-language CH media; ETH researchers have access via LiRI/UZH; restricted license — no redistribution, keep Swissdox data on ETH infrastructure only). Comparing CC extraction against Swissdox quantifies Common Crawl's coverage bias (paywalls: NZZ, Tamedia; small outlets) — a headline result for the methods paper. Germany was rejected as pilot (Kriesch & Losacker already provide an open German dataset → small contribution); Hungary is covered by a separate existing paper, so not used in the pilot, but in the comparative collection.
2. **Assess pilot quality** (coverage per outlet × month vs. Swissdox, extraction quality, face validity).
3. **Go directly comparative**: collect the same data for the full country set — **28 countries, frozen in `data collection/countries.csv`** (Europe + North America ∩ DNR coverage ∩ at least electoral democracy per V-Dem at some point 2016–2025; Serbia and Turkey added manually as DNR-covered autocratization cases). No country gets separate substantive treatment within this project.

The grant applications in `orga/` (Career Seed: Hungary proof-of-concept; Ambizione: larger agenda incl. surveys/experiments) are **background context only, not design documents** — the working plan is the one above.

## Key methodological facts

- **Data sources**: CC-NEWS corpus (RSS/sitemap-based, from Aug/Sep 2016, WARC format, on AWS S3); CC-MAIN for earlier years / gap-filling (monthly crawls since 2013, coverage must be assessed); Internet Archive as fallback.
- **Outlet population**: defined via Reuters DNR consumption data (e.g. outlets with ≥3% weekly reach); domains per outlet researched and mapped over time; domains drive targeted retrieval from the crawls.
- **Extraction pipeline** (adapt Kriesch & Losacker 2025): domain filtering → Trafilatura text extraction + language detection → text-quality heuristics → dedup.
- **Measurement**: dimensions operationalized as binary statements about article content; LLM-generated labels → fine-tuned multilingual NLI classifier → predictions for full corpus → outlet-year scores from shares of articles fulfilling/contradicting items; bias correction via design-based supervised learning (Egami et al. 2023) with hand-coded validation samples.
- **Aggregation**: outlet scores → country-year pluralism index, weighted by DNR audience reach. Exact index formulation still open.
- **Copyright**: full article text must NOT be redistributed. Publish derived measures, metadata, IDs/URLs (Kriesch & Losacker model: they publish embeddings + metadata; texts retrievable from CC by ID). Store full text privately.

## Folder layout

- `orga/` — related grant applications (context only)
- `lit/data collection/` — Kriesch & Losacker 2025, Scientific Data: German CC-NEWS pipeline (only extraction + storage stages relevant; ignore geolocation/NER/geoparsing). Code: github.com/LukasKriesch/CommonCrawlNewsDataSet
- `data collection/` — pipeline work lives here (incl. `data_collection_proposal.md`)
- `README.md` — human-facing project description + milestones

## Conventions & context

- Related infrastructure exists: `cnn_scraper` project (per-country news scrapers, config-driven) and a Reuters-DNR country extraction workflow (`dnr-country-extract` skill) — reuse the DNR extraction for outlet-universe building.
- Keep summaries short, bullet-pointed (user preference).
