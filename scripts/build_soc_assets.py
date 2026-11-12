#!/usr/bin/env python3
"""Build the static SOC-wall drawings for the profile README.

Usage:
    pip install fonttools brotli
    python3 scripts/build_soc_assets.py            # writes assets/soc/*.svg

Live panels (event feed, threat gauge, telemetry) are drawn separately by
scripts/build_soc_stats.py inside the GitHub workflow.
"""
import math
import os

import soc_kit as K
import soc_worldmap as M
from soc_kit import (AMBER, BG, BLUE, BORDER, DIM, MUTED, PANEL2, SOFT, TEAL, TEXT, Svg, arrow_ne, chip,
                     header, lamp, tw, wall, wrap)

OUT = os.path.join(K.ROOT, "assets", "soc")

# Self-assessed capability levels, 0 to 5. Edit these to taste and re-run the script.
BUILD_AXES = [("Backend", 4.5), ("APIs", 4.5), ("Frontend", 4.0), ("Databases", 4.0), ("DevOps / CI", 3.5),
              ("ML", 2.5)]
SECURITY_AXES = [("Web AppSec", 4.0), ("Network analysis", 4.0), ("Recon", 3.5), ("Reporting", 3.5),
                 ("Forensics", 2.5), ("Reverse eng.", 2.0)]


def out(name):
    return os.path.join(OUT, name)


