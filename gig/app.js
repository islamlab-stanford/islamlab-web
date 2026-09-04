(() => {
  "use strict";

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const colors = {
    paper: "#f7f4ed",
    white: "#fffdf8",
    ink: "#071b39",
    muted: "#718096",
    coral: "#c94130",
    coralSoft: "#f0a698",
    blue: "#4e7698",
    blueSoft: "#9fbed3",
    gold: "#c98a23",
    mint: "#6c998c",
    navy: "#061936"
  };

  function initNavigation() {
    const toggle = $(".nav-toggle");
    const nav = $("#primary-nav");
    if (!toggle || !nav) return;
    const close = () => {
      toggle.setAttribute("aria-expanded", "false");
      nav.classList.remove("open");
      document.body.classList.remove("nav-open");
    };
    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("open", open);
      document.body.classList.toggle("nav-open", open);
    });
    $$("a", nav).forEach(link => link.addEventListener("click", close));
    window.addEventListener("resize", () => { if (window.innerWidth > 880) close(); });
  }

  function initReveals() {
    const items = $$(".reveal");
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach(item => item.classList.add("visible"));
      return;
    }
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: .12, rootMargin: "0px 0px -30px" });
    items.forEach(item => observer.observe(item));
  }

  function initCaptions() {
    const video = $("#gig-video");
    const button = $("#video-cc-toggle");
    if (!video || !button) return;
    let captionsOn = false;
    const setMode = () => {
      [...video.textTracks].forEach(track => { track.mode = captionsOn ? "showing" : "hidden"; });
      button.setAttribute("aria-pressed", String(captionsOn));
      button.setAttribute("aria-label", captionsOn ? "Turn captions off" : "Turn captions on");
      button.title = captionsOn ? "Turn captions off" : "Turn captions on";
      const state = $("b", button);
      if (state) state.textContent = captionsOn ? "On" : "Off";
    };
    video.addEventListener("loadedmetadata", setMode);
    button.addEventListener("click", () => { captionsOn = !captionsOn; setMode(); });
    setMode();
  }

  function initBibtex() {
    const button = $("#copy-bibtex");
    const block = $("#bibtex");
    if (!button || !block) return;
    button.addEventListener("click", async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(block.textContent.trim());
        button.textContent = "Copied";
      } catch (_) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(block);
        selection.removeAllRanges();
        selection.addRange(range);
        button.textContent = "Select and copy";
      }
      window.setTimeout(() => { button.textContent = original; }, 1800);
    });
  }

  const roundedRect = (ctx, x, y, w, h, r = 8) => {
    const radius = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
  };

  const text = (ctx, value, x, y, size = 14, color = colors.white, align = "left", family = "Source Sans 3") => {
    ctx.save();
    ctx.fillStyle = color;
    ctx.font = `${size}px "${family}"`;
    ctx.textAlign = align;
    ctx.textBaseline = "middle";
    ctx.fillText(value, x, y);
    ctx.restore();
  };

  function initMethodAnimation() {
    const canvas = $("#method-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const labels = [
      "Find patient-specific signal",
      "Retrieve curated pathways",
      "Compose one graph per patient",
      "Encode measurement and gene identity",
      "Message-pass, pool, and predict",
      "Return attribution to the graph"
    ];
    const genes = ["TP53", "AKT1", "MAPK1", "EGFR", "KRAS", "PIK3R1", "MYC", "CTNNB1"];
    const values = [.22, .85, .68, .74, .18, .63, .78, .54];
    const graphNodes = [
      [666, 210], [735, 151], [815, 211], [775, 302], [674, 327], [650, 275], [888, 293], [866, 127]
    ];
    const graphEdges = [[0,1],[0,3],[0,5],[0,4],[1,2],[1,7],[2,3],[2,7],[2,6],[3,4],[3,6],[4,5],[4,6],[5,0],[6,7]];
    let step = 0;
    let paused = false;
    let stepStart = performance.now();
    const duration = 4800;

    function updateUi(progress = 0) {
      $("#method-index").textContent = `${String(step + 1).padStart(2, "0")} / 06`;
      $("#method-label").textContent = labels[step];
      $("#method-progress").style.width = `${progress * 100}%`;
      $$("#method-steps li").forEach((item, index) => item.classList.toggle("active", index === step));
      const toggle = $("#method-toggle");
      toggle.textContent = paused ? "Play" : "Pause";
      toggle.setAttribute("aria-pressed", String(paused));
    }

    function panel(x, y, w, h, title, active) {
      ctx.save();
      roundedRect(ctx, x, y, w, h, 5);
      ctx.fillStyle = active ? "rgba(255,255,255,.075)" : "rgba(255,255,255,.035)";
      ctx.fill();
      ctx.strokeStyle = active ? colors.coral : "rgba(255,255,255,.18)";
      ctx.lineWidth = active ? 2 : 1;
      ctx.stroke();
      text(ctx, title.toUpperCase(), x + 15, y + 20, 10, active ? colors.coralSoft : "#8190a5", "left", "IBM Plex Mono");
      ctx.restore();
    }

    function drawTable(progress) {
      panel(42, 78, 280, 430, "patient expression", step === 0);
      text(ctx, "PATIENT 024", 67, 122, 12, "#dce5ef", "left", "IBM Plex Mono");
      genes.forEach((gene, i) => {
        const y = 158 + i * 39;
        text(ctx, gene, 67, y, 11, "#aab7c7", "left", "IBM Plex Mono");
        ctx.fillStyle = "rgba(255,255,255,.09)";
        ctx.fillRect(137, y - 6, 137, 12);
        const selected = values[i] > .5;
        const grow = step === 0 ? clamp(progress * 1.7 - i * .045, 0, 1) : 1;
        ctx.fillStyle = selected ? colors.coral : colors.blue;
        ctx.fillRect(137, y - 6, values[i] * 137 * grow, 12);
        if (selected && (step > 0 || progress > .58)) {
          ctx.strokeStyle = colors.coralSoft;
          ctx.strokeRect(57, y - 14, 230, 28);
        }
      });
      text(ctx, "within-patient z-score", 67, 483, 9, "#74859a", "left", "IBM Plex Mono");
    }

    function drawPathways(progress) {
      panel(355, 78, 235, 430, "curated pathways", step === 1);
      const groups = [
        { name: "PI3K–AKT", color: colors.coral, nodes: [[391,160],[451,139],[523,170],[463,205]] },
        { name: "MAPK", color: colors.gold, nodes: [[390,285],[452,260],[526,296],[456,327]] },
        { name: "WNT", color: colors.blue, nodes: [[397,400],[465,373],[524,417]] }
      ];
      groups.forEach((group, gi) => {
        const show = step > 1 ? 1 : step === 1 ? clamp(progress * 2 - gi * .35, 0, 1) : 0;
        ctx.save();
        ctx.globalAlpha = .18 + .82 * show;
        group.nodes.forEach((node, i) => {
          if (i) {
            ctx.beginPath();
            ctx.moveTo(group.nodes[i - 1][0], group.nodes[i - 1][1]);
            ctx.lineTo(node[0], node[1]);
            ctx.strokeStyle = group.color;
            ctx.globalAlpha = .22 + .6 * show;
            ctx.stroke();
          }
        });
        group.nodes.forEach(node => {
          ctx.beginPath(); ctx.arc(node[0], node[1], 6 + 2 * show, 0, Math.PI * 2);
          ctx.fillStyle = group.color; ctx.fill();
        });
        text(ctx, group.name, 472, group.nodes[0][1] - 34, 9, group.color, "center", "IBM Plex Mono");
        ctx.restore();
      });
      if (step === 1) {
        const travel = clamp(progress * 1.35, 0, 1);
        [["AKT1", 451,139],["MAPK1",452,260],["EGFR",524,417]].forEach((g, i) => {
          const x = 303 + (g[1] - 303) * travel;
          const y = 190 + i * 78 + (g[2] - (190 + i * 78)) * travel;
          text(ctx, g[0], x, y, 8, colors.white, "center", "IBM Plex Mono");
        });
      }
    }

    function drawPatientGraph(progress) {
      panel(623, 78, 304, 430, "patient graph", step === 2 || step === 3 || step === 5);
      const appear = step < 2 ? 0 : clamp(step === 2 ? progress * 1.7 : 1, 0, 1);
      ctx.save();
      ctx.beginPath();
      ctx.rect(632, 108, 286, 386);
      ctx.clip();
      ctx.globalAlpha = .08 + .92 * appear;
      graphEdges.forEach(([a,b], edgeIndex) => {
        const p1 = graphNodes[a], p2 = graphNodes[b];
        ctx.beginPath(); ctx.moveTo(...p1); ctx.lineTo(...p2);
        ctx.strokeStyle = step === 4 && (edgeIndex + Math.floor(progress * 25)) % 5 === 0 ? colors.coralSoft : "#526a83";
        ctx.lineWidth = step === 4 ? 1.8 : 1;
        ctx.stroke();
      });
      graphNodes.forEach((node, i) => {
        const attribution = [1,.72,.63,.58,.46,.41,.35,.31][i];
        const radius = step === 5 ? 7 + 14 * attribution * clamp(progress * 1.8, .25, 1) : 8;
        ctx.beginPath(); ctx.arc(node[0], node[1], radius, 0, Math.PI * 2);
        const channel = step === 3 ? values[i] : attribution;
        ctx.fillStyle = channel > .6 ? colors.coral : channel > .42 ? colors.gold : colors.blue;
        ctx.fill();
        ctx.strokeStyle = colors.white; ctx.globalAlpha = .75 * appear; ctx.stroke();
        if (step >= 3) text(ctx, genes[i], node[0], node[1] + radius + 12, 8, "#c8d2df", "center", "IBM Plex Mono");
      });
      ctx.restore();
      if (step === 2) {
        text(ctx, "PATHWAYS MERGE", 775, 470, 9, colors.coralSoft, "center", "IBM Plex Mono");
      }
    }

    function drawLearner(progress) {
      panel(960, 78, 278, 430, "graph learner", step === 4);
      const layers = [128, 96, 64];
      if (step === 4) {
        const signalX = 934 + progress * 216;
        ctx.beginPath(); ctx.arc(signalX, 280, 4, 0, Math.PI * 2); ctx.fillStyle = colors.coralSoft; ctx.fill();
      }
      layers.forEach((width, i) => {
        const x = 984 + i * 54;
        const y = 155 + i * 22;
        ctx.fillStyle = step === 4 ? `rgba(78,118,152,${.35 + .15 * Math.sin(progress * 10 + i)})` : "rgba(78,118,152,.18)";
        ctx.fillRect(x, y, 36, 180 - i * 44);
        text(ctx, i < 2 ? "GNN" : "POOL", x + 18, y - 13, 8, "#9daec1", "center", "IBM Plex Mono");
      });
      ctx.beginPath();
      ctx.arc(1184, 280, 34, 0, Math.PI * 2);
      ctx.fillStyle = step >= 4 ? "rgba(201,65,48,.24)" : "rgba(255,255,255,.05)";
      ctx.fill(); ctx.strokeStyle = step >= 4 ? colors.coral : "#526a83"; ctx.stroke();
      text(ctx, "CLASS", 1184, 230, 8, "#98aabd", "center", "IBM Plex Mono");
      text(ctx, "0.91", 1184, 280, 15, colors.white, "center", "IBM Plex Mono");
    }

    function draw(now) {
      const elapsed = now - stepStart;
      let progress = reduceMotion ? .82 : clamp(elapsed / duration, 0, 1);
      if (!paused && !reduceMotion && elapsed >= duration) {
        step = (step + 1) % 6;
        stepStart = now;
        progress = 0;
      }
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = colors.navy;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      text(ctx, "ONE PROFILE → ONE BIOLOGICALLY STRUCTURED GRAPH → ONE PREDICTION", 42, 36, 11, "#91a1b5", "left", "IBM Plex Mono");
      drawTable(progress);
      drawPathways(progress);
      drawPatientGraph(progress);
      drawLearner(progress);
      updateUi(progress);
      requestAnimationFrame(draw);
    }

    $("#method-toggle").addEventListener("click", () => {
      paused = !paused;
      if (!paused) stepStart = performance.now();
      updateUi(0);
    });
    $("#method-restart").addEventListener("click", () => { step = 0; paused = false; stepStart = performance.now(); });
    $$("[data-method-step]").forEach(button => button.addEventListener("click", () => {
      step = Number(button.dataset.methodStep);
      paused = false;
      stepStart = performance.now();
    }));
    requestAnimationFrame(draw);
  }

  function initTopology(controls) {
    const canvas = $("#topology-canvas");
    if (!canvas || !controls?.length) return;
    const ctx = canvas.getContext("2d");
    const nodes = Array.from({ length: 34 }, (_, i) => {
      const group = i % 4;
      const centers = [[180,150],[385,125],[250,310],[570,265]];
      const angle = (i * 2.399) % (Math.PI * 2);
      const radius = 34 + (i % 6) * 9;
      return { x: centers[group][0] + Math.cos(angle) * radius, y: centers[group][1] + Math.sin(angle) * radius, group };
    });
    const realEdges = [];
    for (let i = 0; i < nodes.length; i++) {
      realEdges.push([i, (i + 4) % nodes.length]);
      if (i % 2 === 0) realEdges.push([i, (i + 8) % nodes.length]);
      if (i % 7 === 0) realEdges.push([i, (i + 13) % nodes.length]);
    }
    const randomEdges = realEdges.map((_, i) => [(i * 7 + 3) % 34, (i * 13 + 17) % 34]).filter(e => e[0] !== e[1]);
    const degreeEdges = realEdges.map(([a,b], i) => i % 3 === 0 ? [a, (b + 9) % 34] : [a,b]).filter(e => e[0] !== e[1]);
    let dataset = "rareseq_binary";
    let condition = "real";

    const current = () => controls.find(item => item.id === dataset) || controls[0];
    const conditionLabel = { real: "Curated pathway graph", erdos_renyi: "Edge-count-matched random graph", degree_preserved: "Degree-preserving rewiring" };

    function updateTopologyUi() {
      const item = current();
      $("#topology-context").textContent = item.context;
      $("#topology-condition").textContent = conditionLabel[condition];
      const metric = item[condition];
      $("#topology-bars").innerHTML = [
        ["Accuracy", metric.accuracy], ["Macro-F1", metric.macro_f1]
      ].map(([label,value]) => `<div class="topology-bar"><header><span>${label}</span><b>${value.toFixed(1)}%</b></header><i><b style="width:${value}%"></b></i></div>`).join("");
      const lossA = item.real.accuracy - metric.accuracy;
      const lossF = item.real.macro_f1 - metric.macro_f1;
      let reading;
      if (condition === "real") {
        const alternatives = ["erdos_renyi", "degree_preserved"];
        const losses = alternatives.map(key => item.real.macro_f1 - item[key].macro_f1);
        reading = dataset === "prostate"
          ? "This high-signal tissue task remains nearly separable after rewiring; expression measurements carry most of the predictive information in this ablation."
          : `Replacing the curated graph costs ${Math.min(...losses).toFixed(1)}–${Math.max(...losses).toFixed(1)} macro-F1 points. That controlled loss isolates information carried by biological organization.`;
      } else {
        reading = `${conditionLabel[condition]} changes held-out accuracy by ${lossA.toFixed(1)} points and macro-F1 by ${lossF.toFixed(1)} points relative to the curated graph.`;
      }
      if (dataset === "prostate") reading += " Prostate topology controls use a single held-out ablation split, so they are not directly equivalent to five-fold means.";
      $("#topology-reading").textContent = reading;
      $$("[data-topology]").forEach(btn => btn.classList.toggle("active", btn.dataset.topology === dataset));
      $$("[data-condition]").forEach(btn => btn.classList.toggle("active", btn.dataset.condition === condition));
    }

    function draw(now) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = colors.white; ctx.fillRect(0, 0, canvas.width, canvas.height);
      const edges = condition === "real" ? realEdges : condition === "erdos_renyi" ? randomEdges : degreeEdges;
      edges.forEach(([a,b], i) => {
        const p1 = nodes[a], p2 = nodes[b];
        ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y);
        const pulse = !reduceMotion && (i + Math.floor(now / 110)) % 21 === 0;
        ctx.strokeStyle = pulse ? colors.coral : "rgba(78,118,152,.26)";
        ctx.lineWidth = pulse ? 2 : 1;
        ctx.stroke();
      });
      nodes.forEach((node, i) => {
        ctx.beginPath(); ctx.arc(node.x, node.y, i % 9 === 0 ? 8 : 5, 0, Math.PI * 2);
        ctx.fillStyle = [colors.coral, colors.gold, colors.blue, colors.mint][node.group]; ctx.fill();
        ctx.strokeStyle = colors.white; ctx.lineWidth = 1; ctx.stroke();
      });
      const item = current();
      text(ctx, item.label.toUpperCase(), 33, 34, 10, colors.ink, "left", "IBM Plex Mono");
      text(ctx, condition === "real" ? "curated modules remain locally coherent" : condition === "erdos_renyi" ? "local modules are removed" : "node degree remains; partners change", 33, 382, 9, colors.muted, "left", "IBM Plex Mono");
      requestAnimationFrame(draw);
    }

    $$("[data-topology]").forEach(button => button.addEventListener("click", () => { dataset = button.dataset.topology; condition = "real"; updateTopologyUi(); }));
    $$("[data-condition]").forEach(button => button.addEventListener("click", () => { condition = button.dataset.condition; updateTopologyUi(); }));
    updateTopologyUi();
    requestAnimationFrame(draw);
  }

  function initResults(data) {
    const select = $("#analysis-select");
    const chart = $("#performance-chart");
    if (!select || !chart || !data?.analyses?.length) return;
    data.analyses.forEach(analysis => {
      const option = document.createElement("option");
      option.value = analysis.id;
      option.textContent = `${analysis.cohort} · ${analysis.outcome}`;
      select.append(option);
    });
    let metric = "accuracy";
    const metricLabels = { accuracy: "Accuracy", macro_f1: "Macro-F1", sensitivity: "Sensitivity", specificity: "Specificity" };

    function render() {
      const analysis = data.analyses.find(item => item.id === select.value) || data.analyses[0];
      const models = analysis.models.filter(model => model[metric] && Number.isFinite(model[metric].mean));
      $("#result-context").innerHTML = [
        ["Cohort", analysis.cohort], ["Outcome", analysis.outcome], ["Profiles / classes", `${analysis.samples.toLocaleString()} / ${analysis.classes}`], ["Source", analysis.source]
      ].map(([label,value]) => `<div class="context-item"><span>${label}</span><b>${value}</b></div>`).join("");
      if (!models.length) {
        chart.innerHTML = `<p class="empty-metric">${metricLabels[metric]} was not reported for this saved analysis. Choose another metric.</p>`;
      } else {
        chart.innerHTML = models.map(model => {
          const value = model[metric].mean;
          const sd = model[metric].sd;
          const low = clamp(value - (sd || 0), 0, 100);
          const high = clamp(value + (sd || 0), 0, 100);
          return `<div class="performance-row ${model.family === "GiG" ? "gig" : ""}">
            <div class="performance-name"><b>${model.name}</b><small>${model.family === "GiG" ? `GiG · ${model.backbone.toUpperCase()}` : `node GNN · ${model.backbone.toUpperCase()}`}</small></div>
            <div class="performance-track"><div class="performance-fill" style="width:${value}%"></div>${Number.isFinite(sd) ? `<i class="performance-whisker" style="left:${low}%;width:${high-low}%"></i>` : ""}</div>
            <div class="performance-value">${value.toFixed(1)}%${Number.isFinite(sd) ? `<small>± ${sd.toFixed(1)}</small>` : ""}</div>
          </div>`;
        }).join("");
      }
      const caveat = analysis.id === "rareseq_subtype" && metric === "macro_f1" ? " For this imbalanced subtype task, the strongest node baseline has higher macro-F1 than the saved GiG model; accuracy and macro-F1 should be interpreted together." : "";
      $("#result-footnote").textContent = `${data.evaluation_note} GiG and matched node-GNN baselines share the same input node channels and fold assignments.${caveat}`;
    }
    select.value = data.analyses[0].id;
    select.addEventListener("change", render);
    $$("#metric-toggle button").forEach(button => button.addEventListener("click", () => {
      metric = button.dataset.metric;
      $$("#metric-toggle button").forEach(item => item.classList.toggle("active", item === button));
      render();
    }));
    render();
  }

  function initExamples(data) {
    const track = $("#example-track");
    if (!track || !data?.analyses?.length) return;
    const best = analysis => analysis.models.find(model => model.family === "GiG") || analysis.models[0];
    track.innerHTML = data.analyses.map(analysis => {
      const model = best(analysis);
      const acc = model.accuracy?.mean;
      const f1 = model.macro_f1?.mean;
      return `<article class="example-card">
        <header><span class="assay">${analysis.assay}</span><span class="source-tag">${analysis.availability === "capsule" ? "capsule-backed" : "saved result"}</span></header>
        <h3>${analysis.outcome}</h3><p class="cohort">${analysis.cohort}</p>
        <div class="example-stats"><p><span>profiles</span><b>${analysis.samples.toLocaleString()}</b></p><p><span>classes</span><b>${analysis.classes}</b></p><p><span>accuracy</span><b>${Number.isFinite(acc) ? `${acc.toFixed(1)}%` : "—"}</b></p><p><span>macro-F1</span><b>${Number.isFinite(f1) ? `${f1.toFixed(1)}%` : "—"}</b></p></div>
        <a class="button button-quiet" href="https://app.islamlab.org/gig/?example=${encodeURIComponent(analysis.id)}">Open saved analysis <span aria-hidden="true">→</span></a>
      </article>`;
    }).join("");
    const updatePosition = () => {
      const cards = $$(".example-card", track);
      if (!cards.length) return;
      let nearest = 0, distance = Infinity;
      cards.forEach((card, index) => {
        const d = Math.abs(card.offsetLeft - track.scrollLeft);
        if (d < distance) { distance = d; nearest = index; }
      });
      $("#example-position").textContent = `${String(nearest + 1).padStart(2,"0")} / ${String(cards.length).padStart(2,"0")}`;
    };
    const scrollCards = direction => {
      const card = $(".example-card", track);
      if (!card) return;
      track.scrollBy({ left: direction * (card.offsetWidth + 15), behavior: reduceMotion ? "auto" : "smooth" });
    };
    $("#example-prev").addEventListener("click", () => scrollCards(-1));
    $("#example-next").addEventListener("click", () => scrollCards(1));
    track.addEventListener("scroll", updatePosition, { passive: true });
    updatePosition();
  }

  function initPatientGraph(network) {
    const canvas = $("#patient-graph");
    const ranking = $("#gene-ranking");
    const tooltip = $("#graph-tooltip");
    if (!canvas || !network?.nodes?.length) return;
    const ctx = canvas.getContext("2d");
    const map = new Map(network.nodes.map(node => [node.id, node]));
    const positions = new Map(network.nodes.map(node => [node.id, { x: 50 + node.x * 800, y: 38 + node.y * 560 }]));
    let hover = null;
    const top = network.nodes.filter(node => node.attributed).sort((a,b) => b.importance - a.importance).slice(0, 8);
    ranking.innerHTML = top.map(node => `<div class="gene-row"><span>${node.id}</span><i><b style="width:${node.importance * 100}%"></b></i><em>${node.importance.toFixed(2)}</em></div>`).join("");

    function nodeRadius(node) { return node.attributed ? 7 + node.importance * 11 : 5; }
    function draw(now) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#041329"; ctx.fillRect(0,0,canvas.width,canvas.height);
      network.edges.forEach((edge, index) => {
        const a = positions.get(edge.source), b = positions.get(edge.target);
        if (!a || !b) return;
        ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y);
        const pulse = !reduceMotion && (index + Math.floor(now / 100)) % 43 === 0;
        ctx.strokeStyle = pulse ? "rgba(240,166,152,.85)" : "rgba(103,125,151,.25)";
        ctx.lineWidth = pulse ? 1.8 : .8; ctx.stroke();
      });
      network.nodes.forEach((node, index) => {
        const p = positions.get(node.id);
        const r = nodeRadius(node);
        if (node.attributed && !reduceMotion) {
          const halo = r + 3 + (Math.sin(now / 550 + index) + 1) * 2;
          ctx.beginPath(); ctx.arc(p.x,p.y,halo,0,Math.PI*2); ctx.fillStyle = `rgba(201,65,48,${.04 + node.importance*.06})`; ctx.fill();
        }
        ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2);
        ctx.fillStyle = node.attributed ? (node.importance > .65 ? colors.coral : colors.gold) : colors.blue;
        ctx.fill();
        ctx.strokeStyle = hover === node.id ? colors.white : "rgba(255,255,255,.72)";
        ctx.lineWidth = hover === node.id ? 2.5 : 1; ctx.stroke();
        if (node.attributed || hover === node.id) text(ctx, node.id, p.x, p.y + r + 12, node.attributed ? 9 : 8, "#e4ebf2", "center", "IBM Plex Mono");
      });
      text(ctx, "DE-IDENTIFIED SUBGRAPH · ACTUAL SAVED EDGES", 28, 23, 9, "#7f90a4", "left", "IBM Plex Mono");
      requestAnimationFrame(draw);
    }
    canvas.addEventListener("pointermove", event => {
      const rect = canvas.getBoundingClientRect();
      const mx = (event.clientX - rect.left) * canvas.width / rect.width;
      const my = (event.clientY - rect.top) * canvas.height / rect.height;
      let nearest = null, distance = 24;
      network.nodes.forEach(node => {
        const p = positions.get(node.id);
        const d = Math.hypot(mx-p.x,my-p.y);
        if (d < distance) { distance = d; nearest = node; }
      });
      hover = nearest?.id || null;
      if (nearest) {
        tooltip.hidden = false;
        tooltip.style.left = `${clamp(event.clientX - rect.left + 13, 5, rect.width - 205)}px`;
        tooltip.style.top = `${clamp(event.clientY - rect.top - 12, 5, rect.height - 82)}px`;
        tooltip.innerHTML = `<b>${nearest.id}</b><br>${nearest.group}<br>${nearest.attributed ? `relative attribution ${nearest.importance.toFixed(2)}` : "shared pathway neighbor"}`;
      } else tooltip.hidden = true;
    });
    canvas.addEventListener("pointerleave", () => { hover = null; tooltip.hidden = true; });
    requestAnimationFrame(draw);
  }

  async function loadData() {
    try {
      const [evidenceResponse, networkResponse] = await Promise.all([
        fetch("assets/data/evidence.json"),
        fetch("assets/data/prostate-network.json")
      ]);
      if (!evidenceResponse.ok || !networkResponse.ok) throw new Error("data request failed");
      const [evidence, network] = await Promise.all([evidenceResponse.json(), networkResponse.json()]);
      initTopology(evidence.topology_controls);
      initResults(evidence);
      initExamples(evidence);
      initPatientGraph(network);
    } catch (error) {
      console.error("Graph-in-Graph page data could not be loaded", error);
      const track = $("#example-track");
      if (track) track.innerHTML = '<p class="loading">Saved examples are unavailable in this preview.</p>';
      const chart = $("#performance-chart");
      if (chart) chart.innerHTML = '<p class="empty-metric">Evidence data could not be loaded. Serve this folder through a local web server rather than opening the file directly.</p>';
    }
  }

  initNavigation();
  initReveals();
  initCaptions();
  initBibtex();
  initMethodAnimation();
  loadData();
})();
