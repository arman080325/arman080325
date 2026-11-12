#!/usr/bin/env python3
"""Build the static metro-style drawings for the profile README.

Usage:
    pip install fonttools brotli
    python3 scripts/build_metro_assets.py          # writes assets/metro/*.svg

Live statistics boards are drawn separately by scripts/build_metro_stats.py
inside the GitHub workflow.
"""
import os
import random

import metro_kit as K
from metro_kit import (AMBER, GO, GREY, INK, INK2, LINE, LINE_NAME, PAPER, PAPER2, SIGN, SIGN2, SIGN_BORDER,
                       TICKET_LINE, WHITE, Svg, arrow_ne, arrow_right, bullet, panel, sign_plate, tw, wrap)

OUT = os.path.join(K.ROOT, "assets", "metro")


def out(name):
    return os.path.join(OUT, name)


# ── 1. DEPARTURE BOARD (hero) ────────────────────────────────────────────
FLAP_CSS = (
    ".c{transform-box:fill-box;transform-origin:center;animation:fl 16s infinite both;animation-delay:var(--d)}"
    "@keyframes fl{0%{transform:scaleY(1)}1%{transform:scaleY(.08)}2%{transform:scaleY(1)}3%{transform:scaleY(.08)}"
    "4%,100%{transform:scaleY(1)}}"
    ".a,.b{opacity:0}"
    ".a{animation:sa 16s steps(1) infinite both;animation-delay:var(--d)}@keyframes sa{0%{opacity:1}1%,100%{opacity:0}}"
    ".b{animation:sb 16s steps(1) infinite both;animation-delay:var(--d)}"
    "@keyframes sb{0%{opacity:0}1%{opacity:1}3%,100%{opacity:0}}"
    ".f{animation:sf 16s steps(1) infinite both;animation-delay:var(--d)}@keyframes sf{0%{opacity:0}3%,100%{opacity:1}}"
)
ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def flap_row(s, rnd, x, y, text, n, color, row, cw=20, ch=34, gap=2, size=19):
    """One row of split-flap cells. Each cell flips through two random glyphs to its letter."""
    text = text.ljust(n)[:n]
    for i, ch_ in enumerate(text):
        cx = x + i * (cw + gap)
        s.add(f'<g style="--d:{row * .35 + i * .045:.2f}s">')
        s.rect(cx, y, cw, ch, 3, SIGN2)
        s.add('<g class="c">')
        base = y + ch / 2 + size * .36
        s.text(cx + cw / 2, base, rnd.choice(ALPHA), "monob", size, GREY, anchor="middle", cls="a")
        s.text(cx + cw / 2, base, rnd.choice(ALPHA), "monob", size, GREY, anchor="middle", cls="b")
        if ch_ != " ":
            s.text(cx + cw / 2, base, ch_, "monob", size, color, anchor="middle", cls="f")
        s.add("</g>")
        s.add(f'<line x1="{cx}" y1="{y + ch / 2}" x2="{cx + cw}" y2="{y + ch / 2}" stroke="{SIGN}" stroke-width="1.3"/>')
        s.add("</g>")