# ── 1. THE WALL (hero) ───────────────────────────────────────────────────
def build_wall():
    s = Svg(1000, 540)
    wall(s, 14)
    # top bar
    s.path("M30,14 l10,5 v8 c0,6 -4,10 -10,13 c-6,-3 -10,-7 -10,-13 v-8 z", TEAL, 1.8)
    s.path("M25.5,26 l3.5,3.5 l6,-7", TEAL, 1.8)
    s.text(50, 31, "ARMAN // SOC", "monob", 13, TEXT, ls=1.5)
    s.text(500, 31, "SECURITY OPERATIONS  ·  BUILD + BREAK", "mono", 10.5, MUTED, anchor="middle", ls=1.5)
    st = "ALL SYSTEMS NOMINAL"
    lamp(s, 972 - tw("monom", st, 11, 1.2) - 12, 27, TEAL, 4)
    s.text(972, 31, st, "monom", 11, TEAL, anchor="end", ls=1.2)
    s.path("M16,48 H984", BORDER, 1)
    # operator column
    s.text(28, 84, "OPERATOR ON SHIFT", "mono", 10, MUTED, ls=1.6)
    s.text(26, 130, "Arman Ahemad", "uib", 40, TEXT, ls=-1, cls="fi", d=.1)
    s.text(26, 174, "Khan", "uib", 40, TEXT, ls=-1, cls="fi", d=.25)
    s.text(28, 204, "Full-stack developer  ·  Ethical hacker", "ui", 15, SOFT, cls="fi", d=.4)
    s.path("M28,222 H360", BORDER, 1)
    rows = [("ROLE", "Cybersecurity Intern"), ("FOCUS", "Pentesting · web application security"),
            ("EDU", "B.Tech CSE '27 · Silicon IT, Bhubaneswar"), ("BASE", "India · IST (UTC+5:30)"),
            ("SCOPE", "CTFs · labs · authorized programs")]
    for i, (k, v) in enumerate(rows):
        y = 250 + i * 28
        s.add(f'<g class="fi" style="--d:{.55 + i * .1:.2f}s">')
        s.text(28, y, k, "mono", 10, TEAL, ls=1.4)
        s.text(92, y, v, "ui", 13, TEXT)
        s.add("</g>")
    # map panel
    px, py, pw, ph = 392, 62, 580, 340
    s.rect(px, py, pw, ph, 10, "#0a1016", BORDER, 1)
    s.text(px + 16, py + 24, "GLOBAL VIEW", "monob", 10.5, TEXT, ls=1.6)
    s.text(px + pw - 16, py + 24, "VERCEL EDGE REGIONS SERVING THE APPS", "mono", 9.5, MUTED, anchor="end", ls=1)
    mx, my = px + 12, py + 50
    step = (pw - 24) / len(M.ROWS[0])

    def xy(lon, lat):
        return (mx + (lon - M.LON0) / M.STEP * step + step / 2, my + (M.LAT0 - lat) / M.STEP * step + step / 2)

    d = []
    for r, row in enumerate(M.ROWS):
        for c, ch in enumerate(row):
            if ch == "#":
                d.append(f"M{mx + c * step + step / 2:.1f},{my + r * step + step / 2:.1f}h0")
    s.path("".join(d), "#2b4152", 2.3)
    hq = xy(85.8, 20.3)
    nodes = [("PDX", -122.7, 45.5), ("IAD", -77.0, 38.9), ("FRA", 8.7, 50.1), ("SIN", 103.8, 1.35)]
    s.style(".flow{stroke-dasharray:3 7;animation:flow 1.6s linear infinite}@keyframes flow{to{stroke-dashoffset:-20}}"
            ".scan{animation:scan 9s linear infinite}@keyframes scan{from{transform:translateX(0)}"
            f"to{{transform:translateX({pw - 24}px)}}}}")
    for i, (name, lon, lat) in enumerate(nodes):
        x, y = xy(lon, lat)
        midx, midy = (x + hq[0]) / 2, min(y, hq[1]) - 46 - abs(x - hq[0]) * .08
        arc = f"M{hq[0]:.1f},{hq[1]:.1f} Q{midx:.1f},{midy:.1f} {x:.1f},{y:.1f}"
        s.path(arc, TEAL, 1.2, cls="flow", op=.55)
        k = f"pk{i}"
        s.style(f".{k}{{offset-path:path('{arc}');animation:{k} {3.2 + i * .5:.1f}s ease-in-out {i * .6:.1f}s infinite}}"
                f"@keyframes {k}{{0%{{offset-distance:0%;opacity:0}}10%{{opacity:1}}90%{{opacity:1}}"
                f"100%{{offset-distance:100%;opacity:0}}}}")
        s.add(f'<circle class="{k}" r="2.6" fill="{TEAL}"/>')
        s.circle(x, y, 4, BLUE, cls="ping", d=i * .5)
        s.circle(x, y, 3.2, BLUE)
        s.text(x, y - 9, name, "monom", 9, BLUE, anchor="middle", ls=.8)
    s.circle(hq[0], hq[1], 6, TEAL, cls="ping")
    s.circle(hq[0], hq[1], 5, TEAL, "#0a1016", 1.5)
    s.text(hq[0] + 13, hq[1] - 6, "HQ · INDIA", "monob", 10, TEAL, ls=1)
    # scan line
    s.defs.append(f'<linearGradient id="sg" x1="0" x2="1"><stop offset="0" stop-color="{TEAL}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{TEAL}" stop-opacity=".16"/></linearGradient>'
                  f'<clipPath id="mc"><rect x="{mx}" y="{my}" width="{pw - 24}" height="{len(M.ROWS) * step:.0f}"/></clipPath>')
    s.add(f'<g clip-path="url(#mc)"><g class="scan"><rect x="{mx - 60}" y="{my}" width="60" '
          f'height="{len(M.ROWS) * step:.0f}" fill="url(#sg)"/><rect x="{mx - 1}" y="{my}" width="1.2" '
          f'height="{len(M.ROWS) * step:.0f}" fill="{TEAL}" opacity=".5"/></g></g>')
    by = py + ph - 16
    s.circle(px + 20, by - 3.5, 3.5, TEAL)
    s.text(px + 30, by, "HQ", "mono", 9.5, SOFT, ls=1)
    s.circle(px + 66, by - 3.5, 3.5, BLUE)
    s.text(px + 76, by, "EDGE REGION", "mono", 9.5, SOFT, ls=1)
    s.text(px + pw - 16, by, "HOSTS: VERCEL · RENDER · GITHUB PAGES", "mono", 9.5, MUTED, anchor="end", ls=1)
    # KPI strip
    tiles = [("ASSETS MONITORED", "10", "projects on the wall", TEXT),
             ("IN SERVICE", "9", "live deployments", TEAL),
             ("DISCIPLINES", "2", "build + break", TEXT),
             ("RULES OF ENGAGEMENT", "3 / 3", "authorized · scoped · disclosed", TEAL)]
    tw_ = (944 - 3 * 12) / 4
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 28 + i * (tw_ + 12)
        s.add(f'<g class="fi" style="--d:{.9 + i * .12:.2f}s">')
        s.rect(x, 420, tw_, 96, 10, PANEL2, BORDER, 1)
        s.text(x + 16, 444, lab, "mono", 9.5, MUTED, ls=1.4)
        s.text(x + 16, 482, val, "uib", 30, col, ls=-.5)
        s.text(x + 16, 502, sub, "mono", 10, SOFT)
        s.add("</g>")
    s.save(out("wall.svg"), "SOC wall. Operator on shift: Arman Ahemad Khan, full-stack developer and ethical "
                            "hacker. Cybersecurity Intern focused on pentesting and web application security; B.Tech "
                            "CSE 2027 at Silicon Institute of Technology; based in India. World map of the Vercel "
                            "edge regions serving 9 live deployments. All systems nominal.")


