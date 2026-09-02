"""Frame rendering for the BioGlyph explainer, one scene per narration segment.

Everything is drawn with PIL at 1920x1080 in the lab's palette. No stock assets.

Two rules that keep it legible at video size, learned from how the page's own figures read:
  - nothing smaller than 26 px, because YouTube-grade compression eats thin small type;
  - the graph geometry is computed once with a fixed seed and reused across segments 2 to 5,
    so the viewer tracks the same region rather than re-reading a new picture each time.

`render(seg, t, size)` returns a PIL image for progress t in [0, 1] within segment `seg`.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- palette: the same tokens as bioglyph/style.css -------------------------
INK = (23, 32, 44)
SOFT = (70, 82, 98)
MUTED = (112, 122, 134)
PAPER = (255, 255, 255)
WARM = (245, 243, 238)
LINE = (217, 214, 206)
ACCENT = (168, 63, 53)
BLUE = (71, 109, 137)
GOLD = (179, 133, 54)
GREEN = (98, 128, 96)

FONTS = Path("C:/Windows/Fonts")
_cache: dict = {}


def font(kind: str, px: int):
    """Cambria stands in for Source Serif 4, Consolas for IBM Plex Mono, Calibri for Source Sans."""
    key = (kind, px)
    if key not in _cache:
        name = {"serif": "cambria.ttc", "serif_b": "cambriab.ttf", "mono": "consola.ttf",
                "mono_b": "consolab.ttf", "sans": "calibri.ttf", "sans_b": "calibrib.ttf"}[kind]
        _cache[key] = ImageFont.truetype(str(FONTS / name), px)
    return _cache[key]


def ease(t: float) -> float:
    """Smoothstep. Linear reveals look mechanical at 30 fps."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def stagger(t: float, i: int, n: int, overlap: float = 0.45) -> float:
    """Progress of item i when n items reveal in sequence across the segment."""
    if n <= 1:
        return ease(t)
    span = 1.0 / (n - (n - 1) * overlap)
    start = i * span * (1 - overlap)
    return ease((t - start) / span) if span > 0 else 1.0


# --- the region, laid out once ---------------------------------------------

