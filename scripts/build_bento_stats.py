#!/usr/bin/env python3
"""Generate the live GitHub stats tiles for the bento README.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN, then draws three
tiles in the same style as the rest of the README:

    stats-overview.svg   contributions, streaks, repositories and stars
    stats-languages.svg  top languages across your own repositories
    stats-activity.svg   a year-long contribution heatmap

Drawing the cards ourselves means the README never depends on third-party
card services that can be rate-limited or offline.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_bento_stats.py --user arman080325 --out dist
    python3 scripts/build_bento_stats.py --sample --out /tmp/preview   # offline preview
"""
import argparse
import datetime as dt
import json
import os
import random
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import build_bento_assets as B  # noqa: E402  (shared fonts, tokens and SVG builder)

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
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
        "User-Agent": "profile-readme-stats"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def sample():
    """Deterministic fake data shaped like the API response, for previews."""
    rnd = random.Random(7)
    end = dt.date(2026, 11, 11)
    start = end - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # weeks start on Sunday
    weeks, week, d = [], [], start
    while d <= end:
        busy = 0.35 + 0.5 * (d.month in (6, 7, 8, 10, 11))
        n = 0 if rnd.random() > busy else rnd.choice([1, 1, 2, 3, 4, 6, 9, 12])
        if d >= end - dt.timedelta(days=33):
            n = max(n, 1)
        week.append({"date": d.isoformat(), "contributionCount": n})
        if len(week) == 7:
            weeks.append({"contributionDays": week})
            week = []
        d += dt.timedelta(days=1)
    if week:
        weeks.append({"contributionDays": week})
    langs = [("Java", "#b07219", 900), ("JavaScript", "#f1e05a", 700), ("Python", "#3572A5", 420),
             ("TypeScript", "#3178c6", 380), ("HTML", "#e34c26", 260), ("CSS", "#563d7c", 210), ("PHP", "#4F5D95", 40)]
    nodes = [{"stargazerCount": 1, "languages": {"edges": [{"size": s * 1000, "node": {"name": n, "color": c}}]}}
             for n, c, s in langs]
    total = sum(dd["contributionCount"] for w in weeks for dd in w["contributionDays"])
    return {"followers": {"totalCount": 12},
            "repositories": {"totalCount": 31, "nodes": nodes + [{"stargazerCount": 3, "languages": {"edges": []}}] * 24},
            "contributionsCollection": {"contributionCalendar": {"totalContributions": total, "weeks": weeks}}}


def summarise(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    # current streak: count back from today; a quiet "today" does not break it yet
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:
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
            n = e["node"]["name"]
            size, color = langs.get(n, (0, e["node"]["color"] or "#8b8b95"))
            langs[n] = (size + e["size"], color)
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])
    stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
    active_days = sum(1 for c in counts if c)
    return dict(total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"],
                repos=user["repositories"]["totalCount"], stars=stars,
                followers=user["followers"]["totalCount"], langs=top, active=active_days,
                best=max(counts) if counts else 0)


