# To-do: outlet domains and Swiss pilot

*Milestones until Christmas 2026. Step numbers refer to `data_collection/outlet_urls/outlet_domains_plan.md`; results so far are in `data_collection/outlet_urls/extraction_report.md`. Last updated 2026-11-27.*

## Done

- [x] Outlets from the DNR 2012–2026, checked by the RA (887 outlets in 28 countries for 2016–2026)
- [x] Step 1: candidate domains from Wikidata (website for 796 of 887 outlets) and earlier domains from its edit history

## Open decisions (block the steps below)

- [ ] **AWS account** for the Common Crawl index and the CC-NEWS scans — needed from 7 Dec; request this week
- [ ] **How the step 2 agent runs**: subagents in Claude Code, or a script on the Claude API (reproducible, billed separately)
- [ ] **Human review in step 2**: none, flagged rows only, or flagged rows plus a 10% sample (60–90 outlets)
- [ ] **Storage location** for raw article records (private, not in the repo) — needed by 14 Dec

## Milestones

### By 4 Dec — domain registry v1 (step 2)

- [ ] Pilot the agent search on the 34 Swiss outlets; settle the output format and the cost per outlet
- [ ] Run it for all 887 outlets: every domain used 2016–2026, with first and last year, evidence URL and confidence
- [ ] Write `outlet_domains.csv` (outlet × domain × years) and fill `domain` in the yearly tables from it
- [ ] Add step 2 to the extraction report

### By 11 Dec — registry checked against Common Crawl (steps 3 and 4)

- [ ] Step 3: query the CC-MAIN columnar index for all registry domains, 2016–2026; flag `redirect` and `missing`
- [ ] Resolve flagged domains (redirect targets into the registry, `missing` looked up in the Wayback Machine)
- [ ] Step 4 for Switzerland: one-month CC-NEWS scan per year, one page per outlet × year, agent page check
- [ ] First article counts per Swiss outlet × scanned month

### By 18 Dec — Swiss raw corpus (step 5)

- [ ] Short design note: storage schema and extraction pipeline (replaces the deleted proposal; README still links to it)
- [ ] Full CC-NEWS scan for the Swiss domains, Aug 2016–2026; raw records stored privately

### By 23 Dec — freeze before the break

- [ ] Registry v1 frozen for all 28 countries
- [ ] Coverage table: articles per Swiss outlet × month
- [ ] Extraction report updated with steps 3–5; README milestone table updated

## After Christmas

- [ ] Text extraction, language detection, quality filters and deduplication on the Swiss corpus
- [ ] Pilot quality assessment (incl. Swissdox comparison, currently set aside)
- [ ] Steps 4 and 5 for the other 27 countries
- [ ] Draft for DVPW Methods, CompText
- [ ] Classifier development
- [ ] Validation


## Housekeeping

- [ ] Commit today's work on `data/outlet-domains` (report, plan update, history script and file, plot)
- [x] Close PR #1 (superseded; its scripts were dropped)
- [ ] Fix `data collection/` → `data_collection/` in `CLAUDE.md` and `README.md`; add `__pycache__` to `.gitignore`
