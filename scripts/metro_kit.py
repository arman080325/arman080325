"""Shared drawing kit for the metro-style README components.

Everything here produces self-contained SVG: fonts are subset and embedded as
WOFF2 (GitHub blocks external resources inside <img> SVGs), and all motion is
disabled for viewers who prefer reduced motion.

Visual language
- five metro lines: 1 Build, 2 Server, 3 Data, 4 Ship, 5 Security (the circle line)
- boards and signs are always dark, like real station signage
- maps and panels follow the viewer's light or dark theme through CSS variables
- tickets are always printed on cream paper
"""
import base64
import io
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

# theme-adaptive tokens (used as var(--name))
TOKENS = {
    "dark": dict(card="#12161c", card2="#1a2029", border="#2b3442", fg="#f2f4f7", soft="#c5ccd6",
                 muted="#8a94a4", l1="#3b9dff", l2="#2ecc7a", l3="#ffc533", l4="#b07cff", l5="#ff5a52"),
    "light": dict(card="#ffffff", card2="#f2f4f7", border="#d5dae2", fg="#12161c", soft="#2c333d",
                  muted="#5a6473", l1="#0b6fe0", l2="#0d9a55", l3="#e0a100", l4="#7b45e6", l5="#e0322b"),
}
# fixed colours for always-dark signage
SIGN = "#0c0e11"
SIGN2 = "#181b20"
SIGN_BORDER = "#2c3038"
WHITE = "#f4f5f7"
GREY = "#8d95a3"
AMBER = "#ffc533"
GO = "#3ee07f"
LINE = {1: "#3b9dff", 2: "#2ecc7a", 3: "#ffc533", 4: "#b07cff", 5: "#ff5a52"}
LINE_NAME = {1: "BUILD", 2: "SERVER", 3: "DATA", 4: "SHIP", 5: "SECURITY"}
# ticket colours (cream paper needs deeper inks)
PAPER = "#f4ecd8"
PAPER2 = "#e9dfc6"
INK = "#1b1d21"
INK2 = "#5b5648"
TICKET_LINE = {1: "#0b6fe0", 2: "#0d8a4d", 3: "#b97f00", 4: "#7b45e6", 5: "#d62f28"}

FONT_FILES = {
    "sign": "overpass-latin-700-normal.woff",
    "signx": "overpass-latin-900-normal.woff",
    "mono": "overpass-mono-latin-500-normal.woff",
    "monob": "overpass-mono-latin-700-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}
_metrics = {}


def tw(key, text, size, ls=0):
    if key not in _metrics:
        f = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm + ls * len(text)


def _font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []  # no kerning or contextual rules: signage is set letter by letter
    font = TTFont(os.path.join(FONT_DIR, FONT_FILES[key]))
    sub = subset.Subsetter(opts)
    sub.populate(text="".join(sorted(set(chars + " "))))
    sub.subset(font)
    # Overpass classifies the middle dot as a combining mark, which makes browsers give it
    # zero width. Signage needs no shaping tables, so drop them.
    for table in ("GDEF", "GPOS", "GSUB"):
        if table in font:
            del font[table]
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
    """A token name becomes a CSS variable; hex colours and url() pass through."""
    return c if c.startswith(("#", "url", "none")) else f"var(--{c})"


BASE_CSS = (
    ".pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.3}}"
    ".blink{animation:blink 1.2s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    ".fi{opacity:0;animation:fi .7s ease-out var(--d,0s) forwards}@keyframes fi{to{opacity:1}}"
    ".grow{transform-box:fill-box;transform-origin:left;animation:grow 1.3s cubic-bezier(.2,.8,.2,1) var(--d,0s) both}"
    "@keyframes grow{from{transform:scaleX(0)}}"
)
# With motion switched off, everything must still be visible in its final state.
REDUCED = ("@media (prefers-reduced-motion:reduce){*{animation:none!important}"
           ".fi{opacity:1!important}.a,.b{opacity:0!important}.cl{opacity:var(--o,1)!important}"
           ".dr{stroke-dashoffset:0!important}}")


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [BASE_CSS], []
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, font, size, fill="fg", anchor=None, ls=0, cls="", d=None):
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        delay = f";--d:{d}s" if d is not None else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}"'
                          f'{a}{l}{c} style="fill:{paint(fill)}{delay}">{escape(s)}</text>')

    def rect(self, x, y, w, h, rx=0, fill="card", stroke=None, sw=1, cls="", extra=""):
        st = f"fill:{paint(fill)}" + (f";stroke:{paint(stroke)};stroke-width:{sw}" if stroke else "")
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}"{c} '
                          f'style="{st}" {extra}/>')

    def circle(self, cx, cy, r, fill="fg", stroke=None, sw=1, cls="", extra=""):
        st = f"fill:{paint(fill)}" + (f";stroke:{paint(stroke)};stroke-width:{sw}" if stroke else "")
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}"{c} style="{st}" {extra}/>')

    def path(self, d, stroke="fg", sw=2, fill="none", cls="", cap="round", extra=""):
        c = f' class="{cls}"' if cls else ""
        self.parts.append(f'<path d="{d}"{c} style="fill:{paint(fill)};stroke:{paint(stroke)};stroke-width:{sw};'
                          f'stroke-linecap:{cap};stroke-linejoin:round" {extra}/>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def save(self, path, title):
        faces = "".join(_font_face(k, v) for k, v in self.chars.items() if v)
        var = lambda t: ";".join(f"--{k}:{v}" for k, v in TOKENS[t].items())
        css = (faces + f"svg{{{var('dark')}}}@media (prefers-color-scheme:light){{svg{{{var('light')}}}}}"
               + "".join(self.css) + REDUCED)
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)


# ── signage pieces ───────────────────────────────────────────────────────
def bullet(s, cx, cy, n, size=22, color=None, text_color=None):
    """Line bullet: a rounded square with the line number."""
    col = color or LINE[n]
    s.rect(cx - size / 2, cy - size / 2, size, size, size * .28, col)
    tc = text_color or ("#14161a" if n == 3 else "#ffffff")
    s.text(cx, cy + size * .25, str(n), "signx", size * .68, tc, anchor="middle")


def arrow_right(s, x, y, color, size=10, sw=2.4):
    s.path(f"M{x},{y} h{size * 1.6} m-{size * .7},-{size * .7} l{size * .7},{size * .7} l-{size * .7},{size * .7}",
           color, sw)


def arrow_ne(s, x, y, color, size=9, sw=2.2):
    s.path(f"M{x},{y + size} L{x + size},{y} M{x + size * .25},{y} H{x + size} V{y + size * .75}", color, sw)


def panel(s, radius=14):
    """Theme-adaptive panel background."""
    s.rect(.75, .75, s.w - 1.5, s.h - 1.5, radius, "card", "border", 1.5)


def sign_plate(s, radius=12):
    """Always-dark signage plate."""
    s.rect(0, 0, s.w, s.h, radius, SIGN)
    s.rect(.75, .75, s.w - 1.5, s.h - 1.5, radius, "none", SIGN_BORDER, 1.5)
