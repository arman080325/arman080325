#!/usr/bin/env python3
"""Draw live terminal-style GitHub stat panels for the terminal-edition README.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    term-recon.svg     `./recon --target=self`: contributions, streaks, repos, stars
    term-langs.svg     `cloc --by-language`: language mix across own repositories
    term-activity.svg  weekly contributions over the last 52 weeks as a line chart
    term-langs-repo.svg     top languages by number of repositories (donut)
    term-langs-commit.svg   top languages by commits in the past year (donut)
    term-profile.svg        stars, commits, pull requests, issues, repos contributed to
    term-hours.svg          commits by hour of day, in India time (UTC+5:30)

These replace third-party stat cards, which were often rate-limited or offline
and showed up as broken images.

Usage:
    GITHUB_TOKEN=... python3 scripts/build_terminal_stats.py --user arman080325 --out dist
    python3 scripts/build_terminal_stats.py --sample --out /tmp/preview       # offline preview
"""
import argparse
import base64
import datetime as dt
import io
import json
import os
import random
import urllib.request
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
FONT_FILES = {"mono": "fira-code-latin-400-normal.woff", "monob": "fira-code-latin-600-normal.woff",
              "monoh": "fira-code-latin-700-normal.woff"}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}

# palette shared with scripts/build_terminal_assets.py
TERM = "#0a0e14"
CHROME = "#161b22"
LINE = "#21262d"
BORDER = "#30363d"
GREEN = "#00ff41"
MINT = "#00ff9d"
CYAN = "#00d8ff"
BLUE = "#2496ff"
PINK = "#ff2e63"
AMBER = "#ffbd2e"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
WHITE = "#e6f1ff"

QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(includeUserRepositories: true,
                              contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        name
        stargazerCount
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      commitContributionsByRepository(maxRepositories: 100) {
        contributions { totalCount }
        repository { primaryLanguage { name } }
      }
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
# Timestamps of the user's own commits on each repository's default branch (for the hour histogram).
HOURS_QUERY = """
query($login: String!, $id: ID!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { defaultBranchRef { target { ... on Commit {
        history(first: 100, author: {id: $id}) { nodes { authoredDate } }
      } } } }
    }
  }
}
"""
IST = dt.timedelta(hours=5, minutes=30)
# GitHub's linguist colours, so languages look the way people expect.
LANG_COLORS = {"JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Java": "#b07219", "Python": "#3572a5",
               "CSS": "#663399", "HTML": "#e34c26", "C": "#a8b9cc", "C++": "#f34b7d", "PHP": "#4f5d95",
               "Shell": "#89e051", "Jupyter Notebook": "#da5b0b", "HCL": "#844fba", "Go": "#00add8",
               "Rust": "#dea584", "Kotlin": "#a97bff", "SCSS": "#c6538c", "Dockerfile": "#384d54"}

_metrics = {}


def tw(key, text, size):
    if key not in _metrics:
        f = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm


def font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    font = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
    cmap = font.getBestCmap()
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(c for c in set(chars + " ?") if ord(c) in cmap)))
    sub.subset(font)
    for table in ("GDEF", "GPOS", "GSUB"):
        if table in font:
            del font[table]
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return (f"@font-face{{font-family:{FAMILY[key]};src:url(data:font/woff2;base64,"
            f"{base64.b64encode(buf.getvalue()).decode()})}}")


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts, self.css = w, h, [], []
        self.chars = {k: "" for k in FONT_FILES}

    def text(self, x, y, s, font, size, fill=TEXT, anchor=None, cls="", d=None):
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="--d:{d}s"' if d is not None else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}" xml:space="preserve"{a}{c}{st}>{escape(s)}</text>')

    def spans(self, x, y, segs, size):
        out, cx = [], x
        for t, font, col in segs:
            self.chars[font] += t
            out.append(f'<tspan x="{cx:.1f}" font-family="{FAMILY[font]}" fill="{col}">{escape(t)}</tspan>')
            cx += tw(font, t, size)
        self.parts.append(f'<text y="{y:.1f}" font-size="{size}" xml:space="preserve">{"".join(out)}</text>')
        return cx

    def add(self, raw):
        self.parts.append(raw)

    def save(self, path, title):
        faces = "".join(font_face(k, v) for k, v in self.chars.items() if v)
        css = (faces + ".fi{opacity:0;animation:fi .5s ease-out var(--d,0s) forwards}@keyframes fi{to{opacity:1}}"
               ".blink{animation:bl 1.05s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
               ".grow{transform-box:fill-box;transform-origin:left;animation:gr 1.2s cubic-bezier(.2,.8,.2,1) "
               "var(--d,0s) both}@keyframes gr{from{transform:scaleX(0)}}"
               ".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr 2.2s cubic-bezier(.4,0,.2,1) .3s forwards}"
               "@keyframes dr{to{stroke-dashoffset:0}}"
               + "".join(self.css) +
               "@media (prefers-reduced-motion:reduce){*{animation:none!important}.fi{opacity:1!important}"
               ".dr{stroke-dashoffset:0!important}}")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
               f'<style>{css}</style>{"".join(self.parts)}</svg>')
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)


