#!/usr/bin/env python3
"""Generate the animated neon SVG components used by the profile README.

Every SVG is self-contained: fonts are subset to the characters actually used
and embedded as base64 WOFF2, so the art renders identically on GitHub for
everyone (GitHub blocks external resources inside <img> SVGs).

Usage:
    pip install fonttools brotli
    python3 scripts/build_assets.py --fonts <dir with the .woff files>

Fonts (OFL, from @fontsource on npm): Orbitron 900, Share Tech Mono 400,
Press Start 2P 400, Rajdhani 700.
"""
import argparse
import base64
import io
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "neon")

# ── palette ──────────────────────────────────────────────────────────────
BG = "#07020f"
PANEL = "#0d0620"
MAGENTA = "#ff2a6d"
CYAN = "#05d9e8"
LIME = "#b8ff3c"
YELLOW = "#f9f002"
VIOLET = "#9d4dff"
WHITE = "#f4f1ff"
DIM = "#8a7fb0"

FONT_FILES = {
    "orb": "orbitron-latin-900-normal.woff",
    "mono": "share-tech-mono-latin-400-normal.woff",
    "pix": "press-start-2p-latin-400-normal.woff",
    "raj": "rajdhani-latin-700-normal.woff",
}
FONT_FAMILY = {"orb": "Orb", "mono": "Mono", "pix": "Pix", "raj": "Raj"}
_fonts = {}


def load_fonts(font_dir):
    for key, name in FONT_FILES.items():
        path = None
        for root, _, files in os.walk(font_dir):
            if name in files:
                path = os.path.join(root, name)
        if not path:
            raise SystemExit(f"missing font {name} under {font_dir}")
        _fonts[key] = path


def text_width(key, text, size):
    font = TTFont(_fonts[key])
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    upm = font["head"].unitsPerEm
    total = 0
    for ch in text:
        glyph = cmap.get(ord(ch)) or cmap.get(ord("?"))
        total += hmtx[glyph][0]
    return total * size / upm


def font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    font = TTFont(_fonts[key])
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(chars + " "))))
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return (f"@font-face{{font-family:{FONT_FAMILY[key]};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")


