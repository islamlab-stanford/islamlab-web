/* Jeus project page: the example browser and the results chart.
   Data comes from assets/examples.js and assets/results.js (one window.* object each), built
   from the manuscript's released records. Nothing on this page is computed; it is shown. */
(function () {
  "use strict";
  var EX = window.JEUS_EXAMPLES, RES = window.JEUS_RESULTS;
  var AGENT_CLASS = { "Jeus": "jeus", "Codex CLI": "codex", "Claude Code": "claude", "Biomni A1": "biomni" };
  var AGENT_COLOR = { "Jeus": "#a83f35", "Codex CLI": "#476d89", "Claude Code": "#628060", "Biomni A1": "#7d6490" };

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) {
      if (k === "class") node.className = attrs[k];
      else if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { if (c) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return node;
  }
  function fmtInt(n) { return n == null ? "—" : String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fail(container, what) {
    container.replaceChildren(el("p", { class: "widget-fail", text: what + " could not be loaded. The same content is in the manuscript's Supplementary Note 2." }));
  }

  /* ---------------------------------------------------------------- examples */
  function splitOptions(text) {
    // "stem (A) ... (B) ... (C) ... (D) ..." -> { stem, options: [[letter, text], ...] }
    var parts = text.split(/\s*\(([A-D])\)\s*/);
    if (parts.length < 3) return { stem: text, options: [] };
    var options = [];
    for (var i = 1; i < parts.length; i += 2) options.push([parts[i], parts[i + 1].trim()]);
    return { stem: parts[0].trim(), options: options };
  }

  function taskCard(ex) {
    var card = el("div", { class: "task" });
    if (ex.id === "E2") {
      var q = splitOptions(ex.published_text);
      card.appendChild(el("small", { text: ex.benchmark + " · published question · " + ex.item_id }));
      card.appendChild(el("blockquote", { text: q.stem }));
      card.appendChild(el("ul", { class: "opts" }, q.options.map(function (o) { return el("li", null, [el("b", { text: o[0] }), el("span", { text: o[1] })]); })));
      card.appendChild(el("p", { class: "key" }, ["Answer key: ", el("b", { text: ex.reference_answer }), " · " + ex.reference_note]));
    } else {
      card.appendChild(el("small", { text: ex.benchmark + " · the benchmark authors' description of the task · " + ex.item_id }));
      card.appendChild(el("blockquote", { text: ex.published_text }));
      if (ex.criteria) {
        card.appendChild(el("p", { class: "key" }, [el("b", { text: "Rubric: nine criteria, 100 points." }), " Each criterion is graded A, B or C with the points below; the ninth is a penalty that acts only through the deducted total."]));
        card.appendChild(el("ul", { class: "criteria" }, ex.criteria.map(function (c) {
          return el("li", null, [el("b", { text: String(c.n) }), el("span", { text: c.name, style: "white-space:normal;font:inherit;color:inherit" }),
            el("span", { text: "A " + c.A + " · B " + c.B + " · C " + c.C })]);
        })));
      }
    }
    if (ex.note) card.appendChild(el("p", { class: "key", text: ex.note }));
    card.appendChild(el("p", { class: "credit", text: ex.credit_line }));
    return card;
  }

  function verdict(ex, run) {
    if (ex.id === "E2") {
      if (!run.answered) return ["No answer", "no"];
      return run.credit >= 1 ? ["Correct", "yes"] : ["Incorrect", "no"];
    }
    return run.answered ? [run.main + " / 100", "na"] : ["No answer", "no"];  // a rubric score, not a pass or fail
  }

  function outcomeCard(ex, run) {
    var v = verdict(ex, run);
    var card = el("div", { class: "outcome " + AGENT_CLASS[run.agent] });
    card.appendChild(el("div", { class: "outcome-head" }, [el("b", { text: run.agent }), el("span", { class: "verdict " + v[1], text: v[0] })]));
    var stats = [];
    if (ex.id === "E2") stats.push(el("span", null, ["Answer ", el("b", { text: run.answered ? run.answer : "none" })]));
    else stats.push(el("span", null, ["Deducted total ", el("b", { text: String(run.deducted) })]));
    stats.push(el("span", null, ["Calls ", el("b", { text: fmtInt(run.calls) })]));
    stats.push(el("span", null, ["Tokens ", el("b", { text: fmtInt(run.tokens) })]));
    if (!run.answered) stats.push(el("span", null, ["Ended at the ", el("b", { text: run.end_reason.replace("_", " ") })]));
    card.appendChild(el("div", { class: "stats" }, stats));
    if (run.levels) {
      card.appendChild(el("div", { class: "levels", title: "Criterion levels, in rubric order 1 to 9" }, run.levels.map(function (l) { return el("i", { class: l, text: l }); })));
    }
    if (run.verbatim) {
      card.appendChild(el("div", { class: "quote" }, [el("small", { text: "Final answer, excerpt (every omission is marked [...])" }), el("p", { text: run.excerpt })]));
      card.appendChild(el("div", { class: "quote" }, [el("small", { text: "What it did" }), el("p", { class: "method", text: run.method })]));
    }
    return card;
  }

  function allRunsTable(ex) {
    var head = ex.id === "E2" ? ["Model", "Agent", "Answer", "Credit", "Calls", "Tokens"] : ["Model", "Agent", "Criterion levels 1–9", "Main", "Deducted", "Calls", "Tokens"];
    var table = el("table", null, [el("thead", null, [el("tr", null, head.map(function (h) { return el("th", { text: h }); }))])]);
    var body = el("tbody");
    var last = null;
    ex.runs.forEach(function (r) {
      var cls = (r.model !== last ? "first " : "") + (EX.models.some(function (m) { return m.id === r.model && m.kind === "proprietary"; }) ? "paid" : "");
      var cells = [el("td", { class: "model", text: r.model !== last ? r.model : "" }), el("td", { class: "agent-" + AGENT_CLASS[r.agent], text: r.agent })];
      if (ex.id === "E2") {
        cells.push(el("td", { text: r.answered ? r.answer : "No answer" }), el("td", { class: "n", text: r.credit.toFixed(1) }));
      } else {
        cells.push(el("td", { text: r.levels.join(", ") }), el("td", { class: "n", text: String(r.main) }), el("td", { class: "n", text: String(r.deducted) }));
      }
      cells.push(el("td", { class: "n", text: fmtInt(r.calls) }), el("td", { class: "n", text: fmtInt(r.tokens) }));
      body.appendChild(el("tr", { class: cls.trim() }, cells));
      last = r.model;
    });
    table.appendChild(body);
    var det = el("details", { class: "alltable" }, [el("summary", { text: "All 19 recorded outcomes for this task, every model and agent" }), el("div", { class: "scroll" }, [table])]);
    return det;
  }

  function fullPanel(ex) {
    var panel = el("div", { class: "ex-grid" });
    panel.appendChild(taskCard(ex));
    var side = el("div", { class: "ex-side" });
    var pick = el("div", { class: "pick" });
    var open = el("div", { class: "pick-row" }), paid = el("div", { class: "pick-row" });
    var outcomes = el("div", { class: "outcomes" });
    var note = el("p", { class: "ex-note" });
    var current = EX.models[0].id;
    function render() {
      [].concat(Array.from(open.children), Array.from(paid.children)).forEach(function (b) { b.classList.toggle("on", b.dataset.model === current); });
      outcomes.replaceChildren();
      ex.runs.filter(function (r) { return r.model === current; }).forEach(function (r) { outcomes.appendChild(outcomeCard(ex, r)); });
      var level = (EX.reasoning[ex.id] || {})[current];
      var verbatim = ex.runs.some(function (r) { return r.model === current && r.verbatim; });
      note.textContent = "Reasoning setting: " + level + ". " + (verbatim
        ? "Excerpts are reproduced verbatim from the graded final answer; \"what it did\" describes the recorded steps in a sentence, without code."
        : "Excerpts and summaries are shown for GLM-5.3, Claude Sonnet 5 and GPT-6 Sol, the models the manuscript quotes.");
    }
    EX.models.forEach(function (m) {
      var b = el("button", { class: "model", type: "button", "data-model": m.id, text: m.id });
      b.addEventListener("click", function () { current = m.id; render(); });
      (m.kind === "open-weight" ? open : paid).appendChild(b);
    });
    pick.appendChild(el("small", { text: "Open-weight models" }));
    pick.appendChild(open);
    pick.appendChild(el("small", { text: "Proprietary models" }));
    pick.appendChild(paid);
    side.appendChild(pick);
    side.appendChild(outcomes);
    side.appendChild(note);
    panel.appendChild(side);
    var wrap = el("div", null, [panel, allRunsTable(ex)]);
    render();
    return wrap;
  }

  function formatPanel(list) {
    var why = {
      E1: "Figure 6 of the BixBench paper shows an earlier wording of a question we evaluated. Its published answer differs from the evaluated version's, so the item is shown for format only, without results.",
      E3: "The second question of the BAISBench box is not in the evaluated collection, so it has no results.",
      E4: "One of the benchmark's private tasks, not among the 50 public tasks we evaluated; shown for format only."
    };
    var grid = el("div", { class: "fmts" }, list.map(function (ex) {
      return el("div", { class: "fmt" }, [
        el("small", { text: ex.benchmark + (ex.item_id ? " · " + ex.item_id : "") }),
        el("b", { class: "t", text: ex.title }),
        el("blockquote", { text: ex.published_text }),
        ex.id === "E4" ? el("p", { class: "why" }, [el("b", { text: "Published with it: " }), ex.reference_answer]) : null,
        el("p", { class: "why", text: why[ex.id] }),
        el("p", { class: "credit", text: ex.credit_line })
      ]);
    }));
    return el("div", null, [grid, el("p", { class: "ex-note", text: "Three more tasks from the benchmark papers, as published, with the reason no results are shown. BioMysteryBench and Verified-50 have no published example item." })]);
  }

  function initExamples() {
    var tabs = document.getElementById("exTabs"), panel = document.getElementById("exPanel");
    if (!tabs || !panel) return;
    if (!EX || !EX.examples) return fail(panel, "The examples");
    var full = EX.examples.filter(function (e) { return e.type === "full"; });
    var format = EX.examples.filter(function (e) { return e.type !== "full"; });
    var views = full.map(function (ex) {
      var sub = ex.id === "E2" ? "a published question, 19 recorded outcomes" : "a published task, 19 recorded outcomes";
      return { label: ex.title, sub: sub, make: function () { return fullPanel(ex); } };
    });
    views.push({ label: "What the other tasks look like", sub: "three published items, no results", make: function () { return formatPanel(format); } });
    var buttons = views.map(function (v, i) {
      var b = el("button", { class: "ex-tab", type: "button", role: "tab", text: v.label }, [el("small", { text: v.sub })]);
      b.addEventListener("click", function () { show(i); });
      tabs.appendChild(b);
      return b;
    });
    function show(i) {
      buttons.forEach(function (b, j) { b.classList.toggle("on", i === j); b.setAttribute("aria-selected", String(i === j)); });
      panel.replaceChildren(views[i].make());
    }
    show(0);
  }

  /* ------------------------------------------------------------------ chart */
  function initChart() {
    var box = document.getElementById("chart");
    if (!box) return;
    if (!RES || !RES.benchmarks) return fail(box, "The chart");
    var agents = ["Jeus", "Codex CLI", "Claude Code", "Biomni A1"];
    var W = 1000, H = 330, left = 46, top = 16, bottom = 54, right = 12;
    var plotW = W - left - right, plotH = H - top - bottom;
    var groups = RES.benchmarks.length, gw = plotW / groups, bw = gw / 5.4, gap = 6;
    var NS = "http://www.w3.org/2000/svg";
    function s(tag, attrs) { var n = document.createElementNS(NS, tag); Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); }); return n; }
    var svg = s("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Five-model mean score of each agent on BixBench, Verified-50 and BAISBench" });
    var y = function (v) { return top + plotH - v / 100 * plotH; };
    [0, 25, 50, 75, 100].forEach(function (v) {
      svg.appendChild(s("line", { x1: left, x2: W - right, y1: y(v), y2: y(v), stroke: v === 0 ? "#d9d6ce" : "#eeeae2", "stroke-width": 1 }));
      var t = s("text", { x: left - 8, y: y(v) + 4, "text-anchor": "end", "font-size": 12, fill: "#707a86", "font-family": "IBM Plex Mono, monospace" });
      t.textContent = String(v); svg.appendChild(t);
    });
    RES.benchmarks.forEach(function (b, gi) {
      var present = agents.filter(function (a) { return b.scores[a] != null; });
      var total = present.length * bw + (present.length - 1) * gap;
      var x0 = left + gi * gw + (gw - total) / 2;
      present.forEach(function (a, ai) {
        var v = b.scores[a], x = x0 + ai * (bw + gap);
        svg.appendChild(s("rect", { x: x, y: y(v), width: bw, height: y(0) - y(v), fill: AGENT_COLOR[a], opacity: a === "Jeus" ? 1 : .78 }));
        var t = s("text", { x: x + bw / 2, y: y(v) - 6, "text-anchor": "middle", "font-size": 12.5, "font-weight": a === "Jeus" ? 700 : 500, fill: "#17202c", "font-family": "IBM Plex Mono, monospace" });
        t.textContent = v.toFixed(1); svg.appendChild(t);
      });
      var label = s("text", { x: left + gi * gw + gw / 2, y: H - 30, "text-anchor": "middle", "font-size": 15, "font-weight": 600, fill: "#17202c", "font-family": "Source Sans 3, Arial, sans-serif" });
      label.textContent = b.name; svg.appendChild(label);
      var sub = s("text", { x: left + gi * gw + gw / 2, y: H - 11, "text-anchor": "middle", "font-size": 12, fill: "#707a86", "font-family": "Source Sans 3, Arial, sans-serif" });
      sub.textContent = b.metric + " · " + b.questions + " questions"; svg.appendChild(sub);
    });
    var legend = el("div", { class: "legend" }, agents.map(function (a) { return el("span", null, [el("i", { style: "background:" + AGENT_COLOR[a] }), a]); }));
    box.replaceChildren(legend, svg, el("p", { class: "chart-cap" }, [el("b", { text: "Five-model mean score, in percent. " }),
      "Biomni A1 was evaluated on BixBench and Verified-50. Paired differences and their 95% confidence intervals are in the manuscript; several of the gaps between Jeus, Codex CLI and Claude Code are within the interval that includes zero."]));
  }

  /* ------------------------------------------------------------- captions */
  function initCaptions() {
    var video = document.getElementById("jeusExplainerVideo"), button = document.getElementById("videoCcToggle");
    if (!video || !button) return;
    function track() { var t = video.textTracks; return t && t.length ? t[0] : null; }
    function render(on) {
      button.setAttribute("aria-pressed", String(on));
      button.setAttribute("aria-label", on ? "Turn captions off" : "Turn captions on");
      button.title = on ? "Turn captions off" : "Turn captions on";
      button.querySelector(".video-cc-state").textContent = on ? "On" : "Off";
    }
    var t = track();
    if (t) t.mode = "hidden";
    render(false);
    button.addEventListener("click", function () {
      var tr = track();
      if (!tr) return;
      var on = tr.mode !== "showing";
      tr.mode = on ? "showing" : "hidden";
      render(on);
    });
  }

  initExamples();
  initChart();
  initCaptions();
})();
