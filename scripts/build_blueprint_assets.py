#!/usr/bin/env python3
"""Build the static blueprint drawings for the profile README.

Usage:
    pip install fonttools brotli
    python3 scripts/build_blueprint_assets.py        # writes assets/blueprint/*.svg

Live statistics are drawn separately by scripts/build_blueprint_stats.py
inside the GitHub workflow.
"""
import os

import blueprint_kit as K
from blueprint_kit import (AMBER, CYAN, DIM, GREEN, INK, INK2, PAPER, PAPER2, RED, Svg, arrow, arrowhead,
                           dimension, frame, paper, redline, section_bubble, stamp, tw, wrap)

OUT = os.path.join(K.ROOT, "assets", "blueprint")


def out(name):
    return os.path.join(OUT, name)


# ── 1. TITLE SHEET (hero) ────────────────────────────────────────────────
def build_hero():
    s = Svg(1000, 500)
    paper(s)
    frame(s)
    s.text(44, 54, "SHEET 01 / 06  —  GENERAL ARRANGEMENT", "monom", 11, DIM, ls=1)
    name = "ARMAN AHEMAD KHAN"
    size = 64
    nw = tw("condb", name, size, 1)
    # outlined name that draws itself, then fills
    s.style(".nm{fill:transparent;stroke:#eaf2ff;stroke-width:1.3;stroke-dasharray:700;stroke-dashoffset:700;"
            "animation:nmd 2.6s cubic-bezier(.45,.05,.25,1) .2s forwards,nmf .8s ease 2.4s forwards}"
            "@keyframes nmd{to{stroke-dashoffset:0}}@keyframes nmf{to{fill:#eaf2ff}}")
    dimension(s, 44, 44 + nw, 84, "FULL-STACK DEVELOPER  ×  ETHICAL HACKER", draw=.1, size=11)
    s.text(44, 152, name, "condb", size, INK, ls=1, cls="nm")
    s.text(46, 190, "I build web products, then review them the way an attacker would.", "cond", 20, INK2,
           cls="fi", d=1.6)
    specs = [("EDU", "B.Tech CSE '23-'27  ·  Silicon Institute of Technology, Bhubaneswar"),
             ("NOW", "Cybersecurity Intern  ·  pentesting & web application security"),
             ("SHIP", "9 live deployments  ·  Vercel · Render · GitHub Pages")]
    for i, (k, v) in enumerate(specs):
        y = 232 + i * 26
        s.add(f'<g class="fi" style="--d:{2.0 + i * .25:.2f}s">')
        s.add(f'<rect x="46" y="{y - 10}" width="8" height="8" fill="{CYAN}"/>')
        s.text(64, y - 1.5, k, "monob", 11.5, CYAN, ls=1)
        s.text(110, y - 1.5, v, "mono", 12.5, INK)
        s.add("</g>")
    # red review note pointing at the name
    redline(s, 356, 318, ["REV C: REVIEWED BY REDTEAM", "HARDENED BEFORE RELEASE"], draw=2.8, size=11,
            leader=(44 + nw * .82, 162))
    # detail callout: build + break emblem
    cx, cy, r = 838, 178, 98
    s.circle(cx, cy, r, INK, 1.6, extra='class="dr" pathLength="1" style="--d:.6s"')
    s.line(cx - r - 12, cy, cx + r + 12, cy, DIM, .8, dash="14 4 2 4")
    s.line(cx, cy - r - 12, cx, cy + r + 12, DIM, .8, dash="14 4 2 4")
    s.path(f"M{cx - 52},{cy - 26} L{cx - 78},{cy} L{cx - 52},{cy + 26}", INK, 5, draw=1.2)
    s.path(f"M{cx + 52},{cy - 26} L{cx + 78},{cy} L{cx + 52},{cy + 26}", INK, 5, draw=1.4)
    s.path(f"M{cx},{cy - 52} L{cx + 38},{cy - 36} V{cy + 2} C{cx + 38},{cy + 28} {cx + 18},{cy + 44} {cx},{cy + 54} "
           f"C{cx - 18},{cy + 44} {cx - 38},{cy + 28} {cx - 38},{cy + 2} V{cy - 36} Z", RED, 3.2, draw=1.8, t=1.8)
    s.path(f"M{cx - 15},{cy + 2} L{cx - 4},{cy + 13} L{cx + 17},{cy - 9}", RED, 3.6, draw=3.0, t=.6)
    # detail marker near the name + dash-dot leader
    mx, my = 44 + nw + 34, 128
    s.circle(mx, my, 13, INK, 1.4)
    s.text(mx, my + 4.5, "A", "monob", 13, INK, anchor="middle")
    s.line(mx + 13, my, cx - r * .93, cy - r * .36, DIM, 1, dash="10 4 2 4")
    s.text(cx, cy + r + 30, "DETAIL A  —  BUILD + BREAK", "monob", 11.5, INK, anchor="middle", ls=1)
    s.text(cx, cy + r + 46, "SCALE 2:1", "mono", 10.5, DIM, anchor="middle")
    # scale bar: 2023 -> 2027 with "now"
    bx, by, bw = 44, 438, 300
    for i in range(4):
        s.add(f'<rect x="{bx + i * bw / 4:.1f}" y="{by}" width="{bw / 4:.1f}" height="7" '
              f'fill="{INK if i % 2 == 0 else "none"}" stroke="{INK}" stroke-width="1"/>')
    for i, yr in enumerate(("2023", "2024", "2025", "2026", "2027")):
        s.text(bx + i * bw / 4, by + 22, yr, "mono", 9.5, INK2, anchor="middle")
    nx = bx + bw * (3 + 10.3 / 12) / 4
    s.add(f'<path d="M{nx:.1f},{by - 4} l-5,-8 h10 z" fill="{RED}" class="pulse"/>')
    s.text(nx, by - 15, "NOW", "monob", 9.5, RED, anchor="middle")
    s.text(bx, by - 14, "SCALE OF YEARS", "monom", 9.5, DIM, ls=1)
    # title block
    tx, ty, tw_, th = 560, 340, 408, 128
    s.add(f'<rect x="{tx}" y="{ty}" width="{tw_}" height="{th}" fill="{PAPER2}" stroke="{INK}" stroke-width="1.6"/>')
    for yy in (ty + 34, ty + 66, ty + 97):
        s.line(tx, yy, tx + tw_, yy, INK, 1)
    cells = [
        [(0, 408, "PROJECT", "ARMAN AHEMAD KHAN  ·  PORTFOLIO")],
        [(0, 272, "ROLE", "FULL-STACK DEV / ETHICAL HACKER"), (272, 136, "DWG NO.", "AK-2027-01")],
        [(0, 136, "DRAWN", "ARMANXPLOITS"), (136, 136, "CHECKED", "REDTEAM"), (272, 72, "SCALE", "1:1"),
         (344, 64, "REV", "C")],
        [(0, 136, "LOCATION", "INDIA"), (136, 208, "STATUS", "CYBERSECURITY INTERN"), (344, 64, "SHEET", "1 / 6")],
    ]
    rows_y = [ty, ty + 34, ty + 66, ty + 97]
    for r_, row in enumerate(cells):
        y0 = rows_y[r_]
        for (ox, w, lab, val) in row:
            if ox:
                s.line(tx + ox, y0, tx + ox, y0 + (34 if r_ == 0 else 32 if r_ < 3 else 31), INK, 1)
            s.text(tx + ox + 7, y0 + 11, lab, "mono", 7.5, DIM, ls=.8)
            col = RED if val in ("REDTEAM", "C") else INK
            s.text(tx + ox + 7, y0 + 26, val, "condb", 13 if r_ == 0 else 12, col, ls=.6)
    # CAD cursor wandering over the drawing
    s.style(".cad{animation:cad 16s ease-in-out infinite}"
            "@keyframes cad{0%,100%{transform:translate(180px,120px)}20%{transform:translate(520px,150px)}"
            "40%{transform:translate(830px,170px)}60%{transform:translate(760px,400px)}"
            "80%{transform:translate(420px,350px)}}")
    s.add('<g class="cad" opacity=".85">')
    s.line(-18, 0, -5, 0, CYAN, 1.2)
    s.line(5, 0, 18, 0, CYAN, 1.2)
    s.line(0, -18, 0, -5, CYAN, 1.2)
    s.line(0, 5, 0, 18, CYAN, 1.2)
    s.add(f'<rect x="-4" y="-4" width="8" height="8" fill="none" stroke="{CYAN}" stroke-width="1.2"/>')
    s.add("</g>")
    s.save(out("hero.svg"), "Arman Ahemad Khan — Full-Stack Developer and Ethical Hacker. Title sheet of a blueprint "
                            "drawing set: B.Tech CSE 2027, Cybersecurity Intern, 9 live deployments.")


