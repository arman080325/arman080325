#!/usr/bin/env python3
"""Draw live GitHub statistics as blueprint "field measurement" sheets.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    stats-overview.svg   contributions, streaks drawn as dimension lines
    stats-languages.svg  top languages on a protractor gauge
    stats-activity.svg   a year of contributions as a plotted dot grid

Drawing the cards ourselves means the README never depends on third-party
card services that can be rate-limited or offline.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_blueprint_stats.py --user arman080325 --out dist
    python3 scripts/build_blueprint_stats.py --sample --out /tmp/preview      # offline preview
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request

import blueprint_kit as K
from blueprint_kit import (AMBER, CYAN, DIM, GREEN, INK, INK2, PAPER2, RED, Svg, arrowhead, dimension, paper,
                           tw)

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
SERIES = [CYAN, INK, AMBER, GREEN, RED, INK2]


# ── data ─────────────────────────────────────────────────────────────────
def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-blueprint"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def sample():
    """Deterministic fake data shaped like the API response, for offline previews."""
    rnd = random.Random(11)
    end = dt.date(2026, 11, 11)
    start = end - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    weeks, week, d = [], [], start
    while d <= end:
        busy = .25 + .65 * (d >= dt.date(2026, 5, 15))
        n = 0 if rnd.random() > busy else rnd.choice([1, 2, 3, 4, 6, 9, 14])
        week.append({"date": d.isoformat(), "contributionCount": n})
        if len(week) == 7:
            weeks.append({"contributionDays": week})
            week = []
        d += dt.timedelta(days=1)
    if week:
        weeks.append({"contributionDays": week})
    langs = [("JavaScript", 700), ("C", 520), ("TypeScript", 490), ("CSS", 465), ("HTML", 420), ("Java", 400)]
    nodes = [{"stargazerCount": 1, "languages": {"edges": [{"size": s * 1000, "node": {"name": n}}]}}
             for n, s in langs]
    total = sum(x["contributionCount"] for w in weeks for x in w["contributionDays"])
    return {"repositories": {"totalCount": 32, "nodes": nodes + [{"stargazerCount": 1, "languages": {"edges": []}}] * 24},
            "contributionsCollection": {"contributionCalendar": {"totalContributions": total, "weeks": weeks}}}


def summarise(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    counts = [x["contributionCount"] for w in cal["weeks"] for x in w["contributionDays"]]
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:  # a quiet "today" does not break the streak yet
        i -= 1
    while i >= 0 and counts[i] > 0:
        cur += 1
        i -= 1
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    langs = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return dict(total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"],
                repos=user["repositories"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
                active=sum(1 for c in counts if c), best=max(counts or [0]),
                langs=sorted(langs.items(), key=lambda kv: -kv[1]))


def sheet(s, label, title):
    paper(s)
    s.box(6, 6, s.w - 12, s.h - 12, INK2, 1)
    s.box(12, 12, s.w - 24, s.h - 24, INK, 1.4)
    s.text(28, 40, label, "monom", 10.5, DIM, ls=1)
    s.text(28, 68, title, "condb", 21, INK, ls=1)
    s.line(28, 82, s.w - 28, 82, INK2, .8)


# ── tiles ────────────────────────────────────────────────────────────────
def build_overview(d, out):
    s = Svg(490, 300)
    sheet(s, "MEASUREMENT M-01", "CONTRIBUTIONS · PAST 12 MONTHS")
    big = f"{d['total']:,}"
    s.text(28, 146, big, "condb", 58, INK, ls=1, cls="fi", d=.2)
    s.text(30, 166, "COMMITS · PULL REQUESTS · ISSUES · REVIEWS", "mono", 9.5, DIM, cls="fi", d=.4)
    # streaks as dimension lines, scaled to the longest
    span = 300
    longest = max(d["longest"], 1)
    cur_w = max(30, span * d["current"] / longest)
    dimension(s, 28, 28 + span, 202, f"LONGEST STREAK  {d['longest']} DAYS", INK2, draw=.4, size=10.5)
    dimension(s, 28, 28 + cur_w, 238, f"CURRENT {d['current']} D", RED, draw=.8, size=10.5, label_color=RED)
    # readings table on the right
    tx, ty = 346, 100
    rows = [("REPOS", d["repos"]), ("STARS", d["stars"]), ("ACTIVE DAYS", d["active"]), ("BEST DAY", d["best"])]
    s.add(f'<rect x="{tx}" y="{ty}" width="116" height="{len(rows) * 34}" fill="{PAPER2}" stroke="{INK}" stroke-width="1.2"/>')
    for i, (k, v) in enumerate(rows):
        y = ty + i * 34
        if i:
            s.line(tx, y, tx + 116, y, INK2, .8)
        s.text(tx + 10, y + 13, k, "mono", 8.5, DIM, ls=.8)
        s.text(tx + 10, y + 29, str(v), "condb", 15, CYAN if i == 0 else INK, cls="fi", d=.3 + i * .1)
    s.text(28, 268, "SOURCE: GITHUB API · PUBLIC CONTRIBUTIONS · RE-MEASURED EVERY 12 H", "mono", 9.5, DIM, ls=.4)
    s.save(os.path.join(out, "stats-overview.svg"),
           f"{d['total']:,} contributions in the past 12 months. Current streak {d['current']} days, longest "
           f"{d['longest']} days. {d['repos']} public repositories, {d['stars']} stars, {d['active']} active days.")


def build_languages(d, out):
    s = Svg(490, 300)
    sheet(s, "MEASUREMENT M-02", "LANGUAGES · SHARE OF CODE")
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    cx, cy, r = 162, 236, 100
    # protractor scale
    s.path(f"M{cx - r - 14},{cy} A{r + 14},{r + 14} 0 0 1 {cx + r + 14},{cy}", INK2, 1)
    s.line(cx - r - 22, cy, cx + r + 22, cy, INK2, 1)
    for t in range(0, 101, 5):
        a = math.pi * (1 - t / 100)
        long_ = t % 25 == 0
        r1, r2 = r + 14, r + (24 if long_ else 19)
        s.line(cx + r1 * math.cos(a), cy - r1 * math.sin(a), cx + r2 * math.cos(a), cy - r2 * math.sin(a),
               INK2, 1 if long_ else .7)
        if long_:
            s.text(cx + (r + 36) * math.cos(a), cy - (r + 36) * math.sin(a) + 3.5, str(t), "mono", 9, DIM,
                   anchor="middle")
    # arcs, drawn one after another
    acc = 0
    for i, (name, size) in enumerate(top):
        frac = size / total
        a0 = math.pi * (1 - acc)
        a1 = math.pi * (1 - acc - frac) + .012
        x0, y0 = cx + r * math.cos(a0), cy - r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy - r * math.sin(a1)
        s.path(f"M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}", SERIES[i % len(SERIES)], 16,
               draw=.2 + i * .25, t=.5, cap="butt")
        acc += frac
    s.circle(cx, cy, 4, INK, 1.2, INK)
    # legend
    lx = 326
    for i, (name, size) in enumerate(top):
        y = 112 + i * 26
        s.add(f'<g class="fi" style="--d:{.3 + i * .12:.2f}s">')
        s.add(f'<rect x="{lx}" y="{y - 9}" width="12" height="12" fill="{SERIES[i % len(SERIES)]}"/>')
        s.text(lx + 20, y + 1.5, name.upper(), "condb", 12.5, INK, ls=.8)
        s.text(462, y + 1.5, f"{100 * size / total:.1f}%", "mono", 11, INK2, anchor="end")
        s.add("</g>")
    s.text(lx, 270, "BY BYTES, OWN REPOS", "mono", 9, DIM, ls=.6)
    s.save(os.path.join(out, "stats-languages.svg"),
           "Top languages by share of code: " + ", ".join(f"{n} {100 * v / total:.0f}%" for n, v in top))


def build_activity(d, out):
    weeks = d["weeks"][-53:]
    s = Svg(1000, 300)
    sheet(s, "MEASUREMENT M-03", "CONTRIBUTION PLOT · ONE DOT PER DAY")
    step = 16.6
    ox = (1000 - len(weeks) * step) / 2 + 22
    oy = 118
    counts = sorted(x["contributionCount"] for w in weeks for x in w["contributionDays"] if x["contributionCount"])
    q = [counts[int(len(counts) * f)] if counts else 1 for f in (.25, .5, .75)]
    for j, lab in enumerate(("SUN", "", "TUE", "", "THU", "", "SAT")):
        if lab:
            s.text(ox - 14, oy + j * step + 3.5, lab, "mono", 8.5, DIM, anchor="end")
    last = None
    for wi, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            s.text(ox + wi * step, oy - 16, first.strftime("%b").upper(), "mono", 9, INK2)
            s.line(ox + wi * step, oy - 11, ox + wi * step, oy - 6, INK2, .8)
            last = first.month
        for x_ in w["contributionDays"]:
            n = x_["contributionCount"]
            dow = dt.date.fromisoformat(x_["date"]).isoweekday() % 7
            cx, cy = ox + wi * step, oy + dow * step
            delay = f"--d:{wi * .018:.3f}s"
            if n == 0:
                s.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.3" fill="{DIM}" opacity=".6"/>')
            else:
                lvl = 1 + sum(n > t for t in q)
                rr = (2.6, 3.8, 5.0, 6.4)[lvl - 1]
                col = RED if lvl == 4 else (CYAN if lvl == 3 else INK)
                s.add(f'<circle class="fi" style="{delay}" cx="{cx:.1f}" cy="{cy:.1f}" r="{rr}" fill="{col}"/>')
    # dimension across the year
    x1, x2 = ox - 6, ox + (len(weeks) - 1) * step + 6
    dimension(s, x1, x2, oy + 7 * step + 18, f"52 WEEKS  ·  {d['total']:,} CONTRIBUTIONS", DIM, draw=.4, size=10.5)
    # legend
    lx = 28
    ly = 274
    s.text(lx, ly, "SCALE", "mono", 9, DIM, ls=.8)
    for i, (rr, col, lab) in enumerate(((1.3, DIM, "0"), (2.6, INK, "LOW"), (5.0, CYAN, "HIGH"), (6.4, RED, "PEAK"))):
        x = lx + 60 + i * 64
        s.add(f'<circle cx="{x}" cy="{ly - 3.5}" r="{rr}" fill="{col}"/>')
        s.text(x + 10, ly, lab, "mono", 9, INK2)
    s.text(972, ly, f"CURRENT STREAK {d['current']} D  ·  LONGEST {d['longest']} D", "monom", 10, RED, anchor="end",
           ls=.6)
    s.save(os.path.join(out, "stats-activity.svg"),
           f"Contribution plot for the last year: {d['total']:,} contributions, current streak {d['current']} days.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="arman080325")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", action="store_true", help="use fake data (offline preview)")
    a = ap.parse_args()
    if a.sample:
        user = sample()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set (use --sample for an offline preview)")
        user = fetch(a.user, token)
    d = summarise(user)
    os.makedirs(a.out, exist_ok=True)
    build_overview(d, a.out)
    build_languages(d, a.out)
    build_activity(d, a.out)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
