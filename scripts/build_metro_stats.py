#!/usr/bin/env python3
"""Draw live GitHub statistics as metro station boards.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    stats-ridership.svg   contributions on a split-flap counter, streaks, repos, stars
    stats-lines.svg       top languages drawn as metro lines ("line usage")
    stats-timetable.svg   a year of contributions, one cell per day

Drawing the boards ourselves means the README never depends on third-party
card services that can be rate-limited or offline.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_metro_stats.py --user arman080325 --out dist
    python3 scripts/build_metro_stats.py --sample --out /tmp/preview        # offline preview
"""
import argparse
import datetime as dt
import json
import os
import random
import urllib.request

from metro_kit import AMBER, SIGN, SIGN2, Svg, panel, tw

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


# ── data ─────────────────────────────────────────────────────────────────
def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-metro"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def sample():
    """Deterministic fake data shaped like the API response, for offline previews."""
    rnd = random.Random(4)
    end = dt.date(2026, 11, 12)
    start = end - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    weeks, week, d = [], [], start
    while d <= end:
        busy = .2 + .7 * (d >= dt.date(2026, 5, 20))
        n = 0 if rnd.random() > busy else rnd.choice([1, 2, 3, 5, 8, 13, 30])
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


def heading(s, title, sub):
    s.text(28, 44, title, "signx", 19, "fg", ls=.8)
    s.text(29, 63, sub, "mono", 10, "muted", ls=1.2)


# ── boards ───────────────────────────────────────────────────────────────
def build_ridership(d, out):
    s = Svg(490, 300)
    panel(s, 16)
    heading(s, "RIDERSHIP", "CONTRIBUTIONS CARRIED  ·  PAST 12 MONTHS")
    # split-flap counter
    digits = f"{d['total']:,}"
    cw, ch, gap = 38, 54, 5
    x = 28
    s.style(".fp{transform-box:fill-box;transform-origin:center;animation:fp .5s cubic-bezier(.3,1.4,.5,1) var(--d) both}"
            "@keyframes fp{from{transform:scaleY(0)}}")
    for i, c in enumerate(digits):
        if c == ",":
            s.text(x + 3, 80 + ch - 6, ",", "signx", 34, "fg")
            x += 16
            continue
        s.rect(x, 80, cw, ch, 6, SIGN)
        s.add(f'<g class="fp" style="--d:{.15 + i * .12:.2f}s">')
        s.text(x + cw / 2, 80 + ch / 2 + 13, c, "signx", 38, AMBER, anchor="middle")
        s.add("</g>")
        s.add(f'<line x1="{x}" y1="{80 + ch / 2}" x2="{x + cw}" y2="{80 + ch / 2}" stroke="{SIGN2}" stroke-width="1.6"/>')
        x += cw + gap
    s.text(x + 8, 104, "COMMITS", "mono", 9.5, "muted", ls=1)
    s.text(x + 8, 118, "PULL REQUESTS", "mono", 9.5, "muted", ls=1)
    s.text(x + 8, 132, "ISSUES · REVIEWS", "mono", 9.5, "muted", ls=1)
    # four readouts
    tiles = [("CURRENT STREAK", d["current"], "DAYS", "l5"), ("LONGEST STREAK", d["longest"], "DAYS", "l3"),
             ("REPOSITORIES", d["repos"], "PUBLIC", "l1"), ("STARS", d["stars"], "TOTAL", "l4")]
    tw_, th = 102, 74
    for i, (lab, val, unit, col) in enumerate(tiles):
        tx = 28 + i * (tw_ + 9)
        s.add(f'<g class="fi" style="--d:{.5 + i * .12:.2f}s">')
        s.rect(tx, 156, tw_, th, 9, "card2", "border", 1)
        s.rect(tx + 10, 156, 28, 4, 2, col)
        s.text(tx + 10, 196, str(val), "signx", 26, "fg")
        s.text(tx + 12 + tw("signx", str(val), 26), 196, unit, "mono", 8.5, "muted", ls=.8)
        s.text(tx + 10, 216, lab, "mono", 8.5, "soft", ls=.6)
        s.add("</g>")
    s.circle(34, 262, 5, "l2", cls="pulse")
    s.text(46, 266, f"GOOD SERVICE  ·  {d['active']} ACTIVE DAYS  ·  BEST DAY {d['best']}", "monob", 10.5, "soft", ls=.8)
    s.save(os.path.join(out, "stats-ridership.svg"),
           f"Ridership board: {d['total']:,} contributions in the past 12 months. Current streak {d['current']} days, "
           f"longest streak {d['longest']} days, {d['repos']} public repositories, {d['stars']} stars.")


