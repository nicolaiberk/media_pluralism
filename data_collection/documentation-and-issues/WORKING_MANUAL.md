# Working Manual — verify the results, then pitch the method

*What you do by hand before the next meeting with Berk, and what to say when you get there.
Everything else — the method, the tooling — is in `../outlet_urls/CLAUDE.md`.
Last updated 15 September 2026.*

---

# Part 1 — Verify

The order matters: steps 2–3 produce the numbers Part 2 depends on. Budget about a working
day. All commands run from `data_collection/outlet_urls/`.

**How you record what you've checked.** Both data files have columns that are yours alone —
the scripts write them empty and never touch them again:

| File | Column | What you put there |
|---|---|---|
| `outlets_dnr_<country>.csv` | `human_checked` | `x` once you've read that row against the printed page |
| `domain_evidence_<country>.tsv` | `human_checked` | `x` once you've looked at that row's archive link |
| | `human_verdict` | what you decided — e.g. `confirmed`, `wrong domain: use tagesanzeiger.ch`, `blank` |
| | `human_note` | why, in a few words |

A row with an `x` has been seen by a person. A row without one hasn't. That is the audit
trail — and it's what Berk's "review every row" would produce, so it's worth keeping filled in.
`validate_outlets.py` prints the `human_checked` count so you can see progress.

## 1. Finish the identity check

The first retry is done: 93 `A3`, 56 `shared`, 8 `A3-noarticles`, 4 `needs-human`, and **78
still unanswered** because Archive.org throttled again. The evidence file now carries the
three human columns.

- [ ] Wait an hour or so from the last run, then run once more:
      ```
      python scripts/wayback_identity.py outlets_dnr_switzerland.csv --retry
      ```
      It keeps settled rows and your columns; it redoes only the failed ones.
- [ ] Regenerate the liveness file so it carries the capture artefact like Sweden's:
      ```
      python scripts/wayback_liveness.py outlets_dnr_switzerland.csv
      ```

Don't start step 2 until the unanswered count is near zero — you want the full `A3` population
to sample from.

## 2. Hand-check thirty `A3` rows — one hour, and it *is* the pitch

The automation's claim is that an `A3` verdict can be trusted. Nobody has measured that.

- [ ] Pick 30 `A3` rows at random — spread across outlets and years.
- [ ] For each, open the `artefact_url` (a Wayback link to the archived homepage). Two questions:
      *is this the outlet the row says?* and *is it a news site with articles, not a portal?*
