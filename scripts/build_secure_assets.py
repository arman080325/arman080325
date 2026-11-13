#!/usr/bin/env python3
"""Build the static "Secure by Design" drawings for the profile README.

Usage:
    pip install fonttools brotli
    python3 scripts/build_secure_assets.py          # writes assets/secure/*.svg

Live panels (git log, coverage heatmap, numbers, languages) are drawn
separately by scripts/build_secure_stats.py inside the GitHub workflow.
"""
import os

import secure_kit as K
from secure_kit import (BORDER, BUILD, BUILD2, CM, CYAN, DIM, FN, KW, LINEBG, MUTED, PANEL, PANEL2, SAFE, SOFT, STR,
                        TEXT, TY, VULN, WARN, Svg, arrow_ne, card, check, chip, section_title, tw, warn_icon,
                        window_bar, wrap)

OUT = os.path.join(K.ROOT, "assets", "secure")


def out(name):
    return os.path.join(OUT, name)


def phase(s, start, end, period, fade=.35):
    """Class that is visible between start and end seconds of a looping timeline."""
    k = s.uid("ph")
    p = lambda t: f"{100 * max(0, min(t, period)) / period:.2f}%"
    s.style(f".{k}{{opacity:0;animation:{k} {period}s infinite}}"
            f"@keyframes {k}{{0%,{p(start)}{{opacity:0}}{p(start + fade)},{p(end)}{{opacity:1}}"
            f"{p(end + fade)},100%{{opacity:0}}}}")
    return k


# ── 1. HERO: write, break, fix ───────────────────────────────────────────
CODE_TOP = [
    [("@Repository", FN)],
    [("public class ", KW), ("AccountRepository", TY), (" {", SOFT)],
    [],
    [("  public ", KW), ("Account ", TY), ("findById", FN), ("(", SOFT), ("Connection ", TY), ("db, ", SOFT),
     ("String ", TY), ("id", SOFT), (") {", SOFT)],
]
CODE_BAD = [
    [("    String ", TY), ("sql = ", SOFT), ('"SELECT * FROM accounts WHERE id = \'"', STR), (" + id + ", SOFT),
     ('"\'"', STR), (";", SOFT)],
    [("    ResultSet ", TY), ("rs = db.", SOFT), ("createStatement", FN), ("().", SOFT), ("executeQuery", FN),
     ("(sql);", SOFT)],
    [("    return ", KW), ("map", FN), ("(rs);", SOFT)],
    [("  }", SOFT)],
    [("}", SOFT)],
]
CODE_FIX = [
    ("+", [("    PreparedStatement ", TY), ("ps = db.", SOFT), ("prepareStatement", FN), ("(", SOFT)]),
    ("+", [("        ", SOFT), ('"SELECT * FROM accounts WHERE id = ?"', STR), (");", SOFT)]),
    ("+", [("    ps.", SOFT), ("setString", FN), ("(1, id);", SOFT), ("   // bound as data", CM)]),
    ("+", [("    ResultSet ", TY), ("rs = ps.", SOFT), ("executeQuery", FN), ("();", SOFT)]),
    (" ", [("    return ", KW), ("map", FN), ("(rs);", SOFT)]),
    (" ", [("  }", SOFT)]),
    (" ", [("}", SOFT)]),
]