# ── 2. SECTION HEADER STRIPS ─────────────────────────────────────────────
def build_header(name, num, title, sub):
    s = Svg(1000, 92)
    paper(s, 8)
    s.box(6, 6, 988, 80, INK2, 1)
    section_bubble(s, 52, 46, num, "06")
    s.text(92, 46, title, "condb", 28, INK, ls=1.2)
    s.text(94, 68, sub, "mono", 11.5, INK2, ls=.6)
    x0 = 100 + max(tw("condb", title, 28, 1.2), tw("mono", sub, 11.5, .6)) + 24
    s.line(x0, 46, 900, 46, DIM, 1, draw=.1)
    arrowhead(s, 900, 46, 0, DIM, 7)
    s.text(964, 50, f"SHEET {num}", "monom", 10.5, DIM, anchor="end", ls=1)
    s.save(out(f"h-{name}.svg"), f"Sheet {num}: {title.title()}")


# ── 3. BILL OF MATERIALS (about) ─────────────────────────────────────────
def build_bom():
    rows = [
        ("01", "ENGINEER", "Arman Ahemad Khan  (handle: armanxploits)", "1"),
        ("02", "EDUCATION", "B.Tech CSE, Silicon Institute of Technology, Bhubaneswar  '23-'27", "1"),
        ("03", "CURRENT ROLE", "Cybersecurity Intern: pentesting & web application security", "1"),
        ("04", "LIVE DEPLOYMENTS", "Spring Boot, Node, FastAPI, Next.js on Vercel / Render / GH Pages", "9"),
        ("05", "TRAINING GROUNDS", "PortSwigger Web Security Academy · TryHackMe · HackTheBox", "3"),
        ("06", "WORKSTATION", "ASUS TUF F16 · RTX 3050 · Kali Linux <-> Windows 11 · zsh + p10k", "1"),
        ("07", "RULES OF ENGAGEMENT", "Written authorization · responsible disclosure · scope respected", "ALL"),
    ]
    rh = 34
    s = Svg(1000, 120 + rh * (len(rows) + 1) + 70)
    paper(s)
    frame(s, zones=False)
    s.text(44, 62, "BILL OF MATERIALS", "condb", 26, INK, ls=1.5)
    s.text(46, 84, "PART LIST FOR ONE (1) BUILDER-BREAKER", "mono", 11.5, INK2, ls=.8)
    x0, y0 = 44, 106
    cols = [(0, 56, "ITEM"), (56, 196, "COMPONENT"), (252, 600, "SPECIFICATION"), (852, 60, "QTY")]
    width = 912
    s.add(f'<rect x="{x0}" y="{y0}" width="{width}" height="{rh}" fill="{INK}" opacity=".12"/>')
    for ox, w, lab in cols:
        s.text(x0 + ox + 10, y0 + 22, lab, "monob", 11, INK, ls=1.2)
    s.box(x0, y0, width, rh * (len(rows) + 1), INK, 1.6)
    for ox, _, _ in cols[1:]:
        s.line(x0 + ox, y0, x0 + ox, y0 + rh * (len(rows) + 1), INK, 1)
    for i, (item, comp, spec, qty) in enumerate(rows):
        y = y0 + rh * (i + 1)
        s.line(x0, y, x0 + width, y, INK2, .8)
        s.add(f'<g class="fi" style="--d:{.2 + i * .14:.2f}s">')
        s.text(x0 + 10, y + 22, item, "monom", 12, CYAN)
        s.text(x0 + 66, y + 22, comp, "condb", 14, INK, ls=.8)
        s.text(x0 + 262, y + 22, spec, "mono", 12, INK)
        s.text(x0 + 852 + 30, y + 22, qty, "condb", 15, RED if qty == "ALL" else INK, anchor="middle")
        s.add("</g>")
    table_end = y0 + rh * (len(rows) + 1)
    redline(s, 700, table_end + 14, ["NON-NEGOTIABLE, EVERY TIME"], draw=1.6, size=11,
            leader=(x0 + 852 + 30, table_end - 6))
    s.save(out("bom.svg"), "Bill of materials: Arman Ahemad Khan, B.Tech CSE at Silicon Institute of Technology "
                           "('23-'27), Cybersecurity Intern, 9 live deployments, trains on PortSwigger, TryHackMe and "
                           "HackTheBox, works only with written authorization and responsible disclosure.")


