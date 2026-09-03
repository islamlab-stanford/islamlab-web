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
  threads.json  <- figures/qa_items.json, s1_threads and s1_multiturn
                   Ten real eight-turn conversations (five regions, two models) and two paired
                   three-turn conversations run through both the description and the raw table.
                   Every question, every reply and every verdict is the stored one; the paper's
                   Figure 2 and Figure 7e,f rest on these runs.

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


SHORT_MODEL = {
    "Qwen/Qwen3-8B": "Qwen3-8B",
    "meta-llama/Llama-3.1-8B-Instruct": "Llama-3.1-8B",
}


def _dict(v) -> dict:
    """`who` sub-fields are dicts in some records and repr strings in others."""
    if isinstance(v, str):
        try:
            v = json.loads(v.replace("'", '"').replace("True", "true").replace("False", "false"))
        except ValueError:
            return {}
    return v if isinstance(v, dict) else {}


def build_threads() -> dict:
    """The eight-turn threads, plus the two conversations that were run through both arms.

    The region and the compiled description are stored once per thread, not once per model,
    because that is the claim being shown: one description, sent at turn 1, carrying every later
    turn. Turn 1's prompt length is the description's length; the growth after it is the
    conversation itself.
    """
    qa = json.loads((FIGS / "qa_items.json").read_text(encoding="utf-8"))

    threads = []
    for key, rec in qa["s1_threads"].items():
        region = rec["region"]
        models = []
        context = context_tokens = None
        for full, short in SHORT_MODEL.items():
            m = rec.get(full)
            if not m:
                continue
            if context is None:
                context, context_tokens = m["context"], m["turns"][0]["prompt_tokens"]
            models.append({
                "model": short,
                "scored": m["n_scored"],
                "correct": m["n_scored_correct"],
                "pushback": m.get("pushback_outcome"),
                "disputes": m.get("pushback_disputes_turn"),
                "turns": [{
                    "turn": t["turn"],
                    "cls": t["turn_class"],
                    "label": t["turn_label"],
                    "q": t["question"],
                    "a": (t.get("answer_visible") or "").strip(),
                    "gold": t.get("gold_text") or "",
                    "correct": t.get("correct"),
                    "tokens": t.get("prompt_tokens"),
                } for t in m["turns"]],
            })
        who = _dict(rec[list(SHORT_MODEL)[0]].get("who"))
        meta = rec[list(SHORT_MODEL)[0]]
        threads.append({
            "id": key,
            "dataset": meta["dataset"],
            "kind": meta["thread_kind"],
            "label": meta["label"],
            "n_nodes": meta["n_nodes"],
            "n_edges": meta["n_edges"],
            "focus": region.get("focus") or [],
            "removes": region.get("removes"),
            "pieces": region.get("pieces"),
            "gone": region.get("gone") or [],
            "nodes": region["nodes"],
            "edges": region["edges"],
            "after": region.get("after") or {},
            "genes": _dict(who.get("gene_names")),
            "essential": _dict(who.get("sgd_essential")),
            "context": context,
            "context_tokens": context_tokens,
            "models": models,
        })
    threads.sort(key=lambda t: (t["dataset"], t["kind"]))

    # the paired study: the same conversation, once per rendering. This is what makes the
    # headline legible -- the table does not merely score lower, it often never starts.
    paired = []
    for key, rec in qa["s1_multiturn"].items():
        arms = []
        for arm, a in rec["arms"].items():
            turns = a["turns"]
            order = sorted(turns, key=lambda k: k)  # t1, t2, t3
            arms.append({
                "arm": arm,
                "label": ARM_LABEL.get(arm, arm),
                "pushback": a.get("pushback_outcome"),
                "turns": [{
                    "turn": i + 1,
                    "q": turns[k].get("question") or "",
                    "a": (turns[k].get("answer_visible") or "").strip(),
                    "gold": turns[k].get("gold_text") or "",
                    "correct": turns[k].get("correct"),
                    "tokens": turns[k].get("prompt_tokens"),
                    "sent": turns[k].get("finish_reason") != "too_long",
                } for i, k in enumerate(order)],
            })
        arms.sort(key=lambda a: a["arm"] != "R5_BioGlyph")
        paired.append({
            "id": key,
            "dataset": rec["dataset"],
            "model": SHORT_MODEL.get(rec["model"], rec["model"]),
            "n_nodes": rec["n_nodes"],
            "n_edges": rec["n_edges"],
            "arms": arms,
        })
    paired.sort(key=lambda p: p["dataset"])

    return {"budget": BUDGET, "threads": threads, "paired": paired}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in (("regions.json", build_regions()), ("results.json", build_results()),
                       ("threads.json", build_threads())):
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

    th = build_threads()
    print(f"\n{len(th['threads'])} threads x {len(th['threads'][0]['models'])} models:")
    for t in th["threads"]:
        who = " ".join(f"{k}={v}" for k, v in t["genes"].items()) or "-"
        print(f"  {t['dataset']:14s} {t['kind']:9s} {t['n_nodes']:3d}n  "
              f"desc {t['context_tokens']:5d} tok  {who}")
        for m in t["models"]:
            last = m["turns"][-1]["tokens"]
            print(f"      {m['model']:14s} {m['correct']}/{m['scored']} scored correct  "
                  f"turn 8 at {last} tok  push-back: {m['pushback']}")
    print(f"\n{len(th['paired'])} paired conversations (same questions, both renderings):")
    for p in th["paired"]:
        for a in p["arms"]:
            marks = " ".join(("sent" if t["sent"] else "NEVER SENT") for t in a["turns"])
            print(f"  {p['dataset']:14s} {a['label']:22s} "
                  f"{[t['tokens'] for t in a['turns']]}  {marks}")


if __name__ == "__main__":
    main()
