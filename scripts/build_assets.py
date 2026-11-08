#!/usr/bin/env python3
"""Generate the animated SVG components used by the profile README.

Each component is written twice, as <name>-dark.svg and <name>-light.svg,
so the README can switch with the viewer's GitHub theme via <picture>.
Every SVG is self-contained: fonts are subset to the characters actually
used and embedded as base64 WOFF2 (GitHub blocks external resources inside
<img> SVGs). Animations are slow and subtle and are switched off for
viewers who prefer reduced motion.

Usage:
    pip install fonttools brotli
    npm pack @fontsource/space-grotesk @fontsource/jetbrains-mono @fontsource/inter
    (extract the tarballs into one folder)
    python3 scripts/build_assets.py --fonts <that folder>
"""
import argparse
import base64
import io
import os
import random
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "ui")

FONT_FILES = {
    "head": "space-grotesk-latin-700-normal.woff",
    "semi": "space-grotesk-latin-600-normal.woff",
    "mono": "jetbrains-mono-latin-400-normal.woff",
    "monom": "jetbrains-mono-latin-500-normal.woff",
    "body": "inter-latin-400-normal.woff",
    "bodym": "inter-latin-500-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}
_paths, _metrics = {}, {}

THEMES = {
    "dark": dict(page="#0d1117", panel="#161b22", border="#30363d", text="#e6edf3",
                 muted="#8b949e", soft="#c9d1d9", accent="#3fb950", accent2="#58a6ff",
                 grid="#21262d"),
    "light": dict(page="#ffffff", panel="#f6f8fa", border="#d0d7de", text="#1f2328",
                  muted="#59636e", soft="#31373d", accent="#1a7f37", accent2="#0969da",
                  grid="#e6eaef"),
}
# per-project accent hues (dark, light) — GitHub-style language colours
HUES = {
    "green": ("#3fb950", "#1a7f37"), "blue": ("#58a6ff", "#0969da"),
    "purple": ("#bc8cff", "#8250df"), "orange": ("#f0883e", "#bc4c00"),
    "pink": ("#f778ba", "#bf3989"), "teal": ("#39c5cf", "#1b7c83"),
}


# ── font helpers ─────────────────────────────────────────────────────────
def load_fonts(font_dir):
    for key, name in FONT_FILES.items():
        for root, _, files in os.walk(font_dir):
            if name in files:
                _paths[key] = os.path.join(root, name)
        if key not in _paths:
            raise SystemExit(f"missing font {name} under {font_dir}")
        f = TTFont(_paths[key])
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)


def tw(key, text, size, spacing=0):
    cmap, hmtx, upm = _metrics[key]
    total = sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text)
    return total * size / upm + spacing * len(text)


def font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    font = TTFont(_paths[key])
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(chars + " "))))
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{FAMILY[key]};src:url(data:font/woff2;base64,{data})}}"


def wrap(text, key, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if tw(key, trial, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + ([cur] if cur else [])


class Svg:
    def __init__(self, w, h, theme):
        self.w, self.h, self.t = w, h, THEMES[theme]
        self.theme = theme
        self.parts, self.css = [], []
        self.chars = {k: "" for k in FONT_FILES}

    def text(self, x, y, s, font, size, fill, extra="", cls=""):
        self.chars[font] += s
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}"{c} {extra}>{escape(s)}</text>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def save(self, name, title):
        faces = "".join(font_face(k, v) for k, v in self.chars.items() if v)
        css = (faces + "".join(self.css) +
               "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}">'
               f'<title>{escape(title)}</title><style>{css}</style>{"".join(self.parts)}</svg>')
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, f"{name}-{self.theme}.svg"), "w", encoding="utf-8") as f:
            f.write(svg)


FADE = ("@keyframes up{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}"
        ".up{animation:up .9s cubic-bezier(.2,.7,.2,1) both}")
PULSE = ".pulse{animation:pu 2.4s ease-in-out infinite}@keyframes pu{50%{opacity:.3}}"