def window(s, title, bar=32):
    """Terminal window chrome matching the rest of the terminal edition."""
    w, h, r = s.w, s.h, 10
    s.add(f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="{r}" fill="{TERM}" stroke="{BORDER}" '
          f'stroke-width="1.5"/>')
    s.add(f'<path d="M.75,{bar} V{r} Q.75,.75 {r},.75 H{w - r} Q{w - .75},.75 {w - .75},{r} V{bar} Z" fill="{CHROME}"/>')
    s.add(f'<line x1="0" y1="{bar}" x2="{w}" y2="{bar}" stroke="{BORDER}"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        s.add(f'<circle cx="{18 + i * 18}" cy="{bar / 2}" r="5.5" fill="{c}"/>')
    s.text(w / 2, bar / 2 + 4.5, title, "mono", 11.5, MUTED, anchor="middle")


def prompt(s, x, y, cmd, size=13):
    return s.spans(x, y, [("armanxploits", "monob", GREEN), ("@", "mono", MUTED), ("fsociety", "monob", CYAN),
                          (":~$ ", "mono", WHITE), (cmd, "mono", WHITE)], size)


# ── data ─────────────────────────────────────────────────────────────────
def graphql(query, variables, token):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-terminal"})
    with urllib.request.urlopen(req, timeout=90) as r:
        payload = json.load(r)
    if "errors" in payload and not payload.get("data"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def fetch(login, token):
    user = graphql(QUERY, {"login": login}, token)
    try:
        hours = graphql(HOURS_QUERY, {"login": login, "id": user["id"]}, token)
        user["commitTimes"] = [c["authoredDate"] for r in hours["repositories"]["nodes"]
                               for c in (((r.get("defaultBranchRef") or {}).get("target") or {})
                                         .get("history") or {}).get("nodes") or []]
    except Exception as e:  # the hour chart is a bonus; never fail the whole run over it
        print(f"warning: could not read commit times: {e}")
        user["commitTimes"] = []
    return user


def sample():
    """Deterministic fake data shaped like the API response, for offline previews."""
    rnd = random.Random(1)
    end = dt.date(2026, 11, 13)
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
    langs = [("JavaScript", 700), ("TypeScript", 540), ("C", 520), ("CSS", 465), ("HTML", 420), ("Java", 400)]
    nodes = [{"stargazerCount": 1, "languages": {"edges": [{"size": s * 1000, "node": {"name": n}}]}}
             for n, s in langs]
    total = sum(x["contributionCount"] for w in weeks for x in w["contributionDays"])
    prim = ["JavaScript"] * 9 + ["TypeScript"] * 5 + ["Java"] * 5 + ["Python"] * 4 + ["CSS"] * 4 + ["HTML"] * 3
    for i, n in enumerate(nodes):
        n["primaryLanguage"] = {"name": prim[i]}
    extra = [{"stargazerCount": 1, "languages": {"edges": []}, "primaryLanguage": {"name": prim[6 + i]}}
             for i in range(24)]
    by_repo = [("Java", 220), ("JavaScript", 150), ("Python", 90), ("TypeScript", 70), ("HTML", 56)]
    times = []
    for _ in range(420):
        h = rnd.choice([0, 0, 1, 1, 1, 2, 3, 11, 12, 12, 13, 15, 17, 19, 20, 21, 22, 22, 23, 23, 23])
        times.append(f"2026-10-{rnd.randint(1, 28):02d}T{(h - 5) % 24:02d}:{rnd.randint(0, 59):02d}:00Z")
    return {"pullRequests": {"totalCount": 76}, "issues": {"totalCount": 1},
            "repositoriesContributedTo": {"totalCount": 31},
            "repositories": {"totalCount": 33, "nodes": nodes + extra},
            "contributionsCollection": {
                "totalCommitContributions": 586,
                "commitContributionsByRepository": [
                    {"contributions": {"totalCount": c}, "repository": {"primaryLanguage": {"name": n}}}
                    for n, c in by_repo],
                "contributionCalendar": {"totalContributions": total, "weeks": weeks}},
            "commitTimes": times}


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
        for e in (repo.get("languages") or {}).get("edges") or []:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    by_repo = {}
    for repo in user["repositories"]["nodes"]:
        name = (repo.get("primaryLanguage") or {}).get("name")
        if name:
            by_repo[name] = by_repo.get(name, 0) + 1
    cc = user["contributionsCollection"]
    by_commit = {}
    for item in cc.get("commitContributionsByRepository") or []:
        name = ((item.get("repository") or {}).get("primaryLanguage") or {}).get("name")
        if name:
            by_commit[name] = by_commit.get(name, 0) + item["contributions"]["totalCount"]
    hours = [0] * 24
    for t in user.get("commitTimes") or []:
        hours[(dt.datetime.strptime(t[:19], "%Y-%m-%dT%H:%M:%S") + IST).hour] += 1
    return dict(lang_repo=sorted(by_repo.items(), key=lambda kv: -kv[1]),
                lang_commit=sorted(by_commit.items(), key=lambda kv: -kv[1]),
                commits=cc.get("totalCommitContributions", 0),
                prs=(user.get("pullRequests") or {}).get("totalCount", 0),
                issues=(user.get("issues") or {}).get("totalCount", 0),
                contributed=(user.get("repositoriesContributedTo") or {}).get("totalCount", 0),
                hours=hours,
                total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"],
                weekly=[sum(x["contributionCount"] for x in w["contributionDays"]) for w in cal["weeks"]],
                repos=user["repositories"]["totalCount"],
                stars=sum(r["stargazerCount"] for r in user["repositories"]["nodes"]),
                active=sum(1 for c in counts if c), best=max(counts or [0]),
                langs=sorted(langs.items(), key=lambda kv: -kv[1]))


# ── panels ───────────────────────────────────────────────────────────────
def build_recon(d, out):
    s = Svg(490, 270)
    window(s, "recon  —  target: self")
    prompt(s, 20, 62, "./recon --target=self", 12.5)
    rows = [("contributions", f"{d['total']:,}", "past 12 months", GREEN),
            ("current streak", f"{d['current']} days", "and counting", CYAN),
            ("longest streak", f"{d['longest']} days", "personal best", MINT),
            ("active days", f"{d['active']}", "with commits", GREEN),
            ("public repos", f"{d['repos']}", f"{d['stars']} stars", CYAN)]
    for i, (k, v, note, col) in enumerate(rows):
        y = 96 + i * 28
        s.add(f'<g class="fi" style="--d:{.3 + i * .25:.2f}s">')
        e = s.spans(20, y, [("[", "mono", MUTED), ("+", "monob", GREEN), ("] ", "mono", MUTED), (k, "mono", TEXT)], 13)
        dots_end = 300
        s.text(e + 6, y, "." * max(2, int((dots_end - e - 12) / tw("mono", ".", 13))), "mono", 13, LINE)
        s.text(dots_end + 6, y, v, "monoh", 13, col)
        s.text(470, y, note, "mono", 10.5, MUTED, anchor="end")
        s.add("</g>")
    y = 96 + 5 * 28 + 4
    s.add(f'<g class="fi" style="--d:{.3 + 5 * .25:.2f}s">')
    e = s.spans(20, y, [("[", "mono", MUTED), ("*", "monob", AMBER), ("] ", "mono", MUTED),
                        ("scan complete. target is shipping.", "mono", TEXT)], 12.5)
    s.add(f'<rect class="blink" x="{e + 4:.0f}" y="{y - 12}" width="8" height="15" fill="{GREEN}"/>')
    s.add("</g>")
    s.save(os.path.join(out, "term-recon.svg"),
           f"recon on self: {d['total']:,} contributions in the past 12 months, current streak {d['current']} days, "
           f"longest streak {d['longest']} days, {d['active']} active days, {d['repos']} public repositories, "
           f"{d['stars']} stars.")


def build_langs(d, out):
    s = Svg(490, 270)
    window(s, "cloc  —  by language")
    prompt(s, 20, 62, "cloc --by-language ~/repos", 12.5)
    top = d["langs"][:6]
    total = sum(v for _, v in top) or 1
    biggest = max((v for _, v in top), default=1)
    cols = [GREEN, CYAN, MINT, BLUE, AMBER, PINK]
    for i, (name, size) in enumerate(top):
        y = 94 + i * 27
        col = cols[i % len(cols)]
        s.add(f'<g class="fi" style="--d:{.2 + i * .12:.2f}s">')
        s.text(20, y, name, "mono", 13, TEXT)
        s.text(470, y, f"{100 * size / total:5.1f}%", "monob", 12, col, anchor="end")
        s.add("</g>")
        x0, wmax = 150, 250
        s.add(f'<rect x="{x0}" y="{y - 10}" width="{wmax}" height="11" rx="2" fill="{LINE}"/>')
        s.add(f'<rect class="grow" style="--d:{.3 + i * .12:.2f}s" x="{x0}" y="{y - 10}" '
              f'width="{wmax * size / biggest:.1f}" height="11" rx="2" fill="{col}"/>')
    s.text(20, 256, "share of code by bytes, own public repositories", "mono", 10, MUTED)
    s.save(os.path.join(out, "term-langs.svg"),
           "Top languages by share of code: " + ", ".join(f"{n} {100 * v / total:.0f}%" for n, v in top))


def build_activity(d, out):
    s = Svg(1000, 300)
    window(s, "activity  —  contributions per week, last 52 weeks")
    prompt(s, 20, 62, "./activity --graph --weeks=52", 12.5)
    weekly = d["weekly"][-52:]
    weeks = d["weeks"][-52:]
    x0, x1, y0, y1 = 64, 976, 92, 248
    top = max(max(weekly, default=1), 1)
    nice = max(4, -(-top // 4) * 4)
    for g in range(5):
        y = y1 - (y1 - y0) * g / 4
        dash = "" if g == 0 else ' stroke-dasharray="3 6"'
        s.add(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{LINE}" stroke-width="1"{dash}/>')
        s.text(x0 - 10, y + 4, str(int(nice * g / 4)), "mono", 10, MUTED, anchor="end")
    step = (x1 - x0) / max(1, len(weekly) - 1)
    pts = [(x0 + i * step, y1 - (y1 - y0) * v / nice) for i, v in enumerate(weekly)]
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s.add(f'<defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" '
          f'stop-opacity=".32"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient></defs>')
    s.add(f'<path class="fi" style="--d:1.2s" d="{line} L{x1},{y1} L{x0},{y1} Z" fill="url(#ar)"/>')
    s.add(f'<path class="dr" pathLength="1" d="{line}" fill="none" stroke="{GREEN}" stroke-width="2.2" '
          f'stroke-linejoin="round" stroke-linecap="round"/>')
    for i, (x, y) in enumerate(pts):
        s.add(f'<circle class="fi" style="--d:{.4 + i * .035:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{CYAN}"/>')
    if weekly:
        p = weekly.index(max(weekly))
        px, py = pts[p]
        anchor = "end" if px > 820 else "start"
        s.text(px + (-10 if anchor == "end" else 10), max(py + 4, y0 + 10), f"peak: {weekly[p]}", "monob", 11, AMBER,
               anchor=anchor, cls="fi", d=2.4)
    last = None
    for i, w in enumerate(weeks):
        first = dt.date.fromisoformat(w["contributionDays"][0]["date"])
        if first.month != last and first.day <= 7:
            s.text(x0 + i * step, y1 + 18, first.strftime("%b").lower(), "mono", 10, MUTED, anchor="middle")
            last = first.month
    avg = sum(weekly) / max(1, len(weekly))
    s.text(976, 62, f"avg {avg:.0f}/week  ·  total {sum(weekly):,}", "mono", 11, MUTED, anchor="end")
    s.save(os.path.join(out, "term-activity.svg"),
           f"Contributions per week over the last 52 weeks: {sum(weekly):,} in total, average {avg:.0f} per week, "
           f"peak {max(weekly, default=0)}.")


def lang_color(name, i):
    return LANG_COLORS.get(name, [GREEN, CYAN, MINT, BLUE, AMBER, PINK][i % 6])


def build_donut(d, out, key, fname, title, cmd, unit, note):
    import math
    s = Svg(490, 270)
    window(s, title)
    prompt(s, 20, 62, cmd, 12.5)
    top = d[key][:5]
    total = sum(v for _, v in top) or 1
    if not top:
        s.text(20, 110, "no data yet", "mono", 13, MUTED)
    for i, (name, v) in enumerate(top):
        y = 100 + i * 30
        col = lang_color(name, i)
        s.add(f'<g class="fi" style="--d:{.2 + i * .12:.2f}s">')
        s.add(f'<rect x="20" y="{y - 11}" width="13" height="13" rx="2" fill="{col}"/>')
        s.text(42, y, name, "mono", 13, TEXT)
        s.text(256, y, f"{v} {unit}", "mono", 11, MUTED, anchor="end")
        s.add("</g>")
    cx, cy, r = 378, 156, 66
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{LINE}" stroke-width="26"/>')
    acc = 0.0
    for i, (name, v) in enumerate(top):
        frac = v / total
        a0 = -math.pi / 2 + 2 * math.pi * acc
        a1 = -math.pi / 2 + 2 * math.pi * (acc + frac) - (.02 if len(top) > 1 else 0)
        large = 1 if (a1 - a0) > math.pi else 0
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        s.add(f'<path class="dr" pathLength="1" style="animation-delay:{.3 + i * .25:.2f}s" '
              f'd="M{x0:.1f},{y0:.1f} A{r},{r} 0 {large} 1 {x1:.1f},{y1:.1f}" fill="none" '
              f'stroke="{lang_color(name, i)}" stroke-width="26"/>')
        acc += frac
    if top:
        lead = f"{100 * top[0][1] / total:.0f}%"
        s.text(cx, cy + 2, lead, "monoh", 20, WHITE, anchor="middle")
        s.text(cx, cy + 20, top[0][0][:12], "mono", 10, MUTED, anchor="middle")
    s.text(20, 256, note, "mono", 10, MUTED)
    s.save(os.path.join(out, fname), f"{title}: " + ", ".join(f"{n} {v} {unit}" for n, v in top))


def build_profile(d, out):
    s = Svg(490, 270)
    window(s, "gh profile  —  stats")
    prompt(s, 20, 62, "gh profile --stats", 12.5)
    rows = [("total stars", f"{d['stars']}", GREEN), ("commits", f"{d['commits']:,}", CYAN),
            ("pull requests", f"{d['prs']}", MINT), ("issues", f"{d['issues']}", AMBER),
            ("contributed to", f"{d['contributed']} repos", BLUE)]
    notes = ["own public repos", "past 12 months", "all time", "all time", "all time"]
    for i, ((k, v, col), note) in enumerate(zip(rows, notes)):
        y = 96 + i * 28
        s.add(f'<g class="fi" style="--d:{.3 + i * .2:.2f}s">')
        e = s.spans(20, y, [("[", "mono", MUTED), ("+", "monob", GREEN), ("] ", "mono", MUTED), (k, "mono", TEXT)], 13)
        s.text(e + 6, y, "." * max(2, int((300 - e - 12) / tw("mono", ".", 13))), "mono", 13, LINE)
        s.text(306, y, v, "monoh", 13, col)
        s.text(470, y, note, "mono", 10.5, MUTED, anchor="end")
        s.add("</g>")
    s.text(20, 256, "contributed to: repos (own or others') with my commits, PRs or issues", "mono", 10, MUTED)
    s.save(os.path.join(out, "term-profile.svg"),
           f"Profile stats: {d['stars']} stars, {d['commits']:,} commits in the past year, {d['prs']} pull requests, "
           f"{d['issues']} issues, contributed to {d['contributed']} repositories.")


def build_hours(d, out):
    s = Svg(490, 270)
    window(s, "commits by hour  —  IST (UTC+5:30)")
    prompt(s, 20, 62, "git log --date=ist | hours", 12.5)
    hrs = d["hours"]
    top = max(max(hrs), 1)
    nice = max(4, -(-top // 4) * 4)
    x0, x1, y0, y1 = 52, 470, 84, 222
    for g in range(5):
        y = y1 - (y1 - y0) * g / 4
        dash = "" if g == 0 else ' stroke-dasharray="3 6"'
        s.add(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{LINE}"{dash}/>')
        s.text(x0 - 8, y + 4, str(int(nice * g / 4)), "mono", 9.5, MUTED, anchor="end")
    bw = (x1 - x0) / 24
    peak = hrs.index(max(hrs))
    for h, v in enumerate(hrs):
        if not v:
            continue
        bh = (y1 - y0) * v / nice
        col = AMBER if h == peak else GREEN
        s.add(f'<rect class="fi" style="--d:{.2 + h * .04:.2f}s" x="{x0 + h * bw + 1.5:.1f}" y="{y1 - bh:.1f}" '
              f'width="{bw - 3:.1f}" height="{bh:.1f}" rx="1.5" fill="{col}"/>')
    for h in (0, 6, 12, 18, 23):
        s.text(x0 + h * bw + bw / 2, y1 + 15, str(h), "mono", 9.5, MUTED, anchor="middle")
    night = sum(hrs[h] for h in list(range(21, 24)) + list(range(0, 5)))
    share = 100 * night / max(1, sum(hrs))
    s.text(20, 256, f"peak hour: {peak}:00  ·  {share:.0f}% of commits between 9 pm and 5 am", "mono", 10.5, AMBER)
    s.save(os.path.join(out, "term-hours.svg"),
           f"Commits by hour of day in India time: busiest hour {peak}:00, {share:.0f}% of commits between 9 pm and 5 am.")


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
    build_recon(d, a.out)
    build_langs(d, a.out)
    build_activity(d, a.out)
    build_donut(d, a.out, "lang_repo", "term-langs-repo.svg", "languages  —  by repo", "lang --count --by=repo",
                "repos", "primary language of each public repository")
    build_donut(d, a.out, "lang_commit", "term-langs-commit.svg", "languages  —  by commit",
                "lang --count --by=commit", "commits", "commits in the past 12 months, by repository language")
    build_profile(d, a.out)
    build_hours(d, a.out)
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