class Svg:
    """Tiny builder that tracks which glyphs each font needs."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []
        self.css = []
        self.chars = {k: "" for k in FONT_FILES}

    def text(self, x, y, s, font, size, fill, extra="", cls=""):
        self.chars[font] += s
        c = f' class="{cls}"' if cls else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT_FAMILY[font]}" '
            f'font-size="{size}" fill="{fill}"{c} {extra}>{escape(s)}</text>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def render(self, title):
        faces = "".join(font_face(k, v) for k, v in self.chars.items() if v)
        css = faces + "".join(self.css) + (
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
                f'aria-label="{escape(title)}"><title>{escape(title)}</title>'
                f'<style>{css}</style>{"".join(self.parts)}</svg>')


def save(name, svg, title):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(svg.render(title))


def wrap(text, font, size, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if text_width(font, trial, size) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def scanlines(svg, opacity=0.18):
    svg.add('<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1" fill="#000" opacity="{opacity * 3}"/></pattern></defs>')
    svg.add(f'<rect width="{svg.w}" height="{svg.h}" fill="url(#scan)" opacity="0.6"/>')


def hud_corners(svg, pad, color, size=18, width=3):
    w, h = svg.w, svg.h
    p = pad
    for d in (f"M{p},{p + size} V{p} H{p + size}",
              f"M{w - p - size},{p} H{w - p} V{p + size}",
              f"M{p},{h - p - size} V{h - p} H{p + size}",
              f"M{w - p - size},{h - p} H{w - p} V{h - p - size}"):
        svg.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"/>')


# ── HERO ─────────────────────────────────────────────────────────────────
def build_hero():
    s = Svg(1000, 380)
    s.style(
        f".glitch-a{{animation:ga 3.2s infinite steps(1)}}"
        f".glitch-b{{animation:gb 3.2s infinite steps(1)}}"
        "@keyframes ga{0%,86%,100%{transform:translate(-3px,0)}88%{transform:translate(-14px,2px)}"
        "90%{transform:translate(9px,-3px)}92%{transform:translate(-6px,0)}}"
        "@keyframes gb{0%,86%,100%{transform:translate(3px,0)}88%{transform:translate(12px,-2px)}"
        "90%{transform:translate(-10px,3px)}92%{transform:translate(5px,0)}}"
        ".flick{animation:fl 4s infinite}"
        "@keyframes fl{0%,100%{opacity:1}47%{opacity:1}48%{opacity:.35}49%{opacity:1}72%{opacity:.8}73%{opacity:1}}"
        ".scanbar{animation:sb 5s linear infinite}"
        "@keyframes sb{0%{transform:translateY(-60px)}100%{transform:translateY(440px)}}"
        ".grid{animation:gr 1.6s linear infinite}"
        "@keyframes gr{0%{transform:translateY(0)}100%{transform:translateY(24px)}}"
        ".blink{animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
        ".role{opacity:0;animation:rl 12s infinite}"
        ".r1{animation-delay:0s}.r2{animation-delay:3s}.r3{animation-delay:6s}.r4{animation-delay:9s}"
        "@keyframes rl{0%{opacity:0;transform:translateX(-12px)}3%,22%{opacity:1;transform:translateX(0)}"
        "25%,100%{opacity:0;transform:translateX(12px)}}"
        ".pulse{animation:pu 1.4s ease-in-out infinite}@keyframes pu{50%{opacity:.25}}"
    )
    s.add(f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{BG}"/><stop offset=".62" stop-color="#1a0533"/>'
          f'<stop offset="1" stop-color="#3a0a4a"/></linearGradient>'
          f'<linearGradient id="name" x1="0" y1="0" x2="1" y2="0">'
          f'<stop offset="0" stop-color="{CYAN}"/><stop offset=".5" stop-color="{WHITE}"/>'
          f'<stop offset="1" stop-color="{MAGENTA}"/></linearGradient>'
          f'<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">'
          f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>'
          f'<stop offset=".5" stop-color="{CYAN}" stop-opacity=".22"/>'
          f'<stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>'
          f'<clipPath id="floor"><rect x="0" y="262" width="1000" height="118"/></clipPath>'
          f'<filter id="glow" x="-20%" y="-50%" width="140%" height="200%">'
          f'<feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/>'
          f'<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>')
    s.add('<rect width="1000" height="380" rx="14" fill="url(#sky)"/>')
    # synthwave floor grid
    lines = []
    for i in range(-12, 13):
        lines.append(f'<line x1="{500 + i * 22}" y1="262" x2="{500 + i * 160}" y2="380"/>')
    horiz = "".join(f'<line x1="0" y1="{262 + k * 24}" x2="1000" y2="{262 + k * 24}"/>'
                    for k in range(-1, 6))
    s.add(f'<g clip-path="url(#floor)" stroke="{MAGENTA}" stroke-width="1.2" opacity=".55">'
          f'{"".join(lines)}<g class="grid">{horiz}</g></g>')
    s.add(f'<line x1="0" y1="262" x2="1000" y2="262" stroke="{MAGENTA}" stroke-width="2.5" filter="url(#glow)"/>')
    # top status strip
    s.text(34, 46, "root@armanxploits:~# ./init --persona=dual-boot", "mono", 17, LIME)
    s.add(f'<rect x="465" y="32" width="10" height="17" fill="{LIME}" class="blink"/>')
    s.add(f'<circle cx="842" cy="40" r="6" fill="{MAGENTA}" class="pulse"/>')
    s.text(856, 46, "SYS.ONLINE", "pix", 11, MAGENTA)
    # glitch name
    name = "ARMAN AHEMAD KHAN"
    size = 66
    nx = (1000 - text_width("orb", name, size)) / 2
    s.add('<g class="flick">')
    s.text(round(nx, 1), 148, name, "orb", size, CYAN, 'opacity=".75"', "glitch-a")
    s.text(round(nx, 1), 148, name, "orb", size, MAGENTA, 'opacity=".75"', "glitch-b")
    s.text(round(nx, 1), 148, name, "orb", size, "url(#name)", 'filter="url(#glow)"')
    s.add('</g>')
    # handle
    handle = "// a.k.a  ARMANXPLOITS //"
    hx = (1000 - text_width("pix", handle, 14)) / 2
    s.text(round(hx, 1), 186, handle, "pix", 14, YELLOW)
    # rotating roles
    roles = [("FULL-STACK DEVELOPER", CYAN), ("ETHICAL HACKER", MAGENTA),
             ("CYBERSECURITY INTERN", LIME), ("B.TECH CSE // CLASS OF '27", YELLOW)]
    for i, (r, col) in enumerate(roles, 1):
        label = f"> {r} _"
        rx = (1000 - text_width("raj", label, 30)) / 2
        s.text(round(rx, 1), 236, label, "raj", 30, col, 'letter-spacing="2"', f"role r{i}")
    # bottom tags
    s.text(34, 356, "BUILD", "pix", 12, CYAN)
    s.text(104, 356, "> BREAK", "pix", 12, MAGENTA)
    s.text(212, 356, "> HARDEN", "pix", 12, LIME)
    s.text(332, 356, "> DEPLOY", "pix", 12, YELLOW)
    s.text(800, 356, "LOC: INDIA [IN]", "pix", 12, DIM)
    s.add('<rect class="scanbar" x="0" y="0" width="1000" height="60" fill="url(#bar)"/>')
    scanlines(s)
    hud_corners(s, 12, CYAN)
    save("hero.svg", s, "Arman Ahemad Khan — Full-Stack Developer and Ethical Hacker")


# ── OPERATOR ID CARD ──────────────────────────────────────────────────────
def build_idcard():
    s = Svg(490, 300)
    s.style(".shim{animation:sh 3s linear infinite}"
            "@keyframes sh{0%{transform:translateX(-200px)}100%{transform:translateX(560px)}}"
            ".stamp{animation:st 6s infinite}"
            "@keyframes st{0%,8%{opacity:0;transform:scale(1.6)}12%,100%{opacity:1;transform:scale(1)}}"
            ".pulse{animation:pu 1.4s ease-in-out infinite}@keyframes pu{50%{opacity:.25}}")
    s.add(f'<defs><linearGradient id="sh" x1="0" y1="0" x2="1" y2="0">'
          f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".12"/>'
          f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
          f'<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CYAN}"/>'
          f'<stop offset="1" stop-color="{MAGENTA}"/></linearGradient></defs>')
    s.add(f'<rect x="2" y="2" width="486" height="296" rx="14" fill="{PANEL}" stroke="url(#edge)" stroke-width="2.5"/>')
    s.add(f'<rect x="2" y="2" width="486" height="44" rx="14" fill="{MAGENTA}"/>'
          f'<rect x="2" y="30" width="486" height="16" fill="{MAGENTA}"/>')
    s.text(20, 31, "OPERATOR ID", "orb", 18, BG)
    s.text(330, 30, "#0x7E3A-27", "pix", 10, BG)
    # avatar block — pixel skull-free glyph: a terminal prompt icon
    s.add(f'<rect x="22" y="66" width="110" height="128" rx="8" fill="{BG}" stroke="{CYAN}" stroke-width="2"/>')
    s.text(40, 142, ">_", "pix", 34, CYAN)
    s.add(f'<circle cx="118" cy="80" r="5" fill="{LIME}" class="pulse"/>')
    fields = [("NAME", "Arman Ahemad Khan", WHITE), ("HANDLE", "armanxploits", YELLOW),
              ("ROLE", "Dev // Sec Intern", CYAN), ("BASE", "Silicon IT, BBSR", WHITE),
              ("CLASS", "B.Tech CSE '27", WHITE)]
    y = 70
    for k, v, col in fields:
        s.text(150, y, k, "pix", 8, DIM)
        s.text(150, y + 18, v, "raj", 19, col)
        y += 31
    # barcode
    x = 22
    import random
    rnd = random.Random(27)
    while x < 300:
        w = rnd.choice([2, 2, 3, 4, 6])
        s.add(f'<rect x="{x}" y="232" width="{w}" height="44" fill="{WHITE}" opacity=".85"/>')
        x += w + rnd.choice([2, 3, 4])
    s.text(22, 290, "ACCESS LEVEL :: ROOT", "pix", 8, DIM)
    # stamp
    s.add(f'<g class="stamp" style="transform-origin:400px 252px"><g transform="rotate(-12 400 252)">'
          f'<rect x="326" y="226" width="148" height="52" rx="6" fill="none" stroke="{LIME}" stroke-width="3"/>')
    s.text(338, 260, "GRANTED", "orb", 22, LIME)
    s.add('</g></g>')
    s.add('<rect class="shim" x="0" y="0" width="120" height="300" fill="url(#sh)"/>')
    save("idcard.svg", s, "Operator ID card for Arman Ahemad Khan")


# ── SYSTEM MONITOR ────────────────────────────────────────────────────────
def build_monitor():
    s = Svg(490, 300)
    bars = [("BUILD", CYAN, 92), ("BREAK", MAGENTA, 84), ("HARDEN", LIME, 78),
            ("DEPLOY", YELLOW, 88), ("CAFFEINE", VIOLET, 100)]
    css = ".eq{animation:eq 1.2s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:left}"
    css += "@keyframes eq{0%{transform:scaleX(.55)}100%{transform:scaleX(1)}}"
    css += "".join(f".d{i}{{animation-delay:-{i * 0.37:.2f}s}}" for i in range(len(bars)))
    css += ".pulse{animation:pu 1.4s ease-in-out infinite}@keyframes pu{50%{opacity:.25}}"
    css += ".wave{animation:wv 2.4s linear infinite}@keyframes wv{0%{transform:translateX(0)}100%{transform:translateX(-120px)}}"
    s.style(css)
    s.add(f'<rect x="2" y="2" width="486" height="296" rx="14" fill="{PANEL}" stroke="{CYAN}" stroke-width="2.5"/>')
    s.text(20, 34, "SYS::MONITOR", "orb", 18, CYAN)
    s.add(f'<circle cx="430" cy="27" r="6" fill="{LIME}" class="pulse"/>')
    s.text(442, 32, "LIVE", "pix", 9, LIME)
    s.add(f'<line x1="20" y1="48" x2="470" y2="48" stroke="{CYAN}" stroke-opacity=".3"/>')
    y = 78
    for i, (label, col, pct) in enumerate(bars):
        s.text(20, y + 10, label, "pix", 10, col)
        s.add(f'<rect x="130" y="{y - 2}" width="300" height="14" rx="3" fill="{BG}" stroke="{col}" stroke-opacity=".35"/>')
        s.add(f'<rect class="eq d{i}" x="132" y="{y}" width="{296 * pct / 100:.0f}" height="10" rx="2" fill="{col}"/>')
        s.text(440, y + 10, f"{pct}%", "mono", 13, WHITE)
        y += 32
    # heartbeat line
    pts = []
    for k in range(0, 8):
        bx = 20 + k * 120
        pts.append(f"L{bx},262 L{bx + 40},262 L{bx + 52},240 L{bx + 62},280 L{bx + 72},252 L{bx + 82},262 L{bx + 120},262")
    s.add('<clipPath id="hb"><rect x="20" y="236" width="450" height="50"/></clipPath>')
    s.add(f'<g clip-path="url(#hb)"><path class="wave" d="M20,262 {" ".join(pts)}" fill="none" '
          f'stroke="{MAGENTA}" stroke-width="2.2"/></g>')
    save("monitor.svg", s, "System monitor: build, break, harden, deploy")


# ── SECTION HEADERS ───────────────────────────────────────────────────────
def build_header(fname, code, title, color, accent):
    s = Svg(1000, 76)
    s.style(".run{animation:rn 3.5s linear infinite}"
            "@keyframes rn{0%{transform:translateX(-200px)}100%{transform:translateX(1000px)}}"
            ".flick{animation:fl 5s infinite}"
            "@keyframes fl{0%,100%,60%{opacity:1}61%{opacity:.3}62%{opacity:1}64%{opacity:.5}65%{opacity:1}}")
    s.add(f'<defs><linearGradient id="ln" x1="0" y1="0" x2="1" y2="0">'
          f'<stop offset="0" stop-color="{accent}" stop-opacity="0"/>'
          f'<stop offset=".5" stop-color="{accent}"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/>'
          f'</linearGradient></defs>')
    tag_w = text_width("pix", code, 13) + 24
    s.add(f'<path d="M4,14 H{tag_w + 4} L{tag_w + 18},28 L{tag_w + 4},42 H4 Z" fill="{color}"/>')
    s.text(16, 35, code, "pix", 13, BG)
    s.add('<g class="flick">')
    s.text(round(tag_w + 34, 1), 41, title, "orb", 28, WHITE)
    s.add('</g>')
    tx = tag_w + 34 + text_width("orb", title, 28) + 16
    s.text(round(tx, 1), 41, "_", "orb", 28, color)
    s.add(f'<line x1="4" y1="64" x2="996" y2="64" stroke="{color}" stroke-opacity=".35" stroke-width="2"/>')
    s.add(f'<rect class="run" x="0" y="62" width="200" height="4" fill="url(#ln)"/>')
    save(fname, s, title)


# ── PROJECT CARDS ─────────────────────────────────────────────────────────
PROJECTS = [
    ("netscope", "PRJ-01", "NETSCOPE", "Network Packet Analyzer",
     "Real-time traffic analysis with a SOC-style browser dashboard, protocol breakdowns, anomaly alerts and per-host risk scores.",
     ["PYTHON", "SCAPY", "WEBSOCKET", "RENDER"], CYAN),
    ("fsociety", "PRJ-02", "FSOCIETY-WEB", "Security Portfolio",
     "Cinematic dark portfolio with a terminal boot sequence, interactive roadmap, in-browser utilities and CTF progress.",
     ["VANILLA JS", "HTML", "CSS", "VERCEL"], MAGENTA),
    ("industrust", "PRJ-03", "INDUSTRUST BANK", "Banking System",
     "Spring Boot web bank with a double-entry ledger, row-locked atomic transfers, BigDecimal money and hashed PINs.",
     ["SPRING BOOT", "SECURITY", "POSTGRES", "DOCKER"], LIME),
    ("sms", "PRJ-04", "STUDENT MGMT SYS", "Records Platform",
     "Legacy Swing + Oracle app rebuilt as a cloud REST service with analytics, CSV export and CI on every push.",
     ["SPRING BOOT", "NEON PG", "ACTIONS", "RENDER"], YELLOW),
    ("snapurl", "PRJ-05", "SNAPURL", "Serverless URL Shortener",
     "Base62 short links, custom aliases and self-expiring TTL links on Vercel functions with Turso edge SQLite.",
     ["TYPESCRIPT", "EXPRESS", "TURSO", "VERCEL"], VIOLET),
    ("cineroulette", "PRJ-06", "CINEROULETTE", "Movie Picker",
     "Pick a mood, spin the reel, get one explained pick. Weighted scoring normalized per language and region.",
     ["NEXT.JS", "NESTJS", "PRISMA", "REDIS"], MAGENTA),
    ("gitatlas", "PRJ-07", "GITATLAS", "Git Command Atlas",
     "381 Git commands in plain English, 17 recovery playbooks, a two-question wizard and warnings on risky commands.",
     ["VANILLA JS", "HTML", "CSS", "VERCEL"], CYAN),
    ("grabmedia", "PRJ-08", "GRABMEDIA", "Media Downloader",
     "Save public Instagram and YouTube media up to 2160p or audio-only, behind a hardened rate-limited Express proxy.",
     ["NODE.JS", "EXPRESS", "HELMET", "RENDER"], YELLOW),
    ("disease", "PRJ-09", "DISEASE PREDICT", "Explainable ML",
     "Predicts 41 diseases from 132 symptoms with a tree ensemble, SHAP explanations and downloadable PDF reports.",
     ["FASTAPI", "SKLEARN", "SHAP", "DOCKER"], LIME),
    ("siteshield", "PRJ-10", "SITESHIELD", "Security Posture SaaS",
     "Grades a site's TLS, headers, cookies and DNS hygiene A to F, re-scans on schedule and alerts on regressions.",
     ["REACT", "FASTAPI", "CELERY", "POSTGRES"], VIOLET),
]
BUILDING = {"siteshield"}


def build_card(slug, pid, title, sub, desc, stack, col):
    s = Svg(480, 250)
    building = slug in BUILDING
    s.style(".trace{stroke-dasharray:120 1300;animation:tr 4s linear infinite}"
            "@keyframes tr{0%{stroke-dashoffset:0}100%{stroke-dashoffset:-1420}}"
            ".pulse{animation:pu 1.2s ease-in-out infinite}@keyframes pu{50%{opacity:.2}}"
            ".arrow{animation:ar 1.4s ease-in-out infinite}@keyframes ar{50%{transform:translateX(6px)}}")
    s.add(f'<defs><linearGradient id="bgc" x1="0" y1="0" x2="1" y2="1">'
          f'<stop offset="0" stop-color="{PANEL}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>')
    edge = "M14,2 H466 L478,14 V236 L466,248 H14 L2,236 V14 Z"
    s.add(f'<path d="{edge}" fill="url(#bgc)" stroke="{col}" stroke-opacity=".45" stroke-width="2"/>')
    s.add(f'<path class="trace" d="{edge}" fill="none" stroke="{col}" stroke-width="3"/>')
    s.text(22, 34, pid, "pix", 10, col)
    status = "BUILDING" if building else "ONLINE"
    scol = YELLOW if building else LIME
    sw = text_width("pix", status, 9)
    s.add(f'<circle cx="{456 - sw - 12}" cy="30" r="5" fill="{scol}" class="pulse"/>')
    s.text(round(456 - sw, 1), 34, status, "pix", 9, scol)
    s.text(22, 72, title, "orb", 25, WHITE)
    s.text(22, 96, sub.upper(), "raj", 17, col, 'letter-spacing="1.5"')
    y = 124
    for line in wrap(desc, "mono", 14.5, 436)[:3]:
        s.text(22, y, line, "mono", 14.5, "#cfc8ea")
        y += 20
    x = 22
    for chip in stack:
        w = text_width("pix", chip, 8) + 16
        s.add(f'<rect x="{x}" y="190" width="{w:.0f}" height="20" rx="3" fill="none" stroke="{col}" stroke-opacity=".6"/>')
        s.text(round(x + 8, 1), 204, chip, "pix", 8, col)
        x += w + 8
    cta = "[ SOURCE ]" if building else "[ LAUNCH ]"
    s.text(22, 236, cta, "pix", 9, WHITE)
    s.add(f'<g class="arrow"><path d="M{36 + text_width("pix", cta, 9):.0f},230 h14 m-5,-5 l5,5 l-5,5" '
          f'fill="none" stroke="{col}" stroke-width="2.5"/></g>')
    save(f"card-{slug}.svg", s, f"{title} — {sub}")


# ── LOADOUT ──────────────────────────────────────────────────────────────
def build_loadout():
    groups = [
        ("// BUILD", CYAN, ["JAVA", "SPRING BOOT", "PYTHON", "FASTAPI", "TYPESCRIPT", "JAVASCRIPT",
                           "NODE.JS", "EXPRESS", "NESTJS", "NEXT.JS", "REACT", "TAILWIND", "PHP"]),
        ("// DATA + SHIP", LIME, ["POSTGRESQL", "MYSQL", "MONGODB", "REDIS", "PRISMA", "DOCKER",
                                  "GH ACTIONS", "VERCEL", "RENDER", "GIT", "LINUX"]),
        ("// SECURITY LAB", MAGENTA, ["KALI LINUX", "BURP SUITE", "NMAP", "WIRESHARK", "METASPLOIT",
                                      "HASHCAT", "VOLATILITY3", "GHIDRA", "OWASP TOP 10"]),
    ]
    s = Svg(1000, 0)
    s.style(".chip{animation:cg 4.5s ease-in-out infinite}"
            "@keyframes cg{0%,100%{fill-opacity:0}50%{fill-opacity:.22}}")
    y = 44
    n = 0
    for label, col, chips in groups:
        s.text(24, y, label, "pix", 11, col)
        y += 16
        x = 24
        for chip in chips:
            w = text_width("raj", chip, 17) + 26
            if x + w > 976:
                x = 24
                y += 38
            s.add(f'<rect class="chip" style="animation-delay:-{(n * 0.31) % 4.5:.2f}s" x="{x:.0f}" y="{y}" '
                  f'width="{w:.0f}" height="28" rx="4" fill="{col}" stroke="{col}" stroke-width="1.6"/>')
            s.text(round(x + 13, 1), y + 20, chip, "raj", 17, WHITE)
            x += w + 10
            n += 1
        y += 62
    s.h = y - 20
    s.parts.insert(0, f'<rect x="2" y="2" width="996" height="{s.h - 4}" rx="14" fill="{PANEL}" '
                      f'stroke="{VIOLET}" stroke-opacity=".6" stroke-width="2"/>')
    save("loadout.svg", s, "Toolkit: build, data and ship, security lab")


# ── FOOTER ───────────────────────────────────────────────────────────────
def build_footer():
    s = Svg(1000, 150)
    s.style(".blink{animation:bl 1s steps(1) infinite}@keyframes bl{50%{opacity:0}}"
            ".ga{animation:ga 2.6s infinite steps(1)}"
            "@keyframes ga{0%,80%,100%{transform:translate(0,0)}82%{transform:translate(-8px,1px)}"
            "84%{transform:translate(6px,-2px)}86%{transform:translate(0,0)}}")
    s.add(f'<defs><linearGradient id="ft" x1="0" y1="0" x2="1" y2="0">'
          f'<stop offset="0" stop-color="{MAGENTA}"/><stop offset=".5" stop-color="{VIOLET}"/>'
          f'<stop offset="1" stop-color="{CYAN}"/></linearGradient></defs>')
    s.add('<rect width="1000" height="150" rx="14" fill="url(#ft)"/>')
    s.add(f'<rect x="4" y="4" width="992" height="142" rx="11" fill="{BG}" opacity=".88"/>')
    msg = "SESSION SAVED. SEE YOU IN THE LOGS."
    mx = (1000 - text_width("orb", msg, 26)) / 2
    s.text(round(mx, 1), 72, msg, "orb", 26, MAGENTA, 'opacity=".6"', "ga")
    s.text(round(mx, 1), 72, msg, "orb", 26, WHITE)
    sub = "root@armanxploits:~# exit"
    sx = (1000 - text_width("mono", sub, 18) - 14) / 2
    s.text(round(sx, 1), 110, sub, "mono", 18, LIME)
    s.add(f'<rect x="{sx + text_width("mono", sub, 18) + 6:.0f}" y="96" width="10" height="17" fill="{LIME}" class="blink"/>')
    save("footer.svg", s, "Session saved. See you in the logs.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    load_fonts(ap.parse_args().fonts)
    build_hero()
    build_idcard()
    build_monitor()
    headers = [
        ("h-about.svg", "0x01", "OPERATOR PROFILE", CYAN, MAGENTA),
        ("h-projects.svg", "0x02", "LIVE DEPLOYMENTS", MAGENTA, CYAN),
        ("h-loadout.svg", "0x03", "LOADOUT", LIME, YELLOW),
        ("h-pipeline.svg", "0x04", "THE PIPELINE", YELLOW, MAGENTA),
        ("h-stats.svg", "0x05", "TELEMETRY", VIOLET, LIME),
        ("h-connect.svg", "0x06", "OPEN A CHANNEL", CYAN, YELLOW),
    ]
    for h in headers:
        build_header(*h)
    for p in PROJECTS:
        build_card(*p)
    build_loadout()
    build_footer()


if __name__ == "__main__":
    main()
