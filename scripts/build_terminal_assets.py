#!/usr/bin/env python3
"""Build the animated terminal-style SVG components for the profile README.

Every SVG is self-contained (fonts are subset and embedded as WOFF2), because
GitHub blocks external resources inside SVGs shown with <img>. Animations are
pure CSS, loop gently, and switch off for viewers who prefer reduced motion.

Usage:
    pip install fonttools brotli
    npm pack @fontsource/fira-code @fontsource/space-grotesk   # then extract
    python3 scripts/build_terminal_assets.py --fonts <folder with the .woff files>
"""
import argparse
import base64
import io
import os
import random
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "terminal")

# ── palette (from the original profile) ─────────────────────────────────
PAGE = "#0d1117"
TERM = "#0a0e14"
CHROME = "#161b22"
LINE = "#21262d"
BORDER = "#30363d"
GREEN = "#00ff41"
MINT = "#00ff9d"
CYAN = "#00d8ff"
BLUE = "#2496ff"
PINK = "#ff2e63"
AMBER = "#ffbd2e"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
WHITE = "#e6f1ff"

FONT_FILES = {
    "mono": "fira-code-latin-400-normal.woff",
    "monob": "fira-code-latin-600-normal.woff",
    "monoh": "fira-code-latin-700-normal.woff",
    "head": "space-grotesk-latin-700-normal.woff",
}
FAMILY = {k: f"F{i}" for i, k in enumerate(FONT_FILES)}
_paths, _metrics = {}, {}


def load_fonts(font_dir):
    for key, name in FONT_FILES.items():
        for root, _, files in os.walk(font_dir):
            if name in files:
                _paths[key] = os.path.join(root, name)
        if key not in _paths:
            raise SystemExit(f"missing font {name} under {font_dir}")
        f = TTFont(_paths[key])
        _metrics[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)


def tw(key, text, size):
    cmap, hmtx, upm = _metrics[key]
    return sum(hmtx[cmap.get(ord(c)) or cmap[ord("?")]][0] for c in text) * size / upm


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
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts, self.css, self.defs = [], [], []
        self.chars = {k: "" for k in FONT_FILES}
        self.n = 0

    def uid(self, p="u"):
        self.n += 1
        return f"{p}{self.n}"

    def text(self, x, y, s, font, size, fill, extra="", cls="", style=""):
        self.chars[font] += s
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILY[font]}" font-size="{size}" '
                          f'fill="{fill}"{c}{st} {extra}>{escape(s)}</text>')

    def spans(self, x, y, segs, size, extra=""):
        """segs: list of (text, font, colour) rendered on one baseline."""
        out, cx = [], x
        for s, font, col in segs:
            self.chars[font] += s
            out.append(f'<tspan x="{cx:.1f}" font-family="{FAMILY[font]}" fill="{col}">{escape(s)}</tspan>')
            cx += tw(font, s, size)
        self.parts.append(f'<text y="{y:.1f}" font-size="{size}" {extra} xml:space="preserve">{"".join(out)}</text>')
        return cx

    def add(self, raw):
        self.parts.append(raw)

    def style(self, css):
        self.css.append(css)

    def save(self, name, title):
        faces = "".join(font_face(k, v) for k, v in self.chars.items() if v)
        css = faces + "".join(self.css) + \
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(title)}">'
               f'<title>{escape(title)}</title><style>{css}</style>{defs}{"".join(self.parts)}</svg>')
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)


# ── timeline helpers (looping keyframes) ─────────────────────────────────
def pct(t, period):
    return f"{100 * t / period:.2f}%"


def type_on(svg, x, y, segs, size, start, dur, period, end=None, extra=""):
    """Typewriter reveal of a line: a clip rect grows in character steps."""
    end = end if end is not None else period - 0.6
    width = sum(tw(f, s, size) for s, f, _ in segs) + 4
    nchar = max(1, sum(len(s) for s, _, _ in segs))
    cid, kid = svg.uid("c"), svg.uid("k")
    svg.defs.append(f'<clipPath id="{cid}"><rect class="{kid}" x="{x}" y="{y - size}" '
                    f'width="{width:.0f}" height="{size * 1.5:.0f}"/></clipPath>')
    svg.style(f".{kid}{{transform-box:fill-box;transform-origin:left;animation:{kid} {period}s infinite}}"
              f"@keyframes {kid}{{0%{{transform:scaleX(0)}}"
              f"{pct(start, period)}{{transform:scaleX(0);animation-timing-function:steps({nchar},end)}}"
              f"{pct(start + dur, period)}{{transform:scaleX(1)}}"
              f"{pct(end, period)}{{transform:scaleX(1)}}"
              f"{pct(end + 0.05, period)},100%{{transform:scaleX(0)}}}}")
    svg.add(f'<g clip-path="url(#{cid})">')
    right = svg.spans(x, y, segs, size, extra)
    svg.add("</g>")
    return right


