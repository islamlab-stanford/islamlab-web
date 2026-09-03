"""Render the page's figures from the manuscript's own data.

Three figures, each showing something the page cannot say in prose or a CSS bar:

  og.png              the social card. Every other project page has one; sharing a link to this
                      page produced a blank preview until now.
  tokens-accuracy.png accuracy against median prompt length, with the context limit marked. This
                      is the argument the accuracy chart cannot make: the compiled description is
                      both shorter and better, and the table is longer and worse.
  reactome-targets.png the knockout screen's ranked targets beside their DepMap dependency class,
                      a biomedical result the page did not show at all.

Every value is read from figures/numbers.json. Nothing is retyped.

Run:  python build_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

FIGS = Path(r"c:\Users\ucchw\OneDrive - Stanford\BioGlyph"
            r"\Language-encoded network topology for complex networks\figures")
OUT = Path(__file__).parent / "assets"

INK = "#17202c"
SOFT = "#465262"
MUTED = "#707a86"
LINE = "#d9d6ce"
WARM = "#f5f3ee"
ACCENT = "#a83f35"
BLUE = "#476d89"
GREEN = "#628060"
GOLD = "#b38536"
NAVY = "#091934"

# Cambria and Consolas stand in for the page's Source Serif 4 and IBM Plex Mono, which are
# webfonts and not installed locally.
SERIF = font_manager.FontProperties(fname="C:/Windows/Fonts/cambria.ttc")
SERIF_B = font_manager.FontProperties(fname="C:/Windows/Fonts/cambriab.ttf")
MONO = font_manager.FontProperties(fname="C:/Windows/Fonts/consola.ttf")
SANS = font_manager.FontProperties(fname="C:/Windows/Fonts/calibri.ttf")
SANS_B = font_manager.FontProperties(fname="C:/Windows/Fonts/calibrib.ttf")

NUMS = json.loads((FIGS / "numbers.json").read_text(encoding="utf-8"))
BUDGET = 24576


def save(fig, name: str, dpi: int = 150) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  {name:24s} {p.stat().st_size / 1024:7.1f} KB")


# ---------------------------------------------------------------- og card ---

def og_card() -> None:
    """1200x630 social card, in the explainer's navy so the two read as one project."""
    fig = plt.figure(figsize=(12, 6.3), dpi=100)
    fig.patch.set_facecolor(NAVY)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.set_xlim(0, 1200)
    ax.set_ylim(0, 630)

    ax.add_patch(Rectangle((0, 620), 1200, 10, color="#c4463a"))
    ax.text(64, 540, "ISLAM LAB  \u00b7  STANFORD MEDICINE", color="#7d94ae",
            fontproperties=SANS_B, fontsize=13)
    ax.text(64, 452, "BioGlyph", color="white", fontproperties=SERIF_B, fontsize=64)
    ax.text(64, 396, "A network, stated in words.", color="#cddbe8",
            fontproperties=SERIF, fontsize=30)

    body = ("A deterministic compiler turns graph topology into named structural\n"
            "roles, each with its evidence and what removing it would do.")
    ax.text(64, 300, body, color="#9fb4c9", fontproperties=SANS, fontsize=19, linespacing=1.5)

    arms = NUMS["core"]["headline"]["pooled_8b"]["arms"]
    stats = [(f'{arms["R5_BioGlyph"]["sys"]["acc"]}%', "reading named roles"),
             (f'{arms["R3_RawMetrics"]["sys"]["acc"]}%', "the same numbers as a table"),
             (f'{arms["R0_NoGraph"]["sys"]["acc"]}%', "no network at all")]
    for i, (big, small) in enumerate(stats):
        x = 64 + i * 372
        ax.add_patch(Rectangle((x, 96), 340, 108, color="#122a49"))
        ax.text(x + 26, 148, big, color="#c4463a" if i == 0 else "white",
                fontproperties=SERIF_B, fontsize=40)
        ax.text(x + 26, 118, small, color="#7d94ae", fontproperties=SANS, fontsize=15)
    ax.text(1136, 40, "islamlab.org/bioglyph", color="#7d94ae", fontproperties=MONO,
            fontsize=15, ha="right")
    save(fig, "og.png", dpi=100)


# ------------------------------------------------- accuracy vs prompt size ---