def build_hero():
    P = 14.0
    s = Svg(1000, 500)
    card(s, 16, BUILD)
    ex, ey, ew, eh = 22, 22, 604, 456
    s.rect(ex, ey, ew, eh, 12, K.BG, BORDER, 1.2)
    window_bar(s, ex, ey, ew, "", 36, 12)
    # tabs
    s.rect(ex + 84, ey + 6, 178, 30, 6, K.BG)
    s.text(ex + 98, ey + 26, "AccountRepository.java", "mono", 11, TEXT)
    s.text(ex + 278, ey + 26, "SecurityConfig.java", "mono", 11, MUTED)
    gx, cx, lh, y0, size = ex + 40, ex + 56, 22, ey + 68, 12.5

    def line(n, y, segs, marker=None, cls=""):
        col = {"-": VULN, "+": SAFE}.get(marker, DIM)
        s.text(gx, y, marker if marker in ("+", "-") else str(n), "mono", 11, col, anchor="end")
        if segs:
            s.spans(cx, y, segs, size, cls=cls)

    for i, segs in enumerate(CODE_TOP):
        line(i + 1, y0 + i * lh, segs)
    t_flag, t_fix, t_end = 3.0, 6.4, P - .6
    # state A: vulnerable code
    a = phase(s, 0, t_fix, P, .01)
    s.add(f'<g class="{a}">')
    hy = y0 + 4 * lh
    hl = phase(s, t_flag, t_fix, P, .3)
    s.add(f'<g class="{hl}">')
    s.rect(ex + 1, hy - 16, ew - 2, 22, 0, VULN, op=.13)
    s.rect(ex + 1, hy - 16, 3, 22, 0, VULN)
    wiggle = " ".join(f"q{3},{-3 if j % 2 else 3} 6,0" for j in range(52))
    s.path(f"M{cx + 98},{hy + 5} {wiggle}", VULN, 1.2)
    s.add("</g>")
    for i, segs in enumerate(CODE_BAD):
        line(5 + i, hy + i * lh, segs)
    bub = phase(s, t_flag + .5, t_fix, P, .3)
    by = ey + eh - 140
    s.add(f'<g class="{bub}">')
    s.path(f"M{ex + 3},{hy + 6} V{by + 36} H{cx}", VULN, 1.2, dash="3 3")
    s.rect(cx, by, ew - 76, 72, 10, "#2a1520", VULN, 1.2)
    warn_icon(s, cx + 22, by + 23, VULN, 15)
    s.text(cx + 40, by + 28, "SECURITY REVIEW  ·  CWE-89  ·  SQL injection", "monob", 11.5, VULN, ls=.4)
    s.text(cx + 40, by + 48, "User input is concatenated into the query string,", "body", 12.5, SOFT)
    s.text(cx + 40, by + 64, "so a crafted id could change what the query does.", "body", 12.5, SOFT)
    s.add("</g>")
    s.add("</g>")
    # state B: the diff
    b = phase(s, t_fix, t_end, P, .4)
    s.reduced += f".{b}{{opacity:1!important}}.{a}{{opacity:0!important}}"
    s.add(f'<g class="{b}">')
    for i, segs in enumerate(CODE_BAD[:2]):
        y = hy + i * lh
        s.rect(ex + 1, y - 16, ew - 2, 22, 0, VULN, op=.11)
        line(None, y, segs, "-")
        s.path(f"M{cx},{y - 4} H{cx + tw('mono', ''.join(t for t, _ in segs), size)}", VULN, 1.2, op=.8)
    for i, (mk, segs) in enumerate(CODE_FIX):
        y = hy + (2 + i) * lh
        if mk == "+":
            s.rect(ex + 1, y - 16, ew - 2, 22, 0, SAFE, op=.1)
            s.rect(ex + 1, y - 16, 3, 22, 0, SAFE)
        line(5 + i, y, segs, mk if mk == "+" else None)
    fb = phase(s, t_fix + 1.2, t_end, P, .3)
    s.add(f'<g class="{fb}">')
    s.rect(cx, by + 28, ew - 76, 44, 10, "#11261f", SAFE, 1.2)
    s.circle(cx + 22, by + 50, 9, "none", SAFE, 1.6)
    check(s, cx + 17.5, by + 50.5, SAFE, 9, 2)
    s.text(cx + 40, by + 55, "FIXED  ·  parameterized query, input bound as data  ·  re-tested", "monob", 11, SAFE)
    s.add("</g>")
    s.add("</g>")
    # scan bar
    s.defs.append(f'<linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" '
                  f'stop-opacity="0"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".22"/></linearGradient>')
    s.style(f".sc{{opacity:0;animation:sc {P}s linear infinite}}"
            f"@keyframes sc{{0%,{100 * .9 / P:.2f}%{{opacity:0;transform:translateY(0)}}"
            f"{100 * 1.0 / P:.2f}%{{opacity:1;transform:translateY(0)}}"
            f"{100 * t_flag / P:.2f}%{{opacity:1;transform:translateY({hy - y0 + 10}px)}}"
            f"{100 * (t_flag + .3) / P:.2f}%,100%{{opacity:0;transform:translateY({hy - y0 + 10}px)}}}}")
    s.add(f'<g class="sc"><rect x="{ex + 1}" y="{y0 - 40}" width="{ew - 2}" height="34" fill="url(#scan)"/>'
          f'<rect x="{ex + 1}" y="{y0 - 6}" width="{ew - 2}" height="1.5" fill="{CYAN}"/></g>')
    # status bar
    sy = ey + eh - 26
    s.path(f"M{ex},{sy} H{ex + ew}", BORDER, 1)
    s.text(ex + 16, sy + 17, "main", "mono", 10.5, MUTED)
    s.text(ex + 64, sy + 17, "Java  ·  UTF-8", "mono", 10.5, MUTED)
    p1 = phase(s, t_flag, t_fix, P, .3)
    p0 = phase(s, t_fix + 1.2, t_end, P, .3)
    s.reduced += f".{p0}{{opacity:1!important}}"
    s.add(f'<g class="{p1}">')
    s.circle(ex + ew - 104, sy + 13, 4, VULN)
    s.text(ex + ew - 16, sy + 17, "1 problem", "mono", 10.5, VULN, anchor="end")
    s.add(f'</g><g class="{p0}">')
    s.circle(ex + ew - 112, sy + 13, 4, SAFE)
    s.text(ex + ew - 16, sy + 17, "0 problems", "mono", 10.5, SAFE, anchor="end")
    s.add("</g>")
    # right column
    x = 656
    s.text(x, 64, "SECURE BY DESIGN", "monob", 11.5, BUILD, ls=2.4)
    s.text(x - 2, 112, "Arman Ahemad", "head", 38, TEXT, ls=-1)
    s.text(x - 2, 154, "Khan", "head", 38, TEXT, ls=-1)
    s.text(x, 188, "Full-stack developer", "bodym", 16, SOFT)
    s.text(x, 210, "and ethical hacker.", "bodym", 16, SOFT)
    s.text(x, 240, "I write the code, try to break it,", "body", 13.5, MUTED)
    s.text(x, 258, "then ship the fix.", "body", 13.5, MUTED)
    steps = [("01", "WRITE", "Spring Boot · Node · React", BUILD, 0, t_flag),
             ("02", "BREAK", "Burp · Nmap · manual review", VULN, t_flag, t_fix),
             ("03", "FIX", "parameterized · validated", SAFE, t_fix, t_end)]
    for i, (num, lab, sub, col, a0, a1) in enumerate(steps):
        y = 292 + i * 50
        s.rect(x, y, 318, 42, 10, PANEL2, BORDER, 1)
        act = phase(s, a0, a1, P, .25)
        s.add(f'<g class="{act}">')
        s.rect(x, y, 318, 42, 10, "none", col, 1.4)
        s.rect(x, y + 10, 3, 22, 1.5, col)
        s.add("</g>")
        s.text(x + 16, y + 26, num, "monob", 11, col)
        s.text(x + 44, y + 26, lab, "monob", 12.5, TEXT, ls=1.6)
        s.text(x + 306, y + 26, sub, "mono", 10, MUTED, anchor="end")
    cx2 = x
    for lab, col in (("Cybersecurity Intern", SAFE), ("CSE '27", BUILD2), ("India", SOFT)):
        cx2 += chip(s, cx2, 448, lab, col, 10.5, 24) + 8
    s.save(out("hero.svg"), "Arman Ahemad Khan, full-stack developer and ethical hacker: secure by design. A code "
                            "editor shows a SQL injection flaw (CWE-89) being flagged in review and fixed with a "
                            "parameterized query. Write, break, fix. Cybersecurity Intern, B.Tech CSE 2027, India.")


