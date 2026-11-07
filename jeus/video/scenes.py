"""Frame rendering for the Jeus explainer, one scene per narration segment.

The visual system is the lab's explainers (Graph Foundation Model, BioGlyph): deep navy ground, a
thin accent rule at the very top, a letterspaced project name and an "03 / 07" counter in the
header, one large serif headline per segment, an all-caps summary line centred at the foot, and a
progress bar across the bottom. 1280x720. Nothing is drawn below 15 px, since h264 at this bitrate
eats thin small type.

Every number the scenes show is read from ../assets/results.js and ../assets/examples.js, the files
the page itself reads, so the video cannot show a number the page does not.

`render(seg, t, size)` returns a PIL image for progress t in [0, 1] within segment `seg`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
ASSETS = HERE.parent / "assets"

# --- palette, the GFM / BioGlyph explainer palette ---
BG = (9, 25, 52)
PANEL = (18, 42, 73)
RULE = (27, 43, 71)
TRACK = (43, 59, 84)
ACCENT = (196, 70, 58)
WHITE = (255, 255, 255)
TEXT = (205, 219, 232)
DIM = (125, 148, 174)
BLUE = (94, 152, 200)
GOLD = (203, 158, 72)
GREEN = (122, 163, 118)
PLUM = (160, 128, 184)
AGENT_COLOUR = {"Jeus": ACCENT, "Codex CLI": BLUE, "Claude Code": GREEN, "Biomni A1": PLUM}

FONTS = Path(os.environ.get("JEUS_VIDEO_FONTS", "C:/Windows/Fonts"))
_cache: dict = {}
N_SEG = 7


def _js(name: str) -> dict:
    text = (ASSETS / name).read_text(encoding="utf-8")
    return json.loads(text[text.index("=") + 1:].rstrip().rstrip(";"))


RESULTS = _js("results.js")
EXAMPLES = _js("examples.js")
E2 = next(e for e in EXAMPLES["examples"] if e["id"] == "E2")
GLM = {r["agent"]: r for r in E2["runs"] if r["model"] == "GLM-5.3"}


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


def typed(text: str, pr: float) -> str:
    return text[:max(0, int(round(len(text) * ease(pr))))]


def fmt_int(n: int) -> str:
    return f"{n:,}"


# --- shared chrome ---------------------------------------------------------

def chrome(d, size, seg_n: int, headline: str, footer: str, t: float):
    w, h = size
    d.rectangle([0, 0, w, 6], fill=ACCENT)
    track(d, "JEUS", font("sans_b", 17), 58, 46, 2.4, TEXT)
    d.text((w - 58, 46), f"{seg_n:02d} / {N_SEG:02d}", font=font("sans_b", 17), fill=DIM, anchor="ra")
    d.line([58, 80, w - 58, 80], fill=RULE, width=1)
    f = font("serif_b", 44)
    for i, ln in enumerate(wrap(d, headline, f, w - 300)[:2]):
        d.text((58, 104 + i * 52), ln, font=f, fill=WHITE)
    if footer:
        ff = font("sans_b", 14)
        tw = sum(d.textlength(c, font=ff) + 1.6 for c in footer.upper())
        track(d, footer.upper(), ff, (w - tw) / 2, 634, 1.6, TEXT)
    d.line([58, 700, w - 58, 700], fill=TRACK, width=3)
    done = (seg_n - 1 + ease(t)) / N_SEG
    d.line([58, 700, 58 + (w - 116) * done, 700], fill=ACCENT, width=3)


def panel(d, box, border=None, fill=PANEL, width=2):
    d.rectangle(box, fill=fill)
    if border:
        d.rectangle(box, outline=border, width=width)


def label(d, xy, text, colour=ACCENT):
    d.text(xy, text, font=font("sans_b", 14), fill=colour)


def doc_icon(d, x, y, colour):
    """A small document: a page with its top right corner folded, 16 x 21 px."""
    d.polygon([(x, y), (x + 10, y), (x + 16, y + 6), (x + 16, y + 21), (x, y + 21)], outline=colour, width=2)
    d.line([(x + 10, y), (x + 10, y + 6), (x + 16, y + 6)], fill=colour, width=2)
    for i in range(3):
        d.line([(x + 4, y + 10 + i * 4), (x + 12, y + 10 + i * 4)], fill=colour, width=1)


# --- segments --------------------------------------------------------------

def seg1(d, size, t):
    w, h = size
    panel(d, [58, 176, 640, 600], border=RULE)
    label(d, (88, 206), "THE DATA")
    files = [("expression.tsv", "38,210 genes x 96 samples"), ("metadata.csv", "96 rows, 14 columns"),
             ("cells.h5ad", "12,400 cells"), ("clinical.xlsx", "2 sheets"), ("README.txt", "")]
    for i, (name, note) in enumerate(files):
        pr = stagger(min(t / 0.6, 1.0), i, len(files), overlap=0.3)
        if pr <= 0:
            continue
        y = 246 + i * 58
        doc_icon(d, 90, y + 3, mix(PANEL, DIM, pr))
        d.text((122, y), typed(name, pr), font=font("mono_b", 22), fill=mix(PANEL, WHITE, pr))
        d.text((122, y + 30), note, font=font("sans", 17), fill=mix(PANEL, DIM, pr))
    panel(d, [700, 176, w - 58, 600], border=RULE)
    label(d, (730, 206), "THE QUESTION")
    f = font("serif", 32)
    for i, ln in enumerate(wrap(d, "Which genes separate the two patient groups?", f, 440)):
        d.text((730, 246 + i * 42), ln, font=f, fill=WHITE)
    if (t * 3) % 1 < 0.55:
        d.rectangle([730, 340, 733, 372], fill=ACCENT)
    verbs = ["load the files", "choose a method", "write the code", "run it", "read what comes back"]
    for i, v in enumerate(verbs):
        pr = stagger((t - 0.45) / 0.55, i, len(verbs), overlap=0.3)
        if pr <= 0:
            continue
        y = 404 + i * 34
        d.text((730, y), f"{i + 1}", font=font("mono", 18), fill=mix(PANEL, ACCENT, pr))
        d.text((760, y), v, font=font("sans", 21), fill=mix(PANEL, TEXT, pr))
    chrome(d, size, 1, "A folder of data, and a question.", "the work starts after the question", t)


def seg2(d, size, t):
    w, h = size
    steps = ["list the files", "write the analysis", "run it", "read the result", "go on to the next step",
             "write the answer"]
    d.line([73, 206, 73, 206 + (len(steps) - 1) * 62], fill=TRACK, width=3)
    for i, s in enumerate(steps):
        pr = stagger(t, i, len(steps), overlap=0.4)
        y = 196 + i * 62
        on = pr > 0.5
        d.ellipse([64, y + 6, 82, y + 24], fill=ACCENT if on else PANEL, outline=TRACK if not on else ACCENT, width=2)
        d.text((104, y), s, font=font("mono", 22), fill=WHITE if on else mix(BG, DIM, 0.55))
    panel(d, [560, 176, w - 58, 600], border=RULE)
    label(d, (590, 206), "EVERY STEP RECORDED")
    log = ["01  list the files", "02  python   explore.py", "    96 samples in 2 groups",
           "03  python   differential.py", "    312 genes at q < 0.05", "04  python   enrichment.py",
           "    8 pathways enriched", "05  write the answer"]
    for i, line in enumerate(log):
        pr = stagger(t, i, len(log), overlap=0.35)
        if pr <= 0:
            continue
        d.text((590, 246 + i * 40), typed(line, pr), font=font("mono", 19),
               fill=mix(PANEL, TEXT if not line.startswith(" ") else DIM, pr))
    chrome(d, size, 2, "Jeus writes and runs the analysis.",
           "open-weight or proprietary model, the same loop", t)


def seg3(d, size, t):
    w, h = size
    stem = E2["published_text"].split(" (A)")[0]
    options = []
    rest = E2["published_text"]
    for letter in "ABCD":
        marker = f"({letter}) "
        start = rest.index(marker) + len(marker)
        nxt = rest.find(f"({chr(ord(letter) + 1)}) ", start)
        options.append((letter, rest[start: nxt if nxt > 0 else None].strip()))
    panel(d, [58, 176, w - 58, 600], border=RULE)
    label(d, (88, 206), "BAISBENCH  \u00b7  PUBLISHED QUESTION")
    f = font("serif", 30)
    y = 240
    for ln in wrap(d, stem, f, w - 200):
        d.text((88, y), ln, font=f, fill=WHITE)
        y += 40
    y += 14
    for i, (letter, text) in enumerate(options):
        pr = stagger((t - 0.18) / 0.6, i, 4, overlap=0.35)
        if pr <= 0:
            continue
        d.text((88, y), letter, font=font("mono_b", 22), fill=mix(PANEL, ACCENT, pr))
        lines = wrap(d, text, font("sans", 22), w - 300)
        for j, ln in enumerate(lines):
            d.text((128, y + j * 28), ln, font=font("sans", 22), fill=mix(PANEL, TEXT, pr))
        y += 28 * len(lines) + 12
    if t > 0.74:
        k = ease((t - 0.74) / 0.26)
        panel(d, [w - 330, 520, w - 88, 576], border=ACCENT, fill=mix(PANEL, ACCENT, 0.15 * k))
        d.text((w - 310, 536), "ANSWER KEY", font=font("sans_b", 16), fill=mix(PANEL, TEXT, k))
        d.text((w - 150, 528), E2["reference_answer"], font=font("serif_b", 34), fill=mix(PANEL, WHITE, k))
    chrome(d, size, 3, "A question from a published single-cell study.", "four options; the answer key says A", t)


def seg4(d, size, t):
    w, h = size
    agents = ["Jeus", "Codex CLI", "Claude Code"]
    for i, agent in enumerate(agents):
        run = GLM[agent]
        pr = stagger(min(t / 0.55, 1.0), i, 3, overlap=0.45)
        if pr <= 0:
            continue
        x0 = 58 + i * 404
        col = AGENT_COLOUR[agent]
        panel(d, [x0, 176, x0 + 356, 452], border=col if agent == "Jeus" else RULE, width=3 if agent == "Jeus" else 2)
        d.rectangle([x0, 176, x0 + 8, 452], fill=col)
        d.text((x0 + 30, 200), agent, font=font("sans_b", 24), fill=mix(PANEL, WHITE, pr))
        d.text((x0 + 30, 244), run["answer"], font=font("serif_b", 64), fill=mix(PANEL, col, pr))
        good = run["credit"] >= 1
        d.text((x0 + 30, 338), "CORRECT" if good else "INCORRECT", font=font("mono_b", 18),
               fill=mix(PANEL, GREEN if good else ACCENT, pr))
        d.text((x0 + 30, 372), f"{run['calls']} calls", font=font("mono", 19), fill=mix(PANEL, TEXT, pr))
        d.text((x0 + 30, 400), f"{fmt_int(run['tokens'])} tokens", font=font("mono", 19), fill=mix(PANEL, TEXT, pr))
    if t > 0.5:
        k = ease((t - 0.5) / 0.3)
        label(d, (58, 484), "WHAT JEUS DID", mix(BG, ACCENT, k))
        f = font("sans", 21)
        for j, ln in enumerate(wrap(d, GLM["Jeus"]["method"], f, w - 116)[:3]):
            d.text((58, 512 + j * 30), ln, font=f, fill=mix(BG, TEXT, k))
    chrome(d, size, 4, "The same model, three agents.", "GLM-5.3; one evaluation per agent and question", t)


def seg5(d, size, t):
    w, h = size
    benches = RESULTS["benchmarks"]
    agents = ["Jeus", "Codex CLI", "Claude Code", "Biomni A1"]
    x0, x1, top, base = 100, w - 58, 230, 560
    gw = (x1 - x0) / len(benches)
    bw, gap = 58, 14
    for v in (0, 25, 50, 75, 100):
        y = base - (base - top) * v / 100
        d.line([x0, y, x1, y], fill=RULE if v else TRACK, width=1 if v else 2)
        d.text((x0 - 12, y), str(v), font=font("mono", 16), fill=DIM, anchor="rm")
    for gi, b in enumerate(benches):
        present = [a for a in agents if a in b["scores"]]
        total = len(present) * bw + (len(present) - 1) * gap
        gx = x0 + gi * gw + (gw - total) / 2
        for ai, a in enumerate(present):
            pr = stagger(t, gi * 4 + ai, 12, overlap=0.72)
            v = b["scores"][a]
            x = gx + ai * (bw + gap)
            hh = (base - top) * v / 100 * ease(pr)
            d.rectangle([x, base - hh, x + bw, base], fill=mix(PANEL, AGENT_COLOUR[a], 1.0 if a == "Jeus" else 0.8))
            if pr > 0.7:
                d.text((x + bw / 2, base - hh - 8), f"{v:.1f}", font=font("mono_b", 18 if a == "Jeus" else 16),
                       fill=WHITE if a == "Jeus" else TEXT, anchor="mb")
        d.text((x0 + gi * gw + gw / 2, base + 16), b["name"], font=font("sans_b", 20), fill=WHITE, anchor="mt")
        d.text((x0 + gi * gw + gw / 2, base + 44), f"{b['metric']}  \u00b7  {b['questions']} questions",
               font=font("sans", 16), fill=DIM, anchor="mt")
    lx = w - 58
    for a in reversed(agents):
        f = font("sans", 17)
        tw = d.textlength(a, font=f)
        d.text((lx, 196), a, font=f, fill=TEXT, anchor="ra")
        d.rectangle([lx - tw - 22, 200, lx - tw - 8, 214], fill=AGENT_COLOUR[a])
        lx -= tw + 46
    chrome(d, size, 5, "Highest five-model mean on three benchmarks.",
           "five open-weight models, one evaluation per agent, model and question", t)


def seg6(d, size, t):
    w, h = size
    mem, cost = RESULTS["memory"], RESULTS["cost"]
    cards = [
        ([58, 190, 620, 560], "PEAK PROCESS MEMORY",
         f"{mem['low']:.1f}\u2013{mem['high']:.1f}\u00d7",
         f"of Codex CLI, Claude Code and Biomni A1, relative to Jeus, over {mem['comparisons']} benchmark summaries; "
         "model servers excluded for every agent"),
        ([660, 190, w - 58, 560], "MODEL-ACCESS COSTS",
         f"{cost['low']:.0f}\u2013{cost['high']:.0f}% lower",
         f"with Claude Sonnet 5 and GPT-6 Sol, in {cost['lower_in']} of {cost['of']} benchmark comparisons; "
         "judging excluded"),
    ]
    for i, (box, head, number, sub) in enumerate(cards):
        pr = stagger(t, i, 2, overlap=0.5)
        if pr <= 0:
            continue
        panel(d, box, border=ACCENT if i == 0 else RULE, width=3 if i == 0 else 2)
        d.text((box[0] + 30, box[1] + 28), head, font=font("sans_b", 15), fill=mix(PANEL, ACCENT, pr))
        d.text((box[0] + 30, box[1] + 66), number, font=font("serif_b", 76), fill=mix(PANEL, WHITE, pr))
        f = font("sans", 21)
        for j, ln in enumerate(wrap(d, sub, f, box[2] - box[0] - 60)):
            d.text((box[0] + 30, box[1] + 190 + j * 30), ln, font=f, fill=mix(PANEL, TEXT, pr))
    chrome(d, size, 6, "Less memory, lower cost.", "the same questions, the same models, the same limits for every agent", t)


def seg7(d, size, t):
    w, h = size
    k = ease(min(t / 0.5, 1.0))
    d.text((58, 240), "Jeus", font=font("serif_b", 150), fill=mix(BG, WHITE, k))
    for (x, y, r, c) in [(400, 262, 11, GOLD), (436, 282, 11, ACCENT), (412, 314, 9, BLUE), (446, 324, 8, GREEN)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=mix(BG, c, k))
    k2 = ease((t - 0.3) / 0.4)
    d.text((62, 444), "islamlab.org/jeus", font=font("mono_b", 30), fill=mix(BG, ACCENT, k2))
    d.text((62, 496), "Every number here comes from the manuscript's released records.", font=font("sans", 21),
           fill=mix(BG, TEXT, k2))
    chrome(d, size, 7, "Ask your data a question.",
           "five benchmarks  \u00b7  24 clinical prediction tasks  \u00b7  open-weight or proprietary models", t)


SCENES = {1: seg1, 2: seg2, 3: seg3, 4: seg4, 5: seg5, 6: seg6, 7: seg7}


def render(seg: dict, t: float, size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    SCENES[int(seg["n"])](d, size, t)
    if t < 0.06:
        img = Image.blend(Image.new("RGB", size, BG), img, ease(t / 0.06))
    return img


if __name__ == "__main__":  # preview frames, for iterating on the scenes
    out = HERE / "preview"
    out.mkdir(exist_ok=True)
    for n in range(1, N_SEG + 1):
        for tt in (0.35, 0.9):
            render({"n": n}, tt, (1280, 720)).save(out / f"seg{n:02d}_t{int(tt * 100)}.png")
    print("previews in", out)