def build_board():
    s = Svg(1000, 452)
    rnd = random.Random(2027)
    sign_plate(s, 16)
    s.style(FLAP_CSS)
    # header
    s.circle(42, 41, 5, AMBER, cls="pulse")
    s.text(56, 46, "ARMAN METRO  ·  DEPARTURES", "monob", 12.5, AMBER, ls=1.5)
    s.text(964, 46, "INDIA  ·  IST UTC+5:30", "mono", 11.5, GREY, anchor="end", ls=1)
    s.text(34, 108, "ARMAN AHEMAD KHAN", "signx", 52, WHITE, ls=-.5)
    y = 138
    x = 36
    bullet(s, x + 11, y - 5, 1)
    s.text(x + 30, y, "FULL-STACK DEVELOPER", "sign", 17, WHITE, ls=1)
    x2 = x + 30 + tw("sign", "FULL-STACK DEVELOPER", 17, 1) + 26
    bullet(s, x2 + 11, y - 5, 5)
    s.text(x2 + 30, y, "ETHICAL HACKER", "sign", 17, WHITE, ls=1)
    # table
    cols = {"TIME": 36, "DESTINATION": 142, "LINE": 646, "PLAT": 694, "STATUS": 760}
    for lab, cx in cols.items():
        s.text(cx, 180, lab, "mono", 10, GREY, ls=1.5)
    rows = [
        ("NOW", "CYBERSECURITY INTERN", 5, "01", "ON TIME", GO),
        ("LIVE", "9 APPS IN PRODUCTION", 1, "02", "ARRIVED", GO),
        ("2027", "B.TECH CSE GRADUATION", 2, "03", "BOARDING", AMBER),
        ("NEXT", "YOUR PROJECT", 4, "04", "OPEN", WHITE),
    ]
    for r, (t, dest, ln, plat, status, scol) in enumerate(rows):
        y = 190 + r * 44
        flap_row(s, rnd, cols["TIME"], y, t, 4, AMBER, r)
        flap_row(s, rnd, cols["DESTINATION"], y, dest, 22, WHITE, r)
        bullet(s, cols["LINE"] + 14, y + 17, ln, 24)
        flap_row(s, rnd, cols["PLAT"], y, plat, 2, WHITE, r)
        flap_row(s, rnd, cols["STATUS"], y, status, 8, scol, r)
        if status == "BOARDING":
            s.circle(950, y + 17, 5, AMBER, cls="blink")
    # ticker
    ty = 380
    s.rect(24, ty, 952, 44, 8, "#050607", SIGN_BORDER, 1)
    msg = ("BUILD IT  ·  BREAK IT  ·  HARDEN IT  ·  SHIP IT  ·  MIND THE GAP BETWEEN DEV AND SEC  ·  "
           "ALL SECURITY WORK IS AUTHORIZED, SCOPED AND DISCLOSED RESPONSIBLY  ·  ")
    mw = tw("monob", msg, 15, 1.5)
    s.defs.append(f'<clipPath id="tk"><rect x="30" y="{ty}" width="940" height="44"/></clipPath>')
    s.style(f".tick{{animation:tick {mw / 55:.1f}s linear infinite}}"
            f"@keyframes tick{{to{{transform:translateX(-{mw:.0f}px)}}}}")
    s.add('<g clip-path="url(#tk)"><g class="tick">')
    for i in range(3):
        s.text(40 + i * mw, ty + 28, msg, "monob", 15, AMBER, ls=1.5)
    s.add("</g></g>")
    s.save(out("board.svg"), "Departure board. Arman Ahemad Khan: full-stack developer and ethical hacker. Now: "
                             "Cybersecurity Intern, on time. Live: 9 apps in production, arrived. 2027: B.Tech CSE "
                             "graduation, boarding. Next: your project, open.")


# ── 2. NAV SIGNS ─────────────────────────────────────────────────────────
NAV = [("map", 1, "NETWORK MAP"), ("tickets", 2, "TICKETS"), ("journey", 3, "JOURNEY"), ("boards", 4, "LIVE BOARDS")]


def build_nav():
    for slug, n, label in NAV:
        w = int(tw("sign", label, 14, 1.2) + 78)
        s = Svg(w, 40)
        sign_plate(s, 9)
        bullet(s, 22, 20, n, 20)
        s.text(40, 25, label, "sign", 14, WHITE, ls=1.2)
        s.style(".nd{animation:nd 1.6s ease-in-out infinite}@keyframes nd{50%{transform:translateX(3px)}}")
        s.add('<g class="nd">')
        s.path(f"M{w - 26},20 h10 m-4,-4 l4,4 l-4,4", AMBER, 2)
        s.add("</g>")
        s.save(out(f"nav-{slug}.svg"), label.title())


