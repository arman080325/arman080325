#!/usr/bin/env python3
"""Draw live terminal-style GitHub stat panels for the terminal-edition README.

Runs inside the "Generate contribution graphs" workflow. It reads public data
from the GitHub GraphQL API with the workflow's GITHUB_TOKEN and writes:

    term-recon.svg     `./recon --target=self`: contributions, streaks, repos, stars
    term-langs.svg     `cloc --by-language`: language mix across own repositories
    term-activity.svg  weekly contributions over the last 52 weeks as a line chart

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
def fetch(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "profile-readme-terminal"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "errors" in payload and not payload.get("data"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


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
    return {"repositories": {"totalCount": 33, "nodes": nodes + [{"stargazerCount": 1, "languages": {"edges": []}}] * 24},
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
        for e in (repo.get("languages") or {}).get("edges") or []:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return dict(total=cal["totalContributions"], current=cur, longest=longest, weeks=cal["weeks"],
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
    print(f"stats: {d['total']} contributions, streak {d['current']}/{d['longest']}, {d['repos']} repos, "
          f"top {[n for n, _ in d['langs'][:6]]}")


if __name__ == "__main__":
    main()
