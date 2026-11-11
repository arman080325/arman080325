"""Shared drawing kit for the blueprint-style README components.

Everything here produces self-contained SVG: fonts are subset and embedded as
WOFF2 (GitHub blocks external resources inside <img> SVGs), lines "draw
themselves" with CSS stroke animations, and all motion is disabled for viewers
who prefer reduced motion.

Visual language
- white ink on blueprint blue  = the builder (drawings, schematics)
- red markup and revision clouds = the breaker (security review notes)
"""
import base64
import io
import math
import os
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.join(os.path.dirname(__file__), "..")
FONT_DIR = os.path.join(ROOT, "assets", "fonts")

# ── palette ──────────────────────────────────────────────────────────────
PAPER = "#0b2f6b"      # blueprint blue
PAPER2 = "#0d3779"     # panels on the paper
GRID = "#2a5aa6"       # minor grid
GRID2 = "#3a6cbc"      # major grid
INK = "#eaf2ff"        # white ink
INK2 = "#b9cff2"       # secondary ink
DIM = "#86a7da"        # dimension lines, small labels
CYAN = "#7fdcff"       # highlights
RED = "#ff6b5e"        # redline: security markup
AMBER = "#ffd166"      # stamps, warnings
GREEN = "#7dffb2"      # status: live

FONT_FILES = {
    "mono": "ibm-plex-mono-latin-400-normal.woff",
    "monom": "ibm-plex-mono-latin-500-normal.woff",
    "monob": "ibm-plex-mono-latin-600-normal.woff",
    "cond": "ibm-plex-sans-condensed-latin-500-normal.woff",
    "condb": "ibm-plex-sans-condensed-latin-700-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}
_metrics = {}


def _font_path(key):
    return os.path.join(FONT_DIR, FONT_FILES[key])


def tw(key, text, size, ls=0):
    if key not in _metrics:
        f = TTFont(_font_path(key))
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm + ls * len(text)


def _font_face(key, chars):
    opts = subset.Options()
    opts.flavor = "woff2"
    font = TTFont(_font_path(key))
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


BASE_CSS = (
    # draw-in for any element with pathLength="1"
    ".dr{stroke-dasharray:1;stroke-dashoffset:1;animation:dr var(--t,1.4s) cubic-bezier(.45,.05,.25,1) var(--d,0s) forwards}"
    "@keyframes dr{to{stroke-dashoffset:0}}"
    ".fi{opacity:0;animation:fi .6s ease-out var(--d,0s) forwards}@keyframes fi{to{opacity:1}}"
    ".blink{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
    ".pulse{animation:pulse 2.2s ease-in-out infinite}@keyframes pulse{50%{opacity:.35}}"
)


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [BASE_CSS], []
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    # primitives ----------------------------------------------------------
    def text(self, x, y, s, font, size, fill=INK, anchor=None, ls=0, cls="", d=None, extra=""):
        self.chars[font] += s
        a = f' text-anchor="{anchor}"' if anchor else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="--d:{d}s"' if d is not None else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}"{a}{l}{c}{st} {extra}>{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, color=INK, w=1.4, draw=None, dash=None, extra=""):
        cls = f' class="dr" pathLength="1" style="--d:{draw}s"' if draw is not None else ""
        da = f' stroke-dasharray="{dash}"' if dash and draw is None else ""
        self.parts.append(f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{color}" stroke-width="{w}" '
                          f'fill="none" stroke-linecap="round"{cls}{da} {extra}/>')

    def path(self, d, color=INK, w=1.6, fill="none", draw=None, t=None, extra="", cap="round"):
        cls = ""
        if draw is not None:
            tt = f";--t:{t}s" if t else ""
            cls = f' class="dr" pathLength="1" style="--d:{draw}s{tt}"'
        self.parts.append(f'<path d="{d}" stroke="{color}" stroke-width="{w}" fill="{fill}" '
                          f'stroke-linecap="{cap}" stroke-linejoin="round"{cls} {extra}/>')

    def box(self, x, y, w, h, color=INK, sw=1.4, fill="none", draw=None, r=0, extra=""):
        if r:
            d = (f"M{x + r},{y} H{x + w - r} Q{x + w},{y} {x + w},{y + r} V{y + h - r} Q{x + w},{y + h} {x + w - r},{y + h} "
                 f"H{x + r} Q{x},{y + h} {x},{y + h - r} V{y + r} Q{x},{y} {x + r},{y} Z")
        else:
            d = f"M{x},{y} H{x + w} V{y + h} H{x} Z"
        self.path(d, color, sw, fill, draw, extra=extra)

    def circle(self, cx, cy, r, color=INK, sw=1.4, fill="none", extra=""):
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" stroke="{color}" stroke-width="{sw}" '
                          f'fill="{fill}" {extra}/>')

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def save(self, path, title):
        faces = "".join(_font_face(k, v) for k, v in self.chars.items() if v)
        css = faces + "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important;" \
                                          "stroke-dashoffset:0!important;opacity:1!important}}"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)


