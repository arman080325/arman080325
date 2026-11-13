#!/usr/bin/env python3
"""Draw the live "Secure by Design" panels from real GitHub data.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    live-summary.svg   headline numbers over a 52-week contribution sparkline
    live-gitlog.svg    `git log --oneline` of the latest commits across public repos
    live-langs.svg     language mix across own repositories
    live-coverage.svg  a year of contributions as a "commit coverage" heatmap

Drawing the panels ourselves means the README never depends on third-party
card services that can be rate-limited or offline.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_secure_stats.py --user arman080325 --out dist
    python3 scripts/build_secure_stats.py --sample --out /tmp/preview      # offline preview
"""
import argparse
import datetime as dt
import json
import os
import random
import urllib.request

from secure_kit import (BORDER, BUILD, BUILD2, CYAN, DIM, FN, MUTED, PANEL2, SAFE, SOFT, TEXT, VULN, WARN, Svg,
                        card, fit, tw, window_bar)

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
            abbreviatedOid messageHeadline committedDate author { user { login } }
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


# ── data ─────────────────────────────────────────────────────────────────
def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-secure-stack"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload and not payload.get("data"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def sample(login):
    """Deterministic fake data shaped like the API response, for offline previews."""
    rnd = random.Random(6)
    end = dt.date(2026, 11, 13)
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
    msgs = [("SiteShield-Web", "feat(scanner): add TLS configuration checks"),
            ("arman-learning-streak", "log: 2026-11-13"),
            ("fsociety-web", "refine attack tree animations and copy for the roadmap section"),
            ("Network-packet-analyzer", "fix retransmission detection for out-of-order segments"),
            ("GitAtlas-Project", "add recovery playbook for detached HEAD"),
            ("SnapURL-Project", "validate custom aliases against reserved routes"),
            ("cineroulette", "normalize popularity per language <region> & tune weights"),
            ("Banking-Management-System-Java", "lock accounts in deterministic order")]
    nodes = []
    for i, (repo, msg) in enumerate(msgs):
        when = dt.datetime(2026, 11, 13, 9, 30) - dt.timedelta(hours=i * 9 + 1)
        nodes.append({"name": repo, "stargazerCount": 1,
                      "languages": {"edges": [{"size": langs[i % 6][1] * 1000, "node": {"name": langs[i % 6][0]}}]},
                      "defaultBranchRef": {"target": {"history": {"nodes": [
                          {"abbreviatedOid": f"{rnd.getrandbits(28):07x}", "messageHeadline": msg,
                           "committedDate": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            events.append((c["committedDate"], c.get("abbreviatedOid", "")[:7], repo["name"], c["messageHeadline"]))
    events.sort(reverse=True)
    weekly = [sum(x["contributionCount"] for x in w["contributionDays"]) for w in cal["weeks"]]
    return dict(total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"], weekly=weekly,
                repos=user["repositories"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
                active=sum(1 for c in counts if c), best=max(counts or [0]),
                langs=sorted(langs.items(), key=lambda kv: -kv[1]), events=events[:8])


def ago(when, now):
    t = dt.datetime.strptime(when, "%Y-%m-%dT%H:%M:%SZ")
    secs = max(0, (now - t).total_seconds())
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{int(secs // 86400)}d ago"


# ── panels ───────────────────────────────────────────────────────────────
def build_summary(d, out):
    s = Svg(1000, 196)
    card(s, 16, BUILD)
    weekly = d["weekly"][-52:]
    # sparkline background
    x0, x1, y0, y1 = 22, 978, 96, 178
    top = max(max(weekly, default=1), 1)
    step = (x1 - x0) / max(1, len(weekly) - 1)
    pts = [(x0 + i * step, y1 - (y1 - y0) * v / top) for i, v in enumerate(weekly)]
    s.defs.append(f'<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{BUILD}" '
                  f'stop-opacity=".35"/><stop offset="1" stop-color="{BUILD}" stop-opacity="0"/></linearGradient>')
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s.add(f'<path class="fi" style="--d:.8s" d="{line} L{x1},{y1} L{x0},{y1} Z" fill="url(#ar)"/>')
    s.path(line, BUILD2, 1.8, cls="dr", delay=.2, t=2.2)
    if pts:
        s.circle(pts[-1][0], pts[-1][1], 4, SAFE, cls="ping", d=2.4)
        s.circle(pts[-1][0], pts[-1][1], 3.5, SAFE)
    tiles = [("CONTRIBUTIONS", f"{d['total']:,}", "past 12 months", TEXT),
             ("CURRENT STREAK", f"{d['current']}", "days in a row", SAFE),
             ("LONGEST STREAK", f"{d['longest']}", "days", TEXT),
             ("ACTIVE DAYS", f"{d['active']}", "with commits", TEXT),
             ("REPOSITORIES", f"{d['repos']}", f"public  ·  {d['stars']} stars", TEXT)]
    w = 956 / len(tiles)
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 28 + i * w
        s.add(f'<g class="fi" style="--d:{.1 + i * .1:.2f}s">')
        s.text(x, 40, lab, "monob", 9.5, MUTED, ls=1.4)
        s.text(x, 76, val, "head", 30, col, ls=-.6)
        s.text(x + tw("head", val, 30, -.6) + 8, 76, sub, "mono", 10, MUTED)
        s.add("</g>")
        if i:
            s.path(f"M{x - 14},26 V82", BORDER, 1)
    s.text(978, 190, "52 WEEKS OF CONTRIBUTIONS", "mono", 9, MUTED, anchor="end", ls=1.2)
    s.save(os.path.join(out, "live-summary.svg"),
           f"{d['total']:,} contributions in the past 12 months, current streak {d['current']} days, longest "
           f"{d['longest']} days, {d['active']} active days, {d['repos']} public repositories and {d['stars']} stars.")


def build_gitlog(d, out):
    s = Svg(600, 316)
    card(s, 14, BUILD)
    window_bar(s, 0, 0, 600, "git log --oneline --all-repos", 36, 14)
    rows = d["events"][:8]
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    if rows:
        newest = dt.datetime.strptime(rows[0][0], "%Y-%m-%dT%H:%M:%SZ")
        now = max(now, newest)
    s.spans(20, 62, [("$ ", SAFE), ("git log ", TEXT), ("--oneline -8", MUTED)], 12)
    for i, (when, sha, repo, msg) in enumerate(rows):
        y = 90 + i * 25
        s.add(f'<g class="fi" style="--d:{.2 + i * .15:.2f}s">')
        s.text(20, y, sha or "-------", "mono", 12, FN)
        rx = 20 + tw("mono", "0000000 ", 12)
        rname = fit(repo, "mono", 11.5, 150)
        s.text(rx, y, rname, "mono", 11.5, CYAN)
        mx = rx + 158
        s.text(mx, y, fit(msg, "mono", 11.5, 580 - mx - 52), "mono", 11.5, TEXT if i == 0 else SOFT)
        s.text(580, y, ago(when, now), "mono", 10.5, MUTED, anchor="end")
        s.add("</g>")
    if not rows:
        s.text(20, 92, "No public commits found yet.", "mono", 12, SOFT)
    s.spans(20, 90 + 8 * 25 + 6, [("$ ", SAFE)], 12)
    s.rect(20 + tw("mono", "$ ", 12) + 2, 90 + 8 * 25 - 5, 7, 14, 1, SAFE, cls="blink")
    s.save(os.path.join(out, "live-gitlog.svg"),
           "Latest commits: " + "; ".join(f"{r}: {m}" for _, _, r, m in rows[:5]))


def build_langs(d, out):
    s = Svg(390, 316)
    card(s, 14, BUILD)
    s.text(22, 38, "LANGUAGES", "monob", 11, BUILD2, ls=2)
    s.text(368, 38, "BY BYTES", "mono", 10, MUTED, anchor="end", ls=1)
    s.path("M22,52 H368", BORDER, 1)
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    biggest = max((v for _, v in top), default=1)
    cols = [BUILD2, SAFE, CYAN, WARN, VULN, SOFT]
    for i, (name, size) in enumerate(top):
        y = 84 + i * 37
        col = cols[i % len(cols)]
        s.add(f'<g class="fi" style="--d:{.1 + i * .1:.2f}s">')
        s.text(22, y, name, "bodym", 13.5, TEXT)
        s.text(368, y, f"{100 * size / total:.1f}%", "mono", 11, SOFT, anchor="end")
        s.add("</g>")
        s.rect(22, y + 9, 346, 6, 3, PANEL2)
        s.rect(22, y + 9, 346 * size / biggest, 6, 3, col, cls="grow", d=.3 + i * .1)
    s.save(os.path.join(out, "live-langs.svg"),
           "Language mix by bytes: " + ", ".join(f"{n} {100 * v / total:.0f}%" for n, v in top))


def build_coverage(d, out):
    weeks = d["weeks"][-53:]
    s = Svg(1000, 268)
    card(s, 16, SAFE)
    s.text(28, 40, "COMMIT COVERAGE", "monob", 11, SAFE, ls=2)
    s.text(28, 66, "One square per day, last 52 weeks", "head", 18, TEXT)
    s.text(972, 40, f"{d['active']} / {sum(len(w['contributionDays']) for w in weeks)} days covered", "monob", 11,
           SOFT, anchor="end", ls=.6)
    cell, step = 13, 16.6
    ox = (1000 - len(weeks) * step) / 2 + 14
    oy = 108
    counts = sorted(x["contributionCount"] for w in weeks for x in w["contributionDays"] if x["contributionCount"])
    q = [counts[int(len(counts) * f)] if counts else 1 for f in (.25, .5, .75)]
    ramp = ["#173a33", "#1f6b55", "#2aa57a", SAFE]
    last = None
    for wi, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            s.text(ox + wi * step, oy - 10, first.strftime("%b"), "mono", 9.5, MUTED)
            last = first.month
        for x_ in w["contributionDays"]:
            n = x_["contributionCount"]
            dow = dt.date.fromisoformat(x_["date"]).isoweekday() % 7
            x, y = ox + wi * step, oy + dow * step
            if n == 0:
                s.rect(x, y, cell, cell, 3, PANEL2, BORDER, .8)
            else:
                lvl = sum(n > t for t in q)
                s.rect(x, y, cell, cell, 3, ramp[lvl], cls="fi", d=round(wi * .015, 3))
    for j, lab in enumerate(("", "Mon", "", "Wed", "", "Fri", "")):
        if lab:
            s.text(ox - 8, oy + j * step + 10, lab, "mono", 9, MUTED, anchor="end")
    by = oy + 7 * step + 26
    s.circle(34, by - 4, 4, SAFE, cls="pulse")
    s.text(44, by, f"current streak {d['current']} days  ·  longest {d['longest']} days  ·  best day {d['best']}",
           "mono", 10.5, SOFT)
    lx = 972 - 4 * step - 40
    s.text(lx - 8, by, "less", "mono", 9.5, MUTED, anchor="end")
    s.rect(lx, by - 11, cell, cell, 3, PANEL2, BORDER, .8)
    for i, c in enumerate(ramp):
        s.rect(lx + (i + 1) * step, by - 11, cell, cell, 3, c)
    s.text(lx + 5 * step + 2, by, "more", "mono", 9.5, MUTED)
    s.save(os.path.join(out, "live-coverage.svg"),
           f"Commit coverage: {d['active']} active days in the last year, current streak {d['current']} days, "
           f"longest {d['longest']} days.")


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
    build_summary(d, a.out)
    build_gitlog(d, a.out)
    build_langs(d, a.out)
    build_coverage(d, a.out)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"{len(d['events'])} commits, top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
