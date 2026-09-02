"""Generate the static JSON the BioGlyph page's widgets read.

Everything here is copied out of the manuscript's own figure data, never retyped:

  regions.json  <- figures/qa_items.json, s1_single.main_items
                   Six real retrieved regions, each with its layout coordinates, edges, the node
                   the question asks about, the component each node lands in after that node is
                   removed, both renderings of the region, and the per-arm prompt lengths and
                   outcomes. This is the same evidence the paper's Section S1 shows.
  results.json  <- figures/numbers.json, core.headline.pooled_8b
                   The pooled eight-network headline: accuracy with its interval, overflow share
                   and median prompt length for each representation.

The raw-measurement rendering is stored as a head plus its true row and token counts rather than
in full. Two thirds of the payload would otherwise be table rows no visitor scrolls, and the
honest summary -- 1,708 rows, 37,687 tokens, never sent -- makes the point the full text does not.

Run:  python build_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

FIGS = Path(r"c:\Users\ucchw\OneDrive - Stanford\BioGlyph"
            r"\Language-encoded network topology for complex networks\figures")
OUT = Path(__file__).parent / "assets"
R3_HEAD_LINES = 70
BUDGET = 24576          # the paper's context limit, Methods

ARM_LABEL = {
    "R1_EdgeList": "Edge list",
    "R2_AdjacencyNL": "Adjacency as sentences",
    "R3_RawMetrics": "Raw measurement table",
    "R5_BioGlyph": "BioGlyph description",
}
# the nine rows the page's chart shows, in the order it shows them
CHART_ARMS = [
    ("R5_BioGlyph", "BioGlyph", "named roles, evidence, implication", True),
    ("R5_NamesEvidence", "Names and evidence", "no implication clause", False),
    ("R5_Names", "Names only", "no evidence, no implication", False),
    ("R5_BioGlyph_Opaque", "Meaningless role names", "same structure, opaque tokens", False),
    ("R0_NoGraph", "No graph at all", "the question alone \u2014 the floor", False),
    ("R4_GIN", "GNN node embeddings", "best of GCN, SAGE, GAT, GIN", False),
    ("R2_AdjacencyNL", "Adjacency as sentences", "the edges, written out", False),
    ("R1_EdgeList", "Edge list", "the raw pairs", False),
    ("R3_RawMetrics", "Measurement table", "every number, no threshold", False),
]


def build_regions() -> dict:
    items = json.loads((FIGS / "qa_items.json").read_text(encoding="utf-8"))["s1_single"]["main_items"]
    out = []
    for key, it in items.items():
        r = it["region"]
        r3_lines = it["context_r3"].split("\n")
        who = it.get("who") or {}
        # gene_names is a dict in some regions and a repr string in others
        raw = who.get("gene_names") or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw.replace("'", '"'))
            except ValueError:
                raw = {}
        genes = raw if isinstance(raw, dict) else {}

        arms = []
        for arm, label in ARM_LABEL.items():
            s = it["strip"].get(arm) or {}
            arms.append({
                "arm": arm,
                "label": label,
                "tokens": s.get("prompt_tokens"),
                "correct": bool(s.get("correct")),
                # too_long means the prompt exceeded the budget and never reached the model
                "sent": s.get("finish_reason") != "too_long",
                "finish": s.get("finish_reason"),
            })

        out.append({
            "key": key,
            "dataset": it["dataset"],
            "family": it["family"],
            "question": it["question"],
            "gold": it["gold_text"],
            "model_answer": (it.get("answer_visible") or "").replace("ANSWER:", "").strip(),
            "model_correct": bool(it["correct"]),
            "n_nodes": it["n_nodes"],
            "n_edges": it["n_edges"],
            "nodes": r["nodes"],                 # [id, x, y] with x,y in 0..1
            "edges": r["edges"],
            "focus": r.get("focus") or [],
            "removes": r.get("removes"),
            "gone": r.get("gone") or [],
            "after": r.get("after") or {},       # node id -> component index after removal
            "pieces": r.get("pieces"),
            "genes": genes,
            "context_r5": it["context_r5"],
            "context_r3_head": "\n".join(r3_lines[:R3_HEAD_LINES]),
            "context_r3_lines": len(r3_lines),
            "arms": arms,
        })
    out.sort(key=lambda d: (d["dataset"], d["family"]))
    return {"budget": BUDGET, "regions": out}


def build_results() -> dict:
    nums = json.loads((FIGS / "numbers.json").read_text(encoding="utf-8"))
    arms = nums["core"]["headline"]["pooled_8b"]["arms"]
    rows = []
    for arm, label, sub, hi in CHART_ARMS:
        a = arms[arm]
        rows.append({
            "arm": arm, "label": label, "sub": sub, "highlight": hi,
            "acc": a["sys"]["acc"], "lo": a["sys"]["lo"], "hi": a["sys"]["hi"],
            "overflow": a["overflow"]["too_long"], "median_tokens": a["tokens"]["median"],
        })
    floor = arms["R0_NoGraph"]["sys"]["acc"]
    return {
        "definition": nums["core"]["_definitions"]["system"],
        "pool": nums["core"]["_definitions"]["pooled_8b"],
        "budget": BUDGET,
        "floor": floor,
        "rows": rows,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("regions.json", build_regions()), ("results.json", build_results())):
        p = OUT / name
        p.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"{name:14s} {p.stat().st_size/1024:7.1f} KB")

    reg = build_regions()["regions"]
    print(f"\n{len(reg)} regions:")
    for r in reg:
        never = [a["label"] for a in r["arms"] if not a["sent"]]
        print(f"  {r['dataset']:14s} {r['family']:16s} {r['n_nodes']:3d}n/{r['n_edges']:5d}e  "
              f"pieces={r['pieces']:<3} r3={r['context_r3_lines']:5d} rows"
              + (f"  never sent: {', '.join(never)}" if never else ""))


if __name__ == "__main__":
    main()