# ── 2. NAV ───────────────────────────────────────────────────────────────
NAV = [("stack", "Stack under test"), ("projects", "Projects"), ("toolkit", "Toolkit"), ("activity", "Activity")]


def build_nav():
    for slug, label in NAV:
        w = int(tw("bodym", label, 14) + 62)
        s = Svg(w, 40)
        s.rect(.75, .75, w - 1.5, 38.5, 20, PANEL, BORDER, 1.5)
        s.circle(20, 20, 5, BUILD)
        s.circle(27, 20, 5, SAFE, op=.9)
        s.text(42, 25, label, "bodym", 14, TEXT)
        s.save(out(f"nav-{slug}.svg"), label)


# ── 3. SECTION HEADERS ───────────────────────────────────────────────────
def build_header(slug, num, title, sub):
    s = Svg(1000, 72)
    s.rect(.75, .75, 998.5, 70.5, 14, PANEL, BORDER, 1.5)
    s.rect(0, 14, 4, 22, 2, BUILD)
    s.rect(0, 36, 4, 22, 2, SAFE)
    s.text(26, 43, num, "monob", 13, BUILD2)
    s.text(60, 45, title, "head", 23, TEXT, ls=-.4)
    s.text(972, 42, sub, "mono", 10.5, MUTED, anchor="end", ls=1)
    s.save(out(f"h-{slug}.svg"), f"{num} {title}: {sub.lower()}")