def arrow(x, y, color, w=1.6):
    """Small north-east arrow drawn as a path (no glyph needed)."""
    return (f'<path d="M{x},{y + 9} L{x + 9},{y} M{x + 2},{y} H{x + 9} V{y + 7}" fill="none" '
            f'stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


# ── HERO ─────────────────────────────────────────────────────────────────
def build_hero(theme):
    s = Svg(1000, 330, theme)
    t = s.t
    s.style(FADE + PULSE +
            ".d1{animation-delay:.1s}.d2{animation-delay:.35s}.d3{animation-delay:.6s}"
            ".d4{animation-delay:.85s}.d5{animation-delay:1.1s}"
            ".cur{animation:bl 1.1s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
            ".drift{animation:dr 14s ease-in-out infinite alternate}"
            "@keyframes dr{from{transform:translate(0,0)}to{transform:translate(-160px,40px)}}"
            ".node{animation:nd 4s ease-in-out infinite}@keyframes nd{50%{opacity:.25}}"
            ".pkt{offset-rotate:0deg;animation:pk 7s linear infinite}"
            "@keyframes pk{from{offset-distance:0%}to{offset-distance:100%}}")
    s.add(f'<defs><radialGradient id="glow"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".16"/>'
          f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></radialGradient>'
          f'<radialGradient id="glow2"><stop offset="0" stop-color="{t["accent2"]}" stop-opacity=".12"/>'
          f'<stop offset="1" stop-color="{t["accent2"]}" stop-opacity="0"/></radialGradient>'
          f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
          f'<circle cx="2" cy="2" r="1.1" fill="{t["border"]}"/></pattern>'
          f'<linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="{t["panel"]}"/>'
          f'<stop offset=".55" stop-color="{t["panel"]}" stop-opacity="0"/></linearGradient>'
          f'<clipPath id="card"><rect x="1" y="1" width="998" height="328" rx="16"/></clipPath></defs>')
    s.add(f'<g clip-path="url(#card)"><rect width="1000" height="330" fill="{t["panel"]}"/>'
          f'<rect width="1000" height="330" fill="url(#dots)" opacity=".7"/>'
          f'<g class="drift"><circle cx="840" cy="70" r="260" fill="url(#glow)"/></g>'
          f'<circle cx="120" cy="330" r="220" fill="url(#glow2)"/>'
          f'<rect width="1000" height="330" fill="url(#fadeL)"/>')
    # network constellation on the right
    rnd = random.Random(7)
    nodes = [(rnd.randint(640, 960), rnd.randint(40, 290)) for _ in range(16)]
    edges = []
    for i, a in enumerate(nodes):
        near = sorted(nodes, key=lambda b: (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)[1:3]
        for b in near:
            if (b, a) not in edges:
                edges.append((a, b))
    s.add(f'<g stroke="{t["muted"]}" stroke-opacity=".35" stroke-width="1">' +
          "".join(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>' for a, b in edges) + "</g>")
    for i, (x, y) in enumerate(nodes):
        col = t["accent"] if i % 4 == 0 else t["muted"]
        r = 3.6 if i % 4 == 0 else 2.4
        s.add(f'<circle class="node" style="animation-delay:-{i * 0.6:.1f}s" cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
    route = [nodes[0]] + sorted(nodes[1:6], key=lambda p: p[0])
    d = "M" + " L".join(f"{x},{y}" for x, y in route)
    s.add(f'<circle class="pkt" r="3.2" fill="{t["accent2"]}" style="offset-path:path(\'{d}\')"/>')
    s.add("</g>")
    s.add(f'<rect x="1" y="1" width="998" height="328" rx="16" fill="none" stroke="{t["border"]}"/>')
    # left column text
    x = 56
    s.add('<g class="up d1">')
    s.text(x, 78, "arman@kali", "monom", 15, t["accent"])
    w1 = tw("monom", "arman@kali", 15)
    s.text(x + w1, 78, ":~$ whoami", "mono", 15, t["muted"])
    cx = x + w1 + tw("mono", ":~$ whoami", 15) + 6
    s.add(f'<rect class="cur" x="{cx:.0f}" y="65" width="8" height="16" fill="{t["accent"]}"/>')
    s.add("</g>")
    s.add('<g class="up d2">')
    s.text(x - 3, 140, "Arman Ahemad Khan", "head", 54, t["text"], 'letter-spacing="-1"')
    s.add("</g>")
    s.add('<g class="up d3">')
    s.text(x, 182, "Full-Stack Developer", "semi", 23, t["soft"])
    w2 = tw("semi", "Full-Stack Developer", 23)
    s.text(x + w2 + 10, 182, "&", "semi", 23, t["accent"])
    s.text(x + w2 + 34, 182, "Ethical Hacker", "semi", 23, t["soft"])
    s.add("</g>")
    s.add('<g class="up d4">')
    s.text(x, 222, "I build fast, secure web apps, then test them the way", "body", 16, t["muted"])
    s.text(x, 246, "an attacker would, and ship the fixes.", "body", 16, t["muted"])
    s.add("</g>")
    # pills
    s.add('<g class="up d5">')
    px = x
    for i, label in enumerate(["Cybersecurity Intern", "B.Tech CSE '27", "India"]):
        w = tw("mono", label, 12.5) + (40 if i == 0 else 26)
        s.add(f'<rect x="{px}" y="268" width="{w:.0f}" height="30" rx="15" fill="{t["page"]}" '
              f'stroke="{t["border"]}"/>')
        tx = px + 13
        if i == 0:
            s.add(f'<circle class="pulse" cx="{px + 17}" cy="283" r="4" fill="{t["accent"]}"/>')
            tx = px + 29
        s.text(tx, 287, label, "mono", 12.5, t["soft"])
        px += w + 10
    s.add("</g>")
    s.save("hero", "Arman Ahemad Khan — Full-Stack Developer and Ethical Hacker")


# ── SECTION HEADER ───────────────────────────────────────────────────────
def build_header(theme, name, num, title):
    s = Svg(1000, 58, theme)
    t = s.t
    s.style(".draw{stroke-dasharray:1000;animation:dw 1.6s cubic-bezier(.2,.7,.2,1) both .2s}"
            "@keyframes dw{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}"
            ".dot{animation:mv 9s ease-in-out infinite alternate}"
            "@keyframes mv{from{transform:translateX(0)}to{transform:translateX(var(--d))}}")
    s.text(2, 36, num, "monom", 14, t["accent"])
    nx = 2 + tw("monom", num, 14) + 12
    s.text(nx, 38, title, "head", 26, t["text"], 'letter-spacing="-.4"')
    lx = nx + tw("head", title, 26, -0.4) + 20
    s.add(f'<line class="draw" x1="{lx:.0f}" y1="29" x2="996" y2="29" stroke="{t["border"]}" stroke-width="1.5"/>')
    s.add(f'<circle class="dot" style="--d:{996 - lx:.0f}px" cx="{lx:.0f}" cy="29" r="3" fill="{t["accent"]}"/>')
    s.save(name, title)


# ── PROJECT CARD ─────────────────────────────────────────────────────────
PROJECTS = [
    ("netscope", "NetScope", "Security · Network analysis", "teal",
     "Real-time traffic analysis with a SOC-style browser dashboard, protocol breakdowns, anomaly alerts and per-host risk scores.",
     "Python · Scapy · WebSockets"),
    ("fsociety", "fsociety-web", "Security · Portfolio", "pink",
     "A cinematic security portfolio with an interactive learning roadmap, in-browser utilities, field notes and CTF progress.",
     "HTML · CSS · JavaScript"),
    ("industrust", "IndusTrust Bank", "Full-stack · Fintech", "green",
     "Spring Boot web bank with a double-entry ledger, row-locked atomic transfers, BigDecimal money and hashed PINs.",
     "Spring Boot · PostgreSQL · Docker"),
    ("sms", "Student Management", "Full-stack · Education", "orange",
     "A legacy Swing + Oracle desktop app rebuilt as a cloud REST service with analytics, CSV export and CI on every push.",
     "Spring Boot · Neon · GitHub Actions"),
    ("snapurl", "SnapURL", "Serverless · Utility", "blue",
     "Base62 short links, custom aliases and self-expiring links, running on Vercel functions with Turso edge SQLite.",
     "TypeScript · Express · Turso"),
    ("cineroulette", "CineRoulette", "Full-stack · Discovery", "purple",
     "Pick a mood, spin, get one explained movie pick. Weighted scoring normalized per language and region.",
     "Next.js · NestJS · Prisma · Redis"),
    ("gitatlas", "GitAtlas", "Developer tool", "orange",
     "381 Git commands explained in plain English, 17 recovery playbooks, a guided wizard and warnings on risky commands.",
     "HTML · CSS · JavaScript"),
    ("grabmedia", "GrabMedia", "Full-stack · Media", "blue",
     "Save public Instagram and YouTube media up to 2160p or audio-only, behind a hardened, rate-limited Express proxy.",
     "Node.js · Express · Helmet"),
    ("disease", "Disease Prediction", "Machine learning", "green",
     "Predicts 41 diseases from 132 symptoms with a tree ensemble, SHAP explanations and downloadable PDF reports.",
     "FastAPI · scikit-learn · SHAP"),
    ("siteshield", "SiteShield", "Security · SaaS", "purple",
     "Grades a website's TLS, headers, cookies and DNS hygiene from A to F, re-scans on a schedule and alerts on regressions.",
     "React · FastAPI · Celery"),
]
BUILDING = {"siteshield"}


def build_card(theme, slug, title, category, hue, desc, stack):
    s = Svg(480, 214, theme)
    t = s.t
    col = HUES[hue][0 if theme == "dark" else 1]
    live = slug not in BUILDING
    s.style(PULSE +
            ".sheen{animation:sn 6s ease-in-out infinite}"
            "@keyframes sn{0%{transform:translateX(-160px)}60%,100%{transform:translateX(520px)}}"
            ".go{animation:go 2.4s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}")
    s.add(f'<defs><clipPath id="c"><rect x="1" y="1" width="478" height="212" rx="12"/></clipPath>'
          f'<linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
          f'<stop offset=".5" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
          f'</linearGradient><mask id="m"><rect class="sheen" x="0" y="0" width="140" height="4" fill="url(#sh)"/></mask></defs>')
    s.add(f'<g clip-path="url(#c)"><rect width="480" height="214" fill="{t["panel"]}"/>'
          f'<rect width="480" height="3" fill="{col}" opacity=".55"/>'
          f'<rect width="480" height="3" fill="{col}" mask="url(#m)"/></g>')
    s.add(f'<rect x="1" y="1" width="478" height="212" rx="12" fill="none" stroke="{t["border"]}"/>')
    # header row
    s.add(f'<rect x="24" y="26" width="10" height="10" rx="2.5" fill="{col}"/>')
    s.text(42, 36, category.upper(), "monom", 11, t["muted"], 'letter-spacing=".8"')
    status = "Live" if live else "In progress"
    stc = t["accent"] if live else HUES["orange"][0 if theme == "dark" else 1]
    sw = tw("monom", status, 12)
    s.add(f'<circle class="pulse" cx="{448 - sw - 10:.0f}" cy="32" r="4" fill="{stc}"/>')
    s.text(456 - sw, 36, status, "monom", 12, stc)
    s.text(24, 74, title, "head", 24, t["text"], 'letter-spacing="-.3"')
    y = 104
    for line in wrap(desc, "body", 14, 432)[:3]:
        s.text(24, y, line, "body", 14, t["muted"])
        y += 21
    s.add(f'<line x1="24" y1="170" x2="456" y2="170" stroke="{t["border"]}"/>')
    s.text(24, 194, stack, "mono", 12, t["soft"])
    cta = "Visit" if live else "Source"
    cw = tw("bodym", cta, 13)
    s.text(442 - cw, 194, cta, "bodym", 13, col)
    s.add(f'<g class="go">{arrow(446, 184, col)}</g>')
    s.save(f"card-{slug}", f"{title} — {category}")


# ── FOOTER ───────────────────────────────────────────────────────────────
def build_footer(theme):
    s = Svg(1000, 120, theme)
    t = s.t
    s.style(FADE + ".cur{animation:bl 1.1s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
            ".run{animation:rn 7s ease-in-out infinite alternate}"
            "@keyframes rn{from{transform:translateX(-300px)}to{transform:translateX(300px)}}")
    s.add(f'<defs><linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/>'
          f'<stop offset=".5" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/>'
          f'</linearGradient></defs>')
    s.add(f'<line x1="200" y1="20" x2="800" y2="20" stroke="{t["border"]}"/>')
    s.add(f'<g class="run"><rect x="440" y="19" width="120" height="2" fill="url(#ln)"/></g>')
    q = "Build it. Break it. Harden it. Ship it."
    s.add('<g class="up">')
    s.text((1000 - tw("semi", q, 22)) / 2, 66, q, "semi", 22, t["text"])
    p = "arman@kali:~$ logout"
    px = (1000 - tw("mono", p, 14) - 12) / 2
    s.text(px, 98, "arman@kali", "mono", 14, t["accent"])
    s.text(px + tw("mono", "arman@kali", 14), 98, ":~$ logout", "mono", 14, t["muted"])
    s.add(f'<rect class="cur" x="{px + tw("mono", p, 14) + 6:.0f}" y="87" width="7" height="14" fill="{t["accent"]}"/>')
    s.add("</g>")
    s.save("footer", "Build it. Break it. Harden it. Ship it.")


HEADERS = [
    ("h-about", "01", "About"),
    ("h-projects", "02", "Live projects"),
    ("h-stack", "03", "Tech stack"),
    ("h-activity", "04", "Activity"),
    ("h-connect", "05", "Connect"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    load_fonts(ap.parse_args().fonts)
    for theme in THEMES:
        build_hero(theme)
        for h in HEADERS:
            build_header(theme, *h)
        for p in PROJECTS:
            build_card(theme, *p)
        build_footer(theme)


if __name__ == "__main__":
    main()
