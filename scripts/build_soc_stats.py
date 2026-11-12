#!/usr/bin/env python3
"""Draw the live SOC-wall panels from real GitHub data.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    live-feed.svg     event feed: the latest commits across public repositories
    live-gauge.svg    threat level (to bugs), driven by the current commit streak
    live-kpis.svg     headline numbers for the past 12 months
    live-volume.svg   contributions per week with a moving average
    live-mix.svg      language mix across own repositories

Drawing the panels ourselves means the README never depends on third-party
card services that can be rate-limited or offline.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_soc_stats.py --user arman080325 --out dist
    python3 scripts/build_soc_stats.py --sample --out /tmp/preview          # offline preview
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request

from soc_kit import (AMBER, BLUE, BORDER, DIM, MUTED, PANEL, PANEL2, RED, SOFT, TEAL, TEXT, VIOLET, Svg, fit,
                     header, lamp, tw, wall)

ORANGE = "#fb923c"
QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
        defaultBranchRef {
          target { ... on Commit { history(first: 4) { nodes {
            messageHeadline committedDate author { user { login } }
          } } } }
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
# (name, colour, first streak day of the level)
LEVELS = [("LOW", TEAL, 0), ("GUARDED", BLUE, 1), ("ELEVATED", AMBER, 7), ("HIGH", ORANGE, 30), ("SEVERE", RED, 60)]
LEVEL_CAP = 120  # streak at which the needle reaches the end of the scale


# ── data ─────────────────────────────────────────────────────────────────
def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-soc"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload and not payload.get("data"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def sample(login):
    """Deterministic fake data shaped like the API response, for offline previews."""
    rnd = random.Random(5)
    end = dt.date(2026, 11, 12)
    start = end - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    weeks, week, d = [], [], start
    while d <= end:
        busy = .2 + .7 * (d >= dt.date(2026, 5, 20))
        n = 0 if rnd.random() > busy else rnd.choice([1, 2, 3, 5, 8, 13, 30])
        if d >= end - dt.timedelta(days=33):
            n = max(n, 1)
        week.append({"date": d.isoformat(), "contributionCount": n})
        if len(week) == 7:
            weeks.append({"contributionDays": week})
            week = []
        d += dt.timedelta(days=1)
    if week:
        weeks.append({"contributionDays": week})
    langs = [("JavaScript", 700), ("C", 520), ("TypeScript", 490), ("CSS", 465), ("HTML", 420), ("Java", 400)]
    msgs = [("SiteShield-Web", "Add TLS configuration scanner and severity scoring"),
            ("arman-learning-streak", "Day 212: sliding window problems"),
            ("fsociety-web", "Refine attack tree visualiser animations"),
            ("Network-packet-analyzer", "Fix retransmission detection for out-of-order segments with a very long headline"),
            ("GitAtlas-Project", "Add recovery wizard playbook for detached HEAD"),
            ("SnapURL-Project", "Validate custom aliases against reserved routes"),
            ("cineroulette", "Normalize popularity per language <region> & tune weights"),
            ("Banking-Management-System-Java", "Lock accounts in deterministic order")]
    nodes = []
    for i, (repo, msg) in enumerate(msgs):
        when = dt.datetime(2026, 11, 12, 14, 2) - dt.timedelta(hours=i * 7 + 1)
        nodes.append({"name": repo, "stargazerCount": 1,
                      "languages": {"edges": [{"size": langs[i % 6][1] * 1000, "node": {"name": langs[i % 6][0]}}]},
                      "defaultBranchRef": {"target": {"history": {"nodes": [
                          {"messageHeadline": msg, "committedDate": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "author": {"user": {"login": login}}}]}}}})
    total = sum(x["contributionCount"] for w in weeks for x in w["contributionDays"])
    return {"repositories": {"totalCount": 32, "nodes": nodes},
            "contributionsCollection": {"contributionCalendar": {"totalContributions": total, "weeks": weeks}}}


def summarise(user, login):
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
    langs, events = {}, []
    for repo in user["repositories"]["nodes"]:
        for e in (repo.get("languages") or {}).get("edges") or []:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
        target = (repo.get("defaultBranchRef") or {}).get("target") or {}
        for c in (target.get("history") or {}).get("nodes") or []:
            author = ((c.get("author") or {}).get("user") or {}).get("login")
            if author and author.lower() != login.lower():
                continue  # bots and other contributors
            events.append((c["committedDate"], repo["name"], c["messageHeadline"]))
    events.sort(reverse=True)
    weekly = [sum(x["contributionCount"] for x in w["contributionDays"]) for w in cal["weeks"]]
    return dict(total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"], weekly=weekly,
                repos=user["repositories"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
                active=sum(1 for c in counts if c), best=max(counts or [0]),
                langs=sorted(langs.items(), key=lambda kv: -kv[1]), events=events[:8])


def level_for(streak):
    idx = max(i for i, (_, _, start) in enumerate(LEVELS) if streak >= start)
    lo = LEVELS[idx][2]
    hi = LEVELS[idx + 1][2] if idx + 1 < len(LEVELS) else LEVEL_CAP
    within = min(1.0, (streak - lo) / max(1, hi - lo))
    return idx, (idx + (.5 if idx == 0 else within)) / len(LEVELS)


# ── panels ───────────────────────────────────────────────────────────────
def build_feed(d, out):
    s = Svg(600, 340)
    wall(s, 12)
    header(s, "EVENT FEED", "LATEST COMMITS  ·  PUBLIC REPOS", BLUE)
    cols = [(24, "TIME (UTC)"), (118, "TYPE"), (176, "SOURCE"), (338, "EVENT")]
    for x, lab in cols:
        s.text(x, 68, lab, "mono", 8.5, MUTED, ls=1.4)
    rows = d["events"][:8]
    if not rows:
        s.text(24, 110, "No public commits found yet.", "ui", 13, SOFT)
    for i, (when, repo, msg) in enumerate(rows):
        y = 92 + i * 27
        s.add(f'<g class="fi" style="--d:{.25 + i * .22:.2f}s">')
        if i == 0:
            s.rect(16, y - 16, 568, 24, 5, PANEL2, BORDER, 1)
            lamp(s, 577, y - 4, TEAL, 3)
        t = dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ")
        s.text(24, y, t.strftime("%m-%d %H:%M"), "mono", 10.5, MUTED if i else SOFT)
        s.rect(118, y - 12, 44, 16, 3, PANEL, BLUE, 1)
        s.text(140, y - .5, "PUSH", "monob", 8.5, BLUE, anchor="middle", ls=1)
        s.text(176, y, fit(repo, "monom", 11, 150), "monom", 11, TEAL)
        s.text(338, y, fit(msg, "ui", 12, 226), "ui", 12, TEXT if i == 0 else SOFT)
        s.add("</g>")
    by = 318
    s.text(24, by, ">", "monob", 11, TEAL)
    s.text(38, by, "awaiting events", "mono", 10.5, MUTED)
    s.rect(38 + tw("mono", "awaiting events", 10.5) + 5, by - 10, 6, 12, 1, TEAL, cls="blink")
    s.text(576, by, f"{len(rows)} EVENTS SHOWN  ·  REFRESH 12H", "mono", 9, MUTED, anchor="end", ls=1)
    s.save(os.path.join(out, "live-feed.svg"),
           "Event feed of the latest commits: " + "; ".join(f"{r}: {m}" for _, r, m in rows[:5]))


def build_gauge(d, out):
    s = Svg(390, 340)
    wall(s, 12)
    header(s, "THREAT LEVEL", "TO BUGS", RED)
    idx, frac = level_for(d["current"])
    name, col, _ = LEVELS[idx]
    cx, cy, R = 195, 190, 112
    n = len(LEVELS)
    for i, (lname, lcol, start) in enumerate(LEVELS):
        a0 = math.pi * (1 - i / n) - .018
        a1 = math.pi * (1 - (i + 1) / n) + .018
        x0, y0 = cx + R * math.cos(a0), cy - R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy - R * math.sin(a1)
        s.path(f"M{x0:.1f},{y0:.1f} A{R},{R} 0 0 1 {x1:.1f},{y1:.1f}", lcol, 13, cap="butt",
               op=1 if i == idx else .28, cls="dr", delay=.1 + i * .12, t=.5)
        la = math.pi * (1 - i / n)
        s.text(cx + (R + 17) * math.cos(la), cy - (R + 17) * math.sin(la) + 3, str(start), "mono", 9, MUTED,
               anchor="middle")
    for t in range(0, 51):
        a = math.pi * (1 - t / 50)
        r1, r2 = R - 12, R - (19 if t % 10 == 0 else 15)
        s.path(f"M{cx + r1 * math.cos(a):.1f},{cy - r1 * math.sin(a):.1f} L{cx + r2 * math.cos(a):.1f},"
               f"{cy - r2 * math.sin(a):.1f}", DIM, 1)
    ang = -90 + 180 * frac
    s.style(f".nd{{transform-origin:{cx}px {cy}px;animation:nd 1.8s cubic-bezier(.3,1.3,.4,1) .5s both,"
            f"nw 3.4s ease-in-out 2.4s infinite}}"
            f"@keyframes nd{{from{{transform:rotate(-90deg)}}to{{transform:rotate({ang:.1f}deg)}}}}"
            f"@keyframes nw{{0%,100%{{transform:rotate({ang:.1f}deg)}}50%{{transform:rotate({ang + 1.6:.1f}deg)}}}}")
    s.add(f'<g class="nd" style="transform:rotate({ang:.1f}deg)">')
    s.path(f"M{cx - 4},{cy} L{cx},{cy - R + 22} L{cx + 4},{cy} Z", col, 1, fill=col)
    s.add("</g>")
    s.circle(cx, cy, 9, PANEL, col, 2.5)
    num = str(d["current"])
    s.text(cx - 46, cy + 62, num, "uib", 40, TEXT, anchor="end", ls=-1)
    s.text(cx - 38, cy + 46, "DAY", "mono", 9.5, MUTED, ls=1.6)
    s.text(cx - 38, cy + 60, "STREAK", "mono", 9.5, MUTED, ls=1.6)
    lw = tw("monob", name, 15, 2) + 34
    lx = cx + 22
    s.rect(lx, cy + 32, lw, 32, 6, PANEL2, col, 1.2)
    s.circle(lx + 14, cy + 48, 4, col, cls="pulse")
    s.text(lx + 26, cy + 53.5, name, "monob", 15, col, ls=2)
    s.text(cx, cy + 100, "LEVEL RISES WITH THE CURRENT COMMIT STREAK", "mono", 9, MUTED, anchor="middle", ls=1.2)
    s.text(cx, cy + 118, "0 LOW · 1 GUARDED · 7 ELEVATED · 30 HIGH · 60 SEVERE", "mono", 8.5, DIM, anchor="middle",
           ls=.6)
    s.save(os.path.join(out, "live-gauge.svg"),
           f"Threat level to bugs: {name.lower()}, driven by a current commit streak of {d['current']} days.")


def build_kpis(d, out):
    s = Svg(1000, 118)
    wall(s, 12)
    tiles = [("CONTRIBUTIONS · 12 MO", f"{d['total']:,}", TEAL), ("CURRENT STREAK", f"{d['current']} d", RED),
             ("LONGEST STREAK", f"{d['longest']} d", AMBER), ("ACTIVE DAYS", str(d["active"]), BLUE),
             ("PUBLIC REPOS", str(d["repos"]), VIOLET), ("STARS", str(d["stars"]), TEAL)]
    w = (956 - 5 * 10) / 6
    for i, (lab, val, col) in enumerate(tiles):
        x = 22 + i * (w + 10)
        s.add(f'<g class="fi" style="--d:{.1 + i * .1:.2f}s">')
        s.rect(x, 20, w, 78, 9, PANEL2, BORDER, 1)
        s.text(x + 14, 42, lab, "mono", 8.5, MUTED, ls=1.2)
        s.text(x + 14, 78, val, "uib", 26, TEXT, ls=-.5)
        s.add("</g>")
        s.rect(x + 14, 88, w - 28, 2.5, 1.2, col, cls="grow", d=.3 + i * .1, op=.85)
    s.save(os.path.join(out, "live-kpis.svg"),
           f"{d['total']:,} contributions in 12 months, current streak {d['current']} days, longest streak "
           f"{d['longest']} days, {d['active']} active days, {d['repos']} public repositories, {d['stars']} stars.")


def build_volume(d, out):
    s = Svg(600, 300)
    wall(s, 12)
    header(s, "EVENT VOLUME", "CONTRIBUTIONS PER WEEK  ·  52 WEEKS", TEAL)
    weekly = d["weekly"][-53:]
    weeks = d["weeks"][-53:]
    x0, x1, y0, y1 = 52, 576, 76, 232
    top = max(max(weekly, default=1), 1)
    nice = max(5, int(math.ceil(top / 5.0)) * 5)
    for g in range(0, 5):
        y = y1 - (y1 - y0) * g / 4
        s.path(f"M{x0},{y:.1f} H{x1}", BORDER, 1, dash=None if g == 0 else "2 5")
        s.text(x0 - 8, y + 3.5, str(int(nice * g / 4)), "mono", 9, MUTED, anchor="end")
    step = (x1 - x0) / len(weekly)
    bw = step * .68
    peak = weekly.index(max(weekly)) if weekly else 0
    for i, v in enumerate(weekly):
        h = (y1 - y0) * v / nice
        x = x0 + i * step + (step - bw) / 2
        if v:
            s.rect(x, y1 - h, bw, h, 1.5, AMBER if i == peak else TEAL, cls="rise", d=round(.15 + i * .018, 3),
                   op=1 if i == peak else .75)
    # 4-week moving average
    pts = []
    for i in range(len(weekly)):
        win = weekly[max(0, i - 3):i + 1]
        avg = sum(win) / len(win)
        pts.append(f"{x0 + i * step + step / 2:.1f},{y1 - (y1 - y0) * avg / nice:.1f}")
    if pts:
        s.path("M" + " L".join(pts), BLUE, 1.8, cls="dr", delay=1.0, t=2.0)
    if weekly:
        px = x0 + peak * step + step / 2
        py = y1 - (y1 - y0) * weekly[peak] / nice
        lab = f"PEAK {weekly[peak]}"
        anchor = "end" if px > 480 else "start"
        s.text(px + (-8 if anchor == "end" else 8), max(py - 4, y0 + 8), lab, "monob", 9.5, AMBER, anchor=anchor,
               ls=.8, cls="fi", d=1.4)
    last = None
    for i, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            s.text(x0 + i * step, y1 + 16, first.strftime("%b").upper(), "mono", 9, MUTED, ls=.8)
            last = first.month
    avg = sum(weekly) / max(1, len(weekly))
    s.rect(24, 268, 10, 10, 2, TEAL, op=.75)
    s.text(40, 277, "WEEKLY TOTAL", "mono", 9, SOFT, ls=1)
    s.path("M140,273 H160", BLUE, 1.8)
    s.text(166, 277, "4-WEEK AVERAGE", "mono", 9, SOFT, ls=1)
    s.text(576, 277, f"AVG {avg:.0f} / WEEK", "monom", 9.5, SOFT, anchor="end", ls=1)
    s.save(os.path.join(out, "live-volume.svg"),
           f"Contributions per week over the last 52 weeks. Peak week {max(weekly, default=0)}, average "
           f"{avg:.0f} per week.")


def build_mix(d, out):
    s = Svg(390, 300)
    wall(s, 12)
    header(s, "LANGUAGE MIX", "BY BYTES", VIOLET)
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    cols = [TEAL, BLUE, VIOLET, AMBER, RED, SOFT]
    x, bw = 24, 342
    cid = "mx"
    s.defs.append(f'<clipPath id="{cid}"><rect x="24" y="68" width="{bw}" height="12" rx="6"/></clipPath>')
    s.add(f'<g clip-path="url(#{cid})"><g class="grow" style="--d:.2s">')
    for i, (name, size) in enumerate(top):
        w = bw * size / total
        s.rect(x, 68, w + .6, 12, 0, cols[i % len(cols)])
        x += w
    s.add("</g></g>")
    for i, (name, size) in enumerate(top):
        y = 112 + i * 29
        col = cols[i % len(cols)]
        s.add(f'<g class="fi" style="--d:{.4 + i * .1:.2f}s">')
        s.rect(24, y - 10, 10, 10, 2.5, col)
        s.text(44, y, name, "ui", 13, TEXT)
        s.text(366, y, f"{100 * size / total:.1f}%", "monom", 11, SOFT, anchor="end")
        s.add("</g>")
        s.path(f"M176,{y - 4.5} H306", BORDER, 4)
        s.add(f'<g class="grow" style="--d:{.5 + i * .1:.2f}s">')
        s.path(f"M176,{y - 4.5} H{176 + 130 * size / max(v for _, v in top):.1f}", col, 4)
        s.add("</g>")
    s.save(os.path.join(out, "live-mix.svg"),
           "Language mix by bytes: " + ", ".join(f"{n} {100 * v / total:.0f}%" for n, v in top))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="arman080325")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", action="store_true", help="use fake data (offline preview)")
    a = ap.parse_args()
    if a.sample:
        user = sample(a.user)
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("GITHUB_TOKEN is not set (use --sample for an offline preview)")
        user = fetch(a.user, token)
    d = summarise(user, a.user)
    os.makedirs(a.out, exist_ok=True)
    build_feed(d, a.out)
    build_gauge(d, a.out)
    build_kpis(d, a.out)
    build_volume(d, a.out)
    build_mix(d, a.out)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"{len(d['events'])} feed events, top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