# ── 4. EXPLODED VIEW (stack) ─────────────────────────────────────────────
def build_exploded():
    layers = [
        ("01", "INTERFACE", "React · Next.js · Tailwind · HTML/CSS", CYAN),
        ("02", "SERVICES", "Spring Boot · Node/Express · NestJS · FastAPI", INK),
        ("03", "DATA", "PostgreSQL · MySQL · MongoDB · Redis · Prisma", INK),
        ("04", "DELIVERY", "Docker · GitHub Actions · Vercel · Render", INK),
    ]
    s = Svg(1000, 560)
    paper(s)
    frame(s, zones=False)
    s.text(44, 62, "EXPLODED VIEW  —  THE STACK", "condb", 26, INK, ls=1.5)
    s.text(46, 84, "ISOMETRIC · NOT TO SCALE · LAYERS SEPARATED FOR CLARITY", "mono", 11.5, INK2, ls=.8)
    cx, top, gap = 270, 196, 70
    hw, hh, th = 170, 52, 12
    for i, (num, name, items, col) in enumerate(layers):
        y = top + i * gap
        k = s.uid("pl")
        s.style(f".{k}{{animation:{k} 1.6s cubic-bezier(.2,.8,.2,1) {.2 + i * .12:.2f}s both}}"
                f"@keyframes {k}{{from{{transform:translateY({(1.5 - i) * gap * .78:.0f}px);opacity:.2}}}}")
        s.add(f'<g class="{k}">')
        # side faces
        s.add(f'<path d="M{cx - hw},{y} L{cx},{y + hh} L{cx},{y + hh + th} L{cx - hw},{y + th} Z" fill="{PAPER2}" '
              f'stroke="{INK2}" stroke-width="1"/>')
        s.add(f'<path d="M{cx + hw},{y} L{cx},{y + hh} L{cx},{y + hh + th} L{cx + hw},{y + th} Z" fill="#0a2a5f" '
              f'stroke="{INK2}" stroke-width="1"/>')
        # top face
        s.add(f'<path d="M{cx},{y - hh} L{cx + hw},{y} L{cx},{y + hh} L{cx - hw},{y} Z" fill="{PAPER2}" '
              f'stroke="{col}" stroke-width="1.6"/>')
        # inner detail lines on the top face
        for t in (.3, .55, .8):
            s.add(f'<path d="M{cx - hw * t},{y - hh * (1 - t)} L{cx + hw * (1 - t)},{y + hh * t}" stroke="{DIM}" '
                  f'stroke-width=".7" opacity=".7"/>')
        s.text(cx, y + 5, name, "condb", 14, col, anchor="middle", ls=2)
        s.add("</g>")
        # leader to the label column
        lx = 560
        s.line(cx + hw - 6, y, lx - 30, y, DIM, 1, draw=1.2 + i * .15)
        s.circle(cx + hw - 6, y, 2.6, INK, 1, INK)
        s.add(f'<g class="fi" style="--d:{1.5 + i * .15:.2f}s">')
        s.circle(lx - 14, y, 13, col, 1.4)
        s.text(lx - 14, y + 4.5, num, "monob", 11, col, anchor="middle")
        s.text(lx + 8, y - 3, name, "condb", 17, col, ls=1.5)
        s.text(lx + 8, y + 16, items, "mono", 12, INK2)
        s.add("</g>")
    # security perimeter around the whole stack
    py0, py1 = top - hh - 26, top + 3 * gap + hh + th + 22
    s.add(f'<rect x="{cx - hw - 34}" y="{py0}" width="{2 * hw + 68}" height="{py1 - py0}" fill="none" stroke="{RED}" '
          f'stroke-width="1.8" stroke-dasharray="10 6" class="fi" style="--d:2.4s"/>')
    s.text(cx - hw - 26, py0 + 18, "SECURITY PERIMETER", "monob", 10.5, RED, ls=1.2, cls="fi", d=3.0)
    ny = top + 4 * gap + 6
    s.add(f'<g class="fi" style="--d:3.2s">')
    s.circle(546, ny, 13, RED, 1.4)
    s.text(546, ny + 4.5, "05", "monob", 11, RED, anchor="middle")
    s.text(568, ny - 3, "PERIMETER", "condb", 17, RED, ls=1.5)
    s.text(568, ny + 16, "Burp · Nmap · Wireshark · OWASP Top 10", "mono", 12, RED)
    s.add("</g>")
    s.line(cx + hw + 34, ny, 530, ny, RED, 1, draw=3.0)
    s.save(out("exploded.svg"), "Exploded view of the stack: interface (React, Next.js, Tailwind), services (Spring "
                                "Boot, Node, NestJS, FastAPI), data (PostgreSQL, MySQL, MongoDB, Redis), delivery "
                                "(Docker, GitHub Actions, Vercel, Render), all inside a security perimeter reviewed "
                                "with Burp, Nmap and Wireshark.")