# ── 4. THE STACK, UNDER TEST ─────────────────────────────────────────────
LAYERS = [
    ("CLIENT", "what users touch", "React · Next.js · Tailwind · HTML/CSS",
     "XSS, content security policy, secure cookies", "A03 Injection · A05 Misconfiguration"),
    ("EDGE", "how it is served", "Vercel · Render · GitHub Pages · TLS",
     "TLS setup, security headers, CORS rules", "A02 Crypto failures · A05 Misconfiguration"),
    ("API", "where logic lives", "Spring Boot · Express · NestJS · FastAPI",
     "Injection, input validation, rate limits", "A03 Injection · A04 Insecure design"),
    ("AUTH", "who can do what", "Spring Security · BCrypt · sessions · JWT",
     "Broken auth, IDOR, access control", "A01 Access control · A07 Auth failures"),
    ("DATA", "what must not leak", "PostgreSQL · MongoDB · Redis · Prisma",
     "Parameterized queries, least privilege, secrets", "A02 Crypto failures · A03 Injection"),
]


def build_stack():
    n = len(LAYERS)
    top, step = 168, 86
    s = Svg(1000, top + n * step + 70)
    card(s, 16, SAFE)
    section_title(s, "THE STACK, UNDER TEST", "Every layer I build is a layer I test.", BUILD, 28, 42)
    s.text(372, 138, "BUILT WITH", "monob", 10.5, BUILD2, anchor="end", ls=1.6)
    s.text(628, 138, "TESTED FOR", "monob", 10.5, SAFE, ls=1.6)
    P = 7.0
    first_y, last_y = top + 28, top + (n - 1) * step + 28
    s.path(f"M500,{top - 10} V{last_y + 46}", BORDER, 2)
    for i, (name, sub, build, tests, owasp) in enumerate(LAYERS):
        y = top + i * step
        cy = y + 28
        # timing: the packet reaches this layer at t_i
        t_i = .6 + i * 1.0
        s.rect(410, y, 180, 56, 12, PANEL2, BORDER, 1.2)
        k = s.uid("pl")
        pct = lambda t: f"{100 * t / P:.2f}%"
        s.style(f".{k}{{animation:{k} {P}s infinite}}@keyframes {k}{{0%,{pct(t_i - .05)}{{stroke-opacity:0}}"
                f"{pct(t_i + .1)}{{stroke-opacity:1}}{pct(P - .4)}{{stroke-opacity:1}}100%{{stroke-opacity:0}}}}")
        s.add(f'<rect class="{k}" x="410" y="{y}" width="180" height="56" rx="12" fill="none" stroke="{SAFE}" '
              f'stroke-width="1.6" stroke-opacity="0"/>')
        s.text(500, cy - 2, name, "head", 17, TEXT, anchor="middle", ls=1)
        s.text(500, cy + 16, sub, "mono", 9.5, MUTED, anchor="middle")
        # left: build
        s.path(f"M380,{cy} H404", BUILD, 1.4, op=.7)
        s.circle(380, cy, 3.2, BUILD)
        s.text(368, cy - 4, build, "bodym", 13.5, TEXT, anchor="end")
        s.text(368, cy + 14, "build", "mono", 9.5, BUILD2, anchor="end", ls=1)
        # right: tests, with a lamp that lights when the packet passes
        s.path(f"M596,{cy} H620", SAFE, 1.4, op=.7)
        lk = s.uid("lp")
        s.style(f".{lk}{{animation:{lk} {P}s infinite}}@keyframes {lk}{{0%,{pct(t_i - .05)}{{fill:{DIM}}}"
                f"{pct(t_i + .1)}{{fill:{SAFE}}}{pct(P - .4)}{{fill:{SAFE}}}100%{{fill:{DIM}}}}}")
        s.circle(628, cy, 5.5, DIM, cls=lk)
        s.reduced += f".{lk}{{fill:{SAFE}!important}}"
        s.text(644, cy - 4, tests, "bodym", 13.5, TEXT)
        s.text(644, cy + 14, owasp, "mono", 9.5, MUTED)
    # the request packet
    s.style(f".pkt{{animation:pkt {P}s cubic-bezier(.5,0,.5,1) infinite}}"
            f"@keyframes pkt{{0%{{transform:translateY(0);opacity:0}}5%{{opacity:1}}"
            + "".join(f"{100 * (.6 + i * 1.0) / P:.2f}%{{transform:translateY({i * step + 42:.0f}px)}}"
                      for i in range(n))
            + f"{100 * 5.4 / P:.2f}%{{transform:translateY({(n - 1) * step + 84:.0f}px);opacity:1}}"
            f"{100 * 5.8 / P:.2f}%,100%{{transform:translateY({(n - 1) * step + 84:.0f}px);opacity:0}}}}")
    s.add(f'<g class="pkt"><rect x="486" y="{top - 22}" width="28" height="16" rx="4" fill="{CYAN}"/>'
          f'<text x="500" y="{top - 10.5}" font-family="{K.FAMILY["monob"]}" font-size="8.5" fill="{K.BG}" '
          f'text-anchor="middle">GET</text></g>')
    s.chars["monob"] += "GET"
    s.text(500, top - 30, "INCOMING REQUEST", "mono", 9.5, CYAN, anchor="middle", ls=1.4)
    by = last_y + 64
    s.circle(456, by - 4, 9, "none", SAFE, 1.6)
    check(s, 451.5, by - 3.5, SAFE, 9, 2)
    s.text(474, by, "200 OK  ·  passed 5 of 5 checkpoints", "monob", 11.5, SAFE, ls=.6)
    s.save(out("stack.svg"),
           "The stack, under test. Client: built with React, Next.js, Tailwind; tested for XSS, content security "
           "policy, secure cookies. Edge: Vercel, Render, TLS; tested for TLS setup, security headers, CORS. API: "
           "Spring Boot, Express, NestJS, FastAPI; tested for injection, input validation, rate limits. Auth: Spring "
           "Security, BCrypt, sessions, JWT; tested for broken authentication, IDOR, access control. Data: PostgreSQL, "
           "MongoDB, Redis, Prisma; tested for parameterized queries, least privilege, secrets.")