# ── 2. TABS ──────────────────────────────────────────────────────────────
TABS = [("assets", "01", "ASSETS"), ("capabilities", "02", "CAPABILITIES"), ("feed", "03", "LIVE FEED"),
        ("telemetry", "04", "TELEMETRY")]


def build_tabs():
    for slug, num, label in TABS:
        w = int(tw("monob", label, 12, 1.4) + 70)
        s = Svg(w, 38)
        s.rect(.75, .75, w - 1.5, 36.5, 8, K.PANEL, BORDER, 1.5)
        s.text(14, 24, num, "monob", 12, TEAL, ls=1)
        s.text(40, 24, label, "monob", 12, TEXT, ls=1.4)
        s.circle(w - 16, 19, 3, TEAL, cls="pulse")
        s.save(out(f"tab-{slug}.svg"), f"{num} {label.title()}")


# ── 3. SECTION BARS ──────────────────────────────────────────────────────
def build_bar(slug, num, title, sub, color=TEAL):
    s = Svg(1000, 60)
    s.rect(.75, .75, 998.5, 58.5, 10, K.PANEL, BORDER, 1.5)
    s.rect(0, 12, 4, 36, 2, color)
    s.text(24, 37, num, "monob", 14, color, ls=1)
    s.text(60, 38, title, "uib", 20, TEXT, ls=-.2)
    s.text(972, 36, sub, "mono", 10.5, MUTED, anchor="end", ls=1.2)
    s.defs.append(f'<linearGradient id="bl" x1="0" x2="1"><stop offset="0" stop-color="{color}" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="{color}"/><stop offset="1" stop-color="{color}" stop-opacity="0"/>'
                  f'</linearGradient><clipPath id="bc"><rect x="10" y="56" width="980" height="3"/></clipPath>')
    s.style(".run{animation:run 5s ease-in-out infinite alternate}@keyframes run{to{transform:translateX(820px)}}")
    s.add('<g clip-path="url(#bc)"><rect class="run" x="10" y="57" width="160" height="1.6" fill="url(#bl)"/></g>')
    s.save(out(f"bar-{slug}.svg"), f"{num} {title}: {sub.lower()}")