# ── 5. PROJECT SCHEMATICS ────────────────────────────────────────────────
# Each diagram is a 3x2 grid of components. Connections are always straight
# (same row or same column), and the red review note sits in the free bottom-left
# slot with a short leader to the component it is about.
BOX_W, BOX_H = 128, 34
COL_X = [36, 182, 328]
ROW_Y = [104, 170]
CARD_H = 334


def node_xy(col, row):
    return COL_X[col], ROW_Y[row]


def connect(s, a, b, delay):
    (ax, ay), (bx, by) = a, b
    if ay == by:
        y = ay + BOX_H / 2
        x1, x2 = (ax + BOX_W + 2, bx - 3) if bx > ax else (ax - 2, bx + BOX_W + 3)
        arrow(s, x1, y, x2, y, INK, 1.4, draw=delay, size=7)
        return f"M{x1},{y} L{x2},{y}"
    if ax != bx:
        raise ValueError("schematic connections must share a row or a column")
    x = ax + BOX_W / 2
    y1, y2 = (ay + BOX_H + 2, by - 3) if by > ay else (ay - 2, by + BOX_H + 3)
    arrow(s, x, y1, x, y2, INK, 1.4, draw=delay, size=7)
    return f"M{x},{y1} L{x},{y2}"


PROJECTS = [
    dict(slug="netscope", code="02-A", title="NETSCOPE", sub="Network packet analyzer",
         nodes=[("cap", "SCAPY CAPTURE", 0, 0), ("ana", "ANALYZER", 1, 0), ("thr", "THREAT SCORING", 2, 0),
                ("ws", "WEBSOCKET", 1, 1), ("ui", "SOC DASHBOARD", 2, 1)],
         edges=[("cap", "ana"), ("ana", "thr"), ("ana", "ws"), ("ws", "ui")],
         red=(["ANOMALY ALERTS", "PER-HOST RISK"], "ws"),
         stack="Python · Scapy · WebSockets", deploy="Vercel + Render", live=True),
    dict(slug="fsociety", code="02-B", title="FSOCIETY-WEB", sub="Security portfolio",
         nodes=[("site", "STATIC SITE", 0, 0), ("road", "ROADMAP", 1, 0), ("tool", "TOOLBOX", 2, 0),
                ("notes", "FIELD NOTES", 1, 1), ("ctf", "CTF TRACKER", 2, 1)],
         edges=[("site", "road"), ("road", "tool"), ("road", "notes"), ("notes", "ctf")],
         red=(["STATIC SITE", "NO BACKEND"], "notes"),
         stack="HTML · CSS · JavaScript", deploy="Vercel", live=True),
    dict(slug="industrust", code="02-C", title="INDUSTRUST BANK", sub="Banking system",
         nodes=[("web", "BROWSER", 0, 0), ("sec", "SPRING SECURITY", 1, 0), ("svc", "LEDGER SERVICE", 2, 0),
                ("log", "DOUBLE-ENTRY LOG", 1, 1), ("db", "POSTGRESQL", 2, 1)],
         edges=[("web", "sec"), ("sec", "svc"), ("svc", "db"), ("log", "db")],
         red=(["ROW-LEVEL LOCKS", "BCRYPT PINS"], "log"),
         stack="Spring Boot · PostgreSQL · Docker", deploy="Render + Neon", live=True),
    dict(slug="sms", code="02-D", title="STUDENT MGMT SYSTEM", sub="Records platform",
         nodes=[("ui", "DASHBOARD", 0, 0), ("api", "REST API", 1, 0), ("db", "POSTGRESQL", 2, 0),
                ("ci", "GITHUB ACTIONS", 1, 1), ("csv", "CSV EXPORT", 2, 1)],
         edges=[("ui", "api"), ("api", "db"), ("ci", "api"), ("db", "csv")],
         red=(["NO SECRETS IN SRC", "PII REMOVED"], "ci"),
         stack="Spring Boot · Neon · Actions", deploy="Render", live=True),
    dict(slug="snapurl", code="02-E", title="SNAPURL", sub="Serverless URL shortener",
         nodes=[("cli", "CLIENT", 0, 0), ("fn", "VERCEL FUNCTION", 1, 0), ("db", "TURSO EDGE DB", 2, 0),
                ("alias", "CUSTOM ALIAS", 1, 1), ("ttl", "TTL EXPIRY", 2, 1)],
         edges=[("cli", "fn"), ("fn", "db"), ("fn", "alias"), ("db", "ttl")],
         red=(["INPUT VALIDATED", "LINKS SELF-EXPIRE"], "alias"),
         stack="TypeScript · Express · Turso", deploy="Vercel", live=True),
    dict(slug="cineroulette", code="02-F", title="CINEROULETTE", sub="Movie picker",
         nodes=[("web", "NEXT.JS APP", 0, 0), ("api", "NESTJS API", 1, 0), ("pg", "POSTGRESQL", 2, 0),
                ("rd", "REDIS CACHE", 1, 1), ("sync", "SYNC WORKER", 2, 1)],
         edges=[("web", "api"), ("api", "pg"), ("api", "rd"), ("sync", "pg")],
         red=(["WEIGHTED PICKS", "NOT RANDOM"], "rd"),
         stack="Next.js · NestJS · Prisma · Redis", deploy="Vercel", live=True),
    dict(slug="gitatlas", code="02-G", title="GITATLAS", sub="Git command atlas",
         nodes=[("idx", "INDEX.HTML", 0, 0), ("search", "SEARCH", 1, 0), ("cmd", "381 COMMANDS", 2, 0),
                ("play", "17 PLAYBOOKS", 1, 1), ("wiz", "RECOVERY WIZARD", 2, 1)],
         edges=[("idx", "search"), ("search", "cmd"), ("search", "play"), ("play", "wiz")],
         red=(["RISKY COMMANDS", "ARE FLAGGED"], "play"),
         stack="HTML · CSS · JavaScript", deploy="Vercel", live=True),
    dict(slug="grabmedia", code="02-H", title="GRABMEDIA", sub="Media downloader",
         nodes=[("ui", "WEB CLIENT", 0, 0), ("hm", "HELMET HEADERS", 1, 0), ("rl", "RATE LIMITER", 2, 0),
                ("api", "MEDIA API", 1, 1), ("px", "EXPRESS PROXY", 2, 1)],
         edges=[("ui", "hm"), ("hm", "rl"), ("rl", "px"), ("px", "api")],
         red=(["API KEY HIDDEN", "CORS LOCKED"], "api"),
         stack="Node.js · Express · Helmet", deploy="GitHub Pages + Render", live=True),
    dict(slug="disease", code="02-I", title="DISEASE PREDICTION", sub="Explainable ML",
         nodes=[("ui", "STATIC UI", 0, 0), ("api", "FASTAPI", 1, 0), ("ml", "RF + EXTRATREES", 2, 0),
                ("pdf", "PDF REPORT", 1, 1), ("shap", "SHAP EXPLAINER", 2, 1)],
         edges=[("ui", "api"), ("api", "ml"), ("ml", "shap"), ("api", "pdf")],
         red=(["132 SYMPTOMS", "41 DISEASES"], "pdf"),
         stack="FastAPI · scikit-learn · SHAP", deploy="Vercel + Render", live=True),
    dict(slug="siteshield", code="02-J", title="SITESHIELD", sub="Security posture SaaS",
         nodes=[("ui", "REACT DASHBOARD", 0, 0), ("api", "FASTAPI", 1, 0), ("pg", "POSTGRESQL", 2, 0),
                ("q", "REDIS QUEUE", 1, 1), ("w", "CELERY SCANNERS", 2, 1)],
         edges=[("ui", "api"), ("api", "pg"), ("api", "q"), ("q", "w")],
         red=(["PASSIVE CHECKS", "BLUE-TEAM TOOL"], "q"),
         stack="React · FastAPI · Celery", deploy="In development", live=False),
]