- [ ] Put an `x` in `human_checked` and `confirmed` (or what's wrong) in `human_verdict`.
- [ ] Count. **Write the fraction down** — `30/30`, `28/30`, whatever it is.

If it's 29 or 30 out of 30, the tiered approach is evidenced. If it's worse, you've learned that
before proposing it to Berk instead of after.

## 3. Do the residual human review — and time it

This is what "manual review" looks like under the tiered approach. The time it takes is the
number Berk needs.

- [ ] Note the clock.
- [ ] Filter `domain_evidence_switzerland.tsv` to verdicts `needs-human`, `shared`,
      `A3-noarticles`. Group by `outlet_id` — a domain is a property of the outlet, not the
      year, so you decide per outlet and apply it to its rows.
- [ ] For each outlet, `PROCESS_OVERVIEW.md` Step 8b says what the verdict means and Step 8c
      what evidence settles it: an archived imprint, a redirect to a confirmed domain, or two
      independent sources. Twenty minutes per outlet, then stop — blanking the domain and saying
      why is a legitimate verdict.
- [ ] Record it: `x`, `human_verdict`, `human_note`, on every row of that outlet you looked at.
- [ ] The `shared` domains — `20min.ch`, `blick.ch`, `lematin.ch` — you can't settle alone;
      they're open question 10. Mark `x`, verdict `shared - pending Q10`, move on.
- [ ] Note the clock. **That elapsed time is the residual review cost for one country.**

## 4. Clear the `UNVERIFIED` notes — 20 min

- [ ] Search the CSV `notes` for `UNVERIFIED`. Six outlets. Step 3 has now either answered
      each or told you why it's still open. Update the note either way. SonntagsZeitung is
      already rewritten with the evidence.

## 5. Spot-check three charts — 20 min

The Swiss transcription already survived an independent blind re-run (all 504 values matched).
Your check is confirmation, so three charts, one per layout era:

- [ ] DNR **2019**, PDF p. 113 — two-series bars, German pair on top
- [ ] DNR **2022**, PDF p. 107 — the last year German is on top
- [ ] DNR **2026**, PDF p. 120 (printed 117) — solid bars, French on top

Read the CSV rows against the bars, top to bottom. Brand exactly as printed; number at the end
of the full bar. Put an `x` in `human_checked` on each row you confirm. Watch clusters of equal
values — several brands at 10 in the 2026 German online chart — that's where a swap would hide.

Sweden has **not** had a blind re-run. Its three charts are first verification, not
confirmation; either do them or ask for the blind run first.

## 6. Validate and commit — 15 min

- [ ] `python scripts/validate_outlets.py` and `python scripts/validate_outlets.py outlets_dnr_sweden.csv`.
      Both must say PASS.
- [ ] Nothing is committed. `main` is protected. From the repo root:
      ```bash
      git switch main && git pull
      git switch -c data/changing-column-types
      git add .gitignore data_collection dnr_pdfs
      git commit -m "add Swiss and Swedish outlet registries with schema extensions and tooling"
      git push -u origin data/changing-column-types
      ```
- [ ] Open the PR on GitHub (**Compare & pull request** button — no `gh` here). Description in
      Part 2, §5. The eight added columns and `human_checked` are not in Berk's
      `RA_instructions_outlets.md`; say so in the PR rather than editing his file silently.

## 7. Log your hours

Before the meeting. Freelance, first invoice.

---

# Part 2 — The pitch

## 1. The claim, in one sentence

*Review every outlet-era, not every row; automate the three signals that establish a domain;
have a human look only at what automation can't settle — and here are the numbers.*

## 2. Start by conceding what he's right about

Identity is exactly the thing that needs a person, and the failure is silent. Give him the
example: `sonntagszeitung.ch` is live every year, has 73,000 archived pages, **and would pass a
Common Crawl match** — yet the articles lived on `tagesanzeiger.ch`. A fetchability test alone
would have scraped an e-paper portal and called it done.

Then say the disagreement isn't *whether* a person looks, it's *at which rows*.

## 3. The unit of review is wrong by a factor of ten

A domain is a property of an outlet-era, not a row. NZZ's domain in 2019 and 2020 is one fact,
not two. Switzerland's 504 rows are ~45 (outlet, domain) pairs; 26 countries is ~1,200 pairs,
not ~10,000 rows. And most of those pairs are `nzz.ch = NZZ`, where a glance adds nothing a
masthead check didn't already establish.

Worth adding: a person reviewing 10,000 near-identical rows makes errors from attention
fatigue. A documented automated check plus targeted review is more reliable than exhaustive
manual review, not less.

## 4. Three signals, automated, per domain-year

| Signal | Question | Catches |
|---|---|---|
| Liveness | Was the host archived that year? | domains that didn't exist yet, or had died |
| Article-bearing | Did it carry article-shaped URLs? | portals, e-papers, redirects — `bluenews.ch` every year |
| Identity | Was the outlet's name in its masthead? | live hosts that belong to someone else — `20minuten.ch`, `blickamabend.ch` after 2018 |

Each catches what the others miss. A domain-year with all three has a documented artefact
behind each. A domain-year missing any goes to a person, with the evidence attached.

**On Common Crawl match as the acceptance test:** it's the right *final* gate and should stay.
But it tests fetchability — liveness plus article-bearing. It's silent on identity, and
identity is where the dangerous errors live.

## 5. Your numbers — fill in from Part 1

- Step 2: **___ / 30** `A3` rows held up on hand inspection.
- Step 3: residual human review for Switzerland took **___ hours** across **17 outlets**.
- The evidence file: **___** domain-years settled automatically (`A3`), **___** to a person -
  read the counts off the verdict column.
- Per-country estimate under his approach: ~500 rows × a minute = **8+ hours**. Under this:
  the step-3 number.

## 6. What stays human, said plainly

- Rebrand versus domain sale — a redirect can't tell them apart.
- Shared domains — the tool confirms `20min.ch` is 20 Minuten's; it can't say whose articles.
- An outlet whose name legitimately appears on someone else's site.

These are in the evidence file as `needs-human` and `shared`, with a Wayback link each. That's
the audit trail manual review is *for*, and it's more than a manual reviewer leaves behind.

## 7. The ask

Approve the tiered approach for the roll-out: automated three-signal check for every
domain-year; human review of the flagged outlets plus a random sample of the passes; Common
Crawl match as the final gate. Switzerland and Sweden as the worked cases.

## 8. Objections you'll get, and the answers

**"The keyword match could pass the wrong site."** — It could. That's why the sample in step 2
exists, and why the result is a number, not an assurance. Offer to raise the sample size.

**"What about outlets that changed domain mid-period?"** — The liveness discontinuity and the
brand-string change are both triggers (`CLAUDE.md` §14a–b); Blue News was caught exactly that
way. Nothing in the Swiss set turned out to have moved.

**"I'd still rather see every row."** — Then the evidence file *is* every row, with a verdict
and a link per domain-year, sorted so the uncertain ones are on top. Reviewing it takes less
time than transcribing it, and it's what he'd have produced by hand.

---

# Part 3 — Settle these in the meeting

Six questions remain in `OPEN_QUESTIONS.md`; a meeting can do three or four. These change the
data if answered differently:

1. **Shared domains** (#10) — split by path/language at extraction, or accept the merge? Lead
   with this one; it's also the honest case for some human review.
2. **The Swedish "ALSO" box** (#9) — the partisan outlets a pluralism measure exists to see,
   printed 2018–2020 outside the chart. Include?
3. **The commercial-TV ids** (#5) — two ids for one survey item; merge? Trivial, zero risk, and
   the rows are laid out in the file so it's a ten-second answer.
4. **20 Minuten's two editions** (#4) — one id or two? Tied to #10.

Questions 8 (public-broadcaster sub-splits) and 11 (Common Crawl check in the registry or not)
can go in the PR for asynchronous answers.

---

# Part 4 — Where everything is

| | Where |
|---|---|
| The method | `../outlet_urls/CLAUDE.md` |
| Data | `../outlet_urls/outlets_dnr_switzerland.csv`, `outlets_dnr_sweden.csv` |
| Evidence | `../outlet_urls/domain_evidence_*.tsv`, `wb_years_*.tsv` |
| Questions for Berk | `OPEN_QUESTIONS.md` — this folder |
| Open risks / fixed defects | `Failure_Modes_Register.docx`, `Fixed_Issues.docx` — this folder |
| Source PDFs | `ETH Media Pluralism/dnr_pdfs/` — outside the repo |