def appear(svg, start, period, end=None, dur=0.25, rise=0, once=False):
    """Return a class name that fades an element in at `start` and out at `end`.

    With once=True the element fades in a single time and then stays visible.
    """
    k = svg.uid("a")
    tr = f"transform:translateY({rise}px);" if rise else ""
    if once:
        svg.style(f".{k}{{animation:{k} {max(dur, .05)}s ease-out {start}s both}}"
                  f"@keyframes {k}{{from{{opacity:0;{tr}}}to{{opacity:1;transform:none}}}}")
        return k
    end = end if end is not None else period - 0.6
    svg.style(f".{k}{{animation:{k} {period}s infinite}}"
              f"@keyframes {k}{{0%{{opacity:0;{tr}}}{pct(start, period)}{{opacity:0;{tr}}}"
              f"{pct(start + dur, period)}{{opacity:1;transform:none}}{pct(end, period)}{{opacity:1;transform:none}}"
              f"{pct(end + 0.3, period)},100%{{opacity:0}}}}")
    return k


BLINK = ".blink{animation:blink 1.05s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
PULSE = ".pulse{animation:pulse 2s ease-in-out infinite}@keyframes pulse{50%{opacity:.3}}"


def chrome(svg, x, y, w, h, title, radius=10, bar=34):
    svg.add(f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" height="{h - 2}" rx="{radius}" fill="{TERM}" '
            f'stroke="{BORDER}"/>')
    svg.add(f'<path d="M{x + 1},{y + bar} V{y + radius + 1} Q{x + 1},{y + 1} {x + radius + 1},{y + 1} '
            f'H{x + w - radius - 1} Q{x + w - 1},{y + 1} {x + w - 1},{y + radius + 1} V{y + bar} Z" fill="{CHROME}"/>')
    svg.add(f'<line x1="{x + 1}" y1="{y + bar}" x2="{x + w - 1}" y2="{y + bar}" stroke="{BORDER}"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        svg.add(f'<circle cx="{x + 20 + i * 20}" cy="{y + bar / 2}" r="6" fill="{c}"/>')
    size = 12.5
    svg.text(x + (w - tw("mono", title, size)) / 2, y + bar / 2 + 4.5, title, "mono", size, MUTED)


def matrix_rain(svg, x0, x1, y0, y1, cols, seed, opacity=.14, step=17, size=14):
    rnd = random.Random(seed)
    glyphs = "0123456789abcdef$#%&@<>/=+*"
    k = svg.uid("rain")
    cid = svg.uid("rc")
    svg.defs.append(f'<clipPath id="{cid}"><rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}"/></clipPath>')
    svg.style(f".{k}{{animation:{k} linear infinite}}"
              f"@keyframes {k}{{from{{transform:translateY(-{(y1 - y0) + 120}px)}}to{{transform:translateY({y1 - y0}px)}}}}")
    svg.add(f'<g clip-path="url(#{cid})" opacity="{opacity}">')
    for i in range(cols):
        cx = x0 + 12 + i * (x1 - x0 - 24) / max(1, cols - 1)
        n = rnd.randint(8, 16)
        chars = "".join(rnd.choice(glyphs) for _ in range(n))
        svg.chars["mono"] += chars
        dur = rnd.uniform(5, 11)
        delay = rnd.uniform(0, dur)
        tsp = "".join(
            f'<tspan x="{cx:.0f}" dy="{step}" fill="{GREEN if j < n - 1 else WHITE}" '
            f'fill-opacity="{0.25 + 0.75 * j / n:.2f}">{escape(c)}</tspan>'
            for j, c in enumerate(chars))
        svg.add(f'<text class="{k}" style="animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s" '
                f'y="{y0}" font-family="{FAMILY["mono"]}" font-size="{size}">{tsp}</text>')
    svg.add("</g>")


def arrow(x, y, color, w=2):
    return (f'<path d="M{x},{y + 9} L{x + 9},{y} M{x + 2},{y} H{x + 9} V{y + 7}" fill="none" '
            f'stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def ok_tag(svg, x, y, label="OK", col=GREEN):
    """Draw a '[ OK ]' boot tag."""
    return svg.spans(x, y, [("[ ", "mono", MUTED), (label, "monob", col), (" ]", "mono", MUTED)], 14)


# ── 1. HERO: boot sequence ───────────────────────────────────────────────
def build_hero():
    P = 18
    s = Svg(1000, 430)
    s.style(BLINK + PULSE)
    s.defs.append(f'<linearGradient id="nameg" x1="0" x2="1"><stop offset="0" stop-color="{GREEN}"/>'
                  f'<stop offset=".55" stop-color="{MINT}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>'
                  f'<linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="{TERM}"/>'
                  f'<stop offset=".6" stop-color="{TERM}" stop-opacity=".85"/>'
                  f'<stop offset="1" stop-color="{TERM}" stop-opacity="0"/></linearGradient>'
                  f'<filter id="glow" x="-10%" y="-40%" width="120%" height="180%"><feGaussianBlur stdDeviation="6" result="b"/>'
                  f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
                  f'<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse">'
                  f'<rect width="4" height="1" fill="#000" opacity=".35"/></pattern>')
    chrome(s, 0, 0, 1000, 430, "armanxploits@fsociety: ~ (zsh)")
    matrix_rain(s, 540, 998, 36, 428, 16, seed=13, opacity=.22)
    s.add('<rect x="1" y="35" width="700" height="393" fill="url(#fadeL)"/>')
    x = 32
    prompt = [("armanxploits", "monob", GREEN), ("@", "mono", MUTED), ("fsociety", "monob", CYAN),
              (":~$ ", "mono", WHITE)]
    p_end = s.spans(x, 72, prompt, 15)
    type_on(s, p_end, 72, [("./boot --persona=dual", "mono", WHITE)], 15, 0.4, 1.3, P)
    boots = [("mounting /dev/builder", "done", GREEN), ("mounting /dev/breaker", "done", GREEN),
             ("loading persona: full-stack developer", "ready", CYAN),
             ("loading persona: ethical hacker", "armed", PINK)]
    y = 100
    for i, (msg, res, col) in enumerate(boots):
        k = appear(s, 2.0 + i * 0.45, P, dur=.05)
        s.add(f'<g class="{k}">')
        e = ok_tag(s, x, y, "OK", GREEN)
        s.text(e + 10, y, msg, "mono", 14, TEXT)
        dots_x = x + 470
        s.text(dots_x - 6 - tw("mono", "." * 8, 14), y, "." * 8, "mono", 14, LINE)
        s.text(dots_x, y, res, "monob", 14, col)
        s.add("</g>")
        y += 22
    # name with subtle glitch
    k = appear(s, 4.1, P, dur=.4, rise=10)
    gk = s.uid("g")
    s.style(f".{gk}a{{animation:{gk}a 4s infinite steps(1)}}.{gk}b{{animation:{gk}b 4s infinite steps(1)}}"
            f"@keyframes {gk}a{{0%,93%,100%{{transform:translate(0,0);opacity:0}}94%{{transform:translate(-5px,1px);opacity:.8}}"
            f"96%{{transform:translate(4px,-1px);opacity:.8}}98%{{opacity:0}}}}"
            f"@keyframes {gk}b{{0%,93%,100%{{transform:translate(0,0);opacity:0}}94%{{transform:translate(5px,-1px);opacity:.8}}"
            f"96%{{transform:translate(-3px,1px);opacity:.8}}98%{{opacity:0}}}}")
    s.add(f'<g class="{k}">')
    s.text(x - 2, 262, "Arman Ahemad Khan", "monoh", 54, CYAN, cls=f"{gk}a")
    s.text(x - 2, 262, "Arman Ahemad Khan", "monoh", 54, PINK, cls=f"{gk}b")
    s.text(x - 2, 262, "Arman Ahemad Khan", "monoh", 54, "url(#nameg)", 'filter="url(#glow)"')
    s.add("</g>")
    k = appear(s, 4.6, P, dur=.3)
    s.add(f'<g class="{k}">')
    s.spans(x, 296, [("// ", "mono", MUTED), ("Full-Stack Developer", "monob", CYAN), ("  &&  ", "mono", MUTED),
                     ("Ethical Hacker", "monob", GREEN), ("  &&  ", "mono", MUTED),
                     ("CSE '27", "monob", BLUE)], 17)
    s.add("</g>")
    type_on(s, x, 334, [("> ", "monob", GREEN),
                        ("I build the web by day. I break it to secure it by night.", "mono", TEXT)],
            16, 5.2, 2.6, P)
    k = appear(s, 8.0, P, dur=.05)
    s.add(f'<g class="{k}">')
    e = s.spans(x, 390, prompt, 15)
    s.add(f'<rect class="blink" x="{e + 2:.0f}" y="377" width="9" height="17" fill="{GREEN}"/>')
    s.add("</g>")
    # status chip
    s.add(f'<rect x="842" y="54" width="128" height="26" rx="13" fill="{TERM}" stroke="{BORDER}"/>'
          f'<circle class="pulse" cx="860" cy="67" r="4.5" fill="{GREEN}"/>')
    s.text(872, 72, "SYSTEM ONLINE", "monob", 11, GREEN)
    s.add('<rect x="1" y="35" width="998" height="393" fill="url(#scan)" opacity=".5"/>')
    s.save("hero.svg", "Arman Ahemad Khan — Full-Stack Developer and Ethical Hacker")


# ── 2. NAV BUTTONS ───────────────────────────────────────────────────────
NAV = [("about", "~/about"), ("projects", "~/projects"), ("stack", "~/stack"),
       ("activity", "~/activity"), ("contact", "~/contact")]


def build_nav():
    for i, (slug, label) in enumerate(NAV):
        size = 15
        w = int(tw("monob", label, size) + 46)
        s = Svg(w, 40)
        s.style(PULSE)
        s.add(f'<rect x="1" y="1" width="{w - 2}" height="38" rx="8" fill="{TERM}" stroke="{BORDER}"/>')
        s.add(f'<circle class="pulse" style="animation-delay:-{i * .4:.1f}s" cx="18" cy="20" r="4" fill="{GREEN}"/>')
        s.text(30, 25.5, label, "monob", size, TEXT)
        s.save(f"nav-{slug}.svg", label)


# ── 3. SECTION PROMPTS ───────────────────────────────────────────────────
def build_prompt(name, cmd, out=None):
    P = 9
    s = Svg(1000, 50 if not out else 70)
    s.style(BLINK)
    pre = [("armanxploits", "monob", GREEN), ("@", "mono", MUTED), ("fsociety", "monob", CYAN),
           (":~$ ", "mono", WHITE)]
    e = s.spans(4, 32, pre, 17)
    end = type_on(s, e, 32, [(cmd, "monob", WHITE)], 17, 0.4, min(2.4, len(cmd) * 0.07), P, end=P - 0.3)
    k = appear(s, 0.4 + min(2.4, len(cmd) * 0.07), P, end=P - 0.3, dur=.01)
    s.add(f'<rect class="blink {k}" x="{end + 3:.0f}" y="17" width="10" height="19" fill="{GREEN}"/>')
    s.add(f'<line x1="4" y1="46" x2="996" y2="46" stroke="{LINE}" stroke-width="1.5"/>')
    s.save(f"prompt-{name}.svg", f"$ {cmd}")


# ── 4. GIT GRAPH (dual persona) ──────────────────────────────────────────
def build_gitgraph():
    P = 12
    s = Svg(1000, 300)
    s.style(BLINK + PULSE)
    chrome(s, 0, 0, 1000, 300, "~/arman  git log --graph --oneline --all")
    y_main, y_red = 120, 210
    commits = [  # (x, lane, hash, msg, colour)
        (190, "m", "a1f3c2e", "design: clean, responsive UI", CYAN),
        (330, "m", "7be9d10", "build: REST APIs + databases", CYAN),
        (470, "r", "c0ffee1", "assess: threat model + recon", PINK),
        (620, "r", "dead5ec", "test: authorized pentest", PINK),
        (770, "m", "fa13d42", "harden: patch every finding", GREEN),
        (900, "m", "5h1pp3d", "deploy: ship it live", GREEN),
    ]
    path_main = f"M130,{y_main} H960"
    path_red = (f"M330,{y_main} C390,{y_main} 380,{y_red} 440,{y_red} H650 "
                f"C710,{y_red} 700,{y_main} 770,{y_main}")
    for d, col, start in ((path_main, CYAN, 0.2), (path_red, PINK, 1.2)):
        k = s.uid("p")
        s.style(f".{k}{{stroke-dasharray:1200;animation:{k} {P}s infinite}}"
                f"@keyframes {k}{{0%,{pct(start, P)}{{stroke-dashoffset:1200}}{pct(start + 2.2, P)},{pct(P - .6, P)}"
                f"{{stroke-dashoffset:0}}100%{{stroke-dashoffset:1200}}}}")
        s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5" stroke-opacity=".35"/>')
        s.add(f'<path class="{k}" d="{d}" fill="none" stroke="{col}" stroke-width="2.5"/>')
    # branch labels, at the left edge of each lane
    for (ly, label, col) in ((y_main, "main", CYAN), (y_red, "redteam", PINK)):
        w = tw("monob", label, 12) + 18
        s.add(f'<rect x="{110 - w:.0f}" y="{ly - 11}" width="{w:.0f}" height="22" rx="4" fill="{TERM}" stroke="{col}"/>')
        s.text(110 - w + 9, ly + 4.5, label, "monob", 12, col)
    s.add(f'<path d="M112,{y_red} H440" stroke="{PINK}" stroke-opacity=".35" stroke-dasharray="3 5" stroke-width="2"/>')
    for i, (cx, lane, h, msg, col) in enumerate(commits):
        cy = y_main if lane == "m" else y_red
        t0 = 0.6 + i * 0.75
        k = appear(s, t0, P, dur=.3)
        s.add(f'<g class="{k}">')
        s.add(f'<circle cx="{cx}" cy="{cy}" r="9" fill="{TERM}" stroke="{col}" stroke-width="3"/>'
              f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="{col}"/>')
        ty = cy - 22 if lane == "m" else cy + 34
        s.text(cx - tw("mono", h, 12) / 2, ty, h, "mono", 12, AMBER)
        lines = wrap(msg, "mono", 12.5, 150)
        if lane == "r":  # message below the hash
            for j, line in enumerate(lines):
                s.text(cx - tw("mono", line, 12.5) / 2, ty + 17 * (j + 1), line, "mono", 12.5, TEXT)
        else:  # message above the hash
            for j, line in enumerate(reversed(lines)):
                s.text(cx - tw("mono", line, 12.5) / 2, ty - 16 * (j + 1), line, "mono", 12.5, TEXT)
        s.add("</g>")
    # HEAD tag on the last commit
    k = appear(s, 0.6 + 6 * 0.75, P, dur=.3)
    s.add(f'<g class="{k}"><rect x="852" y="{y_main + 18}" width="96" height="22" rx="4" fill="{GREEN}"/>')
    s.text(860, y_main + 33.5, "HEAD -> v27", "monob", 11.5, TERM)
    s.add("</g>")
    s.add(f'<circle class="pulse" cx="960" cy="{y_main}" r="4" fill="{GREEN}"/>')
    s.save("gitgraph.svg", "git log: design, build, assess, test, harden, deploy")


# ── 5. NEOFETCH ──────────────────────────────────────────────────────────
SHIELD_ROWS = ["....##########....", "..##############.."] + [".################."] * 9 + [
    "..##############..", "..##############..", "...############...", "....##########....",
    ".....########.....", "......######......", ".......####......."]
CARVE = {4: (4, 5), 5: (5, 6), 6: (6, 7), 7: (7, 8), 8: (6, 7), 9: (5, 6), 10: (4, 5)}
SHIELD = []
for _r, _row in enumerate(SHIELD_ROWS):
    _row = list(_row)
    for _c in CARVE.get(_r, ()):
        _row[_c] = "."
    if _r == 10:
        for _c in range(10, 15):
            _row[_c] = "."
    SHIELD.append("".join(_row))


def build_neofetch():
    P = 14
    s = Svg(1000, 400)
    s.style(BLINK)
    chrome(s, 0, 0, 1000, 400, "armanxploits@fsociety: ~  neofetch")
    s.defs.append(f'<linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{CYAN}"/>'
                  f'<stop offset=".5" stop-color="{MINT}"/><stop offset="1" stop-color="{GREEN}"/></linearGradient>'
                  f'<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                  f'<stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
                  f'</linearGradient>')
    px, ox, oy = 15, 50, 72
    cells = []
    for r, row in enumerate(SHIELD):
        for c, ch in enumerate(row):
            if ch == "#":
                cells.append(f'<rect x="{ox + c * px}" y="{oy + r * px}" width="{px - 2}" height="{px - 2}" rx="2"/>')
    s.defs.append(f'<clipPath id="shield">{"".join(cells)}</clipPath>')
    s.add(f'<g clip-path="url(#shield)"><rect x="{ox}" y="{oy}" width="{18 * px}" height="{len(SHIELD) * px}" fill="url(#lg)"/>'
          f'<rect class="sw" x="{ox}" y="{oy - 60}" width="{18 * px}" height="60" fill="url(#sweep)"/></g>')
    s.style(f".sw{{animation:sw 3.5s ease-in-out infinite}}@keyframes sw{{0%{{transform:translateY(0)}}"
            f"70%,100%{{transform:translateY({len(SHIELD) * px + 60}px)}}}}")
    s.text(ox + 18 * px / 2 - tw("monob", "armanxploits", 13) / 2, oy + len(SHIELD) * px + 30, "armanxploits", "monob", 13, MUTED)
    # info
    x = 380
    y = 74
    e = s.spans(x, y, [("arman", "monoh", GREEN), ("@", "mono", MUTED), ("fsociety", "monoh", CYAN)], 17)
    s.add(f'<line x1="{x}" y1="{y + 10}" x2="{e:.0f}" y2="{y + 10}" stroke="{MUTED}" stroke-dasharray="6 4"/>')
    info = [
        ("OS", "Kali Linux (Xfce) <-> Windows 11"),
        ("Host", "ASUS TUF Gaming F16 · RTX 3050"),
        ("Shell", "zsh + oh-my-zsh + powerlevel10k"),
        ("Role", "Cybersecurity Intern · Web AppSec"),
        ("Edu", "B.Tech CSE '23-'27 · Silicon IT, BBSR"),
        ("Dev", "Java · Spring Boot · Node · React · FastAPI"),
        ("Sec", "Burp · Nmap · Wireshark · Volatility3"),
        ("Labs", "PortSwigger · TryHackMe · HackTheBox"),
        ("Mantra", "build it. break it. harden it."),
    ]
    y += 38
    for i, (k_, v) in enumerate(info):
        k = appear(s, 0.3 + i * 0.22, P, dur=.15, once=True)
        s.add(f'<g class="{k}">')
        s.text(x, y, k_, "monob", 15, CYAN if i % 2 == 0 else GREEN)
        s.text(x + 82, y, v, "mono", 15, TEXT)
        s.add("</g>")
        y += 26
    k = appear(s, 0.3 + len(info) * 0.22, P, dur=.2, once=True)
    s.add(f'<g class="{k}">')
    for i, col in enumerate((TERM, PINK, GREEN, AMBER, BLUE, "#bc8cff", CYAN, WHITE)):
        s.add(f'<rect x="{x + i * 34}" y="{y - 4}" width="30" height="18" rx="3" fill="{col}" stroke="{BORDER}"/>')
    s.add("</g>")
    s.save("neofetch.svg", "neofetch: Arman Ahemad Khan system info")


# ── 6. HTOP ──────────────────────────────────────────────────────────────
def build_htop():
    P = 12
    s = Svg(1000, 362)
    s.style(BLINK)
    chrome(s, 0, 0, 1000, 362, "htop  —  filter: arman")
    # meters
    meters = [("1", .82, GREEN), ("2", .64, CYAN), ("3", .91, GREEN), ("4", .47, BLUE)]
    for i, (lab, v, col) in enumerate(meters):
        mx = 30 + (i % 2) * 480
        my = 62 + (i // 2) * 24
        s.text(mx, my + 11, lab, "monob", 13, CYAN)
        s.text(mx + 16, my + 11, "[", "monob", 13, WHITE)
        s.text(mx + 420, my + 11, "]", "monob", 13, WHITE)
        k = s.uid("m")
        s.style(f".{k}{{transform-box:fill-box;transform-origin:left;animation:{k} {2.2 + i * .4:.1f}s ease-in-out infinite alternate}}"
                f"@keyframes {k}{{from{{transform:scaleX({v * .65:.2f})}}to{{transform:scaleX(1)}}}}")
        s.add(f'<rect class="{k}" x="{mx + 28}" y="{my + 1}" width="{380 * v:.0f}" height="12" rx="2" fill="{col}"/>')
        s.text(mx + 372, my + 11, f"{v * 100:.0f}%", "mono", 12, MUTED)
    s.spans(30, 132, [("Tasks: ", "mono", CYAN), ("6", "monob", GREEN), (", 2 thr; ", "mono", MUTED),
                      ("Load average: ", "mono", CYAN), ("build 0.98  break 0.91  harden 0.87", "monob", WHITE)], 13)
    # table
    s.add(f'<rect x="20" y="146" width="960" height="24" fill="{GREEN}"/>')
    cols = [(30, "PID"), (110, "USER"), (210, "PRI"), (270, "%CPU"), (350, "%MEM"), (430, "STATE"), (530, "COMMAND")]
    for cx, h in cols:
        s.text(cx, 163, h, "monob", 13, TERM)
    rows = [
        ("1337", "64.2", "11.8", "SHIP", GREEN, "build --fullstack --stack=spring,node,react"),
        ("2027", "58.9", "9.4", "HUNT", PINK, "appsec --scope=authorized --report=responsible"),
        ("0418", "41.5", "7.1", "RUN", CYAN, "memlabs --lab=6 --tool=volatility3"),
        ("0808", "37.0", "6.3", "SHIP", GREEN, "portfolio --theme=terminal --deploy"),
        ("0101", "29.6", "4.9", "RUN", CYAN, "ctf --on=portswigger,thm,htb"),
        ("0042", "18.3", "3.2", "SYNC", AMBER, "notes --vault=obsidian --public"),
    ]
    k = s.uid("sel")
    stops = "".join(f"{pct(i * P / len(rows), P)},{pct((i + 1) * P / len(rows) - 0.01, P)}"
                    f"{{transform:translateY({i * 24}px)}}" for i in range(len(rows)))
    s.style(f".{k}{{animation:{k} {P}s infinite steps(1)}}@keyframes {k}{{{stops}100%{{transform:translateY(0)}}}}")
    s.add(f'<rect class="{k}" x="20" y="172" width="960" height="24" fill="{BLUE}" fill-opacity=".22"/>')
    y = 189
    for pid, cpu, mem, st, sc, cmd in rows:
        s.text(30, y, pid, "mono", 13, MUTED)
        s.text(110, y, "arman", "mono", 13, TEXT)
        s.text(210, y, "20", "mono", 13, MUTED)
        s.text(270, y, cpu, "monob", 13, GREEN)
        s.text(350, y, mem, "mono", 13, TEXT)
        s.text(430, y, st, "monob", 13, sc)
        s.text(530, y, cmd, "mono", 13, WHITE)
        y += 24
    keys = [("F1", "Help"), ("F3", "Search"), ("F5", "Tree"), ("F9", "Kill bugs"), ("F10", "Quit")]
    kx = 20
    for fk, lab in keys:
        s.text(kx, 343, fk, "monob", 12, WHITE)
        w1 = tw("monob", fk, 12)
        s.add(f'<rect x="{kx + w1 + 4:.0f}" y="{329}" width="{tw("mono", lab, 12) + 12:.0f}" height="20" fill="{CYAN}" fill-opacity=".85"/>')
        s.text(kx + w1 + 10, 343, lab, "mono", 12, TERM)
        kx += w1 + tw("mono", lab, 12) + 34
    s.save("htop.svg", "htop: what Arman is running right now")


# ── 7. PROJECT CARDS ─────────────────────────────────────────────────────
PROJECTS = [
    ("netscope", "NetScope", "Network Packet Analyzer", CYAN,
     "Real-time traffic analysis with a SOC-style browser dashboard, protocol breakdowns, anomaly alerts and per-host risk scores.",
     "python · scapy · websockets", "vercel + render"),
    ("fsociety", "fsociety-web", "Security Portfolio", PINK,
     "A cinematic security portfolio with an interactive roadmap, in-browser utilities, field notes and CTF progress.",
     "html · css · vanilla js", "vercel"),
    ("industrust", "IndusTrust Bank", "Banking System", GREEN,
     "Spring Boot web bank with a double-entry ledger, row-locked atomic transfers, BigDecimal money and hashed PINs.",
     "spring boot · postgres · docker", "render + neon"),
    ("sms", "Student Mgmt System", "Records Platform", AMBER,
     "A legacy Swing + Oracle app rebuilt as a cloud REST service with analytics, CSV export and CI on every push.",
     "spring boot · neon · actions", "render"),
    ("snapurl", "SnapURL", "Serverless URL Shortener", BLUE,
     "Base62 short links, custom aliases and self-expiring links on Vercel functions with Turso edge SQLite.",
     "typescript · express · turso", "vercel"),
    ("cineroulette", "CineRoulette", "Movie Picker", PINK,
     "Pick a mood, spin, get one explained movie pick. Weighted scoring normalized per language and region.",
     "next.js · nestjs · prisma · redis", "vercel"),
    ("gitatlas", "GitAtlas", "Git Command Atlas", AMBER,
     "381 Git commands in plain English, 17 recovery playbooks, a guided wizard and warnings on risky commands.",
     "html · css · vanilla js", "vercel"),
    ("grabmedia", "GrabMedia", "Media Downloader", CYAN,
     "Save public Instagram and YouTube media up to 2160p or audio-only, behind a hardened, rate-limited Express proxy.",
     "node.js · express · helmet", "gh pages + render"),
    ("disease", "Disease Predict", "Explainable ML", GREEN,
     "Predicts 41 diseases from 132 symptoms with a tree ensemble, SHAP explanations and downloadable PDF reports.",
     "fastapi · scikit-learn · shap", "vercel + render"),
    ("siteshield", "SiteShield", "Security Posture SaaS", BLUE,
     "Grades a website's TLS, headers, cookies and DNS hygiene A to F, re-scans on schedule and alerts on regressions.",
     "react · fastapi · celery", None),
]


def build_card(slug, title, sub, col, desc, stack, host):
    P = 10
    s = Svg(480, 250)
    s.style(BLINK + PULSE)
    chrome(s, 0, 0, 480, 250, f"~/projects/{slug}", radius=10, bar=30)
    s.add(f'<rect x="1" y="30" width="3" height="219" fill="{col}"/>')
    pre = [("$ ", "monob", GREEN)]
    e = s.spans(22, 58, pre, 13.5)
    cmd = f"./launch {slug}" if host else f"git log -1 {slug}"
    end = type_on(s, e, 58, [(cmd, "mono", WHITE)], 13.5, 0.3, 1.0, P)
    k = appear(s, 1.4, P, dur=.3, once=True)
    s.add(f'<g class="{k}">')
    s.text(22, 94, title, "head", 25, WHITE, 'letter-spacing="-.3"')
    s.text(22 + tw("head", title, 25) + 12, 94, f"// {sub}", "mono", 12.5, col)
    yy = 122
    for line in wrap(desc, "mono", 12.8, 436)[:3]:
        s.text(22, yy, line, "mono", 12.8, TEXT)
        yy += 19
    s.text(22, 190, "stack:", "monob", 12.5, MUTED)
    s.text(22 + tw("monob", "stack: ", 12.5), 190, stack, "mono", 12.5, CYAN)
    s.add("</g>")
    k = appear(s, 1.9, P, dur=.2, once=True)
    s.add(f'<g class="{k}">')
    s.add(f'<line x1="22" y1="204" x2="458" y2="204" stroke="{LINE}"/>')
    if host:
        s.add(f'<circle class="pulse" cx="28" cy="226" r="4.5" fill="{GREEN}"/>')
        e2 = s.spans(40, 230.5, [("live", "monob", GREEN), (f"  on {host}", "mono", MUTED)], 12.5)
        cta = "open"
    else:
        s.add(f'<circle class="pulse" cx="28" cy="226" r="4.5" fill="{AMBER}"/>')
        s.spans(40, 230.5, [("building", "monob", AMBER), ("  in public", "mono", MUTED)], 12.5)
        cta = "source"
    cw = tw("monob", f"[ {cta} ]", 12.5)
    s.text(436 - cw, 230.5, f"[ {cta} ]", "monob", 12.5, col)
    s.add(arrow(442, 220, col))
    s.add("</g>")
    s.save(f"card-{slug}.svg", f"{title} — {sub}")


# ── 8. ETHICS LOG ────────────────────────────────────────────────────────
def build_ethics():
    P = 10
    s = Svg(1000, 200)
    s.style(BLINK)
    chrome(s, 0, 0, 1000, 200, "tail -f /var/log/ethics.log")
    lines = [("OK", GREEN, "explicit written authorization before every test"),
             ("OK", GREEN, "responsible disclosure, always"),
             ("OK", GREEN, "I build to empower and hack to protect, never to harm"),
             ("INFO", CYAN, "scope = CTFs · home labs · authorized bug-bounty programs only")]
    y = 66
    for i, (lvl, col, msg) in enumerate(lines):
        k = appear(s, 0.4 + i * 0.7, P, dur=.05, once=True)
        s.add(f'<g class="{k}">')
        s.text(24, y, f"2026-11-0{i + 1}T0{i}:1{i}:0{i}Z", "mono", 13.5, MUTED)
        e = s.spans(250, y, [("[", "mono", MUTED), (f"{lvl:^4}", "monob", col), ("]", "mono", MUTED)], 13.5)
        s.text(e + 12, y, msg, "mono", 13.5, TEXT)
        s.add("</g>")
        y += 28
    k = appear(s, 0.4 + 4 * 0.7, P, dur=.05, once=True)
    s.add(f'<rect class="blink {k}" x="24" y="{y - 13}" width="9" height="16" fill="{GREEN}"/>')
    s.save("ethics.svg", "ethics.log: authorization, responsible disclosure, scope")


# ── 9. FOOTER ────────────────────────────────────────────────────────────
def build_footer():
    s = Svg(1000, 190)
    s.style(BLINK)
    s.add(f'<rect x="1" y="1" width="998" height="188" rx="12" fill="{TERM}" stroke="{BORDER}"/>')
    matrix_rain(s, 2, 998, 2, 188, 34, seed=27, opacity=.2)
    s.defs.append(f'<radialGradient id="vg"><stop offset="0" stop-color="{TERM}" stop-opacity=".95"/>'
                  f'<stop offset="1" stop-color="{TERM}" stop-opacity="0"/></radialGradient>')
    s.add('<ellipse cx="500" cy="95" rx="420" ry="80" fill="url(#vg)"/>')
    msg = "build  •  break  •  harden  •  ship"
    s.text((1000 - tw("monoh", msg, 28)) / 2, 92, msg, "monoh", 28, GREEN, 'filter="url(#fg)"')
    s.defs.append('<filter id="fg" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="5" result="b"/>'
                  '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    sub = "connection closed by armanxploits. see you in the logs."
    s.text((1000 - tw("mono", sub, 14)) / 2, 128, sub, "mono", 14, MUTED)
    p = "$ exit"
    px = (1000 - tw("monob", p, 14) - 14) / 2
    s.text(px, 156, p, "monob", 14, CYAN)
    s.add(f'<rect class="blink" x="{px + tw("monob", p, 14) + 5:.0f}" y="144" width="8" height="15" fill="{GREEN}"/>')
    s.save("footer.svg", "build, break, harden, ship")


PROMPTS = [
    ("persona", "git log --graph --all   # one dev, two branches"),
    ("whoami", "neofetch"),
    ("projects", "ls ~/projects --live"),
    ("ps", "htop --filter=arman"),
    ("stack", "cat techstack.json"),
    ("ethics", "tail -f /var/log/ethics.log"),
    ("stats", "./recon --target=self"),
    ("contact", "netstat -an | grep ESTABLISHED"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    load_fonts(ap.parse_args().fonts)
    build_hero()
    build_nav()
    for name, cmd in PROMPTS:
        build_prompt(name, cmd)
    build_gitgraph()
    build_neofetch()
    build_htop()
    for p in PROJECTS:
        build_card(*p)
    build_ethics()
    build_footer()


if __name__ == "__main__":
    main()
