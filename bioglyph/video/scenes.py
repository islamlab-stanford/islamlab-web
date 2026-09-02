"""Frame rendering for the BioGlyph explainer, one scene per narration segment.

The visual system is the lab's Graph Foundation Model explainer, sampled from its own frames so
the two videos read as siblings: deep navy ground, a thin accent rule at the very top, a
letterspaced project name and an "03 / 07" counter in the header, one large serif headline per
segment, an all-caps summary line centred at the foot, and a progress bar across the bottom.
1280x720, like GFM's.

Two rules keep it legible at video size:
  - nothing below 15 px, since h264 at this bitrate eats thin small type;
  - the graph geometry is computed once with a fixed seed and reused across segments 2 to 5, so
    the viewer tracks one region rather than re-reading a new picture each time.

`render(seg, t, size)` returns a PIL image for progress t in [0, 1] within segment `seg`.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- palette, sampled from graph-foundation-model/media/gfm-explainer.mp4 ---
BG = (9, 25, 52)            # #091934
PANEL = (18, 42, 73)        # #122a49
RULE = (27, 43, 71)
TRACK = (43, 59, 84)        # #2b3b54
ACCENT = (196, 70, 58)      # #c4463a
WHITE = (255, 255, 255)
TEXT = (205, 219, 232)
DIM = (125, 148, 174)
NODE = (143, 179, 207)
EDGE = (36, 64, 95)
BLUE = (94, 152, 200)
GOLD = (203, 158, 72)
GREEN = (122, 163, 118)

FONTS = Path("C:/Windows/Fonts")
_cache: dict = {}
N_SEG = 7


def font(kind: str, px: int):
    key = (kind, px)
    if key not in _cache:
        name = {"serif": "cambria.ttc", "serif_b": "cambriab.ttf", "mono": "consola.ttf",
                "mono_b": "consolab.ttf", "sans": "calibri.ttf", "sans_b": "calibrib.ttf"}[kind]
        _cache[key] = ImageFont.truetype(str(FONTS / name), px)
    return _cache[key]


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def stagger(t: float, i: int, n: int, overlap: float = 0.45) -> float:
    if n <= 1:
        return ease(t)
    span = 1.0 / (n - (n - 1) * overlap)
    start = i * span * (1 - overlap)
    return ease((t - start) / span)


def mix(a, b, k: float):
    k = max(0.0, min(1.0, k))
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def track(d, text: str, f, x: float, y: float, sp: float, fill):
    """Letterspaced text; PIL has no tracking, and the header needs it."""
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + sp


def wrap(d, text, f, max_w):
    out, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


# --- the region, laid out once ---------------------------------------------

def _layout(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    sizes = [12, 11, 7, 5, 5, 5]
    comm, pos, edges = [], [], []
    centers = [(math.cos(a) * 300, math.sin(a) * 300)
               for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    for c, (sz, (cx, cy)) in enumerate(zip(sizes, centers)):
        for _ in range(sz):
            pos.append((cx + rng.normal(0, 74), cy + rng.normal(0, 74)))
            comm.append(c)
    hub = 0
    pos[hub] = (0.0, 0.0)
    for c in range(6):
        members = [i for i, cc in enumerate(comm) if cc == c and i != hub]
        for a in range(len(members) - 1):
            edges.append((members[a], members[a + 1]))
        for a in rng.choice(members, size=max(1, len(members) // 3), replace=False):
            edges.append((int(a), int(rng.choice(members))))
        edges.append((hub, int(members[0])))
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
    for a, b in edges:
        if a in region or b in region:
            region |= {a, b}
    return {"pos": pos, "edges": edges, "comm": comm, "deg": deg, "hub": hub, "region": region}


REGION = _layout()
COMM = [BLUE, GREEN, GOLD, BLUE, GREEN, DIM]


# --- shared chrome, following GFM's ----------------------------------------

def chrome(d, size, seg_n: int, headline: str, footer: str, t: float):
    w, h = size
    d.rectangle([0, 0, w, 6], fill=ACCENT)
    track(d, "BIOGLYPH", font("sans_b", 17), 58, 46, 2.4, TEXT)
    d.text((w - 58, 46), f"{seg_n:02d} / {N_SEG:02d}", font=font("sans_b", 17), fill=DIM,
           anchor="ra")
    d.line([58, 80, w - 58, 80], fill=RULE, width=1)

    f = font("serif_b", 44)
    for i, ln in enumerate(wrap(d, headline, f, w - 380)[:2]):
        d.text((58, 104 + i * 52), ln, font=f, fill=WHITE)

    if footer:
        ff = font("sans_b", 14)
        tw = sum(d.textlength(c, font=ff) + 1.6 for c in footer.upper())
        track(d, footer.upper(), ff, (w - tw) / 2, 634, 1.6, TEXT)

    d.line([58, 700, w - 58, 700], fill=TRACK, width=3)
    done = (seg_n - 1 + ease(t)) / N_SEG
    d.line([58, 700, 58 + (w - 116) * done, 700], fill=ACCENT, width=3)


def panel(d, box, border=None, fill=PANEL):
    d.rectangle(box, fill=fill)
    if border:
        d.rectangle(box, outline=border, width=2)


# --- graph drawing ---------------------------------------------------------

def sc(p, size, scale, dx, dy):
    w, h = size
    return (w / 2 + p[0] * scale + dx, h / 2 + p[1] * scale + dy + 24)


def graph(d, size, t, *, dim_out=0.0, by_deg=0.0, hulls=0.0, rings=0.0,
          roles=None, scale=1.0, dx=0, dy=0):
    pos, edges, comm, deg, hub = (REGION[k] for k in ("pos", "edges", "comm", "deg", "hub"))
    reg = REGION["region"]
    if hulls > 0:
        for c in range(6):
            pts = [sc(pos[i], size, scale, dx, dy)
                   for i in range(len(pos)) if comm[i] == c and i in reg]
            if len(pts) < 3:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            r = max(math.dist((cx, cy), p) for p in pts) + 26
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix(BG, COMM[c], 0.13 * ease(hulls)))
    for a, b in edges:
        inside = a in reg and b in reg
        col = mix(BG, EDGE, 1.0) if inside else mix(BG, EDGE, 1.0 - 0.8 * dim_out)
        d.line([sc(pos[a], size, scale, dx, dy), sc(pos[b], size, scale, dx, dy)],
               fill=col, width=2 if inside else 1)
    for i, p in enumerate(pos):
        inside = i in reg
        base = ACCENT if i == hub else COMM[comm[i]]
        col = base if inside else mix(BG, base, 1.0 - 0.8 * dim_out)
        r = 5 + (min(deg[i], 20) * 0.5 - 2.5) * by_deg + (6 if i == hub else 0)
        x, y = sc(p, size, scale, dx, dy)
        d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        if rings > 0 and i == hub:
            rr = r + 8 + 4 * math.sin(t * 6)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=ACCENT, width=2)
    for i, (node, label, pr) in enumerate(roles or []):
        if pr <= 0:
            continue
        x, y = sc(pos[node], size, scale, dx, dy)
        f = font("mono_b", 16)
        tw = d.textlength(label, font=f)
        bx, by = x + 16, y - 12 - (i % 2) * 26
        panel(d, [bx - 7, by - 5, bx + tw + 7, by + 21], border=ACCENT)
        d.text((bx, by), label, font=f, fill=WHITE)


# --- segments --------------------------------------------------------------

def seg1(d, size, t):
    w, h = size
    rng = np.random.default_rng(3)
    f = font("mono", 16)
    for row in range(20):
        y = 190 + row * 22 - int(t * 26)
        if not (176 < y < 600):
            continue
        line = "   ".join(f"{rng.integers(1,999):3d} {rng.integers(1,999):3d}" for _ in range(7))
        d.text((58, y), line, font=f, fill=mix(BG, DIM, 0.30 + 0.35 * min(1, (row + 1) / 5)))
    panel(d, [700, 176, w - 58, 600], border=RULE)
    d.text((730, 214), "THE QUESTION", font=font("sans_b", 14), fill=ACCENT)
    for i, ln in enumerate(wrap(d, "Which node holds this region together?", font("serif", 34), 430)):
        d.text((730, 254 + i * 44), ln, font=font("serif", 34), fill=WHITE)
    if (t * 3) % 1 < 0.55:
        d.rectangle([730, 350, 733, 384], fill=ACCENT)
    if t > 0.4:
        k = ease((t - 0.4) / 0.5)
        for i, ln in enumerate(wrap(d, "The structure has to be recovered from the text before "
                                       "the question can be answered.", font("sans", 21), 430)):
            d.text((730, 430 + i * 30), ln, font=font("sans", 21), fill=mix(PANEL, TEXT, k))
    chrome(d, size, 1, "A network as text is complete, not readable.",
           "an edge list carries every connection and no structure", t)


def seg2(d, size, t):
    graph(d, size, t, dim_out=ease(t / 0.75), scale=0.78, dx=-150)
    x, y = sc(REGION["pos"][REGION["hub"]], size, 0.78, -150, 0)
    if t < 0.72:
        r = 30 + ease(min(t / 0.6, 1.0)) * 300
        d.ellipse([x - r, y - r, x + r, y + r], outline=ACCENT, width=3)
    if t > 0.45:
        k = ease((t - 0.45) / 0.4)
        panel(d, [880, 300, size[0] - 58, 430], border=ACCENT)
        d.text((910, 326), "RETRIEVED REGION", font=font("sans_b", 14), fill=ACCENT)
        d.text((910, 356), "45 nodes", font=font("serif_b", 32), fill=mix(PANEL, WHITE, k))
        d.text((910, 394), "71 edges", font=font("serif_b", 26), fill=mix(PANEL, TEXT, k))
    chrome(d, size, 2, "Retrieve the region around the question.",
           "everything after this is computed on the region, not the network", t)


def seg3(d, size, t):
    steps = ["degree", "betweenness", "k core", "articulation points", "bridges", "communities"]
    p = [stagger(t, i, len(steps)) for i in range(len(steps))]
    graph(d, size, t, dim_out=1.0, by_deg=p[0], hulls=p[5], rings=p[3], scale=0.78, dx=170)
    for i, s in enumerate(steps):
        y = 210 + i * 62
        on = p[i] > 0.5
        d.text((92, y), s, font=font("mono", 21), fill=WHITE if on else mix(BG, DIM, 0.55))
        if on:
            d.line([(58, y + 14), (68, y + 24)], fill=ACCENT, width=3)
            d.line([(68, y + 24), (82, y + 4)], fill=ACCENT, width=3)
    chrome(d, size, 3, "Classical algorithms do the arithmetic.",
           "exact, seeded, identical on every run", t)


def seg4(d, size, t):
    deg, hub = REGION["deg"], REGION["hub"]
    others = sorted((i for i in REGION["region"] if i != hub), key=lambda i: -deg[i])
    picks = [(hub, "HUB", stagger(t, 0, 5)), (hub, "CUT_NODE", stagger(t, 1, 5)),
             (others[1], "COMMUNITY_CORE", stagger(t, 2, 5)),
             (others[2], "CROSS_COMMUNITY_CONNECTOR", stagger(t, 3, 5)),
             (others[-1], "PERIPHERAL", stagger(t, 4, 5))]
    graph(d, size, t, dim_out=1.0, by_deg=1.0, hulls=0.7, rings=1.0, roles=picks,
          scale=0.62, dx=-250)
    names = ["CUT_NODE", "BRIDGE_EDGE", "HUB", "AUTHORITY", "BOTTLENECK_LINK",
             "CROSS_COMMUNITY_CONNECTOR", "BOUNDARY_NODE", "COMMUNITY_CORE",
             "ISOLATE", "PERIPHERAL", "FRAGILE_REGION"]
    shown = [p[1] for p in picks if p[2] > 0.4]
    d.text((size[0] - 58, 196), "ELEVEN ROLES", font=font("sans_b", 14), fill=ACCENT, anchor="ra")
    for i, nm in enumerate(names):
        d.text((size[0] - 58, 228 + i * 34), nm, font=font("mono", 17),
               fill=WHITE if nm in shown else mix(BG, DIM, 0.5), anchor="ra")
    chrome(d, size, 4, "One fixed rule assigns each role.",
           "the algorithm decides, never the model", t)


def seg5(d, size, t):
    w, h = size
    panel(d, [58, 200, w - 58, 560], border=RULE)
    d.rectangle([58, 200, w - 58, 203], fill=ACCENT)
    rows = [("NODE 2553 = CUT_NODE", "mono_b", 30, ACCENT),
            ("  [components_before=1, components_after=6]", "mono", 22, TEXT),
            ("  -> articulation point, the only kind of node", "mono", 22, WHITE),
            ("     whose removal splits its own component", "mono", 22, WHITE)]
    last = 0.0
    for i, (txt, fk, px, col) in enumerate(rows):
        pr = stagger(t, i, len(rows), overlap=0.2)
        if pr <= 0:
            continue
        d.text((92, 240 + i * 54), txt[:max(1, int(len(txt) * ease(pr)))], font=font(fk, px),
               fill=col)
        if i >= 2:
            last = max(last, pr)
    if last > 0.9:
        y = 240 + 3 * 54 + 34
        d.line([92, y, 92 + d.textlength("     whose removal splits its own component",
                                         font=font("mono", 22)), y], fill=ACCENT, width=3)
    if t > 0.72:
        k = ease((t - 0.72) / 0.28)
        d.text((58, 588), "a table of numbers stops at the measurement",
               font=font("serif", 26), fill=mix(BG, ACCENT, k))
    chrome(d, size, 5, "Each role carries its evidence, and its consequence.",
           "the clause a table of measurements leaves out", t)


def bars(d, size, t, rows, ref, ref_label, seg_n, tt, headline, footer, maxv=80.0):
    w, h = size
    x0, x1, top, bh, gap = 470, w - 150, 236, 52, 34
    if ref is not None:
        rx = x0 + (x1 - x0) * ref / maxv
        d.line([rx, top - 26, rx, top + len(rows) * (bh + gap) - gap + 10], fill=DIM, width=2)
        d.text((rx + 10, top - 48), ref_label, font=font("sans", 17), fill=DIM)
        d.text((rx + 10, top - 26), f"{ref}%", font=font("mono", 17), fill=DIM)
    for i, (label, val, col) in enumerate(rows):
        y = top + i * (bh + gap)
        pr = stagger(t, i, len(rows), overlap=0.55)
        d.text((x0 - 24, y + bh / 2), label, font=font("sans_b", 20), fill=WHITE, anchor="rm")
        d.rectangle([x0, y, x1, y + bh], fill=PANEL)
        bw = (x1 - x0) * (val / maxv) * ease(pr)
        d.rectangle([x0, y, x0 + bw, y + bh], fill=col)
        if pr > 0.6:
            d.text((x0 + bw + 16, y + bh / 2), f"{val}%", font=font("mono_b", 26), fill=col,
                   anchor="lm")
    chrome(d, size, seg_n, headline, footer, tt)


def seg6(d, size, t):
    bars(d, size, t,
         [("BioGlyph", 70.6, ACCENT), ("the same numbers, as a table", 39.5, BLUE)],
         50.7, "no network at all", 6, t,
         "Only the wording changes.",
         "identical measurements, and the table scores below no network at all")


def seg7(d, size, t):
    bars(d, size, t,
         [("cross-community connectors", 57.6, ACCENT), ("community cores", 46.9, DIM),
          ("hubs", 42.1, DIM), ("peripheral", 12.9, BLUE)],
         30.9, "background rate", 7, t,
         "The same roles carry biological meaning.",
         "compiled from connections alone, with the labels withheld")


SCENES = {1: seg1, 2: seg2, 3: seg3, 4: seg4, 5: seg5, 6: seg6, 7: seg7}


def render(seg: dict, t: float, size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    SCENES[int(seg["n"])](d, size, t)
    if t < 0.06:                       # short fade in from the ground colour at each cut
        img = Image.blend(Image.new("RGB", size, BG), img, ease(t / 0.06))
    return img
