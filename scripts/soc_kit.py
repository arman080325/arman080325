"""Shared drawing kit for the SOC-wall README components.

Everything here produces self-contained SVG: fonts are subset and embedded as
WOFF2 (GitHub blocks external resources inside <img> SVGs), and all motion is
disabled for viewers who prefer reduced motion, with every element left in its
final, visible state.

Visual language: the dark monitoring wall of a security operations centre.
Teal means nominal, blue is information, amber is a warning, red is an alert.
The wall is always dark, on light and dark GitHub themes alike.
"""
import base64
import io
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

BG = "#080d12"        # wall
PANEL = "#0d141b"     # panel fill
PANEL2 = "#121b24"    # raised surfaces inside a panel
BORDER = "#1d2a36"
GRID = "#16212c"
TEXT = "#dbe4ee"
SOFT = "#a9b7c6"
MUTED = "#6c7d8f"
DIM = "#3a4a5a"
TEAL = "#2dd4bf"      # nominal
BLUE = "#38bdf8"      # information
AMBER = "#fbbf24"     # warning
RED = "#f87171"       # alert
VIOLET = "#a78bfa"

FONT_FILES = {
    "ui": "inter-latin-500-normal.woff",
    "uib": "inter-latin-600-normal.woff",
    "mono": "jetbrains-mono-latin-400-normal.woff",
    "monom": "jetbrains-mono-latin-500-normal.woff",
    "monob": "jetbrains-mono-latin-700-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}
_metrics = {}


def tw(key, text, size, ls=0):
    if key not in _metrics:
        f = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm + ls * len(text)


def fit(text, key, size, max_w, ls=0):
    """Truncate text with an ellipsis so it fits max_w."""
    if tw(key, text, size, ls) <= max_w:
        return text
    while text and tw(key, text + "...", size, ls) > max_w:
        text = text[:-1]
    return text.rstrip() + "..."


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


def _font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    opts.notdef_outline = True
    font = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
    cmap = font.getBestCmap()
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(c for c in set(chars + " ?") if ord(c) in cmap)))
    sub.subset(font)
    for table in ("GDEF", "GPOS", "GSUB"):  # no shaping needed; avoids zero-width "mark" glyphs
        if table in font:
            del font[table]
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{FAMILY[key]};src:url(data:font/woff2;base64,{data})}}"


BASE_CSS = (
    ".pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.25}}"
    ".blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    ".fi{opacity:0;animation:fi .6s ease-out var(--d,0s) forwards}@keyframes fi{to{opacity:1}}"
    ".grow{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}"
    "@keyframes grow{from{transform:scaleX(0)}}"
    ".rise{transform-box:fill-box;transform-origin:bottom;animation:rise .9s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}"
    "@keyframes rise{from{transform:scaleY(0)}}"
    ".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr var(--t,1.6s) cubic-bezier(.4,0,.2,1) var(--d,0s) forwards}"
    "@keyframes dr{to{stroke-dashoffset:0}}"
    ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out var(--d,0s) infinite}"
    "@keyframes ping{from{transform:scale(.4);opacity:.9}to{transform:scale(3);opacity:0}}"
)
# With motion switched off, everything must still be visible in its final state.
REDUCED = ("@media (prefers-reduced-motion:reduce){*{animation:none!important}"
           ".fi{opacity:1!important}.dr{stroke-dashoffset:0!important}.ping{opacity:0!important}}")


