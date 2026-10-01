# Multi-Robot Systems Venues Catalogue — working notes for Claude

This repo tracks conferences, journals and special issues for **multi-robot systems** research,
tiers them S/A/B, and publishes `README.md`. **`README.md` is generated — never edit it by
hand.** Edit the YAML in `data/`, then run `python3 scripts/build.py`.

The weekly refresh procedure is `.claude/commands/update-catalogue.md` (`/update-catalogue`).

## Scope

Multi-robot systems in the broad sense: multi-robot coordination, task allocation and planning
(incl. multi-agent path finding), swarm robotics and swarm intelligence, distributed estimation
and control, multi-agent learning, multi-UAV / fleet deployments. The catalogue contains:

- **Dedicated venues** (`area: mrs`): MRS, DARS, ANTS, SWARM, AAMAS; Swarm Intelligence, JAAMAS.
- **General robotics venues** (`area: robotics`) where most multi-robot papers appear: ICRA,
  IROS, RSS, CoRL, the IFRR symposia, CASE, SSRR, ICUAS; T-RO, IJRR, RA-L, AuRo, …
- **Adjacent venues** where multi-robot work routinely appears: control (`area: control` —
  CDC, ACC, ECC, L4DC, NecSys; T-CNS, TAC, Automatica, L-CSS) and AI / planning / learning
  (`area: ai` — NeurIPS, ICML, ICLR, AAAI, IJCAI, ICAPS, SoCS, ALIFE).

Robotics sub-field venues with little multi-robot work (soft, medical, humanoid, HRI,
mechatronics, computer vision) are deliberately left out — don't re-add them.

## Commands

```bash
python3 scripts/build.py              # validate + regenerate README.md
python3 scripts/build.py --check      # validate only
python3 scripts/build.py --worklist   # what needs researching this week
```

## Data schema

### `data/conferences.yaml` — list of venues

| field | required | notes |
|---|---|---|
| `id` | yes | short, lowercase, unique across all files (`icra`, `mrs`) |
| `name` | yes | display acronym |
| `full_name` | yes | |
| `tier` | yes | `S`, `A` or `B` (criteria below) |
| `field` | yes | short sub-field label; add `(adjacent)` for non-robotics venues |
| `area` | no | `mrs`, `robotics` (default), `control` or `ai` — which "Upcoming deadlines" table it goes in and its icon (🐝 🤖 🎛️ 🧠). `mrs` only for venues *dedicated* to multi-robot / swarm / multi-agent systems |
| `cadence_years` | yes | `1` annual, `2` biennial, `3` triennial — drives deadline prediction |
| `url` | yes | stable series homepage (not a single edition) |
| `typical_deadline` | no | free text shown when no deadline history exists ("mid-March") |
| `notes` | no | |
| `editions` | no | list, see below |

Edition fields: `year` (edition year, not deadline year), `start`, `end`, `location`, `url`,
`deadlines`, `status`, `source`, `verified`.

- `deadlines` is a map; allowed keys: `abstract`, `paper`, `journal_transfer`,
  `workshop_proposal`, `late_breaking`, plus a free-text `note` (time zone, "extended from …").
  `paper` is the one that drives the tables and predictions. Use `{}` if unknown.
- `status`: `confirmed` (read on the official edition site or the organising society's page),
  `tentative` (official but explicitly provisional, or official page not reachable and ≥ 2
  consistent secondary sources), `unverified` (single secondary source).
- `source`: URL where the facts were read. `verified`: ISO date you last checked it.
- **Keep at least one past edition with a `paper` deadline** per venue; predictions depend on it.
  Prune editions older than ~2 years once a newer edition has a deadline.

### `data/journals.yaml`

`id`, `name`, `full_name`, `tier`, `publisher`, `url` (required); `scope`,
`conference_option` (e.g. RA-L → ICRA/IROS), `area` (as above), `kind` (`Letters`,
`Magazine`, … default Journal).
No impact factors (they go stale and are easy to hallucinate).

### `data/special_issues.yaml`

`title`, `journal` (an id from journals.yaml — or any id plus `journal_name` for untracked
journals), `deadline`, `url` (the CFP itself), `status`, `verified` (required); `note`, `area`
(default `mrs`, so they all appear in the multi-robot deadlines table).
Delete entries whose deadline has passed.

**Only multi-robot-topical calls.** A call qualifies if multi-robot / swarm / multi-agent /
distributed / cooperative / fleet systems are its theme, or are named as an explicit topic —
then say which in `note` ("Has a 'Cooperative Multi-Robot Systems' topic track"). A general
call that merely *could* take a multi-robot paper does not qualify. Skip invitation-only calls
(e.g. the ANTS special issue in Swarm Intelligence) and research topics that only accept
"manuscript extensions".

## Tier criteria

- **S** — flagship; recognised across all of robotics (ICRA, IROS, RSS, CoRL; T-RO, IJRR,
  Science Robotics) plus the top ML venues where multi-agent learning work routinely appears.
- **A** — excellent, selective: the leading dedicated multi-robot venues (MRS, DARS, ANTS,
  AAMAS; Swarm Intelligence, JAAMAS) and the top of neighbouring sub-fields (ISRR, WAFR, CASE,
  CDC, L4DC, ICAPS; RA-L, AuRo, T-CNS, TAC, …).
- **B** — solid, reputable, more specialised or applied (SWARM, SSRR, ICUAS, ACC, ECC, SoCS, …).

Do not re-tier existing venues during routine updates; only add new venues that clearly meet
B or better *and* fit the scope above (IEEE RAS fully-sponsored/co-sponsored conferences, IFRR
symposia, IFAC / IEEE CSS events, established society journals). Never add predatory /
paper-mill venues (WASET, generic "ICRA 2027 in Lisbon" clones, "conferenceindex.org"
listings, MDPI special issues unless the user asks). ANTS is not ICSI (a different
"International Conference on Swarm Intelligence", optimisation-focused) — don't add ICSI.

## Source reliability (most → least)

1. The edition's official website / CFP PDF.
2. Organising society pages (ieee-ras.org events, ieeecss.org, ifrr.org, a2c2.org, the IEEE
   RAS multi-robot TC at `ieee-ras.org/multi-robot-systems/` and `multirobotsystems.org`,
   `iridia.ulb.ac.be/ants/`, `alife.org/conference/`, `ifac-control.org`).
3. Curated datasets: ccf-deadlines (`github.com/ccfddl/ccf-deadlines`, YAML under
   `conference/AI/`), aideadlin.es.
4. WikiCFP, mldeadlines, conference aggregators, social media — hints only, never `confirmed`.

Web-search result *summaries* are often wrong (e.g. they once placed L4DC 2027 in Zurich; the
official site says Stockholm; they gave the npj Robotics swarm collection deadline as 19 Sep
2026 when the page said 19 Dec). Confirm facts in the page text itself. Elsevier, Wiley and
Springer pages usually block fetching — use search snippets from the publisher domain and mark
such entries `tentative`. nature.com refuses WebFetch but works with
`curl -sL -A "<browser user agent>" -c jar -b jar`; frontiersin.org and the ieee-ras.org CFP
PDFs also fetch fine with curl. science.org and multirobotsystems.org block both — use search
snippets.
