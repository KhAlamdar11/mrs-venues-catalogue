#!/usr/bin/env python3
"""Build README.md from the YAML data in data/.

Usage:
    python3 scripts/build.py              # validate + render README.md
    python3 scripts/build.py --check      # validate only (exit 1 on errors)
    python3 scripts/build.py --worklist   # print what the weekly update should research
    python3 scripts/build.py --today 2026-09-24   # pretend today is another date

Claude (or you) edit only the files in data/. README.md is fully generated.
Deadlines that are not announced yet are *predicted* from the most recent
known edition (same month/day, shifted by the venue's cadence in years).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"

TIERS = ("S", "A", "B")
# `area:` values, in display order. Venues default to "robotics"; special issues default to "mrs"
# (every tracked call is multi-robot-topical, whatever journal it is in).
AREAS = {
    "mrs": "🐝 Multi-robot & swarm",
    "robotics": "🤖 General robotics",
    "control": "🎛️ Control & networked systems",
    "ai": "🧠 AI, planning & learning",
}
AREA_ICON = {a: label.split()[0] for a, label in AREAS.items()}
STATUSES = ("confirmed", "tentative", "unverified")
DEADLINE_KEYS = ("abstract", "paper", "journal_transfer", "workshop_proposal", "late_breaking")
TIER_BLURB = {
    "S": "Flagship venues. Recognised across all of robotics / AI; where the most visible multi-robot work appears.",
    "A": "Excellent, selective venues: the leading dedicated multi-robot / swarm / multi-agent venues, "
         "plus the top of the neighbouring sub-fields (control, planning, algorithmic robotics, ...).",
    "B": "Solid, reputable venues; good for specialised, applied or early-stage multi-robot work.",
}
STALE_DAYS = 30          # re-verify entries older than this when a deadline is near
HORIZON_DAYS = 180       # "upcoming" window for the worklist
RECENT_DAYS = 21         # show deadlines that closed this recently


# ----------------------------------------------------------------------------- loading
def load(name: str) -> list[dict]:
    path = DATA / f"{name}.yaml"
    with path.open() as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        raise SystemExit(f"{path}: top level must be a list")
    return data


def as_date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def shift_years(d: dt.date, years: int) -> dt.date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, day=28)


# ----------------------------------------------------------------------------- validation
def validate(confs: list[dict], journals: list[dict], issues: list[dict]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def need(obj: dict, keys: tuple[str, ...], where: str) -> None:
        for k in keys:
            if obj.get(k) in (None, ""):
                errors.append(f"{where}: missing '{k}'")

    for c in confs:
        where = f"conferences/{c.get('id', '?')}"
        need(c, ("id", "name", "full_name", "tier", "field", "cadence_years", "url"), where)
        if c.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(c.get("id"))
        if c.get("tier") not in TIERS:
            errors.append(f"{where}: tier must be one of {TIERS}")
        if c.get("area", "robotics") not in AREAS:
            errors.append(f"{where}: area must be one of {tuple(AREAS)}")
        years = []
        for e in c.get("editions") or []:
            ew = f"{where}/{e.get('year', '?')}"
            need(e, ("year", "status"), ew)
            years.append(e.get("year"))
            if e.get("status") not in STATUSES:
                errors.append(f"{ew}: status must be one of {STATUSES}")
            try:
                start, end = as_date(e.get("start")), as_date(e.get("end"))
                dl = {k: as_date(v) for k, v in (e.get("deadlines") or {}).items() if k != "note"}
                as_date(e.get("verified"))
            except (ValueError, TypeError) as exc:
                errors.append(f"{ew}: bad date ({exc})")
                continue
            for k in dl:
                if k not in DEADLINE_KEYS:
                    errors.append(f"{ew}: unknown deadline key '{k}' (allowed: {DEADLINE_KEYS}, note)")
            if start and end and end < start:
                errors.append(f"{ew}: end before start")
            if start and dl.get("paper") and dl["paper"] > start:
                errors.append(f"{ew}: paper deadline after conference start")
            if dl.get("abstract") and dl.get("paper") and dl["abstract"] > dl["paper"]:
                errors.append(f"{ew}: abstract deadline after paper deadline")
            if e.get("status") == "confirmed" and not e.get("source"):
                warnings.append(f"{ew}: confirmed edition without 'source' URL")
        if len(years) != len(set(years)):
            errors.append(f"{where}: duplicate edition years")

    for j in journals:
        where = f"journals/{j.get('id', '?')}"
        need(j, ("id", "name", "full_name", "tier", "publisher", "url"), where)
        if j.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(j.get("id"))
        if j.get("tier") not in TIERS:
            errors.append(f"{where}: tier must be one of {TIERS}")
        if j.get("area", "robotics") not in AREAS:
            errors.append(f"{where}: area must be one of {tuple(AREAS)}")

    journal_ids = {j["id"] for j in journals if "id" in j}
    for i, s in enumerate(issues):
        where = f"special_issues/{s.get('title', i)!s:.50}"
        need(s, ("title", "journal", "deadline", "url", "status", "verified"), where)
        if s.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        if s.get("area", "mrs") not in AREAS:
            errors.append(f"{where}: area must be one of {tuple(AREAS)}")
        try:
            as_date(s.get("deadline"))
            as_date(s.get("verified"))
        except (ValueError, TypeError) as exc:
            errors.append(f"{where}: bad date ({exc})")
        if s.get("journal") not in journal_ids and not s.get("journal_name"):
            warnings.append(f"{where}: journal '{s.get('journal')}' not in journals.yaml; add 'journal_name'")
    return errors, warnings


# ----------------------------------------------------------------------------- analysis
@dataclass
class Deadline:
    date: dt.date
    kind: str                 # "paper", "abstract", ...
    year: int                 # edition year it belongs to
    predicted: bool
    status: str               # confirmed / tentative / unverified / predicted
    basis: str = ""           # e.g. "from 2026 (2026-03-02)"
    note: str = ""


@dataclass
class ConfView:
    conf: dict
    next_deadline: Deadline | None
    next_meeting: dict | None      # edition dict (may be synthetic/predicted)
    meeting_predicted: bool
    recent_deadline: Deadline | None


def editions(c: dict) -> list[dict]:
    return sorted(c.get("editions") or [], key=lambda e: e["year"])


def analyse_conf(c: dict, today: dt.date) -> ConfView:
    eds = editions(c)
    cadence = int(c.get("cadence_years", 1))

    # Known future deadlines (earliest first). Prefer the paper deadline, but if an
    # abstract deadline precedes it we still key the row on the paper deadline and show both.
    future: list[Deadline] = []
    recent: list[Deadline] = []
    for e in eds:
        dls = e.get("deadlines") or {}
        paper = as_date(dls.get("paper"))
        if paper is None:
            continue
        d = Deadline(paper, "paper", e["year"], False, e["status"], note=str(dls.get("note", "") or ""))
        if paper >= today:
            future.append(d)
        elif (today - paper).days <= RECENT_DAYS:
            recent.append(d)
    future.sort(key=lambda d: d.date)

    next_deadline = future[0] if future else None
    if next_deadline is None:
        base = next((e for e in reversed(eds) if as_date((e.get("deadlines") or {}).get("paper"))), None)
        if base:
            base_date = as_date(base["deadlines"]["paper"])
            k = 1
            while shift_years(base_date, k * cadence) < today:
                k += 1
            pd = shift_years(base_date, k * cadence)
            next_deadline = Deadline(pd, "paper", base["year"] + k * cadence, True, "predicted",
                                     basis=f"{c['name']} {base['year']} deadline {fmt_date(base_date)}")

    # Next meeting: first edition that has not ended yet.
    next_meeting, meeting_predicted = None, False
    for e in eds:
        end = as_date(e.get("end")) or as_date(e.get("start"))
        if end is None:
            if e["year"] >= today.year:
                next_meeting = e
                break
            continue
        if end >= today:
            next_meeting = e
            break
    if next_meeting is None and eds:
        last = eds[-1]
        start = as_date(last.get("start"))
        k = 1
        while start and shift_years(start, k * cadence) < today:
            k += 1
        next_meeting = {
            "year": last["year"] + k * cadence,
            "start": shift_years(start, k * cadence) if start else None,
            "end": None, "location": "TBA",
        }
        meeting_predicted = True

    return ConfView(c, next_deadline, next_meeting, meeting_predicted, recent[-1] if recent else None)


def edition_for(c: dict, year: int) -> dict | None:
    return next((e for e in c.get("editions") or [] if e["year"] == year), None)


# ----------------------------------------------------------------------------- formatting
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def fmt_date(d: dt.date | None) -> str:
    return f"{d.day:02d} {MONTHS[d.month - 1]} {d.year}" if d else "—"


def fmt_range(start: dt.date | None, end: dt.date | None) -> str:
    if not start:
        return "TBA"
    if not end or end == start:
        return fmt_date(start)
    if start.year == end.year and start.month == end.month:
        return f"{start.day:02d}–{end.day:02d} {MONTHS[start.month - 1]} {start.year}"
    if start.year == end.year:
        return f"{start.day:02d} {MONTHS[start.month - 1]} – {end.day:02d} {MONTHS[end.month - 1]} {start.year}"
    return f"{fmt_date(start)} – {fmt_date(end)}"


def days_left(d: dt.date, today: dt.date) -> str:
    n = (d - today).days
    if n < 0:
        return f"closed {-n}d ago"
    if n == 0:
        return "**today**"
    if n <= 14:
        return f"**{n}d** 🔥"
    return f"{n}d"


STATUS_BADGE = {
    "confirmed": "✅ confirmed",
    "tentative": "🟡 tentative",
    "unverified": "⚠️ unverified",
    "predicted": "🔮 predicted",
}


def dl_cell(d: Deadline | None, c: dict | None = None) -> str:
    if d is None:
        typical = (c or {}).get("typical_deadline")
        return f"_typically {typical}_" if typical else "TBA"
    if d.predicted:
        return f"~{fmt_date(d.date)}"
    return fmt_date(d.date)


def link(text: str, url: str | None) -> str:
    return f"[{text}]({url})" if url else text


def anchor(heading: str) -> str:
    """GitHub's heading slug: lowercase, drop punctuation/emoji, spaces -> hyphens."""
    return "#" + re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def area_of(item: dict, default: str = "robotics") -> str:
    return item.get("area", default)