# ── tiles ────────────────────────────────────────────────────────────────
def build_overview(d):
    s = B.Svg(490, 250)
    s.style(B.RISE + B.PULSE)
    B.tile(s, "violet")
    B.eyebrow(s, 28, 44, "Past 12 months", "violet")
    big = f"{d['total']:,}"
    s.add('<g class="rise">')
    s.text(28, 104, big, "dispx", 52, "url(#og)", ls=-1.5)
    s.grad("og", [(0, "violet", 1), (1, "pink", 1)])
    s.text(30, 130, "contributions", "bodym", 15, "soft")
    s.add("</g>")
    cells = [("Current streak", f"{d['current']}", "days", "pink"),
             ("Longest streak", f"{d['longest']}", "days", "amber"),
             ("Repositories", f"{d['repos']}", "public", "cyan"),
             ("Stars earned", f"{d['stars']}", "total", "green")]
    # right-hand 2x2 grid
    gx, gy = 252, 64
    for i, (lab, val, unit, acc) in enumerate(cells):
        x = gx + (i % 2) * 112
        y = gy + (i // 2) * 84
        s.add(f'<g class="rise" style="animation-delay:{.15 + i * .1:.2f}s">')
        s.rect(x, y, 104, 74, 14, "tile2", "border")
        s.text(x + 12, y + 40, val, "disp", 24, "fg", ls=-.5)
        s.text(x + 14 + B.tw("disp", val, 24, -.5), y + 40, unit, "mono", 10.5, "muted")
        s.circle(x + 16, y + 58, 3.5, acc)
        s.text(x + 24, y + 62, lab, "body", 11, "muted")
        s.add("</g>")
    s.add('<line x1="28" y1="168" x2="222" y2="168" style="stroke:var(--border)"/>')
    s.text(28, 196, f"{d['active']} active days", "bodym", 14, "soft")
    s.text(28, 218, f"best day: {d['best']} contributions", "body", 13, "muted")
    s.save("stats-overview.svg", f"{d['total']:,} contributions in the past year, current streak {d['current']} days, "
                                 f"longest streak {d['longest']} days, {d['repos']} public repositories, {d['stars']} stars")


def build_languages(d):
    s = B.Svg(490, 250)
    s.style(B.RISE + ".grow{transform-box:fill-box;transform-origin:left;"
            "animation:grow 1.4s cubic-bezier(.2,.8,.2,1) .2s both}@keyframes grow{from{transform:scaleX(0)}}")
    B.tile(s, "cyan")
    B.eyebrow(s, 28, 44, "Languages", "cyan")
    s.text(28, 80, "What my repos are made of", "disp", 19, "fg", ls=-.4)
    top = d["langs"][:6]
    total = sum(v[0] for _, v in top) or 1
    x, bw = 28, 434
    s.defs.append('<clipPath id="bar"><rect x="28" y="98" width="434" height="14" rx="7"/></clipPath>')
    s.add('<g clip-path="url(#bar)" class="grow">')
    for name, (size, color) in top:
        w = bw * size / total
        s.add(f'<rect x="{x:.1f}" y="98" width="{w + .5:.1f}" height="14" fill="{color}"/>')
        x += w
    s.add("</g>")
    for i, (name, (size, color)) in enumerate(top):
        cx = 28 + (i % 2) * 222
        cy = 146 + (i // 2) * 32
        s.add(f'<g class="rise" style="animation-delay:{.4 + i * .08:.2f}s">')
        s.add(f'<circle cx="{cx + 6}" cy="{cy - 4}" r="5.5" fill="{color}"/>')
        s.text(cx + 20, cy + 1, name, "bodym", 14.5, "soft")
        s.text(cx + 200, cy + 1, f"{100 * size / total:.1f}%", "mono", 12.5, "muted", anchor="end")
        s.add("</g>")
    names = ", ".join(n for n, _ in top)
    s.save("stats-languages.svg", f"Top languages: {names}")


def build_activity(d):
    weeks = d["weeks"][-53:]
    cell, gap = 13.6, 3.2
    gw = len(weeks) * (cell + gap)
    s = B.Svg(1000, 278)
    s.style(B.RISE + ".sq{animation:sq .5s ease-out both}@keyframes sq{from{opacity:0;transform:scale(.4)}}")
    B.tile(s, "green")
    B.eyebrow(s, 28, 44, "Contribution heatmap", "green")
    s.text(28, 80, f"{d['total']:,} contributions in the last year", "disp", 19, "fg", ls=-.4)
    counts = sorted(c["contributionCount"] for w in weeks for c in w["contributionDays"] if c["contributionCount"])
    q = [counts[int(len(counts) * f)] if counts else 1 for f in (.25, .5, .75)]
    ox = (1000 - gw) / 2 + 10
    oy = 122
    months, last = [], None
    for wi, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            months.append((wi, first.strftime("%b")))
            last = first.month
        for di, day in enumerate(w["contributionDays"]):
            n = day["contributionCount"]
            lvl = 0 if n == 0 else 1 + sum(n > t for t in q)
            x = ox + wi * (cell + gap)
            y = oy + int(dt.date.fromisoformat(day["date"]).isoweekday() % 7) * (cell + gap)
            delay = f'style="animation-delay:{wi * .012:.3f}s;transform-box:fill-box;transform-origin:center"'
            if lvl == 0:
                s.add(f'<rect class="sq" style="animation-delay:{wi * .012:.3f}s;transform-box:fill-box;'
                      f'transform-origin:center;fill:var(--tile2);stroke:var(--border)" '
                      f'x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3.2"/>')
            else:
                op = (.32, .55, .78, 1)[lvl - 1]
                s.add(f'<rect class="sq" {delay} x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3.2" '
                      f'opacity="{op}" fill="currentColor"/>')
    for wi, label in months:
        s.text(ox + wi * (cell + gap), oy - 8, label, "mono", 10.5, "muted")
    # legend
    lx = 1000 - 28 - 5 * (cell + gap) - 70
    s.text(lx - 6, 258, "less", "mono", 10.5, "muted", anchor="end")
    for i, op in enumerate((0, .32, .55, .78, 1)):
        x = lx + i * (cell + gap)
        if op == 0:
            s.add(f'<rect x="{x}" y="{247}" width="{cell}" height="{cell}" rx="3.2" style="fill:var(--tile2);stroke:var(--border)"/>')
        else:
            s.add(f'<rect x="{x}" y="{247}" width="{cell}" height="{cell}" rx="3.2" opacity="{op}" fill="currentColor"/>')
    s.text(lx + 5 * (cell + gap) + 4, 258, "more", "mono", 10.5, "muted")
    s.text(28, 258, f"current streak {d['current']} days  ·  longest {d['longest']} days", "mono", 11.5, "muted")
    # the heatmap colour follows the theme's green accent
    s.style("svg{color:var(--green)}")
    s.save("stats-activity.svg", f"Contribution heatmap: {d['total']:,} contributions in the last year")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="arman080325")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fonts", default=os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    ap.add_argument("--sample", action="store_true", help="use fake data (offline preview)")
    a = ap.parse_args()
    B.OUT = a.out
    B.load_fonts(a.fonts)
    if a.sample:
        user = sample()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set (use --sample for an offline preview)")
        user = fetch(a.user, token)
    d = summarise(user)
    build_overview(d)
    build_languages(d)
    build_activity(d)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, "
          f"{d['repos']} repos, top langs {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
