#!/usr/bin/env python3
"""Build the animated "bento" SVG tiles used by the profile README.

Design notes
- Each tile is a self-contained SVG: fonts are subset and embedded as WOFF2
  (GitHub blocks external resources inside <img> SVGs).
- Colours are CSS variables with a light and a dark set, switched by
  prefers-color-scheme inside the SVG, so every tile matches the viewer.
- Motion is slow, purposeful and disabled under prefers-reduced-motion.
- Tiles in one README row share a height and their widths are proportional,
  so they line up as a real bento grid when sized with percentages.

Usage:
    pip install fonttools brotli
    python3 scripts/build_bento_assets.py            # fonts are read from assets/fonts/

The live stats tiles are drawn by scripts/build_bento_stats.py in the workflow.
"""
import argparse
import base64
import io
import math
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "bento")

FONT_FILES = {
    "disp": "sora-latin-700-normal.woff",
    "dispx": "sora-latin-800-normal.woff",
    "semi": "sora-latin-600-normal.woff",
    "body": "inter-latin-400-normal.woff",
    "bodym": "inter-latin-500-normal.woff",
    "mono": "jetbrains-mono-latin-400-normal.woff",
    "monom": "jetbrains-mono-latin-500-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}

TOKENS = {
    "dark": dict(page="#0d1117", tile="#111118", tile2="#17171f", border="#262633", fg="#f5f5f7",
                 soft="#d6d6de", muted="#9b9bab", violet="#8b7bff", pink="#ff6b9a", cyan="#2fd6f0",
                 amber="#ffb547", green="#34d399", glow=".55"),
    "light": dict(page="#ffffff", tile="#ffffff", tile2="#f6f6f9", border="#e5e5ee", fg="#111118",
                  soft="#2a2a35", muted="#5f5f70", violet="#6d4dff", pink="#e0306b", cyan="#0aa3c2",
                  amber="#d48600", green="#0e9e6c", glow=".28"),
}
ACCENTS = ["violet", "pink", "cyan", "amber", "green"]

_paths, _metrics = {}, {}


# ── fonts ────────────────────────────────────────────────────────────────
def load_fonts(font_dir):
    for key, name in FONT_FILES.items():
        for root, _, files in os.walk(font_dir):
            if name in files:
                _paths[key] = os.path.join(root, name)
        if key not in _paths:
            raise SystemExit(f"missing font {name} under {font_dir}")
        f = TTFont(_paths[key])
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)


def tw(key, text, size, ls=0):
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm + ls * len(text)


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


def paint(c):
    """A colour token name becomes a CSS variable; anything else is literal."""
    return c if c.startswith(("#", "url", "none")) else f"var(--{c})"


