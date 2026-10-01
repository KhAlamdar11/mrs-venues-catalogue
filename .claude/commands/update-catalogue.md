---
description: Weekly refresh of multi-robot systems conference / journal / special-issue deadlines
---

You are refreshing the multi-robot systems venues catalogue in this repository. Read
`CLAUDE.md` first: it defines the scope, data schema, tier criteria and source-reliability
rules, and they apply throughout. You only edit files in `data/` and `CHANGELOG.md`;
`README.md` is generated.

$ARGUMENTS

## 0. Orient

1. Run `date +%F` — use that as today's date everywhere (for `verified:` fields and the changelog).
2. Run `python3 scripts/build.py --worklist`. This is your priority list. Work top-down:
   S before A before B, sooner deadlines first.
3. Download the ccf-deadlines dataset once as a cross-check (it is a curated, machine-readable
   source; treat it as reliability level 3):
   `curl -sL https://codeload.github.com/ccfddl/ccf-deadlines/tar.gz/refs/heads/main | tar xz -C "$TMPDIR"`
   (use your scratchpad directory if `$TMPDIR` is unset) and grep the relevant
   `conference/AI/*.yml` files when checking a venue.

## 1. Conferences (worklist sections 1–3)

For each item:

- Find the official edition website (search `"<NAME> <YEAR>" call for papers` or
  `important dates`), open it, and read the dates from the page text itself.
- Add or update the edition in `data/conferences.yaml`: dates, location, edition `url`,
  `deadlines` (+ `note` with time zone and "extended from …" if applicable), `status`,
  `source`, `verified: <today>`.
- If a deadline was **extended**, record the new date and keep the history in `note`.
- If only secondary sources exist, record it as `tentative`/`unverified` — never `confirmed`.
- If nothing is announced yet, leave the prediction alone (the renderer handles it) but make
  sure the most recent past edition's `paper` deadline is recorded — for "NO deadline history"
  items, find the last one or two editions' deadlines (the old edition sites, WikiCFP, dblp
  front matter, or ccf-deadlines) so predictions become possible.
- For any confirmed/tentative deadline in the next 60 days, re-open its page even if already
  confirmed — extensions are common in the final weeks.

Time-box: stop spending effort on a single B-tier venue after ~3 searches; note it in the
changelog as "could not verify" and move on.

## 2. Special issues (worklist sections 4–5)

- Delete special issues whose deadline has passed.
- Re-check open ones that are not `confirmed` or were verified > 30 days ago.
- Discover new calls. **Only multi-robot-topical calls qualify** (see `CLAUDE.md` →
  special_issues: the theme, or an explicit topic, must be multi-robot / swarm / multi-agent /
  distributed / cooperative / fleet systems). Check at least these sources each week:
  - npj Robotics collections: `nature.com/npjrobot/collections` (curl with a browser UA and a
    cookie jar; each collection page shows "Submission status" and "Submission deadline").
  - Frontiers in Robotics and AI, Multi-Robot Systems section:
    `frontiersin.org/journals/robotics-and-ai/sections/multi-robot-systems/research-topics`
    — open each topic; add only those "currently accepting articles" with a
    "Manuscript Submission Deadline" (skip extension-only / no-deadline topics). Also skim other
    sections' topics with "multi-", "swarm", "cooperative" or "collaborative" in the title.
  - IEEE RAS journal pages: `ieee-ras.org/publications/<t-ro|ra-l|t-ase|ram|t-fr|t-rl|ra-p>`
    → "special issues"/"special collections" pages (download linked CFP PDFs and read the
    deadline and topic list with `pdftotext` — RAS pages list some expired calls as "open").
  - IEEE CSS journals: `ieeecss.org/publication/transactions-control-network-systems/tcns-special-issues`
    and the TAC / L-CSS pages.
  - Springer (search snippets): Swarm Intelligence (`link.springer.com/journal/11721/collections`),
    Autonomous Robots (`/journal/10514/collections`), JAAMAS (`/journal/10458/collections`).
  - Web searches: `"multi-robot" special issue call for papers <current year>`,
    `"swarm robotics" special issue call for papers`, `"multi-agent" robotics special issue deadline`,
    `IJRR special issue call for papers`, `Science Robotics special issue call`,
    `"Robotics and Autonomous Systems" special issue multi-robot`,
    `Journal of Field Robotics special issue call for papers`, and the multirobotsystems.org
    news / CFP postings (via search snippets).
- Only add calls in journals that are in `data/journals.yaml`, or in other clearly reputable
  journals (use `journal_name`). Skip MDPI/Hindawi/paper-mill calls.
- Record the CFP URL (PDF or page), exact deadline, status, `verified: <today>`, and a `note`
  saying what the multi-robot angle is when the call is broader than multi-robot systems.

## 3. New venues (light touch)

If, while researching, you encounter a reputable venue we do not track that clearly meets tier B
or better *and* fits the multi-robot scope in `CLAUDE.md`, add it with at least one edition
with a deadline and the right `area` (`mrs` only if it is dedicated to multi-robot / swarm /
multi-agent systems). Do not re-add the sub-field venues the scope excludes. Do not change
existing tiers — instead, list tier-change suggestions in the changelog for the human to decide.

## 4. Build and validate

1. `python3 scripts/build.py --check` — fix every ERROR and any warning you introduced.
2. `python3 scripts/build.py` — regenerates `README.md`.
3. Skim the "Upcoming deadlines" table in README.md for anything implausible (a deadline after
   its conference, a predicted date that obviously contradicts what you just read, etc.).

## 5. Changelog

Prepend a section to `CHANGELOG.md` (newest first):

```markdown
## <today>
- **New confirmed deadlines:** …
- **Changed / extended:** … (old → new)
- **New special issues:** …
- **Removed (expired):** …
- **Could not verify:** …
- **Suggestions for the maintainer:** … (tier changes, venues to add, anything odd)
```

Omit empty bullets. Be concrete (venue, year, date, source).

## 6. Finish

If this directory is a git repository, commit `data/`, `README.md` and `CHANGELOG.md` with the
message `Weekly catalogue update <today>` (do not push). Then print a short summary: deadlines in
the next 30 days, what changed, and what could not be verified.

## Rules

- Never invent or "round" dates. A date goes into a `deadlines` map only if you read it on a
  page this run. Otherwise leave it out and let the renderer predict.
- Search-result summaries hallucinate; confirm facts in the fetched page or PDF text.
- Beware look-alike predatory events ("ICRA 2027 — International Conference on Robotics and
  Automation, Lisbon" on waset.org / conferenceindex.org). Official IEEE RAS editions are on
  `<year>.ieee-<name>.org`, `ieee-ras.org`, or linked from the society page.
- Keep YAML formatting consistent with the existing entries; do not reorder unrelated entries.