# ── 3. STATION SIGNS (section headers) ───────────────────────────────────
def build_sign(slug, n, title, sub):
    s = Svg(1000, 84)
    sign_plate(s, 12)
    col = LINE[n]
    s.defs.append('<clipPath id="pl"><rect width="1000" height="84" rx="12"/></clipPath>')
    s.add('<g clip-path="url(#pl)">')
    s.rect(0, 0, 14, 84, 0, col)
    s.add("</g>")
    bullet(s, 54, 42, n, 40)
    s.text(90, 46, title, "signx", 29, WHITE, ls=.5)
    s.text(92, 66, sub, "mono", 10.5, GREY, ls=1.2)
    s.text(964, 34, f"STOP {n} OF 4", "mono", 10.5, GREY, anchor="end", ls=1.5)
    # a small train shuttling along a track on the right
    x0, x1, ty = 700, 964, 58
    s.path(f"M{x0},{ty} H{x1}", col, 3)
    for sx in (x0, x1):
        s.circle(sx, ty, 4.5, SIGN, WHITE, 2)
    k = "tr"
    s.style(f".{k}{{animation:{k} 6s ease-in-out infinite alternate}}@keyframes {k}{{to{{transform:translateX({x1 - x0 - 30}px)}}}}")
    s.add(f'<g class="{k}">')
    s.rect(x0, ty - 7, 30, 14, 4, WHITE)
    for i in range(3):
        s.rect(x0 + 4 + i * 8, ty - 4, 5.5, 5, 1, SIGN)
    s.add("</g>")
    s.save(out(f"sign-{slug}.svg"), f"{title.title()}: {sub.lower()}")