def tokens_accuracy() -> None:
    """The point the bar chart cannot make: shorter AND better, on one axis pair."""
    arms = NUMS["core"]["headline"]["pooled_8b"]["arms"]
    pts = [("BioGlyph", "R5_BioGlyph", ACCENT, (14, 10)),
           ("names + evidence", "R5_NamesEvidence", SOFT, (12, -20)),
           ("names only", "R5_Names", SOFT, (-8, -24)),
           ("opaque names", "R5_BioGlyph_Opaque", SOFT, (12, 8)),
           # the dotted floor line already names this point; a second label collided with it
           ("", "R0_NoGraph", MUTED, (0, 0)),
           ("GNN embeddings", "R4_GIN", MUTED, (-42, 13)),
           ("adjacency text", "R2_AdjacencyNL", BLUE, (14, -18)),
           ("edge list", "R1_EdgeList", BLUE, (-12, -24)),
           ("measurement table", "R3_RawMetrics", BLUE, (-30, -26))]

    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.axvspan(BUDGET, 60000, color="#fbf1ef", zorder=0)
    ax.axvline(BUDGET, color=ACCENT, lw=1.6, ls="--", zorder=1)
    ax.text(BUDGET * 1.04, 74.5, "context limit\n24,576 tokens", color=ACCENT,
            fontproperties=SANS_B, fontsize=11, va="top")

    floor = arms["R0_NoGraph"]["sys"]["acc"]
    ax.axhline(floor, color=MUTED, lw=1.2, ls=":", zorder=1)
    ax.text(58000, floor + 0.9, "no network at all", color=MUTED, fontproperties=SANS,
            fontsize=11, ha="right")

    for label, key, col, off in pts:
        a = arms[key]
        x, y = a["tokens"]["median"], a["sys"]["acc"]
        big = key == "R5_BioGlyph"
        ax.errorbar(x, y, yerr=[[y - a["sys"]["lo"]], [a["sys"]["hi"] - y]],
                    fmt="none", ecolor=col, elinewidth=1.2, capsize=3, alpha=0.75, zorder=3)
        ax.scatter([x], [y], s=190 if big else 90, color=col, zorder=4,
                   edgecolor="white", linewidth=1.5)
        if label:
            ax.annotate(label, (x, y), textcoords="offset points", xytext=off,
                        fontproperties=SANS_B if big else SANS, fontsize=12 if big else 10.5,
                        color=col)

    ax.set_xscale("log")
    ax.set_xlim(200, 60000)
    ax.set_ylim(35, 76)
    ax.set_xlabel("median prompt length (tokens, log scale)", fontproperties=SANS, fontsize=12,
                  color=SOFT)
    ax.set_ylabel("accuracy (%)", fontproperties=SANS, fontsize=12, color=SOFT)
    ax.set_xticks([300, 1000, 3000, 10000, 30000])
    ax.set_xticklabels(["300", "1,000", "3,000", "10,000", "30,000"])
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_fontproperties(MONO)
        lbl.set_fontsize(10)
        lbl.set_color(MUTED)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.grid(axis="y", color=LINE, lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, "tokens-accuracy.png")


# ------------------------------------------------------ reactome knockout ---

def reactome_targets() -> None:
    """Ranked by proteins detached, coloured by the independent DepMap dependency class."""
    scr = NUMS["bio"]["reactome_screen"]
    tg = scr["top_targets"][:12]
    cls_col = {"common": ACCENT, "selective": GOLD, "too_few": MUTED, "too_many": BLUE}
    cls_lab = {"common": "common essential in DepMap", "selective": "selectively essential",
               "too_few": "rarely a dependency", "too_many": "near-universal dependency"}

    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ys = range(len(tg))
    for y, t in zip(ys, tg):
        col = cls_col.get(t["depmap_class"], MUTED)
        ax.barh(y, t["detached"], height=0.66, color=col)
        ax.text(t["detached"] + 1.2, y, str(t["detached"]), va="center",
                fontproperties=MONO, fontsize=11, color=col)
        ax.text(-1.6, y, t["symbol"], va="center", ha="right",
                fontproperties=SANS_B, fontsize=12, color=INK)
        ax.text(-1.6, y - 0.30, f'degree {t["degree"]}', va="center", ha="right",
                fontproperties=MONO, fontsize=8.5, color=MUTED)

    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlim(0, max(t["detached"] for t in tg) * 1.16)
    ax.set_xlabel("proteins detached from the main component when this one is removed",
                  fontproperties=SANS, fontsize=12, color=SOFT)
    for lbl in ax.get_xticklabels():
        lbl.set_fontproperties(MONO)
        lbl.set_fontsize(10)
        lbl.set_color(MUTED)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(LINE)
    ax.grid(axis="x", color=LINE, lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)

    seen = []
    for t in tg:
        if t["depmap_class"] not in seen:
            seen.append(t["depmap_class"])
    handles = [Rectangle((0, 0), 1, 1, color=cls_col[c]) for c in seen]
    leg = ax.legend(handles, [cls_lab[c] for c in seen], loc="lower right", frameon=False,
                    fontsize=10.5, handlelength=1.1, handleheight=1.1)
    for txt in leg.get_texts():
        txt.set_fontproperties(SANS)
        txt.set_color(SOFT)

    n = scr["network"]
    ax.set_title(f'Every cut node in the Reactome main component was screened: '
                 f'{n["n_cut_nodes"]} of {n["n_proteins_main_component"]:,} proteins',
                 fontproperties=SANS, fontsize=11.5, color=MUTED, loc="left", pad=14)
    fig.tight_layout()
    save(fig, "reactome-targets.png")


if __name__ == "__main__":
    print("rendering figures from numbers.json:")
    og_card()
    tokens_accuracy()
    reactome_targets()