def esc(text) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


LOC_BADGE = {"tentative": " 🟡", "unverified": " ⚠️"}


def location_cell(ed: dict | None) -> str:
    if not ed or not ed.get("location"):
        return "TBA"
    return esc(ed["location"]) + LOC_BADGE.get(ed.get("status", ""), "")


def meeting_cell(v: ConfView) -> str:
    m = v.next_meeting
    if not m:
        return "TBA"
    when = fmt_range(as_date(m.get("start")), as_date(m.get("end")))
    where = m.get("location") or "TBA"
    label = f"{v.conf['name']} {m['year']}"
    if v.meeting_predicted:
        return f"{label}: ~{when} (predicted)"
    badge = LOC_BADGE.get(m.get("status", ""), "")
    return f"{link(label, m.get('url'))}: {when}, {where}{badge}"


# ----------------------------------------------------------------------------- rendering
def render(confs, journals, issues, today: dt.date) -> str:
    views = [analyse_conf(c, today) for c in confs]
    jmap = {j["id"]: j for j in journals}
    open_issues = sorted(
        (s for s in issues if as_date(s["deadline"]) >= today),
        key=lambda s: as_date(s["deadline"]),
    )
    tier_rank = {t: i for i, t in enumerate(TIERS)}
    out: list[str] = []
    w = out.append

    w("# 🐝 Multi-Robot Systems Venues Catalogue")
    w("")
    w(f"_Last updated: **{today.isoformat()}** · generated by `scripts/build.py` from `data/*.yaml` — "
      "do not edit this file by hand._")
    w("")
    w("Where to publish **multi-robot, swarm and multi-agent robotics** research: the dedicated "
      "multi-robot venues, plus the general robotics, control and AI venues where multi-robot work "
      "routinely appears, and special issues on multi-robot topics.")
    w("")
    n_mrs = sum(1 for x in [*confs, *journals] if area_of(x) == "mrs")
    w(f"Tracking **{len(confs)} conferences**, **{len(journals)} journals** ({n_mrs} of them dedicated "
      f"multi-robot / swarm / multi-agent venues) and **{len(open_issues)} open special issues**, "
      "ranked into S / A / B tiers.")
    w("")
    w("**Areas:** " + " · ".join(AREAS.values()) + ".")
    w("")
    w("**Legend:** ✅ confirmed on the official site · 🟡 tentative (announced but may change) · "
      "⚠️ unverified (secondary source only) · 🔮 predicted from last edition's dates (`~` prefix) · "
      "🔥 ≤ 14 days left. Dates are the main paper deadline unless noted; always double-check the "
      "official site (time zones are usually AoE or US Pacific).")
    w("")
    w("## Contents")
    w("")
    w("- [⏰ Upcoming deadlines](#-upcoming-deadlines)")
    w("  - " + " · ".join(f"[{label}]({anchor(label)})" for label in AREAS.values()))
    for t in TIERS:
        w(f"- [Tier {t}](#tier-{t.lower()})")
    w("- [📰 Open special issues](#-open-special-issues)")
    w("- [📚 Full list](#-full-list)")
    w("- [Methodology](#methodology)")
    w("")

    # ---- upcoming deadlines (conferences + special issues), next 12 months, split by area
    w("## ⏰ Upcoming deadlines")
    w("")
    w("Everything with a submission deadline in the next 12 months, soonest first, split by area. "
      "Special issues are all on multi-robot topics, so they are listed with the multi-robot venues "
      "whatever journal they appear in.")
    w("")
    rows: dict[str, list] = {a: [] for a in AREAS}
    horizon = today + dt.timedelta(days=365)
    for v in views:
        d = v.next_deadline
        if d and d.date <= horizon:
            c = v.conf
            ed = edition_for(c, d.year)
            extra = []
            if ed:
                dls = ed.get("deadlines") or {}
                if dls.get("abstract") and as_date(dls["abstract"]) >= today:
                    extra.append(f"abstract {fmt_date(as_date(dls['abstract']))}")
                if dls.get("note"):
                    extra.append(esc(dls["note"]))
            if d.predicted:
                extra.append(f"based on {d.basis}")
            label = link(f"{c['name']} {d.year}", (ed or {}).get("url") or c.get("url"))
            rows[area_of(c)].append(
                (d.date, c["tier"], label, location_cell(ed), "Conference", dl_cell(d),
                 days_left(d.date, today), STATUS_BADGE[d.status], "; ".join(extra)))
    for s in open_issues:
        j = jmap.get(s["journal"])
        jname = j["name"] if j else s.get("journal_name", s["journal"])
        tier = j["tier"] if j else "–"
        dd = as_date(s["deadline"])
        if dd <= horizon:
            rows[area_of(s, "mrs")].append(
                (dd, tier, link(esc(s["title"]), s["url"]), "—", f"Special issue · {jname}",
                 fmt_date(dd), days_left(dd, today), STATUS_BADGE[s["status"]], esc(s.get("note", ""))))
    for area, heading in AREAS.items():
        w(f"### {heading}")
        w("")
        if not rows[area]:
            w("_Nothing in the next 12 months._")
            w("")
            continue
        w("| Deadline | Days left | Tier | Venue | Location | Type | Status | Notes |")
        w("|---|---|:-:|---|---|---|---|---|")
        for r in sorted(rows[area], key=lambda r: (r[0], tier_rank.get(r[1], 9))):
            w(f"| {r[5]} | {r[6]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[7]} | {r[8]} |")
        w("")

    recent = sorted((v for v in views if v.recent_deadline), key=lambda v: v.recent_deadline.date, reverse=True)
    if recent:
        w(f"<details><summary>Recently closed (last {RECENT_DAYS} days)</summary>")
        w("")
        for v in recent:
            d = v.recent_deadline
            loc = (edition_for(v.conf, d.year) or {}).get("location") or "TBA"
            w(f"- **{v.conf['name']} {d.year}** ({loc}) — closed {fmt_date(d.date)}")
        w("")
        w("</details>")
        w("")

    # ---- tiers
    for t in TIERS:
        w(f"## Tier {t}")
        w("")
        w(f"_{TIER_BLURB[t]}_")
        w("")
        tv = sorted((v for v in views if v.conf["tier"] == t),
                    key=lambda v: (v.next_deadline.date if v.next_deadline else dt.date.max))
        if tv:
            w(f"### Conferences ({len(tv)})")
            w("")
            w("| Venue | Field | Next paper deadline | Days left | Status | Next meeting |")
            w("|---|---|---|---|---|---|")
            for v in tv:
                c = v.conf
                d = v.next_deadline
                w(f"| {AREA_ICON[area_of(c)]} {link('**' + c['name'] + '**', c['url'])} | {esc(c['field'])} | "
                  f"{dl_cell(d, c)} | "
                  f"{days_left(d.date, today) if d else '—'} | {STATUS_BADGE[d.status] if d else '—'} | "
                  f"{meeting_cell(v)} |")
            w("")
        area_rank = {a: i for i, a in enumerate(AREAS)}
        tj = sorted((j for j in journals if j["tier"] == t),
                    key=lambda j: (area_rank[area_of(j)], j["name"].lower()))
        if tj:
            w(f"### Journals ({len(tj)})")
            w("")
            w("| Journal | Publisher | Scope | Conference presentation option | Open special issues |")
            w("|---|---|---|---|:-:|")
            for j in tj:
                n = sum(1 for s in open_issues if s["journal"] == j["id"])
                w(f"| {AREA_ICON[area_of(j)]} {link('**' + j['name'] + '**', j['url'])} — {esc(j['full_name'])} | "
                  f"{esc(j['publisher'])} | "
                  f"{esc(j.get('scope', ''))} | {esc(j.get('conference_option', '')) or '—'} | {n or '—'} |")
            w("")

    # ---- special issues
    w("## 📰 Open special issues")
    w("")
    if open_issues:
        w("| Deadline | Days left | Journal | Tier | Special issue | Status |")
        w("|---|---|---|:-:|---|---|")
        for s in open_issues:
            j = jmap.get(s["journal"])
            jname = j["name"] if j else s.get("journal_name", s["journal"])
            dd = as_date(s["deadline"])
            w(f"| {fmt_date(dd)} | {days_left(dd, today)} | {esc(jname)} | {j['tier'] if j else '–'} | "
              f"{link(esc(s['title']), s['url'])} | {STATUS_BADGE[s['status']]} |")
    else:
        w("_No open special issues tracked._")
    w("")

    # ---- full list
    w("## 📚 Full list")
    w("")
    w("All tracked venues, alphabetical.")
    w("")
    w("| Venue | Kind | Tier | Area | Field / publisher | Cadence | Full name |")
    w("|---|---|:-:|---|---|---|---|")
    allv = [(c["name"], "Conference", c["tier"], AREAS[area_of(c)], c["field"],
             "annual" if c["cadence_years"] == 1 else f"every {c['cadence_years']} yrs", c["full_name"], c["url"])
            for c in confs]
    allv += [(j["name"], j.get("kind", "Journal"), j["tier"], AREAS[area_of(j)], j["publisher"], "rolling",
              j["full_name"], j["url"])
             for j in journals]
    for name, kind, tier, area, field, cad, full, url in sorted(allv, key=lambda r: r[0].lower()):
        w(f"| {link(name, url)} | {kind} | {tier} | {area} | {esc(field)} | {cad} | {esc(full)} |")
    w("")

    # ---- methodology
    w("## Methodology")
    w("")
    w("**Scope.** This catalogue is for multi-robot systems research: multi-robot coordination, task "
      "allocation and planning (incl. multi-agent path finding), swarm robotics, distributed estimation "
      "and control, multi-agent learning, and multi-UAV / fleet deployments. It tracks the dedicated "
      "multi-robot, swarm and multi-agent venues (🐝), the general robotics flagships where most "
      "multi-robot papers appear (🤖), and the control (🎛️) and AI / planning / learning (🧠) venues "
      "where multi-robot work routinely appears. Sub-field venues with little multi-robot work (soft, "
      "medical, humanoid, HRI, vision) are deliberately left out. Special issues are only listed if "
      "multi-robot / swarm / multi-agent systems are their theme or an explicit topic.")
    w("")
    w("**Tiers** reflect standing *within the robotics and multi-robot community* (selectivity, citation "
      "impact, and how a paper there is perceived by hiring/tenure committees in robotics). Adjacent "
      "control and AI venues are tiered by overall prestige. Tiers are opinionated — edit `tier:` in "
      "`data/*.yaml` to taste.")
    w("")
    w("**Predictions.** When a venue has not announced its next deadline, the most recent known deadline is "
      "shifted forward by the venue's cadence (1 year, or 2 for biennial venues), keeping the same "
      "month/day. Most robotics venues are very regular (e.g. ICRA ≈ 15 Sep, IROS ≈ 1 Mar), so this is "
      "usually accurate to within ~2 weeks; the smaller multi-robot symposia (MRS, DARS, ANTS, SWARM) "
      "move around more. Predicted dates are prefixed with `~` and marked 🔮.")
    w("")
    w("**Updates.** Data is refreshed weekly by Claude using `.claude/commands/update-catalogue.md` "
      "(see [`CHANGELOG.md`](CHANGELOG.md) for what changed and [`CLAUDE.md`](CLAUDE.md) for the data schema).")
    w("")
    return "\n".join(out)