# ── 4. MONITORED ASSETS (projects) ───────────────────────────────────────
ASSETS = [
    ("netscope", "NetScope", "NETWORK ANALYZER",
     "Real-time traffic analysis with a SOC-style dashboard, protocol breakdowns and per-host risk scores.",
     "Vercel + Render", "Python · Scapy · WebSockets", ["anomaly detection", "threat scoring", "entropy analysis"], True),
    ("fsociety", "fsociety-web", "SECURITY PORTFOLIO",
     "Cinematic security portfolio with an interactive roadmap, in-browser utilities and CTF progress.",
     "Vercel", "HTML · CSS · JavaScript", ["static site", "client-side tools", "field notes"], True),
    ("industrust", "IndusTrust Bank", "WEB APP · FINTECH",
     "Spring Boot web bank with a double-entry ledger and atomic, row-locked transfers.",
     "Render + Neon", "Spring Boot · PostgreSQL · Docker", ["BCrypt hashing", "row-level locks", "session auth"], True),
    ("sms", "Student Management", "WEB APP · RECORDS",
     "A legacy Swing + Oracle desktop app rebuilt as a cloud REST service with analytics and CSV export.",
     "Render + Neon", "Spring Boot · PostgreSQL · Actions", ["server-side validation", "env-driven secrets", "CI tests"],
     True),
    ("snapurl", "SnapURL", "SERVERLESS · UTILITY",
     "URL shortener with custom aliases and self-expiring links on Vercel functions and Turso edge SQLite.",
     "Vercel", "TypeScript · Express · Turso", ["input validation", "TTL expiry", "base62 IDs"], True),
    ("cineroulette", "CineRoulette", "WEB APP · DISCOVERY",
     "Pick a mood, spin, get one explained movie pick, weighted per language and region.",
     "Vercel", "Next.js · NestJS · Prisma · Redis", ["weighted scoring", "per-region fairness", "reduced motion"], True),
    ("gitatlas", "GitAtlas", "DEVELOPER TOOL",
     "381 Git commands explained in plain English, with guided recovery playbooks and a wizard.",
     "Vercel", "HTML · CSS · JavaScript", ["381 commands", "17 playbooks", "risk warnings"], True),
    ("grabmedia", "GrabMedia", "WEB APP · MEDIA",
     "Saves public Instagram and YouTube media up to 2160p through a hardened Express proxy.",
     "GitHub Pages + Render", "Node.js · Express · Helmet", ["secure headers", "rate limiting", "locked CORS"], True),
    ("disease", "Disease Prediction", "MACHINE LEARNING",
     "Predicts 41 diseases from 132 symptoms with a tree ensemble and explains each result.",
     "Vercel + Render", "FastAPI · scikit-learn · SHAP", ["SHAP explanations", "PDF reports", "health checks"], True),
    ("siteshield", "SiteShield", "SECURITY SAAS",
     "Grades a website's TLS, headers, cookies and DNS hygiene from A to F and re-scans on a schedule.",
     "In development", "React · FastAPI · Celery", ["passive checks", "A to F grading", "regression alerts"], False),
]