def _layout(n: int = 90, seed: int = 7) -> dict:
    """A spring layout with a deliberate cut node, so segment 4's claim is visibly true."""
    rng = np.random.default_rng(seed)
    # six communities, one hub node bridging them: mirrors the Power-Grid region on the page
    sizes = [12, 11, 7, 5, 5, 5]
    comm, pos, edges = [], [], []
    centers = [(math.cos(a) * 300, math.sin(a) * 300) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    idx = 0
    for c, (sz, (cx, cy)) in enumerate(zip(sizes, centers)):
        for _ in range(sz):
            pos.append((cx + rng.normal(0, 78), cy + rng.normal(0, 78)))
            comm.append(c)
            idx += 1
    hub = 0  # index 0 sits in community 0 and will be wired to every other community
    pos[hub] = (0.0, 0.0)
    for c, sz in enumerate(sizes):
        members = [i for i, cc in enumerate(comm) if cc == c and i != hub]
        for a in range(len(members) - 1):
            edges.append((members[a], members[a + 1]))
        for a in rng.choice(members, size=max(1, len(members) // 3), replace=False):
            edges.append((int(a), int(rng.choice(members))))
        edges.append((hub, int(members[0])))          # the bridge that makes hub a cut node
    filler = [i for i in range(len(pos)) if i != hub]
    for _ in range(len(pos) - 30):
        a, b = rng.choice(filler, size=2, replace=False)
        if comm[a] == comm[b]:
            edges.append((int(a), int(b)))
    edges = [(a, b) for a, b in {(min(a, b), max(a, b)) for a, b in edges} if a != b]

    deg = {i: 0 for i in range(len(pos))}
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    region = {hub} | {b for a, b in edges if a == hub} | {a for a, b in edges if b == hub}
    for a, b in edges:                                  # two hops
        if a in region or b in region:
            region |= {a, b}
    return {"pos": pos, "edges": edges, "comm": comm, "deg": deg, "hub": hub, "region": region}


REGION = _layout()
COMM_COLORS = [BLUE, GREEN, GOLD, BLUE, GREEN, MUTED]


def _screen(p, size, scale=1.0, dx=0, dy=0):
    w, h = size
    return (w / 2 + p[0] * scale + dx, h / 2 + p[1] * scale + dy)


# --- shared chrome ---------------------------------------------------------

def _frame(size) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", size, PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, size[0], 8], fill=ACCENT)
    return img, d


def _chrome(d, size, seg_n: int, label: str = ""):
    w, h = size
    d.text((72, h - 104), "Bio", font=font("serif_b", 40), fill=INK)
    wl = d.textlength("Bio", font=font("serif_b", 40))
    d.text((72 + wl, h - 104), "Glyph", font=font("serif_b", 40), fill=ACCENT)
    d.text((72, h - 54), "a network, stated in words", font=font("sans", 26), fill=MUTED)
    if label:
        d.text((w - 72, h - 62), label, font=font("mono", 26), fill=MUTED, anchor="rs")
    for i in range(1, 8):                                  # progress dots
        x = w - 72 - (7 - i) * 26
        r = 6
        c = ACCENT if i <= seg_n else LINE
        d.ellipse([x - r, h - 104 - r, x + r, h - 104 + r], fill=c)


def _wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = f"{cur} {wd}".strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# --- segments --------------------------------------------------------------

def seg1(d, size, t):
    w, h = size
    rng = np.random.default_rng(3)
    f = font("mono", 27)
    shift = int(t * 40)
    for row in range(26):
        y = 150 + row * 34 - shift
        if not (120 < y < h - 190):
            continue
        pairs = "   ".join(f"{rng.integers(1,999):3d} {rng.integers(1,999):3d}" for _ in range(9))
        fade = min(1.0, (row + 2) / 6)
        col = tuple(int(PAPER[i] + (MUTED[i] - PAPER[i]) * 0.55 * fade) for i in range(3))
        d.text((72, y), pairs, font=f, fill=col)
    d.rectangle([w * 0.60, 0, w, h], fill=WARM)
    d.line([w * 0.60, 0, w * 0.60, h], fill=LINE, width=2)
    d.text((w * 0.60 + 60, 300), "The question", font=font("mono", 26), fill=ACCENT)
    for i, ln in enumerate(_wrap(d, "Which node holds this region together?", font("serif", 54), w * 0.34)):
        d.text((w * 0.60 + 60, 360 + i * 70), ln, font=font("serif", 54), fill=INK)
    if (t * 3) % 1 < 0.55:
        d.rectangle([w * 0.60 + 60, 530, w * 0.60 + 64, 578], fill=ACCENT)
    if t > 0.45:
        a = ease((t - 0.45) / 0.5)
        col = tuple(int(WARM[i] + (SOFT[i] - WARM[i]) * a) for i in range(3))
        for i, ln in enumerate(_wrap(d, "complete, but not readable", font("sans", 34), w * 0.34)):
            d.text((w * 0.60 + 60, 640 + i * 46), ln, font=font("sans", 34), fill=col)
    _chrome(d, size, 1, "an edge list")


def _draw_graph(d, size, t, *, dim_outside=0.0, size_by_degree=0.0, hulls=0.0,
                cut_rings=0.0, roles=None, scale=1.0, dx=0, dy=0):
    pos, edges, comm, deg, hub = (REGION[k] for k in ("pos", "edges", "comm", "deg", "hub"))
    region = REGION["region"]
    if hulls > 0:
        for c in range(6):
            pts = [_screen(pos[i], size, scale, dx, dy) for i in range(len(pos)) if comm[i] == c and i in region]
            if len(pts) < 3:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            r = max(math.dist((cx, cy), p) for p in pts) + 30
            a = ease(hulls)
            col = tuple(int(PAPER[i] + (COMM_COLORS[c][i] - PAPER[i]) * 0.10 * a) for i in range(3))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    for a_, b_ in edges:
        inside = a_ in region and b_ in region
        # in-region edges are drawn toward SOFT, not LINE: at 1080p with h264 the page's hairline
        # grey disappears entirely, and the region has to stay legible as a graph.
        base = SOFT if inside else LINE
        alpha = 0.55 if inside else (1.0 - 0.85 * dim_outside) * 0.5
        col = tuple(int(PAPER[i] + (base[i] - PAPER[i]) * alpha) for i in range(3))
        d.line([_screen(pos[a_], size, scale, dx, dy), _screen(pos[b_], size, scale, dx, dy)],
               fill=col, width=3 if inside else 2)
    for i, p in enumerate(pos):
        inside = i in region
        alpha = 1.0 if inside else 1.0 - 0.85 * dim_outside
        base = ACCENT if i == hub else COMM_COLORS[comm[i]]
        col = tuple(int(PAPER[k] + (base[k] - PAPER[k]) * alpha) for k in range(3))
        r = 9 + (min(deg[i], 20) * 0.75 - 4) * size_by_degree
        if i == hub:
            r += 8
        x, y = _screen(p, size, scale, dx, dy)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        if cut_rings > 0 and i == hub:
            rr = r + 10 + 6 * math.sin(t * 6)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=ACCENT, width=3)
    if roles:
        for i, (node, text, prog) in enumerate(roles):
            if prog <= 0:
                continue
            x, y = _screen(pos[node], size, scale, dx, dy)
            f = font("mono_b", 25)
            tw = d.textlength(text, font=f)
            bx, by = x + 22, y - 16 - i % 2 * 34
            a = ease(prog)
            d.rectangle([bx - 8, by - 6, bx + tw + 8, by + 32], fill=PAPER, outline=ACCENT, width=2)
            d.text((bx, by), text, font=f, fill=ACCENT)


def seg2(d, size, t):
    _draw_graph(d, size, t, dim_outside=ease(t / 0.75), scale=0.95)
    hub = REGION["hub"]
    x, y = _screen(REGION["pos"][hub], size, 0.95)
    r = 40 + ease(min(t / 0.6, 1.0)) * 420
    if t < 0.72:
        d.ellipse([x - r, y - r, x + r, y + r], outline=ACCENT, width=4)
    if t > 0.5:
        a = ease((t - 0.5) / 0.4)
        col = tuple(int(PAPER[i] + (INK[i] - PAPER[i]) * a) for i in range(3))
        d.text((72, 130), "retrieved region", font=font("mono", 28), fill=ACCENT)
        d.text((72, 172), "45 nodes, 71 edges", font=font("serif_b", 46), fill=col)
    _chrome(d, size, 2, "retrieve")


def seg3(d, size, t):
    steps = ["degree", "betweenness", "k core", "articulation points", "bridges", "communities"]
    p = [stagger(t, i, len(steps)) for i in range(len(steps))]
    _draw_graph(d, size, t, dim_outside=1.0, size_by_degree=p[0],
                hulls=p[5], cut_rings=p[3], scale=0.95, dx=180)
    for i, s in enumerate(steps):
        y = 210 + i * 62
        done = p[i] > 0.5
        col = INK if done else LINE
        d.text((72, y), s, font=font("mono", 30), fill=col)
        if done:
            d.line([(40, y + 20), (52, y + 32)], fill=ACCENT, width=4)
            d.line([(52, y + 32), (66, y + 6)], fill=ACCENT, width=4)
    d.text((72, 130), "computed exactly, nothing learned", font=font("sans", 28), fill=MUTED)
    _chrome(d, size, 3, "measure")


def seg4(d, size, t):
    pos, comm, deg = REGION["pos"], REGION["comm"], REGION["deg"]
    hub = REGION["hub"]
    others = sorted((i for i in REGION["region"] if i != hub), key=lambda i: -deg[i])
    picks = [(hub, "HUB", stagger(t, 0, 5)), (hub, "CUT_NODE", stagger(t, 1, 5)),
             (others[1], "COMMUNITY_CORE", stagger(t, 2, 5)),
             (others[2], "CROSS_COMMUNITY_CONNECTOR", stagger(t, 3, 5)),
             (others[-1], "PERIPHERAL", stagger(t, 4, 5))]
    _draw_graph(d, size, t, dim_outside=1.0, size_by_degree=1.0, hulls=0.7,
                cut_rings=1.0, roles=picks, scale=0.80, dx=-330)
    names = ["CUT_NODE", "BRIDGE_EDGE", "HUB", "AUTHORITY", "BOTTLENECK_LINK",
             "CROSS_COMMUNITY_CONNECTOR", "BOUNDARY_NODE", "COMMUNITY_CORE",
             "ISOLATE", "PERIPHERAL", "FRAGILE_REGION"]
    d.text((size[0] - 72, 140), "eleven roles, one fixed rule each",
           font=font("sans", 27), fill=MUTED, anchor="rs")
    for i, nm in enumerate(names):
        used = nm in [p[1] for p in picks if p[2] > 0.4]
        d.text((size[0] - 72, 196 + i * 46), nm, font=font("mono", 26),
               fill=ACCENT if used else LINE, anchor="rs")
    _chrome(d, size, 4, "name")


def seg5(d, size, t):
    w, h = size
    lines = [("NODE 2553 = CUT_NODE", "mono_b", 46, ACCENT),
             ("  [components_before=1, components_after=6]", "mono", 38, SOFT),
             ("  -> articulation point, the only kind of node", "mono", 38, INK),
             ("     whose removal splits its own connected", "mono", 38, INK),
             ("     component", "mono", 38, INK)]
    d.rectangle([140, 300, w - 140, 300 + 6], fill=ACCENT)
    d.rectangle([140, 306, w - 140, 760], fill=PAPER, outline=LINE, width=2)
    shown = 0.0
    for i, (txt, fk, px, col) in enumerate(lines):
        pr = stagger(t, i, len(lines), overlap=0.25)
        if pr <= 0:
            continue
        n = max(1, int(len(txt) * ease(pr)))
        d.text((190, 360 + i * 76), txt[:n], font=font(fk, px), fill=col)
        if i >= 2:
            shown = max(shown, pr)
    if shown > 0.85:
        y = 360 + 4 * 76 + 52
        x2 = 190 + d.textlength("     component", font=font("mono", 38))
        d.line([190, y, x2, y], fill=ACCENT, width=4)
    d.text((140, 200), "evidence, and the consequence of removal",
           font=font("sans", 32), fill=MUTED)
    if t > 0.7:
        a = ease((t - 0.7) / 0.3)
        col = tuple(int(PAPER[i] + (ACCENT[i] - PAPER[i]) * a) for i in range(3))
        d.text((140, 810), "a table of numbers stops at the measurement",
               font=font("serif", 40), fill=col)
    _chrome(d, size, 5, "state the consequence")


def _bars(d, size, t, rows, ref, ref_label, title, sub, seg_n, chrome_label, maxv=80.0):
    w, h = size
    d.text((72, 130), title, font=font("mono", 28), fill=ACCENT)
    for i, ln in enumerate(_wrap(d, sub, font("serif", 44), w - 640)):
        d.text((72, 178 + i * 58), ln, font=font("serif", 44), fill=INK)
    x0, x1 = 620, w - 200
    top = 400
    bh, gap = 104, 62
    if ref is not None:
        rx = x0 + (x1 - x0) * ref / maxv
        d.line([rx, top - 30, rx, top + len(rows) * (bh + gap)], fill=MUTED, width=3)
        d.text((rx + 12, top - 62), ref_label, font=font("sans", 26), fill=MUTED)
        d.text((rx + 12, top - 32), f"{ref}", font=font("mono", 26), fill=MUTED)
    for i, (label, val, col) in enumerate(rows):
        y = top + i * (bh + gap)
        pr = stagger(t, i, len(rows), overlap=0.55)
        d.text((x0 - 30, y + bh / 2), label, font=font("sans_b", 32), fill=INK, anchor="rm")
        d.rectangle([x0, y, x1, y + bh], fill=WARM)
        bw = (x1 - x0) * (val / maxv) * ease(pr)
        d.rectangle([x0, y, x0 + bw, y + bh], fill=col)
        if pr > 0.6:
            d.text((x0 + bw + 20, y + bh / 2), f"{val}%", font=font("mono_b", 36),
                   fill=col, anchor="lm")
    _chrome(d, size, seg_n, chrome_label)


def seg6(d, size, t):
    _bars(d, size, t,
          [("BioGlyph", 70.6, ACCENT), ("the same numbers, as a table", 39.5, BLUE)],
          50.7, "no graph at all", "benchmark accuracy",
          "Identical measurements. Only the wording changes.", 6, "compare")


def seg7(d, size, t):
    _bars(d, size, t,
          [("cross-community connectors", 57.6, ACCENT), ("community cores", 46.9, MUTED),
           ("hubs", 42.1, MUTED), ("peripheral", 12.9, BLUE)],
          30.9, "background rate", "yeast gene essentiality",
          "The roles were compiled from connections alone, with the labels withheld.",
          7, "islamlab.org/bioglyph")


SCENES = {1: seg1, 2: seg2, 3: seg3, 4: seg4, 5: seg5, 6: seg6, 7: seg7}


def render(seg: dict, t: float, size: tuple[int, int]) -> Image.Image:
    img, d = _frame(size)
    SCENES[int(seg["n"])](d, size, t)
    # a short cross-fade in from white at each cut, so segment changes do not jar
    if t < 0.06:
        img = Image.blend(Image.new("RGB", size, PAPER), img, ease(t / 0.06))
    return img