def build_schematic(p):
    H = CARD_H
    s = Svg(490, H)
    paper(s)
    s.box(6, 6, 478, H - 12, INK2, 1)
    s.box(12, 12, 466, H - 24, INK, 1.4)
    s.text(28, 40, f"SCHEMATIC {p['code']}", "monom", 10.5, DIM, ls=1)
    s.text(28, 70, p["title"], "condb", 24, INK, ls=1.2)
    s.text(30 + tw("condb", p["title"], 24, 1.2) + 10, 70, p["sub"].upper(), "mono", 10.5, INK2, ls=.6)
    status, scol = ("LIVE", GREEN) if p["live"] else ("IN BUILD", AMBER)
    sw = tw("monob", status, 10.5, 1) + 30
    s.box(462 - sw, 26, sw, 22, scol, 1.2, r=11)
    s.add(f'<circle cx="{462 - sw + 12}" cy="37" r="4" fill="{scol}" class="pulse"/>')
    s.text(462 - sw + 22, 41, status, "monob", 10.5, scol, ls=1)
    s.line(28, 84, 462, 84, INK2, .8)
    pos = {nid: node_xy(c, r) for nid, _, c, r in p["nodes"]}
    for i, (nid, label, c, r) in enumerate(p["nodes"]):
        x, y = pos[nid]
        s.box(x, y, BOX_W, BOX_H, INK, 1.4, PAPER2, draw=.1 + i * .12)
        s.text(x + BOX_W / 2, y + 21.5, label, "condb", 12, INK, anchor="middle", ls=.8, cls="fi", d=.4 + i * .12)
    first = None
    for j, (a, b) in enumerate(p["edges"]):
        d = connect(s, pos[a], pos[b], .9 + j * .2)
        first = first or d
    # a data packet travelling the first connection
    k = s.uid("pk")
    s.style(f".{k}{{offset-path:path('{first}');animation:{k} 2.4s linear 2s infinite;opacity:0}}"
            f"@keyframes {k}{{0%{{offset-distance:0%;opacity:1}}90%{{opacity:1}}100%{{offset-distance:100%;opacity:0}}}}")
    s.add(f'<circle class="{k}" r="3.5" fill="{CYAN}"/>')
    # red review note in the free bottom-left slot, leader to the component's left edge
    lines, target = p["red"]
    tx, ty = pos[target]
    redline(s, 30, ROW_Y[1] - 4, lines, draw=2.0, size=10.5, pad=8, leader=(tx - 1, ty + BOX_H / 2))
    # title strip
    y0, div = 234, 352
    s.add(f'<rect x="12" y="{y0}" width="466" height="{H - 24 - y0 + 12}" fill="{PAPER2}"/>')
    s.line(12, y0, 478, y0, INK, 1.4)
    s.line(12, y0 + 44, div, y0 + 44, INK, 1)
    s.line(div, y0, div, H - 12, INK, 1)
    s.line(96, y0, 96, H - 12, INK, 1)
    s.text(24, y0 + 27, "STACK", "monom", 9.5, DIM, ls=1)
    s.text(106, y0 + 27, p["stack"], "mono", 11.5, INK)
    s.text(24, y0 + 71, "DEPLOY", "monom", 9.5, DIM, ls=1)
    s.text(106, y0 + 71, p["deploy"], "mono", 11.5, INK)
    cta = "OPEN LIVE" if p["live"] else "SOURCE"
    cw = tw("condb", cta, 14.5, 1.4)
    cx0 = div + (478 - div - cw - 20) / 2
    s.text(cx0, y0 + 50, cta, "condb", 14.5, CYAN, ls=1.4)
    s.style(".go{animation:go 1.8s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add('<g class="go">')
    s.path(f"M{cx0 + cw + 8},{y0 + 52} l9,-9 M{cx0 + cw + 10},{y0 + 43} h7 v7", CYAN, 2)
    s.add("</g>")
    s.save(out(f"schematic-{p['slug']}.svg"),
           f"Schematic of {p['title'].title()}, {p['sub']}: " +
           ", ".join(lbl.lower() for _, lbl, _, _ in p["nodes"]) + f". Stack: {p['stack']}. "
           + ("Live." if p["live"] else "In development."))


# ── 6. REVISION HISTORY (journey) ────────────────────────────────────────
def build_revisions():
    rows = [
        ("A", "START", "Started B.Tech CSE at Silicon Institute of Technology, Bhubaneswar", "RELEASED"),
        ("B", "BUILD", "First full-stack apps: Java, JavaScript, PHP, MySQL", "RELEASED"),
        ("C", "SHIP", "Live deployments: Spring Boot, Node, FastAPI on Vercel and Render", "RELEASED"),
        ("D", "NOW", "Cybersecurity Intern: pentesting & web application security", "CURRENT"),
        ("E", "2027", "Graduate: build + break, full-time", "PLANNED"),
    ]
    rh = 38
    s = Svg(1000, 130 + rh * (len(rows) + 1) + 26)
    paper(s)
    frame(s, zones=False)
    s.text(44, 62, "REVISION HISTORY", "condb", 26, INK, ls=1.5)
    s.text(46, 84, "EVERY CHANGE TO THE ENGINEER, IN ORDER", "mono", 11.5, INK2, ls=.8)
    x0, y0, width = 44, 108, 912
    cols = [(0, 60, "REV"), (60, 100, "PHASE"), (160, 600, "DESCRIPTION"), (760, 152, "STATUS")]
    s.add(f'<rect x="{x0}" y="{y0}" width="{width}" height="{rh}" fill="{INK}" opacity=".12"/>')
    for ox, _, lab in cols:
        s.text(x0 + ox + 12, y0 + 24, lab, "monob", 11, INK, ls=1.2)
    total_h = rh * (len(rows) + 1)
    s.box(x0, y0, width, total_h, INK, 1.6)
    for ox, _, _ in cols[1:]:
        s.line(x0 + ox, y0, x0 + ox, y0 + total_h, INK, 1)
    for i, (rev, phase, desc, status) in enumerate(rows):
        y = y0 + rh * (i + 1)
        s.line(x0, y, x0 + width, y, INK2, .8)
        cur = status == "CURRENT"
        planned = status == "PLANNED"
        col = RED if cur else (DIM if planned else INK)
        s.add(f'<g class="fi" style="--d:{.2 + i * .18:.2f}s">')
        s.circle(x0 + 30, y + rh / 2, 11, col, 1.4)
        s.text(x0 + 30, y + rh / 2 + 4.5, rev, "monob", 12, col, anchor="middle")
        s.text(x0 + 72, y + 24, phase, "condb", 14, col, ls=1.2)
        s.text(x0 + 172, y + 24, desc, "mono", 12.5, INK if not planned else DIM)
        scol = GREEN if status == "RELEASED" else (RED if cur else AMBER)
        s.text(x0 + 772, y + 24, status, "monob", 11.5, scol, ls=1.2)
        s.add("</g>")
        if cur:
            s.path(K.rev_cloud(x0 + 4, y + 3, width - 8, rh - 6, 6), RED, 1.5, draw=1.4, t=1.6)
    s.save(out("revisions.svg"), "Revision history: A, started B.Tech CSE; B, first full-stack apps; C, live "
                                 "deployments; D (current), Cybersecurity Intern; E (planned), graduate in 2027.")


# ── 7. SIGN-OFF (footer) ─────────────────────────────────────────────────
def build_signoff():
    s = Svg(1000, 270)
    paper(s)
    frame(s, zones=False)
    s.text(44, 72, "END OF DRAWING SET", "condb", 30, INK, ls=2)
    s.text(46, 104, "Need something built, or reviewed before it ships?", "cond", 19, INK2)
    s.text(46, 140, "arman-portfolio.online", "monom", 17, CYAN)
    s.line(46, 148, 46 + tw("monom", "arman-portfolio.online", 17), 148, CYAN, 1.2, draw=.6)
    s.text(46, 174, "fsociety-web.vercel.app  ·  github.com/arman080325", "mono", 12.5, INK2)
    # signature block
    sx, sy = 540, 200
    s.line(sx, sy, sx + 250, sy, INK, 1.2)
    s.text(sx, sy + 18, "A. A. KHAN  —  ENGINEER OF RECORD", "monom", 10.5, DIM, ls=1)
    s.path(f"M{sx + 10},{sy - 14} C{sx + 22},{sy - 52} {sx + 30},{sy - 52} {sx + 28},{sy - 18} "
           f"C{sx + 26},{sy - 2} {sx + 40},{sy - 30} {sx + 52},{sy - 36} C{sx + 64},{sy - 42} {sx + 56},{sy - 10} "
           f"{sx + 70},{sy - 16} C{sx + 84},{sy - 22} {sx + 90},{sy - 40} {sx + 104},{sy - 26} "
           f"C{sx + 116},{sy - 14} {sx + 128},{sy - 30} {sx + 142},{sy - 28} C{sx + 168},{sy - 24} {sx + 190},{sy - 18} "
           f"{sx + 226},{sy - 22}", INK, 2.2, draw=.8, t=2.4)
    stamp(s, 860, 120, ["APPROVED", "FOR RELEASE"], RED, angle=-9, delay=2.6, size=16)
    s.text(860, 200, "REV C  ·  SHEET 6 / 6", "monom", 10.5, DIM, anchor="middle", ls=1)
    s.save(out("signoff.svg"), "End of drawing set. Need something built, or reviewed before it ships? "
                               "arman-portfolio.online. Approved for release, signed A. A. Khan.")


HEADERS = [
    ("about", "02", "BILL OF MATERIALS", "WHO IS BEHIND THE DRAWINGS"),
    ("stack", "03", "EXPLODED VIEW", "WHAT I BUILD WITH, AND WHAT GUARDS IT"),
    ("work", "04", "SYSTEM SCHEMATICS", "TEN SHIPPED SYSTEMS · CLICK ANY SHEET TO OPEN IT"),
    ("journey", "05", "REVISION HISTORY", "HOW THE ENGINEER CHANGED OVER TIME"),
    ("activity", "06", "FIELD MEASUREMENTS", "LIVE DATA FROM GITHUB · RE-MEASURED EVERY 12 HOURS"),
]


def main():
    build_hero()
    for h in HEADERS:
        build_header(*h)
    build_bom()
    build_exploded()
    for p in PROJECTS:
        build_schematic(p)
    build_revisions()
    build_signoff()


if __name__ == "__main__":
    main()