# ── drawing-sheet elements ───────────────────────────────────────────────
def paper(s, radius=10):
    """Blueprint paper: blue sheet with a minor/major grid."""
    gid = s.uid("grid")
    s.defs.append(
        f'<pattern id="{gid}m" width="10" height="10" patternUnits="userSpaceOnUse">'
        f'<path d="M10,0 H0 V10" fill="none" stroke="{GRID}" stroke-width=".5" opacity=".55"/></pattern>'
        f'<pattern id="{gid}" width="50" height="50" patternUnits="userSpaceOnUse">'
        f'<rect width="50" height="50" fill="url(#{gid}m)"/>'
        f'<path d="M50,0 H0 V50" fill="none" stroke="{GRID2}" stroke-width=".9" opacity=".6"/></pattern>'
        f'<radialGradient id="{gid}v" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity=".28"/></radialGradient>')
    s.add(f'<rect width="{s.w}" height="{s.h}" rx="{radius}" fill="{PAPER}"/>')
    s.add(f'<rect width="{s.w}" height="{s.h}" rx="{radius}" fill="url(#{gid})"/>')
    s.add(f'<rect width="{s.w}" height="{s.h}" rx="{radius}" fill="url(#{gid}v)"/>')


def frame(s, inset=12, zones=True):
    """Double-line drawing frame with zone markers along the edges."""
    w, h = s.w, s.h
    s.box(inset, inset, w - 2 * inset, h - 2 * inset, INK2, 1.2)
    s.box(inset + 8, inset + 8, w - 2 * inset - 16, h - 2 * inset - 16, INK, 1.6)
    if not zones:
        return
    cols = max(2, int((w - 2 * inset) // 160))
    for i in range(cols):
        x = inset + 8 + (w - 2 * inset - 16) * (i + .5) / cols
        s.text(x, inset + 6.5, str(i + 1), "mono", 7.5, DIM, anchor="middle")
        s.text(x, h - inset - 1.5, str(i + 1), "mono", 7.5, DIM, anchor="middle")
        if i:
            xx = inset + 8 + (w - 2 * inset - 16) * i / cols
            s.line(xx, inset, xx, inset + 8, INK2, .8)
            s.line(xx, h - inset - 8, xx, h - inset, INK2, .8)
    rows = max(2, int((h - 2 * inset) // 120))
    for j in range(rows):
        y = inset + 8 + (h - 2 * inset - 16) * (j + .5) / rows
        s.text(inset + 4, y + 3, "ABCDEFGH"[j], "mono", 7.5, DIM, anchor="middle")
        s.text(w - inset - 4, y + 3, "ABCDEFGH"[j], "mono", 7.5, DIM, anchor="middle")
        if j:
            yy = inset + 8 + (h - 2 * inset - 16) * j / rows
            s.line(inset, yy, inset + 8, yy, INK2, .8)
            s.line(w - inset - 8, yy, w - inset, yy, INK2, .8)


def arrowhead(s, x, y, angle, color=INK, size=8, fill=True):
    a = math.radians(angle)
    p1 = (x - size * math.cos(a - .38), y - size * math.sin(a - .38))
    p2 = (x - size * math.cos(a + .38), y - size * math.sin(a + .38))
    f = color if fill else "none"
    s.add(f'<path d="M{x:.1f},{y:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{f}" stroke="{color}" '
          f'stroke-width="1" stroke-linejoin="round"/>')


def arrow(s, x1, y1, x2, y2, color=INK, w=1.5, draw=None, size=8):
    s.line(x1, y1, x2, y2, color, w, draw)
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if draw is not None:
        s.add(f'<g class="fi" style="--d:{draw + 1.1:.2f}s">')
        arrowhead(s, x2, y2, ang, color, size)
        s.add("</g>")
    else:
        arrowhead(s, x2, y2, ang, color, size)


def dimension(s, x1, x2, y, label, color=DIM, draw=None, ext=10, font="mono", size=11, label_color=None):
    """Horizontal dimension line with extension lines, arrowheads and a label."""
    s.line(x1, y - ext, x1, y + 4, color, .9)
    s.line(x2, y - ext, x2, y + 4, color, .9)
    lw = tw(font, label, size) + 14
    mid = (x1 + x2) / 2
    s.line(x1 + 1, y, mid - lw / 2, y, color, 1, draw)
    s.line(mid + lw / 2, y, x2 - 1, y, color, 1, draw)
    arrowhead(s, x1, y, 180, color, 7)
    arrowhead(s, x2, y, 0, color, 7)
    s.text(mid, y + size * .36, label, font, size, label_color or INK2, anchor="middle",
           cls="fi" if draw is not None else "", d=(draw + .6) if draw is not None else None)


def vdimension(s, x, y1, y2, label, color=DIM, size=10.5):
    s.line(x - 4, y1, x + 10, y1, color, .9)
    s.line(x - 4, y2, x + 10, y2, color, .9)
    s.line(x + 6, y1 + 1, x + 6, y2 - 1, color, 1)
    arrowhead(s, x + 6, y1, -90, color, 6)
    arrowhead(s, x + 6, y2, 90, color, 6)
    mid = (y1 + y2) / 2
    s.add(f'<g transform="rotate(-90 {x + 2:.1f} {mid:.1f})">')
    s.text(x + 2, mid, label, "mono", size, INK2, anchor="middle")
    s.add("</g>")


def rev_cloud(x, y, w, h, r=7):
    """Scalloped 'revision cloud' outline used to mark up changes."""
    pts = []

    def edge(x1, y1, x2, y2):
        length = math.hypot(x2 - x1, y2 - y1)
        n = max(1, round(length / (2 * r)))
        for i in range(1, n + 1):
            pts.append((x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n, length / n / 2))

    edge(x, y, x + w, y)
    edge(x + w, y, x + w, y + h)
    edge(x + w, y + h, x, y + h)
    edge(x, y + h, x, y)
    d = f"M{x:.1f},{y:.1f} " + " ".join(f"A{rr:.1f},{rr:.1f} 0 0 1 {px:.1f},{py:.1f}" for px, py, rr in pts)
    return d


def redline(s, x, y, lines, draw=0.0, size=11.5, pad=10, leader=None):
    """A red markup note inside a revision cloud, with an optional leader line."""
    w = max(tw("monom", t, size) for t in lines) + 2 * pad
    h = len(lines) * (size + 5) + 2 * pad - 5
    if leader:
        lx, ly = leader
        sx = x if lx < x else x + w
        sy = min(max(ly, y), y + h)
        s.line(sx, sy, lx, ly, RED, 1.3, draw)
        s.circle(lx, ly, 2.6, RED, 1, RED, extra=f'class="fi" style="--d:{draw:.2f}s"')
    s.path(rev_cloud(x, y, w, h), RED, 1.6, draw=draw + .3, t=1.6)
    for i, t in enumerate(lines):
        s.text(x + pad, y + pad + size * .85 + i * (size + 5), t, "monom", size, RED, cls="fi", d=draw + 1.0)
    return w, h


def section_bubble(s, cx, cy, top, bottom, r=22, color=INK):
    s.circle(cx, cy, r, color, 1.6)
    s.line(cx - r, cy, cx + r, cy, color, 1.2)
    s.text(cx, cy - 6, top, "monob", 12, color, anchor="middle")
    s.text(cx, cy + 15, bottom, "mono", 10, DIM, anchor="middle")


def stamp(s, cx, cy, lines, color=RED, angle=-8, delay=0.0, size=15):
    w = max(tw("condb", t, size, 2) for t in lines) + 36
    h = len(lines) * (size + 6) + 18
    k = s.uid("st")
    s.style(f".{k}{{opacity:0;transform-box:fill-box;transform-origin:center;"
            f"animation:{k} .5s cubic-bezier(.2,1.6,.4,1) {delay}s forwards}}"
            f"@keyframes {k}{{from{{opacity:0;transform:scale(1.8)}}to{{opacity:.92;transform:scale(1)}}}}")
    s.add(f'<g class="{k}"><g transform="rotate({angle} {cx} {cy})">')
    s.box(cx - w / 2, cy - h / 2, w, h, color, 2.6, r=6)
    s.box(cx - w / 2 + 4, cy - h / 2 + 4, w - 8, h - 8, color, 1, r=4)
    for i, t in enumerate(lines):
        s.text(cx, cy - h / 2 + 9 + size + i * (size + 6), t, "condb", size, color, anchor="middle", ls=2)
    s.add("</g></g>")