def clean(text):
    """Make arbitrary text (commit messages, repo names) safe to draw: one line, printable."""
    text = " ".join(str(text).split())
    return "".join(c if c.isprintable() else "?" for c in text)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [BASE_CSS], []
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, font, size, fill=TEXT, anchor=None, ls=0, cls="", d=None, op=None):
        s = clean(s)
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="--d:{d}s"' if d is not None else ""
        o = f' opacity="{op}"' if op is not None else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}"{a}{l}{c}{st}{o}>{escape(s)}</text>')

    def rect(self, x, y, w, h, rx=0, fill=PANEL, stroke=None, sw=1, cls="", d=None, op=None):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        c = f' class="{cls}"' if cls else ""
        dl = f' style="--d:{d}s"' if d is not None else ""
        o = f' opacity="{op}"' if op is not None else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" rx="{rx}" '
                          f'fill="{fill}"{st}{c}{dl}{o}/>')

    def circle(self, cx, cy, r, fill=TEXT, stroke=None, sw=1, cls="", d=None, op=None):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        c = f' class="{cls}"' if cls else ""
        dl = f' style="--d:{d}s"' if d is not None else ""
        o = f' opacity="{op}"' if op is not None else ""
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}"{st}{c}{dl}{o}/>')

    def path(self, d, stroke=TEXT, sw=1.5, fill="none", cls="", delay=None, t=None, cap="round", op=None, dash=None):
        c = f' class="{cls}"' if cls else ""
        style = []
        if delay is not None:
            style.append(f"--d:{delay}s")
        if t is not None:
            style.append(f"--t:{t}s")
        st = f' style="{";".join(style)}"' if style else ""
        pl = ' pathLength="1"' if "dr" in cls.split() else ""
        o = f' opacity="{op}"' if op is not None else ""
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}" stroke-linecap="{cap}" '
                          f'stroke-linejoin="round"{c}{st}{pl}{o}{da}/>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def save(self, path, title):
        faces = "".join(_font_face(k, v) for k, v in self.chars.items() if v)
        css = faces + "".join(self.css) + REDUCED
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        title = clean(title)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title, {chr(34): "&quot;"})}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)


# ── wall pieces ──────────────────────────────────────────────────────────
def wall(s, radius=12):
    """Panel background with a faint grid and corner ticks."""
    gid = s.uid("g")
    s.defs.append(f'<pattern id="{gid}" width="24" height="24" patternUnits="userSpaceOnUse">'
                  f'<path d="M24,0 H0 V24" fill="none" stroke="{GRID}" stroke-width="1"/></pattern>'
                  f'<clipPath id="{gid}c"><rect width="{s.w}" height="{s.h}" rx="{radius}"/></clipPath>')
    s.add(f'<g clip-path="url(#{gid}c)"><rect width="{s.w}" height="{s.h}" fill="{PANEL}"/>'
          f'<rect width="{s.w}" height="{s.h}" fill="url(#{gid})" opacity=".55"/></g>')
    s.rect(.75, .75, s.w - 1.5, s.h - 1.5, radius, "none", BORDER, 1.5)
    t = 14
    for (x, y, dx, dy) in ((8, 8, 1, 1), (s.w - 8, 8, -1, 1), (8, s.h - 8, 1, -1), (s.w - 8, s.h - 8, -1, -1)):
        s.path(f"M{x + dx * t},{y} H{x} V{y + dy * t}", DIM, 1.5)


def header(s, title, right=None, color=TEAL, y=34, lamp=True):
    """Panel title row: accent bar, title, optional right-hand status."""
    s.rect(22, y - 13, 3, 16, 1.5, color)
    s.text(34, y, title, "monob", 12, TEXT, ls=1.6)
    if right:
        rw = tw("mono", right, 10.5, 1)
        if lamp:
            s.circle(s.w - 26 - rw - 12, y - 4, 3.5, color, cls="pulse")
        s.text(s.w - 26, y, right, "mono", 10.5, MUTED, anchor="end", ls=1)
    s.path(f"M22,{y + 14} H{s.w - 22}", BORDER, 1)


def lamp(s, x, y, color=TEAL, r=4.5):
    s.circle(x, y, r, color, cls="ping")
    s.circle(x, y, r, color)


def chip(s, x, y, label, color=TEAL, size=10, h=20):
    w = tw("monom", label, size, .4) + 16
    s.rect(x, y, w, h, 4, PANEL2, color, 1, op=None)
    s.text(x + 8, y + h / 2 + size * .36, label, "monom", size, color, ls=.4)
    return w


def arrow_ne(s, x, y, color, size=8, sw=1.8):
    s.path(f"M{x},{y + size} L{x + size},{y} M{x + size * .25},{y} H{x + size} V{y + size * .75}", color, sw)