# ── 5. PROJECT PIPELINES ─────────────────────────────────────────────────
PROJECTS = [
    ("netscope", "Network-packet-analyzer", "NetScope",
     "Real-time traffic analysis with a SOC-style dashboard, protocol breakdowns and per-host risk scores.",
     "Python · Scapy · WebSockets", ["anomaly detection", "threat scoring", "demo mode, no root"], True),
    ("fsociety", "fsociety-web", "fsociety-web",
     "A cinematic security portfolio with an interactive roadmap, in-browser utilities and CTF progress.",
     "HTML · CSS · JavaScript", ["static, no backend", "client-side tools", "no tracking"], True),
    ("industrust", "Banking-Management-System-Java", "IndusTrust Bank",
     "Spring Boot web bank with a double-entry ledger, atomic transfers and BigDecimal money.",
     "Spring Boot · PostgreSQL · Docker", ["BCrypt passwords + PINs", "row-level locks", "per-user isolation"], True),
    ("sms", "Student-Management-System-Java-Springboot", "Student Management",
     "A legacy Swing + Oracle desktop app rebuilt as a cloud REST service with analytics and CSV export.",
     "Spring Boot · Neon · Actions", ["no secrets in source", "needless PII removed", "CI on every push"], True),
    ("snapurl", "SnapURL-Project", "SnapURL",
     "Serverless URL shortener with custom aliases and self-expiring links on Turso edge SQLite.",
     "TypeScript · Express · Turso", ["input validation", "links self-expire", "stateless functions"], True),
    ("cineroulette", "cineroulette", "CineRoulette",
     "Pick a mood, spin, get one explained movie pick, weighted per language and region.",
     "Next.js · NestJS · Prisma · Redis", ["server-side scoring", "cached lookups", "reduced-motion aware"], True),
    ("gitatlas", "GitAtlas-Project", "GitAtlas",
     "381 Git commands in plain English, 17 recovery playbooks and a guided recovery wizard.",
     "HTML · CSS · JavaScript", ["risky commands flagged", "read-only checks first", "cookie-free analytics"], True),
    ("grabmedia", "GrabMedia-Project", "GrabMedia",
     "Saves public Instagram and YouTube media up to 2160p through a backend proxy.",
     "Node.js · Express · Helmet", ["Helmet headers", "rate limiting", "API key kept server-side"], True),
    ("disease", "Disease-Prediction-Updated", "Disease Prediction",
     "Predicts 41 diseases from 132 symptoms with a tree ensemble and explains every result with SHAP.",
     "FastAPI · scikit-learn · SHAP", ["CORS locked to frontend", "health checks", "PDF reports"], True),
    ("siteshield", "SiteShield-Web", "SiteShield",
     "Grades a website's TLS, headers, cookies and DNS hygiene A to F and alerts when a grade drops.",
     "React · FastAPI · Celery", ["passive checks only", "JWT + bcrypt", "per-user isolation"], False),
]
STAGES = ["BUILD", "HARDEN", "DEPLOY", "LIVE"]