def build_lines(d, out):
    s = Svg(490, 300)
    panel(s, 16)
    heading(s, "LINE USAGE", "SHARE OF CODE BY LANGUAGE  ·  OWN REPOSITORIES")
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    biggest = max((v for _, v in top), default=1)
    cols = ["l1", "l2", "l3", "l4", "l5", "muted"]
    x0, x1 = 176, 404
    for i, (name, size) in enumerate(top):
        y = 96 + i * 33
        col = cols[i % len(cols)]
        s.rect(28, y - 11, 22, 22, 6, col)
        s.text(39, y + 5.5, str(i + 1), "signx", 14, "#14161a" if col == "l3" else "#ffffff", anchor="middle")
        s.text(60, y + 5, name, "sign", 14, "fg")
        s.path(f"M{x0},{y} H{x1}", "border", 7)
        end = x0 + (x1 - x0) * size / biggest
        s.add(f'<g class="grow" style="--d:{.2 + i * .12:.2f}s">')
        s.path(f"M{x0},{y} H{end:.1f}", col, 7)
        s.add("</g>")
        s.circle(x0, y, 5.5, "card", "fg", 2.4)
        s.add(f'<g class="fi" style="--d:{1.1 + i * .12:.2f}s">')
        s.circle(end, y, 5.5, "card", "fg", 2.4)
        s.add("</g>")
        s.text(462, y + 4.5, f"{100 * size / total:.1f}%", "monob", 12, "soft", anchor="end")
    s.save(os.path.join(out, "stats-lines.svg"),
           "Line usage, share of code by language: " + ", ".join(f"{n} {100 * v / total:.0f}%" for n, v in top))


def build_timetable(d, out):
    weeks = d["weeks"][-53:]
    s = Svg(1000, 300)
    panel(s, 16)
    heading(s, "TIMETABLE", "ONE CELL PER DAY  ·  LAST 52 WEEKS")
    s.text(972, 44, f"{d['total']:,}", "signx", 22, "fg", anchor="end")
    s.text(972, 63, "CONTRIBUTIONS", "mono", 10, "muted", anchor="end", ls=1.2)
    cell, step = 13, 16.4
    ox = (1000 - len(weeks) * step) / 2 + 18
    oy = 124
    counts = sorted(x["contributionCount"] for w in weeks for x in w["contributionDays"] if x["contributionCount"])
    q = [counts[int(len(counts) * f)] if counts else 1 for f in (.25, .5, .75)]
    # month line with stations
    s.path(f"M{ox},{oy - 18} H{ox + (len(weeks) - 1) * step + cell}", "border", 3)
    last = None
    for wi, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            mx = ox + wi * step + cell / 2
            s.circle(mx, oy - 18, 4.5, "card", "fg", 2)
            s.text(mx, oy - 30, first.strftime("%b").upper(), "monob", 9.5, "soft", anchor="middle", ls=1)
            last = first.month
    for j, lab in enumerate(("S", "M", "T", "W", "T", "F", "S")):
        if j % 2 == 1:
            s.text(ox - 12, oy + j * step + 10.5, lab, "mono", 9, "muted", anchor="end")
    s.style(".cl{opacity:0;animation:cl .45s ease-out var(--d) forwards}@keyframes cl{to{opacity:var(--o,1)}}")
    for wi, w in enumerate(weeks):
        for x_ in w["contributionDays"]:
            n = x_["contributionCount"]
            dow = dt.date.fromisoformat(x_["date"]).isoweekday() % 7
            x, y = ox + wi * step, oy + dow * step
            if n == 0:
                s.rect(x, y, cell, cell, 3.2, "card2", "border", 1)
            else:
                lvl = 1 + sum(n > t for t in q)
                op = (.35, .58, .8, 1)[lvl - 1]
                s.add(f'<rect class="cl" x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3.2" '
                      f'style="fill:var(--l2);--o:{op};--d:{wi * .016:.3f}s"/>')
    by = oy + 7 * step + 22
    s.circle(34, by - 4, 5, "l5", cls="pulse")
    s.text(46, by, f"CURRENT STREAK {d['current']} DAYS  ·  LONGEST {d['longest']} DAYS", "monob", 10.5, "soft", ls=.8)
    lx = 972 - 5 * step - 44
    s.text(lx - 8, by, "QUIET", "mono", 9, "muted", anchor="end", ls=1)
    for i, op in enumerate((0, .35, .58, .8, 1)):
        x = lx + i * step
        if op == 0:
            s.rect(x, by - 11, cell, cell, 3.2, "card2", "border", 1)
        else:
            s.add(f'<rect x="{x:.1f}" y="{by - 11}" width="{cell}" height="{cell}" rx="3.2" style="fill:var(--l2);opacity:{op}"/>')
    s.text(lx + 5 * step + 4, by, "BUSY", "mono", 9, "muted", ls=1)
    s.save(os.path.join(out, "stats-timetable.svg"),
           f"Timetable: {d['total']:,} contributions over the last 52 weeks, one cell per day. Current streak "
           f"{d['current']} days, longest {d['longest']} days.")


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
    build_ridership(d, a.out)
    build_lines(d, a.out)
    build_timetable(d, a.out)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