def build_asset(idx, slug, name, kind, desc, host, stack, highlights, live):
    s = Svg(490, 262)
    wall(s, 12)
    col = TEAL if live else AMBER
    s.text(22, 32, f"AST-{idx:02d}", "monob", 11, col, ls=1.2)
    s.text(78, 32, kind, "mono", 10, MUTED, ls=1.2)
    status = "OPERATIONAL" if live else "PROVISIONING"
    sw = tw("monom", status, 10, 1.2)
    lamp(s, 468 - sw - 11, 28.5, col, 4)
    s.text(468, 32, status, "monom", 10, col, anchor="end", ls=1.2)
    s.path("M22,46 H468", BORDER, 1)
    s.text(22, 78, name, "uib", 22, TEXT, ls=-.4)
    for i, line in enumerate(wrap(desc, "ui", 12.5, 446)[:2]):
        s.text(22, 100 + i * 17, line, "ui", 12.5, SOFT)
    # signal strip
    sy = 148
    s.text(22, sy + 3.5, "SIGNAL", "mono", 8.5, MUTED, ls=1.2)
    x0, x1 = 78, 468
    cid = s.uid("sc")
    s.defs.append(f'<clipPath id="{cid}"><rect x="{x0}" y="{sy - 16}" width="{x1 - x0}" height="32"/></clipPath>')
    s.path(f"M{x0},{sy} H{x1}", BORDER, 1)
    if live:
        beat = 130
        pts = [f"M{x0 - beat},{sy}"]
        for k in range(-1, 5):
            bx = x0 + k * beat
            pts.append(f"L{bx + 40},{sy} L{bx + 48},{sy - 4} L{bx + 54},{sy} L{bx + 62},{sy} L{bx + 68},{sy - 14} "
                       f"L{bx + 75},{sy + 10} L{bx + 81},{sy} L{bx + 92},{sy} L{bx + 100},{sy - 5} L{bx + 108},{sy} "
                       f"L{bx + beat},{sy}")
        s.style(f".wv{{animation:wv {2.4 + (idx % 3) * .3:.1f}s linear infinite}}"
                f"@keyframes wv{{to{{transform:translateX({beat}px)}}}}")
        s.add(f'<g clip-path="url(#{cid})"><path class="wv" d="{" ".join(pts)}" fill="none" stroke="{TEAL}" '
              f'stroke-width="1.6" stroke-linejoin="round"/></g>')
    else:
        s.path(f"M{x0},{sy} H{x1}", AMBER, 1.6, dash="2 8", cls="pulse")
    # fields
    s.text(22, 186, "HOST", "mono", 9, MUTED, ls=1.2)
    s.text(78, 186, host, "monom", 11, TEXT)
    s.text(22, 206, "STACK", "mono", 9, MUTED, ls=1.2)
    s.text(78, 206, stack, "monom", 11, TEXT)
    cx = 22
    for h in highlights:
        cx += chip(s, cx, 222, h, col if live else AMBER, 9.5, 20) + 6
    cta = "OPEN" if live else "SOURCE"
    s.text(455, 236, cta, "monob", 10.5, col, anchor="end", ls=1.2)
    s.style(".go{animation:go 1.8s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add('<g class="go">')
    arrow_ne(s, 459, 227, col, 8)
    s.add("</g>")
    s.save(out(f"asset-{slug}.svg"),
           f"Asset {idx:02d}: {name}, {kind.lower()}. {desc} Host: {host}. Stack: {stack}. "
           f"Highlights: {', '.join(highlights)}. Status: {status.lower()}.")


# ── 5. CAPABILITY RADARS (skills) ────────────────────────────────────────
def radar(s, cx, cy, R, axes, color, title, tools, delay):
    n = len(axes)

    def pt(i, r):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * math.cos(a), cy + r * math.sin(a)

    for ring in range(1, 6):
        d = " ".join(("M" if i == 0 else "L") + f"{pt(i, R * ring / 5)[0]:.1f},{pt(i, R * ring / 5)[1]:.1f}"
                     for i in range(n)) + " Z"
        s.path(d, BORDER if ring < 5 else DIM, 1)
    for i in range(n):
        x, y = pt(i, R)
        s.path(f"M{cx},{cy} L{x:.1f},{y:.1f}", BORDER, 1)
    # sweep
    k = s.uid("sw")
    gid = s.uid("sg")
    s.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{color}" '
                  f'stop-opacity="0"/><stop offset="1" stop-color="{color}" stop-opacity=".22"/></linearGradient>')
    s.style(f".{k}{{transform-origin:{cx}px {cy}px;animation:{k} 7s linear infinite}}"
            f"@keyframes {k}{{to{{transform:rotate(360deg)}}}}")
    ex, ey = cx + R * math.cos(-math.pi / 2 - .5), cy + R * math.sin(-math.pi / 2 - .5)
    s.add(f'<g class="{k}"><path d="M{cx},{cy} L{ex:.1f},{ey:.1f} A{R},{R} 0 0 1 {cx},{cy - R} Z" fill="url(#{gid})"/>'
          f'<path d="M{cx},{cy} L{cx},{cy - R}" stroke="{color}" stroke-width="1.2" opacity=".7"/></g>')
    # capability polygon
    poly = " ".join(("M" if i == 0 else "L") + f"{pt(i, R * v / 5)[0]:.1f},{pt(i, R * v / 5)[1]:.1f}"
                    for i, (_, v) in enumerate(axes)) + " Z"
    p = s.uid("pg")
    s.style(f".{p}{{transform-origin:{cx}px {cy}px;animation:{p} 1.4s cubic-bezier(.2,.8,.2,1) {delay}s both}}"
            f"@keyframes {p}{{from{{transform:scale(0)}}}}")
    s.add(f'<g class="{p}"><path d="{poly}" fill="{color}" fill-opacity=".16" stroke="{color}" stroke-width="2" '
          f'stroke-linejoin="round"/>')
    for i, (_, v) in enumerate(axes):
        x, y = pt(i, R * v / 5)
        s.circle(x, y, 3.4, K.PANEL, color, 2)
    s.add("</g>")
    for i, (name, v) in enumerate(axes):
        x, y = pt(i, R + 16)
        anchor = "middle" if abs(x - cx) < 10 else ("start" if x > cx else "end")
        dy = -4 if y < cy - R else (12 if y > cy + R - 20 and abs(x - cx) < 10 else 4)
        s.text(x, y + dy, name, "ui", 12, TEXT, anchor=anchor)
        s.text(x, y + dy + 14, f"{v:.1f}", "monom", 10, color, anchor=anchor)
    s.text(cx, cy - R - 52, title, "monob", 12, color, anchor="middle", ls=2)
    s.text(cx, cy + R + 64, tools, "mono", 10.5, MUTED, anchor="middle")