# ── 4. NETWORK MAP ───────────────────────────────────────────────────────
def build_map():
    s = Svg(1000, 630)
    panel(s, 16)
    s.style(".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr 2.2s cubic-bezier(.4,0,.2,1) var(--d,0s) forwards}"
            "@keyframes dr{to{stroke-dashoffset:0}}"
            ".tn{offset-rotate:auto}"
            ".ring{transform-box:fill-box;transform-origin:center;animation:ring 2.4s ease-out infinite}"
            "@keyframes ring{from{transform:scale(.5);opacity:.8}to{transform:scale(2.2);opacity:0}}")
    hub = (120, 300)
    y1, y2, y3, xs = 168, 300, 432, 836
    ring = "M82,92 H918 Q964,92 964,138 V502 Q964,548 918,548 H82 Q36,548 36,502 V138 Q36,92 82,92 Z"
    paths = {
        5: ring,
        1: f"M{hub[0]},{hub[1]} L252,{y1} H{xs}",
        2: f"M{hub[0]},{hub[1]} H{xs}",
        3: f"M{hub[0]},{hub[1]} L252,{y3} H{xs}",
        4: f"M{xs},{y1} V{y3}",
    }
    trunk = {
        1: (y1, [(280, "HTML/CSS"), (375, "JavaScript"), (470, "TypeScript"), (565, "React"), (660, "Next.js"),
                 (755, "Tailwind")]),
        2: (y2, [(205, "Java"), (297, "Spring Boot"), (389, "Node.js"), (481, "Express"), (573, "NestJS"),
                 (665, "FastAPI"), (757, "Python")]),
        3: (y3, [(300, "MySQL"), (420, "PostgreSQL"), (540, "MongoDB"), (660, "Redis"), (760, "Prisma")]),
    }
    ship = [(212, "Git"), (256, "GitHub Actions"), (366, "Render")]
    inter = [(y1, "Vercel"), (y2, "Docker"), (y3, "Neon · Turso")]
    sec_top = [(200, "Kali Linux"), (420, "Nmap"), (640, "Burp Suite")]
    sec_bottom = [(200, "Wireshark"), (420, "Metasploit"), (640, "Volatility3")]
    n_stations = (sum(len(v[1]) for v in trunk.values()) + len(ship) + len(inter) + len(sec_top) + len(sec_bottom) + 3)
    # title
    s.text(32, 48, "ARMAN METRO", "signx", 27, "fg", ls=.5)
    s.text(34, 70, "NETWORK MAP  ·  SKILLS AND TOOLS  ·  NOT TO SCALE", "mono", 11, "muted", ls=1.2)
    s.text(968, 48, f"5 LINES  ·  {n_stations} STATIONS", "monob", 12, "soft", anchor="end", ls=1.2)
    s.text(968, 70, "SECURITY RUNS THE CIRCLE LINE AROUND EVERYTHING", "mono", 10.5, "l5", anchor="end", ls=.8)
    # lines (drawn in on load)
    for i, n in enumerate((5, 2, 1, 3, 4)):
        s.path(paths[n], f"l{n}", 9, cls="dr", extra='pathLength="1"')
        s.parts[-1] = s.parts[-1].replace('style="', f'style="--d:{i * .25:.2f}s;', 1)
    # trains
    for n, dur, mode in ((5, 30, "linear infinite"), (1, 9, "ease-in-out infinite alternate"),
                         (2, 8, "ease-in-out infinite alternate"), (3, 10, "ease-in-out infinite alternate"),
                         (4, 5, "ease-in-out infinite alternate")):
        k = f"t{n}"
        s.style(f".{k}{{offset-path:path('{paths[n]}');animation:{k} {dur}s {mode};animation-delay:2.4s;"
                f"offset-distance:0%}}@keyframes {k}{{to{{offset-distance:100%}}}}")
        s.add(f'<g class="tn {k}">')
        s.rect(-11, -6, 22, 12, 4, "fg", "card", 1.5)
        s.rect(-7, -3, 4, 6, 1, f"l{n}")
        s.rect(-2, -3, 4, 6, 1, f"l{n}")
        s.rect(3, -3, 4, 6, 1, f"l{n}")
        s.add("</g>")

    def station(x, y, big=False):
        s.circle(x, y, 9.5 if big else 5.5, "card", "fg", 3.2 if big else 2.6)

    def label(x, y, t, anchor="middle", size=12.5):
        s.text(x, y, t, "sign", size, "fg", anchor=anchor)

    for n, (y, sts) in trunk.items():
        for x, name in sts:
            station(x, y)
            label(x, y - 15, name)
    for y, name in ship:
        station(xs, y)
        label(xs - 15, y + 4.5, name, "end")
    for y, name in inter:
        station(xs, y, True)
        label(xs + 17, y + 4.5, name, "start")
    for x, name in sec_top:
        station(x, 92)
        label(x, 119, name)
    for x, name in sec_bottom:
        station(x, 548)
        label(x, 532, name)
    station(36, 234)
    label(52, 238.5, "Ghidra", "start")
    station(964, 366)
    label(949, 370.5, "OWASP Top 10", "end")
    # hub
    s.circle(hub[0], hub[1], 13, "l5", cls="ring")
    s.circle(hub[0], hub[1], 13, "card", "fg", 3.6)
    s.circle(hub[0], hub[1], 5, "l5", cls="pulse")
    s.text(hub[0] - 20, hub[1] - 34, "ARMAN", "signx", 13, "fg", anchor="end", ls=.6)
    s.text(hub[0] - 20, hub[1] - 20, "CENTRAL", "signx", 13, "fg", anchor="end", ls=.6)
    s.text(hub[0] - 20, hub[1] + 34, "YOU ARE", "mono", 9, "l5", anchor="end", ls=1)
    s.text(hub[0] - 20, hub[1] + 46, "HERE", "mono", 9, "l5", anchor="end", ls=1)
    # legend
    lx = 60
    for n in (1, 2, 3, 4, 5):
        s.rect(lx - 11, 590 - 11, 22, 22, 6, f"l{n}")
        s.text(lx, 590 + 5.5, str(n), "signx", 15, "#14161a" if n == 3 else "#ffffff", anchor="middle")
        name = LINE_NAME[n] + (" · CIRCLE" if n == 5 else " LINE")
        s.text(lx + 19, 590 + 4.5, name, "sign", 12, "soft", ls=1)
        lx += 19 + tw("sign", name, 12, 1) + 44
    s.save(out("map.svg"),
           "Metro network map of skills. Line 1 Build: HTML/CSS, JavaScript, TypeScript, React, Next.js, Tailwind. "
           "Line 2 Server: Java, Spring Boot, Node.js, Express, NestJS, FastAPI, Python. Line 3 Data: MySQL, "
           "PostgreSQL, MongoDB, Redis, Prisma. Line 4 Ship: Git, GitHub Actions, Docker, Vercel, Render, Neon, Turso. "
           "Line 5 Security, the circle line around everything: Kali Linux, Nmap, Burp Suite, Wireshark, Metasploit, "
           "Volatility3, Ghidra, OWASP Top 10.")