# ----------------------------------------------------------------------------- worklist
def worklist(confs, journals, issues, today: dt.date) -> str:
    lines: list[str] = []
    horizon = today + dt.timedelta(days=HORIZON_DAYS)

    def stale(verified) -> bool:
        v = as_date(verified)
        return v is None or (today - v).days > STALE_DAYS

    lines.append(f"# Weekly worklist for {today.isoformat()}  (priority order: S > A > B, soonest first)\n")
    lines.append("## 1. Predicted deadlines within the next "
                 f"{HORIZON_DAYS} days — find the official CFP / important-dates page")
    items = []
    for c in confs:
        v = analyse_conf(c, today)
        d = v.next_deadline
        if d is None:
            items.append((c["tier"], dt.date.max, f"- [{c['tier']}] {c['id']}: NO deadline history at all — "
                                                   f"find the last 1–2 editions' deadlines ({c['url']})"))
        elif d.predicted and d.date <= horizon:
            items.append((c["tier"], d.date, f"- [{c['tier']}] {c['id']} {d.year}: predicted ~{d.date} "
                                             f"({d.basis}) — {c['url']}"))
    lines += [i[2] for i in sorted(items, key=lambda i: (TIERS.index(i[0]), i[1]))] or ["- (none)"]

    lines.append("\n## 2. Known upcoming deadlines that are not 'confirmed' or are stale "
                 f"(> {STALE_DAYS} days since verified) — re-check for changes/extensions")
    items = []
    for c in confs:
        for e in c.get("editions") or []:
            p = as_date((e.get("deadlines") or {}).get("paper"))
            if p and today <= p <= horizon and (e["status"] != "confirmed" or stale(e.get("verified"))):
                items.append((c["tier"], p, f"- [{c['tier']}] {c['id']} {e['year']}: deadline {p}, "
                                            f"status={e['status']}, verified={e.get('verified')} — "
                                            f"{e.get('url') or c['url']}"))
    for s in issues:
        dd = as_date(s["deadline"])
        if today <= dd <= horizon and (s["status"] != "confirmed" or stale(s.get("verified"))):
            items.append(("SI", dd, f"- [SI] {s['journal']}: '{s['title'][:60]}' deadline {dd}, "
                                    f"status={s['status']} — {s['url']}"))
    lines += [i[2] for i in sorted(items, key=lambda i: (i[1], i[0]))] or ["- (none)"]

    lines.append("\n## 3. Next meeting unknown (no edition with future dates) — find host city/dates")
    items = []
    for c in confs:
        v = analyse_conf(c, today)
        if v.meeting_predicted or v.next_meeting is None:
            items.append(f"- [{c['tier']}] {c['id']} — {c['url']}")
    lines += sorted(items, key=lambda i: TIERS.index(i[3])) or ["- (none)"]

    lines.append("\n## 4. Special issues to archive (deadline passed) — delete from data/special_issues.yaml")
    items = [f"- {s['journal']}: '{s['title'][:70]}' (deadline {s['deadline']})"
             for s in issues if as_date(s["deadline"]) < today]
    lines += items or ["- (none)"]

    lines.append("\n## 5. Always: search for NEW multi-robot / swarm / multi-agent special issues / calls for "
                 "papers (journals list: " + ", ".join(j["id"] for j in journals) + ")")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--worklist", action="store_true", help="print research worklist")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = ap.parse_args()

    confs, journals, issues = load("conferences"), load("journals"), load("special_issues")
    errors, warnings = validate(confs, journals, issues)
    for msg in warnings:
        print(f"warning: {msg}", file=sys.stderr)
    for msg in errors:
        print(f"ERROR: {msg}", file=sys.stderr)
    if errors:
        return 1
    if args.worklist:
        print(worklist(confs, journals, issues, args.today))
        return 0
    if args.check:
        print(f"OK: {len(confs)} conferences, {len(journals)} journals, {len(issues)} special issues")
        return 0
    README.write_text(render(confs, journals, issues, args.today))
    print(f"wrote {README.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