def build_radars():
    s = Svg(1000, 470)
    wall(s, 12)
    header(s, "CAPABILITY MATRIX", "SELF-ASSESSED  ·  SCALE 0 TO 5")
    radar(s, 262, 256, 124, BUILD_AXES, TEAL, "BUILD", "Spring Boot · Node · FastAPI · React · PostgreSQL · Docker", .2)
    radar(s, 738, 256, 124, SECURITY_AXES, BLUE, "BREAK", "Burp Suite · Nmap · Wireshark · Metasploit · Volatility3 · Ghidra",
          .5)
    s.path("M500,74 V440", BORDER, 1, dash="2 6")
    s.save(out("radars.svg"),
           "Capability matrix, self-assessed on a 0 to 5 scale. Build: " +
           ", ".join(f"{n} {v}" for n, v in BUILD_AXES) + ". Break: " +
           ", ".join(f"{n} {v}" for n, v in SECURITY_AXES) + ".")


# ── 6. SHIFT HANDOVER (footer) ───────────────────────────────────────────
def build_handover():
    s = Svg(1000, 210)
    wall(s, 12)
    header(s, "SHIFT HANDOVER", "CHANNEL OPEN")
    s.text(28, 96, "Need something built,", "uib", 24, TEXT, ls=-.4)
    s.text(28, 126, "or tested before it ships?", "uib", 24, TEXT, ls=-.4)
    url = "arman-portfolio.online"
    s.text(28, 164, url, "monob", 17, TEAL)
    uw = tw("monob", url, 17)
    s.path(f"M28,171 H{28 + uw:.0f}", TEAL, 1.4, cls="dr", delay=.4)
    s.style(".go{animation:go 1.8s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add('<g class="go">')
    arrow_ne(s, 28 + uw + 10, 151, TEAL, 10, 2)
    s.add("</g>")
    s.text(28, 190, "fsociety-web.vercel.app  ·  github.com/arman080325", "mono", 10.5, MUTED)
    # rules of engagement
    x = 560
    s.rect(x, 66, 412, 122, 10, PANEL2, BORDER, 1)
    s.text(x + 18, 90, "RULES OF ENGAGEMENT", "mono", 10, MUTED, ls=1.5)
    rules = ["Written authorization before every test", "Scope respected: CTFs, labs, authorized programs",
             "Responsible disclosure, always"]
    for i, r in enumerate(rules):
        y = 116 + i * 26
        s.add(f'<g class="fi" style="--d:{.4 + i * .25:.2f}s">')
        s.circle(x + 26, y - 4, 8, "none", TEAL, 1.6)
        s.path(f"M{x + 22},{y - 4} l3,3 l5.5,-6", TEAL, 1.8)
        s.text(x + 44, y, r, "ui", 13, TEXT)
        s.add("</g>")
    s.save(out("handover.svg"), "Shift handover. Need something built, or tested before it ships? "
                                "arman-portfolio.online. Rules of engagement: written authorization before every "
                                "test; scope respected; responsible disclosure, always.")


BARS = [
    ("assets", "01", "Monitored assets", "10 ASSETS  ·  9 OPERATIONAL  ·  CLICK A PANEL TO OPEN IT", TEAL),
    ("capabilities", "02", "Capabilities", "TWO DISCIPLINES  ·  ONE OPERATOR", BLUE),
    ("feed", "03", "Live feed", "LATEST COMMITS AND THREAT LEVEL  ·  REFRESHED EVERY 12 HOURS", AMBER),
    ("telemetry", "04", "Telemetry", "A YEAR OF ACTIVITY FROM THE GITHUB API", TEAL),
]


def main():
    build_wall()
    build_tabs()
    for b in BARS:
        build_bar(*b)
    for i, a in enumerate(ASSETS, 1):
        build_asset(i, *a)
    build_radars()
    build_handover()


if __name__ == "__main__":
    main()