# ── 5. TICKETS (projects) ────────────────────────────────────────────────
PROJECTS = [
    ("netscope", "NetScope", 5, "raw packets", "SOC dashboard",
     "Real-time traffic analysis with anomaly alerts and per-host risk scores.",
     "Python · Scapy · WebSockets", "Vercel + Render", True),
    ("fsociety", "fsociety-web", 1, "blank page", "security portfolio",
     "Cinematic portfolio with an interactive roadmap, in-browser tools and CTF progress.",
     "HTML · CSS · JavaScript", "Vercel", True),
    ("industrust", "IndusTrust Bank", 2, "console JDBC app", "web bank",
     "Double-entry ledger, row-locked atomic transfers, BigDecimal money, hashed PINs.",
     "Spring Boot · PostgreSQL · Docker", "Render + Neon", True),
    ("sms", "Student Mgmt System", 2, "Swing + Oracle", "cloud REST service",
     "Records platform with analytics, CSV export and CI on every push.",
     "Spring Boot · Neon · GitHub Actions", "Render", True),
    ("snapurl", "SnapURL", 2, "long URL", "short link",
     "Serverless shortener with custom aliases and self-expiring links.",
     "TypeScript · Express · Turso", "Vercel", True),
    ("cineroulette", "CineRoulette", 1, "100,000 movies", "one pick",
     "Pick a mood, spin, get one explained pick, weighted per language and region.",
     "Next.js · NestJS · Prisma · Redis", "Vercel", True),
    ("gitatlas", "GitAtlas", 1, "git panic", "right command",
     "381 Git commands in plain English, 17 recovery playbooks, risky commands flagged.",
     "HTML · CSS · JavaScript", "Vercel", True),
    ("grabmedia", "GrabMedia", 2, "public post URL", "saved media",
     "Instagram and YouTube media up to 2160p behind a hardened, rate-limited proxy.",
     "Node.js · Express · Helmet", "GH Pages + Render", True),
    ("disease", "Disease Prediction", 3, "132 symptoms", "explained result",
     "Predicts 41 diseases with a tree ensemble, SHAP explanations and PDF reports.",
     "FastAPI · scikit-learn · SHAP", "Vercel + Render", True),
    ("siteshield", "SiteShield", 5, "unknown posture", "A to F grade",
     "Grades a site's TLS, headers, cookies and DNS, re-scans on a schedule.",
     "React · FastAPI · Celery", "In development", False),
]