# ── SVG builder ──────────────────────────────────────────────────────────
class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [], []
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, font, size, fill="fg", anchor=None, ls=0, cls="", op=None):
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        o = f' opacity="{op}"' if op is not None else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}"'
                          f'{a}{l}{c}{o} style="fill:{paint(fill)}">{escape(s)}</text>')

    def spans(self, x, y, segs, size, cls=""):
        out, cx = [], x
        for s, font, col in segs:
            self.chars[font] += s
            out.append(f'<tspan x="{cx:.1f}" font-family="{FAMILY[font]}" style="fill:{paint(col)}">{escape(s)}</tspan>')
            cx += tw(font, s, size)
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<text y="{y:.1f}" font-size="{size}"{c} xml:space="preserve">{"".join(out)}</text>')
        return cx

    def rect(self, x, y, w, h, rx=0, fill="tile", stroke=None, sw=1, extra=""):
        st = f"fill:{paint(fill)};" + (f"stroke:{paint(stroke)};stroke-width:{sw};" if stroke else "")
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" style="{st}" {extra}/>')

    def circle(self, cx, cy, r, fill="fg", stroke=None, sw=1, extra=""):
        st = f"fill:{paint(fill)};" + (f"stroke:{paint(stroke)};stroke-width:{sw};" if stroke else "")
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" style="{st}" {extra}/>')

    def path(self, d, stroke="fg", sw=2, fill="none", extra=""):
        self.parts.append(f'<path d="{d}" style="fill:{paint(fill)};stroke:{paint(stroke)};stroke-width:{sw};'
                          f'stroke-linecap:round;stroke-linejoin:round" {extra}/>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def grad(self, gid, stops, x2=1, y2=0):
        st = "".join(f'<stop offset="{o}" style="stop-color:{paint(c)};stop-opacity:{a}"/>' for o, c, a in stops)
        self.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{st}</linearGradient>')

    def save(self, name, title):
        faces = "".join(font_face(k, v) for k, v in self.chars.items() if v)
        var = lambda t: ";".join(f"--{k}:{v}" for k, v in TOKENS[t].items())
        css = (faces + f"svg{{{var('dark')}}}"
               f"@media (prefers-color-scheme:light){{svg{{{var('light')}}}}}" + "".join(self.css) +
               "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)


# ── shared pieces ────────────────────────────────────────────────────────
RISE = ("@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
        ".rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}")
PULSE = (".pulse{animation:pulse 2.2s ease-in-out infinite}@keyframes pulse{50%{opacity:.35}}"
         ".ring{transform-box:fill-box;transform-origin:center;animation:ring 2.2s ease-out infinite}"
         "@keyframes ring{from{transform:scale(.6);opacity:.7}to{transform:scale(2.6);opacity:0}}")


def tile(s, accent="violet", glow=True):
    """Rounded tile with a soft corner glow in the accent colour."""
    gid = s.uid("tg")
    s.defs.append(f'<radialGradient id="{gid}" cx="1" cy="0" r="1"><stop offset="0" '
                  f'style="stop-color:var(--{accent});stop-opacity:var(--glow)"/>'
                  f'<stop offset="1" style="stop-color:var(--{accent});stop-opacity:0"/></radialGradient>')
    cid = s.uid("tc")
    s.defs.append(f'<clipPath id="{cid}"><rect x="1" y="1" width="{s.w - 2}" height="{s.h - 2}" rx="22"/></clipPath>')
    s.add(f'<g clip-path="url(#{cid})">')
    s.rect(0, 0, s.w, s.h, 0, "tile")
    if glow:
        s.add(f'<rect x="0" y="0" width="{s.w}" height="{s.h}" style="fill:url(#{gid})" opacity=".45"/>')
    s.add("</g>")
    s.rect(1, 1, s.w - 2, s.h - 2, 22, "none", "border", 1.2)


def eyebrow(s, x, y, label, accent="violet", dot=False):
    if dot:
        s.circle(x + 4, y - 4.5, 4, accent, extra='class="pulse"')
        x += 14
    s.text(x, y, label.upper(), "monom", 12, accent, ls=1.6)


def arrow(s, x, y, color, w=2):
    s.path(f"M{x},{y + 9} L{x + 9},{y} M{x + 2},{y} H{x + 9} V{y + 7}", color, w)


def pill(s, x, y, label, fill="tile2", stroke="border", col="soft", font="monom", size=12.5, h=30):
    w = tw(font, label, size) + 28
    s.rect(x, y, w, h, h / 2, fill, stroke)
    s.text(x + 14, y + h / 2 + size * .36, label, font, size, col)
    return w


# ── 1. HERO ──────────────────────────────────────────────────────────────
def build_hero():
    s = Svg(1000, 400)
    s.style(RISE + PULSE +
            ".d1{animation-delay:.05s}.d2{animation-delay:.2s}.d3{animation-delay:.35s}.d4{animation-delay:.5s}"
            ".d5{animation-delay:.7s}"
            ".b1{animation:b1 16s ease-in-out infinite alternate}.b2{animation:b2 19s ease-in-out infinite alternate}"
            ".b3{animation:b3 22s ease-in-out infinite alternate}"
            "@keyframes b1{to{transform:translate(-180px,60px)}}@keyframes b2{to{transform:translate(140px,-40px)}}"
            "@keyframes b3{to{transform:translate(-90px,-70px)}}"
            ".float{animation:float 6s ease-in-out infinite}@keyframes float{50%{transform:translateY(-8px)}}"
            ".caret{animation:caret 1s steps(1) infinite}@keyframes caret{50%{opacity:0}}"
            ".shine{animation:shine 7s ease-in-out infinite}"
            "@keyframes shine{0%,100%{transform:translateX(-30%)}50%{transform:translateX(30%)}}")
    s.defs.append('<filter id="blur" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="55"/></filter>')
    cid = "hc"
    s.defs.append(f'<clipPath id="{cid}"><rect x="1" y="1" width="998" height="398" rx="26"/></clipPath>')
    s.add(f'<g clip-path="url(#{cid})">')
    s.rect(0, 0, 1000, 400, 0, "tile")
    s.add('<g filter="url(#blur)" opacity=".55">')
    s.circle(760, 80, 150, "violet", extra='class="b1"')
    s.circle(930, 330, 130, "pink", extra='class="b2"')
    s.circle(560, 380, 120, "cyan", extra='class="b3"')
    s.add("</g>")
    # fine dot grid
    s.defs.append('<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
                  '<circle cx="2" cy="2" r="1" style="fill:var(--border)"/></pattern>')
    s.add('<rect width="1000" height="400" style="fill:url(#dots)" opacity=".8"/>')
    s.add("</g>")
    s.rect(1, 1, 998, 398, 26, "none", "border", 1.2)
    x = 56
    # status pill
    s.add('<g class="rise d1">')
    label = "Cybersecurity Intern  ·  B.Tech CSE '27  ·  India"
    w = tw("monom", label, 12.5) + 44
    s.rect(x, 50, w, 32, 16, "tile2", "border")
    s.circle(x + 16, 66, 4.5, "green", extra='class="pulse"')
    s.text(x + 30, 70.5, label, "monom", 12.5, "soft")
    s.add("</g>")
    # name with animated gradient
    s.defs.append('<linearGradient id="ng" x1="0" y1="0" x2="1" y2="0" gradientUnits="objectBoundingBox">'
                  '<stop offset="0" style="stop-color:var(--fg)"/><stop offset=".45" style="stop-color:var(--fg)"/>'
                  '<stop offset=".7" style="stop-color:var(--violet)"/><stop offset=".85" style="stop-color:var(--pink)"/>'
                  '<stop offset="1" style="stop-color:var(--amber)"/></linearGradient>')
    s.add('<g class="rise d2">')
    s.text(x - 3, 160, "Arman Ahemad", "dispx", 62, "url(#ng)", ls=-1.6)
    s.text(x - 3, 228, "Khan.", "dispx", 62, "url(#ng)", ls=-1.6)
    s.add("</g>")
    s.add('<g class="rise d3">')
    s.text(x, 276, "Full-stack developer who thinks like an attacker.", "semi", 21, "soft", ls=-.2)
    s.add("</g>")
    s.add('<g class="rise d4">')
    for i, line in enumerate(["I design and ship web products, then try to break them,",
                              "so the version you use is the hardened one."]):
        s.text(x, 310 + i * 24, line, "body", 16, "muted")
    s.add("</g>")
    # floating code card
    s.add('<g class="rise d5"><g class="float">')
    cx, cy, cw, ch = 610, 96, 334, 214
    s.rect(cx, cy, cw, ch, 18, "tile2", "border", 1.2, 'opacity=".96"')
    for i, c in enumerate(("pink", "amber", "green")):
        s.circle(cx + 22 + i * 16, cy + 22, 5, c)
    s.text(cx + cw - 18, cy + 27, "arman.ts", "mono", 12, "muted", anchor="end")
    s.add(f'<line x1="{cx}" y1="{cy + 42}" x2="{cx + cw}" y2="{cy + 42}" style="stroke:var(--border)"/>')
    code = [
        [("const ", "violet"), ("arman", "fg"), (" = {", "muted")],
        [("  builds", "cyan"), (": ", "muted"), ('"full-stack apps"', "green"), (",", "muted")],
        [("  breaks", "cyan"), (": ", "muted"), ('"them, ethically"', "green"), (",", "muted")],
        [("  ships", "cyan"), (": ", "muted"), ('"the hardened one"', "green"), (",", "muted")],
        [("};", "muted")],
    ]
    ly = cy + 72
    for row in code:
        e = s.spans(cx + 22, ly, [(t, "mono", c) for t, c in row], 14)
        ly += 26
    s.rect(e + 4, ly - 26 - 13, 8, 17, 1, "violet", extra='class="caret"')
    s.add("</g></g>")
    s.save("hero.svg", "Arman Ahemad Khan — Full-stack developer who thinks like an attacker")


# ── 2. ROW: NOW + MODE TOGGLE ────────────────────────────────────────────
def build_now():
    s = Svg(400, 230)
    s.style(RISE + PULSE)
    tile(s, "green")
    eyebrow(s, 30, 46, "Right now", "green", dot=True)
    s.add('<g class="rise">')
    s.text(30, 100, "Cybersecurity", "disp", 30, "fg", ls=-.6)
    s.text(30, 136, "Intern", "disp", 30, "fg", ls=-.6)
    s.text(30, 170, "Pentesting & web application security", "body", 15, "muted")
    s.add("</g>")
    px = 30
    for lab in ("Web AppSec", "Recon", "Reporting"):
        px += pill(s, px, 186, lab, size=11.5, h=26) + 8
    s.save("now.svg", "Right now: Cybersecurity Intern, pentesting and web application security")


def build_modes():
    s = Svg(590, 230)
    P = 7
    s.style(RISE +
            f".knob{{animation:knob {P}s cubic-bezier(.65,0,.35,1) infinite}}"
            "@keyframes knob{0%,42%{transform:translateX(0)}50%,92%{transform:translateX(150px)}100%{transform:translateX(0)}}"
            f".trk{{animation:trk {P}s infinite}}"
            "@keyframes trk{0%,42%{opacity:1}50%,92%{opacity:0}100%{opacity:1}}"
            f".trk2{{animation:trk2 {P}s infinite}}"
            "@keyframes trk2{0%,42%{opacity:0}50%,92%{opacity:1}100%{opacity:0}}"
            f".ma{{animation:ma {P}s infinite}}@keyframes ma{{0%,40%{{opacity:1;transform:none}}"
            "46%,94%{opacity:0;transform:translateY(-8px)}100%{opacity:1;transform:none}}"
            f".mb{{animation:mb {P}s infinite}}@keyframes mb{{0%,44%{{opacity:0;transform:translateY(8px)}}"
            "50%,90%{opacity:1;transform:none}96%,100%{opacity:0;transform:translateY(8px)}}")
    tile(s, "pink")
    eyebrow(s, 30, 46, "Two modes · one mission", "pink")
    s.text(30, 92, "Build it. Break it. Ship it hardened.", "disp", 24, "fg", ls=-.5)
    # toggle switch
    tx, ty = 30, 120
    s.add(f'<g class="trk">'); s.rect(tx, ty, 300, 46, 23, "tile2", "border"); s.add("</g>")
    s.add(f'<g class="trk2">'); s.rect(tx, ty, 300, 46, 23, "tile2", "pink", 1.5); s.add("</g>")
    s.add('<g class="knob">')
    s.rect(tx + 4, ty + 4, 142, 38, 19, "fg")
    s.add("</g>")
    # labels: the active one sits on the white knob (drawn twice for contrast)
    s.text(tx + 75, ty + 28.5, "BUILD", "monom", 13, "muted", anchor="middle", ls=1.5)
    s.text(tx + 225, ty + 28.5, "BREAK", "monom", 13, "muted", anchor="middle", ls=1.5)
    s.add('<g class="ma">'); s.text(tx + 75, ty + 28.5, "BUILD", "monom", 13, "tile", anchor="middle", ls=1.5); s.add("</g>")
    s.add('<g class="mb">'); s.text(tx + 225, ty + 28.5, "BREAK", "monom", 13, "tile", anchor="middle", ls=1.5); s.add("</g>")
    # swapping detail line
    s.add('<g class="ma">')
    s.spans(30, 200, [("stack  ", "monom", "violet"), ("Spring Boot · Node · React · FastAPI", "body", "soft")], 14.5)
    s.add("</g><g class=\"mb\">")
    s.spans(30, 200, [("tools  ", "monom", "pink"), ("Burp · Nmap · Wireshark · Volatility3", "body", "soft")], 14.5)
    s.add("</g>")
    # little shield / code glyphs that swap on the right
    gx, gy = 470, 150
    s.add('<g class="ma">')
    s.rect(gx - 50, gy - 50, 100, 100, 26, "tile2", "border")
    s.path(f"M{gx - 18},{gy - 14} L{gx - 32},{gy} L{gx - 18},{gy + 14} M{gx + 18},{gy - 14} L{gx + 32},{gy} "
           f"L{gx + 18},{gy + 14} M{gx + 6},{gy - 20} L{gx - 6},{gy + 20}", "violet", 4)
    s.add("</g><g class=\"mb\">")
    s.rect(gx - 50, gy - 50, 100, 100, 26, "tile2", "border")
    s.path(f"M{gx},{gy - 30} L{gx + 24},{gy - 20} V{gy + 2} C{gx + 24},{gy + 18} {gx + 12},{gy + 26} {gx},{gy + 32} "
           f"C{gx - 12},{gy + 26} {gx - 24},{gy + 18} {gx - 24},{gy + 2} V{gy - 20} Z", "pink", 4)
    s.path(f"M{gx - 10},{gy + 1} L{gx - 2},{gy + 9} L{gx + 12},{gy - 7}", "pink", 4)
    s.add("</g>")
    s.save("modes.svg", "Two modes, one mission: build with Spring Boot, Node, React and FastAPI; test with Burp, Nmap, Wireshark and Volatility3")


# ── 3. ROW: ODOMETER + GLOBE + DEGREE RING ───────────────────────────────
def build_shipped():
    s = Svg(300, 250)
    s.style(RISE +
            ".roll{animation:roll 2.4s cubic-bezier(.2,.8,.2,1) .3s both}"
            "@keyframes roll{from{transform:translateY(0)}to{transform:translateY(-810px)}}")
    tile(s, "violet")
    eyebrow(s, 28, 46, "Shipped", "violet")
    # odometer digit window
    s.defs.append('<clipPath id="win"><rect x="20" y="76" width="130" height="96"/></clipPath>')
    s.add('<g clip-path="url(#win)"><g class="roll">')
    for d in range(10):
        s.text(28, 154 + d * 90, str(d), "dispx", 96, "url(#og)", ls=-2)
    s.add("</g></g>")
    s.grad("og", [(0, "violet", 1), (1, "pink", 1)], 0, 1)
    s.text(100, 152, "+", "disp", 40, "pink")
    s.text(28, 196, "live apps in production", "bodym", 15, "fg")
    s.text(28, 220, "Vercel · Render · GitHub Pages", "body", 13, "muted")
    s.save("shipped.svg", "9+ live apps in production")


def build_globe():
    s = Svg(340, 250)
    s.style(PULSE +
            ".spin{transform-box:fill-box;transform-origin:center;animation:spin 9s linear infinite}"
            "@keyframes spin{0%{transform:scaleX(1)}50%{transform:scaleX(-1)}100%{transform:scaleX(1)}}")
    tile(s, "cyan")
    eyebrow(s, 28, 46, "Based in", "cyan")
    s.text(28, 92, "India", "disp", 34, "fg", ls=-.8)
    s.text(28, 118, "IST · UTC+5:30", "mono", 13, "muted")
    s.text(28, 214, "Open to remote", "bodym", 14, "soft")
    s.text(28, 234, "collaboration", "bodym", 14, "soft")
    gx, gy, r = 238, 150, 78
    s.circle(gx, gy, r, "tile2", "border", 1.4)
    for k, lat in enumerate((-50, -25, 0, 25, 50)):
        yy = gy + r * math.sin(math.radians(lat))
        rx = r * math.cos(math.radians(lat))
        s.add(f'<ellipse cx="{gx}" cy="{yy:.1f}" rx="{rx:.1f}" ry="{rx * .16:.1f}" '
              f'style="fill:none;stroke:var(--border);stroke-width:1.2"/>')
    for k, ph in enumerate((0, .2, .4, .6, .8)):
        s.add(f'<ellipse class="spin" style="animation-delay:-{ph * 9:.1f}s;fill:none;stroke:var(--cyan);'
              f'stroke-opacity:.45;stroke-width:1.2" cx="{gx}" cy="{gy}" rx="{r:.0f}" ry="{r}"/>')
    # India pin (roughly 20N, slightly right of centre)
    px, py = gx + 22, gy - 26
    s.circle(px, py, 6, "pink", extra='class="ring"')
    s.circle(px, py, 6, "pink")
    s.circle(px, py, 2.4, "tile")
    s.save("globe.svg", "Based in India, IST UTC+5:30")


def build_degree():
    s = Svg(340, 250)
    progress = 0.85  # Aug 2023 -> Jun 2027, as of late 2026
    r = 54
    circ = 2 * math.pi * r
    s.style(f".arc{{stroke-dasharray:{circ:.1f};animation:arc 2s cubic-bezier(.2,.8,.2,1) .3s both}}"
            f"@keyframes arc{{from{{stroke-dashoffset:{circ:.1f}}}to{{stroke-dashoffset:{circ * (1 - progress):.1f}}}}}")
    tile(s, "amber")
    eyebrow(s, 28, 46, "Education", "amber")
    s.text(28, 92, "B.Tech CSE", "disp", 28, "fg", ls=-.6)
    s.text(28, 118, "Silicon Institute of", "body", 14, "muted")
    s.text(28, 138, "Technology, BBSR", "body", 14, "muted")
    s.text(28, 214, "Class of", "bodym", 14, "soft")
    s.text(28, 236, "2027", "disp", 18, "amber")
    gx, gy = 252, 160
    s.grad("ag", [(0, "amber", 1), (1, "pink", 1)], 1, 1)
    s.circle(gx, gy, r, "none", "border", 10)
    s.add(f'<circle class="arc" cx="{gx}" cy="{gy}" r="{r}" transform="rotate(-90 {gx} {gy})" '
          f'style="fill:none;stroke:url(#ag);stroke-width:10;stroke-linecap:round"/>')
    s.text(gx, gy + 6, f"{progress * 100:.0f}%", "disp", 24, "fg", anchor="middle")
    s.text(gx, gy + 26, "complete", "mono", 10.5, "muted", anchor="middle")
    s.save("degree.svg", "B.Tech CSE at Silicon Institute of Technology, class of 2027, about 85% complete")


# ── 4. TOOLBOX MARQUEE ───────────────────────────────────────────────────
def build_marquee():
    s = Svg(1000, 150)
    rows = [
        ["Java", "Spring Boot", "TypeScript", "JavaScript", "Python", "FastAPI", "Node.js", "Express",
         "NestJS", "Next.js", "React", "Tailwind"],
        ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Prisma", "Docker", "GitHub Actions", "Vercel",
         "Render", "Kali Linux", "Burp Suite", "Nmap", "Wireshark", "Volatility3"],
    ]
    tile(s, "violet", glow=False)
    s.defs.append('<linearGradient id="edge" x1="0" x2="1">'
                  '<stop offset="0" style="stop-color:var(--tile);stop-opacity:1"/>'
                  '<stop offset=".14" style="stop-color:var(--tile);stop-opacity:0"/>'
                  '<stop offset=".86" style="stop-color:var(--tile);stop-opacity:0"/>'
                  '<stop offset="1" style="stop-color:var(--tile);stop-opacity:1"/></linearGradient>')
    s.defs.append('<clipPath id="mq"><rect x="2" y="2" width="996" height="146" rx="21"/></clipPath>')
    s.add('<g clip-path="url(#mq)">')
    for i, row in enumerate(rows):
        widths = [tw("bodym", t, 14.5) + 34 for t in row]
        total = sum(widths) + 10 * len(row)
        dur = total / 40
        direction = "" if i == 0 else " reverse"
        k = f"m{i}"
        s.style(f".{k}{{animation:{k} {dur:.1f}s linear infinite{direction}}}"
                f"@keyframes {k}{{from{{transform:translateX(0)}}to{{transform:translateX(-{total:.0f}px)}}}}")
        s.add(f'<g class="{k}">')
        y = 30 + i * 52
        for rep in range(3):
            x = 20 + rep * total
            for t, w in zip(row, widths):
                acc = ACCENTS[(row.index(t) + i) % len(ACCENTS)]
                s.rect(x, y, w, 38, 19, "tile2", "border")
                s.circle(x + 16, y + 19, 4, acc)
                s.text(x + 26, y + 24, t, "bodym", 14.5, "soft")
                x += w + 10
        s.add("</g>")
    s.add('<rect width="1000" height="150" style="fill:url(#edge)"/>')
    s.add("</g>")
    s.save("toolbox.svg", "Toolbox: Java, Spring Boot, TypeScript, Python, FastAPI, Node.js, React, PostgreSQL, Docker, Burp Suite, Nmap and more")


# ── SECTION HEADER ───────────────────────────────────────────────────────
def build_header(name, kicker, title, accent):
    s = Svg(1000, 96)
    s.style(".sweep{animation:sweep 5s ease-in-out infinite}"
            "@keyframes sweep{0%,100%{transform:translateX(0)}50%{transform:translateX(120px)}}")
    s.text(2, 30, kicker.upper(), "monom", 12.5, accent, ls=2)
    s.text(0, 72, title, "disp", 34, "fg", ls=-.9)
    s.grad(f"hg", [(0, accent, 1), (1, accent, 0)])
    s.add('<g class="sweep">')
    s.rect(2, 86, 120, 3, 1.5, "url(#hg)")
    s.add("</g>")
    s.save(f"h-{name}.svg", title)


# ── PROJECT CARDS with per-project illustrations ─────────────────────────
def ill_netscope(s, x, y, w, h, a):
    nodes = [(x + 70, y + 60), (x + 160, y + 40), (x + 250, y + 85), (x + 140, y + 120), (x + 330, y + 50),
             (x + 380, y + 120)]
    edges = [(0, 1), (1, 2), (0, 3), (3, 2), (2, 4), (4, 5), (2, 5)]
    for i, j in edges:
        s.add(f'<line x1="{nodes[i][0]}" y1="{nodes[i][1]}" x2="{nodes[j][0]}" y2="{nodes[j][1]}" '
              f'style="stroke:var(--{a});stroke-opacity:.35;stroke-width:1.5"/>')
    for k, (i, j) in enumerate(edges[:5]):
        (x1, y1), (x2, y2) = nodes[i], nodes[j]
        kk = s.uid("pk")
        s.style(f".{kk}{{animation:{kk} {2.2 + k * .35:.2f}s linear infinite}}"
                f"@keyframes {kk}{{from{{transform:translate(0,0)}}to{{transform:translate({x2 - x1}px,{y2 - y1}px)}}}}")
        s.circle(x1, y1, 3.5, a, extra=f'class="{kk}"')
    for i, (nx, ny) in enumerate(nodes):
        s.circle(nx, ny, 9 if i != 4 else 11, "tile", a, 2)
    s.circle(nodes[4][0], nodes[4][1], 11, "pink", extra='class="ring"')
    s.text(nodes[4][0] + 16, nodes[4][1] - 12, "anomaly", "monom", 11, "pink")


def ill_fsociety(s, x, y, w, h, a):
    s.rect(x + 40, y + 20, w - 80, h - 40, 10, "tile", "border")
    for i, c in enumerate(("pink", "amber", "green")):
        s.circle(x + 58 + i * 13, y + 36, 4, c)
    lines = [("$ ./boot --fsociety", "green"), ("[ ok ] loading roadmap", "soft"), ("[ ok ] toolbox online", "soft")]
    for i, (t, c) in enumerate(lines):
        k = s.uid("ty")
        s.style(f".{k}{{animation:{k} 6s steps(1) infinite}}@keyframes {k}{{0%,{8 + i * 18}%{{opacity:0}}"
                f"{9 + i * 18}%,92%{{opacity:1}}100%{{opacity:0}}}}")
        s.text(x + 58, y + 70 + i * 22, t, "mono", 13, c, cls=k)
    s.rect(x + 58, y + 126, 8, 14, 1, a, extra='class="caret"')
    s.style(".caret{animation:caret 1s steps(1) infinite}@keyframes caret{50%{opacity:0}}")


def ill_bank(s, x, y, w, h, a):
    for i, (lab, bal) in enumerate((("ACC 1042", "₹ 48,200"), ("ACC 2077", "₹ 12,950"))):
        bx = x + 40 + i * 230
        s.rect(bx, y + 40, 180, 80, 12, "tile", "border")
        s.text(bx + 16, y + 66, lab, "monom", 11, "muted", ls=1)
        s.text(bx + 16, y + 100, bal.replace("₹ ", "INR "), "disp", 19, "fg")
    k = s.uid("tx")
    s.style(f".{k}{{animation:{k} 2.6s cubic-bezier(.6,0,.4,1) infinite}}"
            f"@keyframes {k}{{0%{{transform:translateX(0);opacity:0}}15%{{opacity:1}}85%{{opacity:1}}100%{{transform:translateX(64px);opacity:0}}}}")
    s.path(f"M{x + 226},{y + 80} H{x + 264}", "border", 2, extra='stroke-dasharray="4 4"')
    s.circle(x + 214, y + 80, 7, a, extra=f'class="{k}"')
    s.text(x + 245, y + 145, "DEBIT  =  CREDIT", "monom", 11, a, anchor="middle", ls=1.2)


def ill_sms(s, x, y, w, h, a):
    s.rect(x + 30, y + 22, 260, h - 44, 10, "tile", "border")
    for i in range(4):
        yy = y + 46 + i * 24
        s.rect(x + 44, yy, 40, 8, 4, "border")
        s.rect(x + 96, yy, 110 - i * 12, 8, 4, "border")
        s.rect(x + 220, yy, 50, 8, 4, a if i == 1 else "border")
    k = s.uid("hl")
    s.style(f".{k}{{animation:{k} 4s steps(1) infinite}}@keyframes {k}{{0%{{transform:translateY(0)}}25%{{transform:translateY(24px)}}"
            f"50%{{transform:translateY(48px)}}75%{{transform:translateY(72px)}}}}")
    s.rect(x + 34, y + 38, 252, 24, 6, a, extra=f'class="{k}" opacity=".18"')
    cx, cy, r = x + 360, y + h / 2, 42
    circ = 2 * math.pi * r
    s.circle(cx, cy, r, "none", "border", 12)
    k2 = s.uid("dn")
    s.style(f".{k2}{{stroke-dasharray:{circ:.1f};animation:{k2} 3s ease-in-out infinite alternate}}"
            f"@keyframes {k2}{{from{{stroke-dashoffset:{circ * .7:.1f}}}to{{stroke-dashoffset:{circ * .3:.1f}}}}}")
    s.add(f'<circle class="{k2}" cx="{cx}" cy="{cy}" r="{r}" transform="rotate(-90 {cx} {cy})" '
          f'style="fill:none;stroke:var(--{a});stroke-width:12;stroke-linecap:round"/>')


def ill_snapurl(s, x, y, w, h, a):
    k1, k2 = s.uid("lu"), s.uid("su")
    s.style(f".{k1}{{animation:{k1} 5s ease-in-out infinite}}@keyframes {k1}{{0%,35%{{opacity:1;transform:none}}"
            f"50%,90%{{opacity:.25;transform:translateY(-6px)}}100%{{opacity:1;transform:none}}}}"
            f".{k2}{{transform-box:fill-box;transform-origin:center;animation:{k2} 5s cubic-bezier(.2,.8,.2,1) infinite}}"
            f"@keyframes {k2}{{0%,40%{{opacity:0;transform:scale(.8)}}55%,90%{{opacity:1;transform:none}}100%{{opacity:0}}}}")
    long_url = "https://example.com/blog/2026/how-i-built..."
    s.add(f'<g class="{k1}">')
    s.rect(x + 30, y + 34, w - 60, 36, 18, "tile", "border")
    s.text(x + 48, y + 57, long_url, "mono", 12.5, "muted")
    s.add("</g>")
    s.add(f'<g class="{k2}">')
    sw = tw("monom", "snap.url/a8Kq", 17) + 70
    sx = x + (w - sw) / 2
    s.rect(sx, y + 92, sw, 46, 23, "tile", a, 2)
    s.path(f"M{sx + 22},{y + 119} l6,-6 a5,5 0 0 1 7,7 l-6,6 M{sx + 34},{y + 111} l-6,6 a5,5 0 0 1 -7,-7 l6,-6", a, 2.4)
    s.text(sx + 48, y + 121, "snap.url/a8Kq", "monom", 17, "fg")
    s.add("</g>")


def ill_cine(s, x, y, w, h, a):
    k = s.uid("reel")
    fw = 70
    s.style(f".{k}{{animation:{k} 3.2s cubic-bezier(.3,.9,.3,1) infinite}}"
            f"@keyframes {k}{{0%{{transform:translateX(0)}}70%,100%{{transform:translateX(-{fw * 5}px)}}}}")
    cid = s.uid("rc")
    s.defs.append(f'<clipPath id="{cid}"><rect x="{x + 20}" y="{y + 20}" width="{w - 40}" height="{h - 40}" rx="10"/></clipPath>')
    s.add(f'<g clip-path="url(#{cid})">')
    s.rect(x + 20, y + 20, w - 40, h - 40, 10, "tile", "border")
    s.add(f'<g class="{k}">')
    for i in range(14):
        fx = x + 40 + i * fw
        acc = ACCENTS[i % len(ACCENTS)]
        s.rect(fx, y + 50, fw - 12, h - 100, 6, acc, extra='opacity=".28"')
        for j in range(3):
            s.rect(fx + 6 + j * 18, y + 34, 10, 8, 2, "border")
            s.rect(fx + 6 + j * 18, y + h - 42, 10, 8, 2, "border")
    s.add("</g></g>")
    cx = x + w / 2
    s.rect(cx - 37, y + 44, 74, h - 88, 8, "none", a, 2.5)
    s.path(f"M{cx},{y + h / 2 - 12} l3.5,7.5 8,.9 -6,5.4 1.7,7.9 -7.2,-4.1 -7.2,4.1 1.7,-7.9 -6,-5.4 8,-.9 z", a, 1.5, fill=a)


def ill_gitatlas(s, x, y, w, h, a):
    ly1, ly2 = y + 62, y + 112
    s.path(f"M{x + 40},{ly1} H{x + w - 40}", "border", 3)
    s.path(f"M{x + 120},{ly1} C{x + 150},{ly1} {x + 150},{ly2} {x + 180},{ly2} H{x + 280} "
           f"C{x + 310},{ly2} {x + 310},{ly1} {x + 340},{ly1}", a, 3)
    for i, cx in enumerate((80, 120, 220, 340, 400)):
        cy = ly2 if cx == 220 else ly1
        col = a if cx in (220,) else "violet"
        dk = s.uid("dl")
        s.style(f".{dk}{{animation-delay:-{i * .4:.1f}s}}")
        s.circle(x + cx, cy, 8, "tile", col, 3, extra=f'class="pulse {dk}"')
    pill(s, x + 40, y + 128, "$ git reset --soft HEAD~1", fill="tile", col="soft", font="mono", size=12, h=28)


def ill_grab(s, x, y, w, h, a):
    s.rect(x + 40, y + 24, 130, 120, 14, a, extra='opacity=".22"')
    s.path(f"M{x + 96},{y + 66} L{x + 124},{y + 84} L{x + 96},{y + 102} Z", a, 2, fill=a)
    bx = x + 200
    s.text(bx, y + 56, "reel_2160p.mp4", "monom", 13, "soft")
    s.rect(bx, y + 70, 200, 10, 5, "border")
    k = s.uid("dl")
    s.style(f".{k}{{transform-box:fill-box;transform-origin:left;animation:{k} 3.4s ease-in-out infinite}}"
            f"@keyframes {k}{{0%{{transform:scaleX(.04)}}80%,100%{{transform:scaleX(1)}}}}")
    s.rect(bx, y + 70, 200, 10, 5, a, extra=f'class="{k}"')
    s.text(bx, y + 104, "audio.m4a", "monom", 13, "soft")
    s.rect(bx, y + 118, 200, 10, 5, "border")
    s.style(f".{k}b{{animation-delay:-1.2s}}")
    s.rect(bx, y + 118, 200, 10, 5, "violet", extra=f'class="{k} {k}b"')


def ill_disease(s, x, y, w, h, a):
    vals = [.35, .8, .5, .95, .4, .65, .3]
    base = y + h - 30
    for i, v in enumerate(vals):
        bx = x + 50 + i * 52
        k = s.uid("bar")
        s.style(f".{k}{{transform-box:fill-box;transform-origin:bottom;animation:{k} {2.4 + i * .2:.1f}s ease-in-out infinite alternate}}"
                f"@keyframes {k}{{from{{transform:scaleY(.35)}}to{{transform:scaleY(1)}}}}")
        s.rect(bx, base - 110 * v, 30, 110 * v, 6, a if i == 3 else "border", extra=f'class="{k}"')
    s.add(f'<line x1="{x + 40}" y1="{base}" x2="{x + w - 40}" y2="{base}" style="stroke:var(--border);stroke-width:1.5"/>')
    s.text(x + w - 44, y + 40, "SHAP", "monom", 12, a, anchor="end", ls=1.5)


def ill_shield(s, x, y, w, h, a):
    cx, cy, r = x + 110, y + h / 2, 52
    circ = 2 * math.pi * r
    k = s.uid("gr")
    s.style(f".{k}{{stroke-dasharray:{circ:.1f};animation:{k} 4s cubic-bezier(.2,.8,.2,1) infinite}}"
            f"@keyframes {k}{{0%{{stroke-dashoffset:{circ:.1f}}}60%,100%{{stroke-dashoffset:{circ * .08:.1f}}}}}")
    s.circle(cx, cy, r, "none", "border", 10)
    s.add(f'<circle class="{k}" cx="{cx}" cy="{cy}" r="{r}" transform="rotate(-90 {cx} {cy})" '
          f'style="fill:none;stroke:var(--{a});stroke-width:10;stroke-linecap:round"/>')
    s.text(cx, cy + 15, "A", "dispx", 44, "fg", anchor="middle")
    checks = ["TLS 1.3", "HSTS header", "Secure cookies", "SPF / DMARC"]
    for i, c in enumerate(checks):
        yy = y + 38 + i * 30
        k2 = s.uid("ck")
        s.style(f".{k2}{{animation:{k2} 4s infinite}}@keyframes {k2}{{0%,{10 + i * 12}%{{opacity:0}}{14 + i * 12}%,92%{{opacity:1}}100%{{opacity:0}}}}")
        s.add(f'<g class="{k2}">')
        s.circle(x + 216, yy, 9, "green")
        s.path(f"M{x + 211},{yy} l3.5,3.5 6.5,-7", "tile", 2.2)
        s.text(x + 234, yy + 5, c, "bodym", 14, "soft")
        s.add("</g>")


PROJECTS = [
    ("netscope", "NetScope", "Security", "cyan", ill_netscope,
     "Real-time network traffic analysis with a SOC-style dashboard, anomaly alerts and per-host risk scores.",
     "Python · Scapy · WebSockets", True),
    ("fsociety", "fsociety-web", "Portfolio", "pink", ill_fsociety,
     "A cinematic security portfolio with an interactive roadmap, in-browser utilities and CTF progress.",
     "HTML · CSS · JavaScript", True),
    ("industrust", "IndusTrust Bank", "Fintech", "green", ill_bank,
     "Spring Boot web bank with a double-entry ledger, row-locked atomic transfers and hashed PINs.",
     "Spring Boot · PostgreSQL · Docker", True),
    ("sms", "Student Management", "Education", "amber", ill_sms,
     "A legacy desktop app rebuilt as a cloud REST service with analytics, CSV export and CI.",
     "Spring Boot · Neon · Actions", True),
    ("snapurl", "SnapURL", "Utility", "violet", ill_snapurl,
     "Serverless URL shortener with custom aliases and self-expiring links on Turso edge SQLite.",
     "TypeScript · Express · Turso", True),
    ("cineroulette", "CineRoulette", "Discovery", "pink", ill_cine,
     "Pick a mood, spin the reel, get one explained movie pick, weighted per language and region.",
     "Next.js · NestJS · Prisma", True),
    ("gitatlas", "GitAtlas", "Dev tool", "amber", ill_gitatlas,
     "381 Git commands in plain English, 17 recovery playbooks and warnings on risky commands.",
     "HTML · CSS · JavaScript", True),
    ("grabmedia", "GrabMedia", "Media", "cyan", ill_grab,
     "Save public Instagram and YouTube media up to 2160p behind a hardened, rate-limited proxy.",
     "Node.js · Express · Helmet", True),
    ("disease", "Disease Prediction", "Machine learning", "green", ill_disease,
     "Predicts 41 diseases from 132 symptoms with a tree ensemble, SHAP explanations and PDF reports.",
     "FastAPI · scikit-learn · SHAP", True),
    ("siteshield", "SiteShield", "Security SaaS", "violet", ill_shield,
     "Grades a website's security posture A to F, re-scans on a schedule and alerts on regressions.",
     "React · FastAPI · Celery", False),
]


def build_card(slug, title, cat, a, ill, desc, stack, live):
    s = Svg(490, 360)
    s.style(PULSE)
    tile(s, a)
    # illustration well
    wx, wy, ww, wh = 14, 14, 462, 176
    cid = s.uid("well")
    s.defs.append(f'<clipPath id="{cid}"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="14"/></clipPath>')
    s.add(f'<g clip-path="url(#{cid})">')
    s.rect(wx, wy, ww, wh, 0, "tile2")
    s.rect(wx, wy, ww, wh, 0, a, extra='opacity=".07"')
    ill(s, wx, wy, ww, wh, a)
    s.add("</g>")
    s.rect(wx, wy, ww, wh, 14, "none", "border")
    # text
    s.text(30, 232, title, "disp", 23, "fg", ls=-.5)
    cw = tw("monom", cat.upper(), 10.5, 1.2) + 22
    s.rect(460 - cw, 214, cw, 24, 12, "tile2", "border")
    s.text(460 - cw + 11, 230, cat.upper(), "monom", 10.5, a, ls=1.2)
    for i, line in enumerate(wrap(desc, "body", 14.5, 430)[:2]):
        s.text(30, 262 + i * 22, line, "body", 14.5, "muted")
    s.add('<line x1="30" y1="306" x2="460" y2="306" style="stroke:var(--border)"/>')
    s.text(30, 334, stack, "mono", 12.5, "soft")
    if live:
        lab = "Open"
        s.text(440 - tw("bodym", lab, 14.5), 334, lab, "bodym", 14.5, a)
        arrow(s, 446, 324, a)
    else:
        lab = "In progress"
        lw = tw("bodym", lab, 14)
        s.circle(456 - lw - 14, 329, 4.5, "amber", extra='class="pulse"')
        s.text(456 - lw, 334, lab, "bodym", 14, "amber")
    s.save(f"card-{slug}.svg", f"{title} — {cat}")


# ── JOURNEY TIMELINE ─────────────────────────────────────────────────────
def build_journey():
    s = Svg(1000, 250)
    s.style(PULSE + RISE +
            ".fill{transform-box:fill-box;transform-origin:left;animation:fill 2.6s cubic-bezier(.2,.8,.2,1) .3s both}"
            "@keyframes fill{from{transform:scaleX(0)}to{transform:scaleX(1)}}")
    tile(s, "violet")
    steps = [("2023", "Started B.Tech CSE", "Silicon IT, Bhubaneswar", "violet"),
             ("Build", "First full-stack apps", "Java, JS, PHP, MySQL", "cyan"),
             ("Ship", "Live deployments", "Spring Boot, Node, FastAPI", "green"),
             ("Now", "Cybersecurity Intern", "Pentesting & web AppSec", "pink"),
             ("2027", "Graduate", "Build + break, full-time", "amber")]
    x0, x1, ly = 90, 910, 118
    s.rect(x0, ly - 2, x1 - x0, 4, 2, "border")
    s.grad("jg", [(0, "violet", 1), (.5, "green", 1), (1, "pink", 1)])
    now_x = x0 + (x1 - x0) * 3 / 4
    s.rect(x0, ly - 2, now_x - x0, 4, 2, "url(#jg)", extra='class="fill"')
    for i, (k, t, sub, acc) in enumerate(steps):
        cx = x0 + (x1 - x0) * i / 4
        done = i <= 3
        s.add(f'<g class="rise" style="animation-delay:{.3 + i * .35:.2f}s">')
        s.text(cx, 82, k.upper(), "monom", 12, acc if done else "muted", anchor="middle", ls=1.6)
        if i == 3:
            s.circle(cx, ly, 10, acc, extra='class="ring"')
        s.circle(cx, ly, 10, "tile", acc if done else "border", 3)
        if done:
            s.circle(cx, ly, 4, acc)
        s.text(cx, 162, t, "semi", 15.5, "fg" if done else "muted", anchor="middle")
        s.text(cx, 186, sub, "body", 13, "muted", anchor="middle")
        s.add("</g>")
    s.text(500, 226, "you are here: building, breaking and shipping", "mono", 12, "muted", anchor="middle")
    s.save("journey.svg", "Journey: started B.Tech CSE in 2023, first full-stack apps, live deployments, cybersecurity intern now, graduating 2027")


# ── CTA ──────────────────────────────────────────────────────────────────
def build_cta():
    s = Svg(1000, 250)
    s.style(RISE +
            ".bg1{animation:bg1 14s ease-in-out infinite alternate}@keyframes bg1{to{transform:translate(220px,30px)}}"
            ".bg2{animation:bg2 17s ease-in-out infinite alternate}@keyframes bg2{to{transform:translate(-200px,-20px)}}"
            ".nudge{animation:nudge 2.4s ease-in-out infinite}@keyframes nudge{50%{transform:translateX(4px)}}")
    s.defs.append('<filter id="cb" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="50"/></filter>')
    s.defs.append('<clipPath id="cc"><rect x="1" y="1" width="998" height="248" rx="26"/></clipPath>')
    s.add('<g clip-path="url(#cc)">')
    s.rect(0, 0, 1000, 250, 0, "tile")
    s.add('<g filter="url(#cb)" opacity=".5">')
    s.circle(200, 60, 130, "violet", extra='class="bg1"')
    s.circle(820, 220, 130, "pink", extra='class="bg2"')
    s.add("</g></g>")
    s.rect(1, 1, 998, 248, 26, "none", "border", 1.2)
    s.add('<g class="rise">')
    s.text(500, 70, "LET'S TALK", "monom", 12.5, "violet", anchor="middle", ls=2.2)
    s.text(500, 118, "Have an idea worth building,", "disp", 32, "fg", anchor="middle", ls=-.8)
    s.text(500, 156, "and worth securing?", "disp", 32, "fg", anchor="middle", ls=-.8)
    s.add("</g>")
    b1 = "Visit my portfolio"
    w1 = tw("semi", b1, 15) + 64
    b2 = "arman-portfolio.online"
    w2 = tw("mono", b2, 13.5) + 36
    total = w1 + 12 + w2
    bx = (1000 - total) / 2
    s.add('<g class="rise" style="animation-delay:.25s">')
    s.rect(bx, 182, w1, 44, 22, "fg")
    s.text(bx + 24, 209, b1, "semi", 15, "tile")
    s.add('<g class="nudge">')
    s.path(f"M{bx + w1 - 34},{204} h12 m-5,-5 l5,5 l-5,5", "tile", 2.2)
    s.add("</g>")
    s.rect(bx + w1 + 12, 182, w2, 44, 22, "tile2", "border")
    s.text(bx + w1 + 30, 208.5, b2, "mono", 13.5, "soft")
    s.add("</g>")
    s.save("cta.svg", "Have an idea worth building, and worth securing? Visit arman-portfolio.online")


# ── HOW I WORK: four principle tiles ─────────────────────────────────────
def _icon_build(s, x, y, a):
    s.path(f"M{x - 10},{y - 8} L{x - 20},{y} L{x - 10},{y + 8} M{x + 10},{y - 8} L{x + 20},{y} L{x + 10},{y + 8} "
           f"M{x + 4},{y - 13} L{x - 4},{y + 13}", a, 3)


def _icon_break(s, x, y, a):
    s.circle(x - 3, y - 3, 11, "none", a, 3)
    s.path(f"M{x + 5},{y + 5} L{x + 15},{y + 15}", a, 3.5)


def _icon_study(s, x, y, a):
    s.path(f"M{x - 18},{y - 10} L{x},{y - 17} L{x + 18},{y - 10} L{x},{y - 3} Z M{x - 11},{y - 7} V{y + 6} "
           f"C{x - 5},{y + 12} {x + 5},{y + 12} {x + 11},{y + 6} V{y - 7}", a, 2.6)


def _icon_rules(s, x, y, a):
    s.path(f"M{x},{y - 17} L{x + 15},{y - 10} V{y + 1} C{x + 15},{y + 10} {x + 8},{y + 15} {x},{y + 18} "
           f"C{x - 8},{y + 15} {x - 15},{y + 10} {x - 15},{y + 1} V{y - 10} Z", a, 2.6)
    s.path(f"M{x - 6},{y + 1} L{x - 1},{y + 6} L{x + 7},{y - 3}", a, 2.6)


PRINCIPLES = [
    ("build", "Build", "violet", _icon_build,
     ["Real auth, real data,", "CI and a public URL", "for everything I ship."]),
    ("break", "Break", "pink", _icon_break,
     ["Web AppSec practice on", "PortSwigger, TryHackMe", "and HackTheBox."]),
    ("study", "Study", "cyan", _icon_study,
     ["Memory forensics with", "Volatility3, plus breach", "case studies."]),
    ("rules", "Rules", "green", _icon_rules,
     ["Written authorization,", "responsible disclosure,", "scope respected."]),
]


def build_principle(slug, title, a, icon, lines):
    s = Svg(240, 230)
    s.style(RISE + ".bob{animation:bob 4s ease-in-out infinite}@keyframes bob{50%{transform:translateY(-4px)}}")
    tile(s, a)
    s.add('<g class="bob">')
    s.rect(24, 24, 56, 56, 16, "tile2", "border")
    icon(s, 52, 52, a)
    s.add("</g>")
    s.text(24, 122, title, "disp", 22, "fg", ls=-.4)
    s.add('<g class="rise" style="animation-delay:.15s">')
    for i, line in enumerate(lines):
        s.text(24, 152 + i * 21, line, "body", 13.5, "muted")
    s.add("</g>")
    s.save(f"work-{slug}.svg", f"{title}: {' '.join(lines)}")


HEADERS = [
    ("work", "Selected work", "Things I've shipped", "violet"),
    ("journey", "Journey", "How I got here", "pink"),
    ("how", "Principles", "How I work", "amber"),
    ("activity", "Activity", "Always committing", "green"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", default=os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))
    load_fonts(ap.parse_args().fonts)
    for p in PRINCIPLES:
        build_principle(*p)
    build_hero()
    build_now()
    build_modes()
    build_shipped()
    build_globe()
    build_degree()
    build_marquee()
    for h in HEADERS:
        build_header(*h)
    for p in PROJECTS:
        build_card(*p)
    build_journey()
    build_cta()


if __name__ == "__main__":
    main()
