"""Shared drawing kit for the "Secure by Design" README components.

Everything here produces self-contained SVG: fonts are subset and embedded as
WOFF2 (GitHub blocks external resources inside <img> SVGs). All motion is
disabled for viewers who prefer reduced motion, leaving every element in its
final, visible state.

Visual language: one product, seen from both sides.
  violet = build (what I write)   green = verified / fixed   red = vulnerability
The panels are dark, like a code editor, on light and dark GitHub themes alike.
"""
import base64
import io
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

BG = "#0b0d14"        # editor background
PANEL = "#10131c"     # card fill
PANEL2 = "#161a26"    # raised surfaces
LINEBG = "#1b2030"    # highlighted rows
BORDER = "#252b3b"
TEXT = "#e6e8f0"
SOFT = "#b4b9c9"
MUTED = "#767d93"
DIM = "#40465a"
BUILD = "#8b7bff"     # violet: build
BUILD2 = "#b3a8ff"
SAFE = "#34d399"      # green: verified, fixed
VULN = "#fb7185"      # red: vulnerability
WARN = "#fbbf24"
CYAN = "#67e8f9"
# code syntax colours
KW = "#c792ea"
TY = "#82aaff"
STR = "#c3e88d"
FN = "#ffcb6b"
CM = "#676e95"

FONT_FILES = {
    "head": "space-grotesk-latin-700-normal.woff",
    "body": "inter-latin-400-normal.woff",
    "bodym": "inter-latin-500-normal.woff",
    "mono": "jetbrains-mono-latin-400-normal.woff",
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


def clean(text):
    """Make arbitrary text (commit messages, repo names) safe to draw: one line, printable."""
    text = " ".join(str(text).split())
    return "".join(c if c.isprintable() else "?" for c in text)


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
    ".pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.3}}"
    ".blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    ".fi{opacity:0;animation:fi .6s ease-out var(--d,0s) forwards}@keyframes fi{to{opacity:1}}"
    ".grow{transform-box:fill-box;transform-origin:left;animation:grow 1.2s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}"
    "@keyframes grow{from{transform:scaleX(0)}}"
    ".rise{transform-box:fill-box;transform-origin:bottom;animation:rise .9s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}"
    "@keyframes rise{from{transform:scaleY(0)}}"
    ".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr var(--t,1.4s) cubic-bezier(.4,0,.2,1) var(--d,0s) forwards}"
    "@keyframes dr{to{stroke-dashoffset:0}}"
    ".ping{transform-box:fill-box;transform-origin:center;animation:ping 2.4s ease-out var(--d,0s) infinite}"
    "@keyframes ping{from{transform:scale(.5);opacity:.8}to{transform:scale(2.8);opacity:0}}"
)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [BASE_CSS], []
        self.reduced = ""   # extra rules for prefers-reduced-motion
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, font, size, fill=TEXT, anchor=None, ls=0, cls="", d=None, op=None, deco=None):
        s = clean(s)
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="--d:{d}s"' if d is not None else ""
        o = f' opacity="{op}"' if op is not None else ""
        dc = f' text-decoration="{deco}"' if deco else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}" xml:space="preserve"{a}{l}{c}{st}{o}{dc}>{escape(s)}</text>')

    def spans(self, x, y, segs, size, font="mono", cls=""):
        """One line made of (text, colour) segments, in a monospaced font."""
        out, cx = [], x
        for t, col in segs:
            t = "".join(c if c.isprintable() else "?" for c in t)  # keep spaces: code indentation matters
            self.chars[font] += t
            out.append(f'<tspan x="{cx:.1f}" fill="{col}">{escape(t)}</tspan>')
            cx += tw(font, t, size)
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<text y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" xml:space="preserve"{c}>'
                          f'{"".join(out)}</text>')
        return cx

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
        reduced = ("@media (prefers-reduced-motion:reduce){*{animation:none!important}"
                   ".fi{opacity:1!important}.dr{stroke-dashoffset:0!important}.ping{opacity:0!important}"
                   + self.reduced + "}")
        css = faces + "".join(self.css) + reduced
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        title = clean(title)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title, {chr(34): "&quot;"})}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)


# ── shared pieces ────────────────────────────────────────────────────────
def card(s, radius=14, glow=BUILD):
    """Dark card with a faint dot grid and a soft corner glow."""
    gid = s.uid("g")
    s.defs.append(f'<pattern id="{gid}" width="18" height="18" patternUnits="userSpaceOnUse">'
                  f'<circle cx="1.5" cy="1.5" r="1" fill="{BORDER}"/></pattern>'
                  f'<radialGradient id="{gid}r" cx="1" cy="0" r="1"><stop offset="0" stop-color="{glow}" '
                  f'stop-opacity=".16"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>'
                  f'<clipPath id="{gid}c"><rect width="{s.w}" height="{s.h}" rx="{radius}"/></clipPath>')
    s.add(f'<g clip-path="url(#{gid}c)"><rect width="{s.w}" height="{s.h}" fill="{PANEL}"/>'
          f'<rect width="{s.w}" height="{s.h}" fill="url(#{gid})" opacity=".6"/>'
          f'<rect width="{s.w}" height="{s.h}" fill="url(#{gid}r)"/></g>')
    s.rect(.75, .75, s.w - 1.5, s.h - 1.5, radius, "none", BORDER, 1.5)


def window_bar(s, x, y, w, title, h=36, radius=14):
    """Editor-style title bar with three lights."""
    s.add(f'<path d="M{x},{y + h} V{y + radius} Q{x},{y} {x + radius},{y} H{x + w - radius} Q{x + w},{y} {x + w},{y + radius} '
          f'V{y + h} Z" fill="{PANEL2}"/>')
    s.path(f"M{x},{y + h} H{x + w}", BORDER, 1)
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        s.circle(x + 20 + i * 18, y + h / 2, 5.5, c)
    s.text(x + w / 2, y + h / 2 + 4.5, title, "mono", 11.5, MUTED, anchor="middle")


def check(s, x, y, color=SAFE, size=9, sw=2, cls="", delay=None):
    s.path(f"M{x},{y} l{size * .38},{size * .38} l{size * .72},-{size * .78}", color, sw, cls=cls, delay=delay)


def warn_icon(s, x, y, color=VULN, size=14):
    h = size * .87
    s.path(f"M{x},{y - h / 2} L{x + size / 2},{y + h / 2} H{x - size / 2} Z", color, 1.6, fill="none")
    s.path(f"M{x},{y - h * .12} V{y + h * .16}", color, 1.8)
    s.circle(x, y + h * .33, 1.1, color)


def arrow_ne(s, x, y, color, size=8, sw=1.8):
    s.path(f"M{x},{y + size} L{x + size},{y} M{x + size * .25},{y} H{x + size} V{y + size * .75}", color, sw)


def chip(s, x, y, label, color, size=10.5, h=22, font="mono", fill=PANEL2):
    w = tw(font, label, size) + 18
    s.rect(x, y, w, h, h / 2, fill, color, 1)
    s.text(x + 9, y + h / 2 + size * .36, label, font, size, color)
    return w


def section_title(s, kicker, title, color=BUILD, x=28, y=40):
    s.text(x, y, kicker, "monob", 11, color, ls=2)
    s.text(x, y + 34, title, "head", 28, TEXT, ls=-.5)
