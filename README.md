# Mapping Media Pluralism from Web Archives


## Project description

A free and ideologically diverse media landscape is considered essential to democracy, yet no dataset documents the ideological diversity of national media markets — largely because collecting media content at scale, across countries and years, has been impractical. This project solves that problem by exploiting **Common Crawl** (especially the CC-NEWS corpus), a freely available web archive that has indexed news content since 2016 but has never been used in political science or communication research.

The project develops a reproducible pipeline that extracts, cleans, and analyzes news content from web archives and turns it into two public datasets:

1. **Outlet-level dataset** — political positions and characteristics of individual news outlets (per outlet-year), measured on four dimensions: government criticism, stance on liberal democracy, economic left-right, and cultural (GAL-TAN) orientation. Positions are estimated with fine-tuned NLI classifiers trained on LLM-annotated samples and validated against human coding.
2. **Country-year dataset** — comparative indicators of media pluralism, aggregating outlet positions weighted by audience reach (Reuters Digital News Report).

**Approach**: The pipeline is first built and validated on a **pilot country: Switzerland**. The near-complete Swissdox@LiRI archive (~29M articles, 260+ Swiss outlets, print and online; accessible to ETH researchers) serves as a gold-standard benchmark, allowing precise quantification of what Common Crawl covers and misses (paywalled content, small outlets, feed dropouts) — itself a core result for the methods paper. No open Swiss media dataset exists, so the pilot is a contribution in its own right; its multilingual media market (DE/FR) also stress-tests the pipeline. Once quality is established, collection extends directly to the comparative set of countries (~26 democracies with democratic starting points and available media consumption data).

**Outputs**: (i) a methods paper introducing Common Crawl as a data source for comparative media research; (ii) a methodological paper developing the content-based media pluralism measure; (iii) both datasets, publicly released (derived measures and metadata; full texts remain retrievable from Common Crawl via provided IDs).

## Major milestones

| # | Milestone | Target |
|---|-----------|--------|
| 1 | **Collection & storage design finalized** — pipeline architecture, storage schema, outlet registry format (see `data collection/data_collection_proposal.md`) | Autumn 2026 |
| 2 | **Outlet universe defined (pilot: Switzerland)** — outlets from Reuters DNR (reach threshold), domains researched and mapped over time; Swissdox@LiRI access secured | Autumn 2026 |
| 3 | **Pilot corpus collected (Switzerland)** — CC-NEWS extraction pipeline running end-to-end; texts cleaned, deduplicated, stored | Winter 2026/27 |
| 4 | **Pilot quality assessment** — coverage vs. Swissdox@LiRI (per outlet × month, paywall/coverage-bias quantification); per-outlet availability over time; decision on CC-MAIN backfill for pre-2016 | Winter 2026/27 |
| 5 | **Comparative extension** — roll-out to further countries  | Spring 2027 |
| 6 | **Measurement pipeline** — LLM annotation, NLI classifier fine-tuning, hand-coded validation, bias correction | Spring/Summer 2027 |
| 7 | **Dataset v1: outlet positions** — outlet-year positions, incl. validation survey on public outlet perceptions | Summer 2027 |
| 8 | **Dataset v1: media pluralism** — country-year index (aggregation weights from DNR) | Summer 2027 |
| 9 | **Papers submitted** — methods paper introducing the data source and pipeline (Political Communication / Political Analysis); measurement paper on the pluralism index | Late 2027 |

## Repository layout

- `orga/` — background context: related grant applications
- `lit/` — key literature (Kriesch & Losacker 2025: German CC-NEWS dataset & pipeline)
- `data collection/` — data collection pipeline and documentation