def build_ticket(idx, slug, name, ln, frm, to, desc, stack, platform, live):
    W, H, NX = 490, 240, 352
    s = Svg(W, H)
    col = TICKET_LINE[ln]
    shape = (f"M14,0 H{NX - 9} A9,9 0 0 0 {NX + 9},0 H{W - 14} Q{W},0 {W},14 V{H - 14} Q{W},{H} {W - 14},{H} "
             f"H{NX + 9} A9,9 0 0 0 {NX - 9},{H} H14 Q0,{H} 0,{H - 14} V14 Q0,0 14,0 Z")
    s.defs.append(f'<clipPath id="tk"><path d="{shape}"/></clipPath>')
    s.style(".scan{animation:scan 2.6s ease-in-out infinite alternate}@keyframes scan{to{transform:translateY(46px)}}"
            ".shine{animation:shine 7s ease-in-out infinite}"
            "@keyframes shine{0%,60%{transform:translateX(-200px)}100%{transform:translateX(620px)}}")
    s.defs.append('<linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                  '<stop offset=".5" stop-color="#fff" stop-opacity=".5"/><stop offset="1" stop-color="#fff" '
                  'stop-opacity="0"/></linearGradient>')
    s.add('<g clip-path="url(#tk)">')
    s.rect(0, 0, W, H, 0, PAPER)
    s.rect(NX, 0, W - NX, H, 0, PAPER2)
    s.rect(0, 0, W, 36, 0, col)
    s.add('<rect class="shine" x="0" y="0" width="90" height="240" fill="url(#sh)" transform="skewX(-18)"/>')
    s.add("</g>")
    s.path(shape, "#00000026", 1.2)
    s.path(f"M{NX},12 V{H - 12}", INK2, 1.4, extra='stroke-dasharray="2 6"')
    # band
    s.rect(15, 8, 20, 20, 5.5, "#ffffff")
    s.text(25, 23.5, str(ln), "signx", 14, col, anchor="middle")
    s.text(44, 23.5, f"LINE {ln}  ·  {LINE_NAME[ln]}", "signx", 12.5, "#ffffff", ls=1.6)
    s.text(NX - 16, 23, f"TICKET {idx:02d}", "mono", 10.5, "#ffffff", anchor="end", ls=1)
    # main
    s.text(20, 72, name, "signx", 24, INK)
    s.text(20, 95, "FROM", "mono", 8.5, INK2, ls=1.2)
    s.text(20, 112, frm, "sign", 13.5, INK)
    ax = 20 + max(tw("sign", frm, 13.5), 44) + 14
    arrow_right(s, ax, 107.5, col, 8, 2.2)
    tx = ax + 30
    s.text(tx, 95, "TO", "mono", 8.5, INK2, ls=1.2)
    s.text(tx, 112, to, "sign", 13.5, INK)
    s.path(f"M20,126 H{NX - 18}", INK2, 1, extra='stroke-dasharray="1 5"')
    for i, line in enumerate(wrap(desc, "mono", 10.8, NX - 44)[:2]):
        s.text(20, 146 + i * 16, line, "mono", 10.8, INK2)
    s.text(20, 190, "STACK", "mono", 8.5, INK2, ls=1.2)
    s.text(20, 207, stack, "sign", 12.5, INK)
    s.text(20, 227, "VALID ON ALL DEVICES  ·  NO LOGIN REQUIRED" if live else "SERVICE OPENS SOON  ·  BUILDING IN PUBLIC",
           "mono", 8, INK2, ls=.8)
    # stub
    cx = (NX + W) / 2
    scol = "#0d8a4d" if live else "#b97f00"
    stxt = "IN SERVICE" if live else "IN BUILD"
    sw = tw("signx", stxt, 11.5, 1.2)
    s.circle(cx - sw / 2 - 9, 60, 4.5, scol, cls="pulse")
    s.text(cx - sw / 2 + 1, 64.5, stxt, "signx", 11.5, scol, ls=1.2)
    s.text(cx, 84, "PLATFORM", "mono", 8.5, INK2, anchor="middle", ls=1.2)
    s.text(cx, 100, platform, "sign", 11.5, INK, anchor="middle")
    rnd = random.Random(slug)
    bx, by, bh = NX + 20, 114, 50
    x = bx
    while x < W - 22:
        w = rnd.choice([1.5, 1.5, 2.5, 3.5])
        s.rect(x, by, w, bh, 0, INK)
        x += w + rnd.choice([1.5, 2.5, 3.5])
    s.add(f'<rect class="scan" x="{bx - 4}" y="{by + 1}" width="{W - NX - 32}" height="2" fill="#e0322b" opacity=".85"/>')
    cta = "TAP TO BOARD" if live else "VIEW SOURCE"
    cw = tw("signx", cta, 12, 1.2)
    s.text(cx - 8, 192, cta, "signx", 12, col, anchor="middle", ls=1.2)
    s.style(".go{animation:go 1.8s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add('<g class="go">')
    arrow_ne(s, cx - 8 + cw / 2 + 5, 182, col, 8)
    s.add("</g>")
    s.text(cx, 222, f"AK-{idx:02d}-2027", "mono", 9, INK2, anchor="middle", ls=1.5)
    s.save(out(f"ticket-{slug}.svg"),
           f"Ticket {idx:02d}, line {ln} {LINE_NAME[ln].title()}: {name}. From {frm} to {to}. {desc} Stack: {stack}. "
           f"Platform: {platform}. " + ("In service." if live else "In development."))


# ── 6. JOURNEY (in-car line diagram) ─────────────────────────────────────
def build_journey():
    s = Svg(1000, 280)
    panel(s, 16)
    stops = [("2023", "Started B.Tech CSE", "Silicon IT, Bhubaneswar", "l1"),
             ("BUILD", "First full-stack apps", "Java · JS · PHP · MySQL", "l2"),
             ("SHIP", "Live deployments", "Spring Boot · Node · FastAPI", "l4"),
             ("NOW", "Cybersecurity Intern", "Pentesting · web AppSec", "l5"),
             ("2027", "Graduate", "Build + break, full-time", "muted")]
    x0, x1, ly = 110, 890, 150
    xs = [x0 + (x1 - x0) * i / 4 for i in range(5)]
    s.text(32, 46, "LINE DIAGRAM", "signx", 20, "fg", ls=.8)
    s.text(34, 66, "THE JOURNEY SO FAR  ·  ONE DIRECTION ONLY", "mono", 10.5, "muted", ls=1.2)
    # next-stop sign
    nw = 318
    s.rect(1000 - 32 - nw, 26, nw, 44, 8, SIGN, SIGN_BORDER, 1.2)
    s.circle(1000 - 32 - nw + 20, 48, 4.5, AMBER, cls="blink")
    s.text(1000 - 32 - nw + 34, 53.5, "NEXT STOP:  GRADUATION 2027", "monob", 14, AMBER, ls=1)
    # track
    s.path(f"M{xs[0]},{ly} H{xs[3]}", "l1", 9)
    s.path(f"M{xs[3]},{ly} H{xs[4]}", "muted", 5, extra='stroke-dasharray="3 12"')
    s.style(".ring{transform-box:fill-box;transform-origin:center;animation:ring 2.4s ease-out infinite}"
            "@keyframes ring{from{transform:scale(.5);opacity:.8}to{transform:scale(2.4);opacity:0}}"
            f".jt{{animation:jt 12s cubic-bezier(.45,0,.2,1) infinite}}"
            f"@keyframes jt{{0%,4%{{transform:translateX(0)}}18%,24%{{transform:translateX({xs[1] - xs[0]:.0f}px)}}"
            f"38%,44%{{transform:translateX({xs[2] - xs[0]:.0f}px)}}60%,100%{{transform:translateX({xs[3] - xs[0]:.0f}px)}}}}")
    for i, (k, t, sub, col) in enumerate(stops):
        x = xs[i]
        future = i == 4
        s.text(x, 100, k, "monob", 12, col, anchor="middle", ls=1.5)
        if i == 3:
            s.circle(x, ly, 11, "l5", cls="ring")
        s.circle(x, ly, 10, "card", "muted" if future else "fg", 3.4)
        s.text(x, 202, t, "sign", 15, "muted" if future else "fg", anchor="middle")
        s.text(x, 222, sub, "mono", 10.5, "muted", anchor="middle")
    # train
    s.add('<g class="jt">')
    tx, ty = xs[0] - 27, ly - 36
    s.rect(tx, ty, 54, 22, 7, "fg")
    for i in range(4):
        s.rect(tx + 6 + i * 11, ty + 5, 8, 8, 2, "card")
    s.path(f"M{xs[0]},{ty + 22} V{ly - 12}", "fg", 2)
    s.add("</g>")
    s.text(500, 256, "THIS TRAIN TERMINATES AT: SECURE SOFTWARE, SHIPPED", "mono", 10, "muted", anchor="middle", ls=1.5)
    s.save(out("journey.svg"), "Line diagram of the journey: 2023 started B.Tech CSE at Silicon Institute of "
                               "Technology; built first full-stack apps; shipped live deployments; now a "
                               "Cybersecurity Intern; next stop, graduation in 2027.")


# ── 7. WAY OUT (footer) ──────────────────────────────────────────────────
def build_wayout():
    s = Svg(1000, 200)
    sign_plate(s, 16)
    s.rect(28, 28, 176, 84, 10, AMBER)
    s.text(46, 64, "WAY OUT", "signx", 27, SIGN, ls=.5)
    s.style(".wo{animation:wo 1.6s ease-in-out infinite}@keyframes wo{50%{transform:translateX(6px)}}")
    s.add('<g class="wo">')
    arrow_right(s, 48, 90, SIGN, 11, 4)
    s.add("</g>")
    s.text(232, 56, "This README terminates here. All change for the full portfolio.", "sign", 17, WHITE)
    s.text(232, 98, "arman-portfolio.online", "signx", 34, AMBER, ls=-.3)
    s.text(964, 98, "fsociety-web.vercel.app", "mono", 12, GREY, anchor="end", ls=.5)
    # hazard stripe with a message
    hy = 138
    s.defs.append(f'<pattern id="hz" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                  f'<rect width="20" height="40" fill="{AMBER}"/><rect x="20" width="20" height="40" fill="{SIGN}"/></pattern>'
                  f'<clipPath id="hc"><rect x="28" y="{hy}" width="944" height="34" rx="6"/></clipPath>')
    s.style(".hz{animation:hz 2.4s linear infinite}@keyframes hz{to{transform:translateX(56.57px)}}")
    s.add(f'<g clip-path="url(#hc)"><rect class="hz" x="-100" y="{hy}" width="1200" height="34" fill="url(#hz)"/></g>')
    msg = "MIND THE GAP BETWEEN BUILD AND BREAK"
    mw = tw("signx", msg, 15, 2) + 40
    s.rect(500 - mw / 2, hy + 3, mw, 28, 5, AMBER)
    s.text(500, hy + 22.5, msg, "signx", 15, SIGN, anchor="middle", ls=2)
    s.save(out("wayout.svg"), "Way out. This README terminates here; all change for the full portfolio at "
                              "arman-portfolio.online. Mind the gap between build and break.")


SIGNS = [
    ("map", 1, "NETWORK MAP", "EVERY SKILL IS A STATION  ·  EVERY DISCIPLINE IS A LINE"),
    ("tickets", 2, "TICKET OFFICE", "TEN PROJECTS  ·  TAP ANY TICKET TO BOARD THE LIVE APP"),
    ("journey", 3, "LINE DIAGRAM", "WHERE THIS TRAIN HAS BEEN, AND WHERE IT STOPS NEXT"),
    ("boards", 4, "LIVE BOARDS", "REAL GITHUB DATA  ·  REFRESHED EVERY 12 HOURS"),
]


def main():
    build_board()
    build_nav()
    for sg in SIGNS:
        build_sign(*sg)
    build_map()
    for i, p in enumerate(PROJECTS, 1):
        build_ticket(i, *p)
    build_journey()
    build_wayout()


if __name__ == "__main__":
    main()