def build_project(slug, repo, name, desc, stack, hardened, live):
    s = Svg(490, 300)
    card(s, 14, SAFE if live else WARN)
    s.text(24, 34, K.fit(f"arman080325/{repo}", "mono", 10.5, 330), "mono", 10.5, MUTED)
    label, col = ("LIVE", SAFE) if live else ("BUILDING", WARN)
    lw = tw("monob", label, 10, 1.2) + 30
    s.rect(466 - lw, 18, lw, 24, 12, PANEL2, col, 1.2)
    s.circle(466 - lw + 13, 30, 3.8, col, cls="pulse")
    s.text(466 - lw + 23, 34, label, "monob", 10, col, ls=1.2)
    s.text(24, 74, name, "head", 23, TEXT, ls=-.4)
    for i, line in enumerate(wrap(desc, "body", 13, 442)[:2]):
        s.text(24, 98 + i * 18, line, "body", 13, SOFT)
    # pipeline
    py = 160
    xs = [40 + i * 136 for i in range(4)]
    done = 4 if live else 2
    s.path(f"M{xs[0]},{py} H{xs[-1]}", BORDER, 3)
    s.add('<g class="grow" style="--d:.2s">')
    s.path(f"M{xs[0]},{py} H{xs[done - 1]}", SAFE, 3)
    s.add("</g>")
    for i, (x, st) in enumerate(zip(xs, STAGES)):
        ok = i < done
        d = .3 + i * .3
        if ok:
            s.add(f'<g class="fi" style="--d:{d:.2f}s">')
            s.circle(x, py, 11, PANEL, SAFE, 2)
            check(s, x - 4.5, py + .5, SAFE, 9, 2)
            s.add("</g>")
        elif i == done:
            s.circle(x, py, 11, PANEL, WARN, 2, cls="pulse")
            s.circle(x, py, 3.5, WARN)
        else:
            s.circle(x, py, 11, PANEL, DIM, 2)
        s.text(x, py + 30, st, "monob", 9.5, (SAFE if ok else (WARN if i == done else MUTED)), anchor="middle", ls=1.2)
    # hardened with
    s.text(24, 222, "HARDENED WITH", "mono", 9, MUTED, ls=1.4)
    x = 24
    for h in hardened:
        w = tw("bodym", h, 12) + 24
        if x + w > 470:
            break
        check(s, x, 241, SAFE, 8, 1.8)
        s.text(x + 13, 245, h, "bodym", 12, TEXT)
        x += w + 10
    s.path("M24,262 H466", BORDER, 1)
    s.text(24, 284, stack, "mono", 11, SOFT)
    cta = "Open" if live else "Source"
    s.text(450, 284, cta, "bodym", 13, BUILD2, anchor="end")
    s.style(".go{animation:go 1.8s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add('<g class="go">')
    arrow_ne(s, 455, 275, BUILD2, 8)
    s.add("</g>")
    s.save(out(f"project-{slug}.svg"),
           f"{name}: {desc} Pipeline: " + ", ".join(STAGES[:done]) + (" complete." if live else ", in progress.")
           + f" Hardened with {', '.join(hardened)}. Stack: {stack}.")


# ── 6. TOOLKIT ───────────────────────────────────────────────────────────
BUILD_KIT = ["Java", "Spring Boot", "Python", "FastAPI", "TypeScript", "JavaScript", "Node.js", "Express", "NestJS",
             "Next.js", "React", "Tailwind", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Prisma", "Docker",
             "GitHub Actions", "Vercel"]
BREAK_KIT = ["Kali Linux", "Burp Suite", "Nmap", "Wireshark", "Metasploit", "Hashcat", "Volatility3", "Ghidra",
             "OWASP Top 10", "PortSwigger Academy", "TryHackMe", "HackTheBox"]


def chips_layout(items, x0, max_w, size=12):
    rows, row, x = [], [], x0
    for it in items:
        w = tw("bodym", it, size) + 24
        if x + w > x0 + max_w and row:
            rows.append(row)
            row, x = [], x0
        row.append((x, it, w))
        x += w + 8
    if row:
        rows.append(row)
    return rows


def build_toolkit():
    lb = chips_layout(BUILD_KIT, 28, 424)
    rb = chips_layout(BREAK_KIT, 548, 424)
    h = 108 + max(len(lb), len(rb)) * 36 + 24
    s = Svg(1000, h)
    card(s, 16, BUILD)
    s.text(28, 44, "BUILD KIT", "monob", 12, BUILD2, ls=2)
    s.text(28, 70, "What I make things with", "head", 19, TEXT)
    s.text(548, 44, "BREAK KIT", "monob", 12, SAFE, ls=2)
    s.text(548, 70, "What I test things with", "head", 19, TEXT)
    s.path(f"M500,30 V{h - 30}", BORDER, 1, dash="2 6")
    s.circle(500, h / 2, 17, PANEL2, BORDER, 1.2)
    s.path(f"M494,{h / 2} H506 M500,{h / 2 - 6} V{h / 2 + 6}", SOFT, 2)
    for rows, col, base in ((lb, BUILD2, .1), (rb, SAFE, .3)):
        for r, row in enumerate(rows):
            for j, (x, it, w) in enumerate(row):
                y = 92 + r * 36
                s.add(f'<g class="fi" style="--d:{base + (r * 5 + j) * .04:.2f}s">')
                s.rect(x, y, w, 28, 14, PANEL2, BORDER, 1)
                s.circle(x + 12, y + 14, 3.5, col)
                s.text(x + 20, y + 18.5, it, "bodym", 12, TEXT)
                s.add("</g>")
    s.save(out("toolkit.svg"), "Build kit: " + ", ".join(BUILD_KIT) + ". Break kit: " + ", ".join(BREAK_KIT) + ".")


# ── 7. FOOTER ────────────────────────────────────────────────────────────
def build_footer():
    s = Svg(1000, 236)
    card(s, 16, SAFE)
    tx, ty, twd, th = 22, 22, 560, 192
    s.rect(tx, ty, twd, th, 12, K.BG, BORDER, 1.2)
    window_bar(s, tx, ty, twd, "zsh  ·  ~/arman", 32, 12)
    lines = [
        (0.3, [("$ ", SAFE), ("git commit -m ", TEXT), ('"build it, break it, fix it, ship it"', STR)]),
        (1.1, [("[main 7c0ffee] build it, break it, fix it, ship it", MUTED)]),
        (1.9, [("$ ", SAFE), ("git push origin main", TEXT)]),
        (2.7, [("  checks: build, harden, deploy ", MUTED), ("passed", SAFE)]),
    ]
    for i, (d, segs) in enumerate(lines):
        s.spans(tx + 20, ty + 64 + i * 24, segs, 12.5, cls="fi")
        s.parts[-1] = s.parts[-1].replace('class="fi"', f'class="fi" style="--d:{d}s"', 1)
    y = ty + 64 + 4 * 24
    s.add('<g class="fi" style="--d:3.4s">')
    s.circle(tx + 27, y - 4, 7.5, "none", SAFE, 1.6)
    check(s, tx + 23, y - 3.5, SAFE, 8, 1.8)
    s.text(tx + 42, y, "deployed to arman-portfolio.online", "monob", 12.5, SAFE)
    s.add("</g>")
    s.rect(tx + 42 + tw("monob", "deployed to arman-portfolio.online", 12.5) + 6, y - 11, 7, 14, 1, SAFE, cls="blink")
    x = 612
    s.text(x, 64, "LET'S TALK", "monob", 11, BUILD2, ls=2.4)
    s.text(x, 100, "Have something to build,", "head", 22, TEXT, ls=-.4)
    s.text(x, 128, "or something to secure?", "head", 22, TEXT, ls=-.4)
    s.text(x, 166, "arman-portfolio.online", "monob", 15, SAFE)
    s.path(f"M{x},172 H{x + tw('monob', 'arman-portfolio.online', 15):.0f}", SAFE, 1.3, cls="dr", delay=.5)
    s.text(x, 198, "Authorized testing only  ·  responsible disclosure", "mono", 10.5, MUTED)
    s.save(out("footer.svg"), "git commit: build it, break it, fix it, ship it. Deployed to arman-portfolio.online. "
                              "Have something to build, or something to secure? Authorized testing only, responsible "
                              "disclosure.")


HEADERS = [
    ("stack", "01", "Stack under test", "WHAT I BUILD AT EACH LAYER, AND WHAT I TEST IT FOR"),
    ("projects", "02", "Projects", "10 PIPELINES  ·  9 LIVE  ·  CLICK A CARD TO OPEN THE APP"),
    ("toolkit", "03", "Toolkit", "ONE KIT FOR MAKING, ONE FOR BREAKING"),
    ("activity", "04", "Activity", "LIVE FROM THE GITHUB API  ·  REFRESHED EVERY 12 HOURS"),
]


def main():
    build_hero()
    build_nav()
    for h in HEADERS:
        build_header(*h)
    build_stack()
    for p in PROJECTS:
        build_project(*p)
    build_toolkit()
    build_footer()


if __name__ == "__main__":
    main()
