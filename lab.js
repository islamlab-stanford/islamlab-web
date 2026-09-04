(() => {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const initProjectCarousel = (carousel) => {
    const slides = [...carousel.querySelectorAll(".project-slide")]
      .sort((left, right) => Number(left.dataset.projectOrder) - Number(right.dataset.projectOrder));
    const previous = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");
    const status = carousel.querySelector("[data-carousel-status]");
    const dots = carousel.querySelector("[data-carousel-dots]");
    const stage = carousel.querySelector(".project-stage");
    if (!slides.length || !previous || !next || !status || !dots) return;

    let index = Math.max(0, slides.findIndex((slide) => slide.classList.contains("is-active")));
    let timer;

    const stop = () => window.clearInterval(timer);
    const start = () => {
      stop();
      if (slides.length < 2 || reducedMotion.matches || document.hidden) return;
      timer = window.setInterval(() => {
        index = (index + 1) % slides.length;
        render();
      }, 6000);
    };

    const renderDots = () => {
      dots.replaceChildren();
      slides.forEach((slide, dotIndex) => {
        const button = document.createElement("button");
        const projectName = slide.dataset.projectName || `project ${dotIndex + 1}`;
        button.type = "button";
        button.className = dotIndex === index ? "is-active" : "";
        button.setAttribute("aria-label", `Show ${projectName}`);
        if (dotIndex === index) button.setAttribute("aria-current", "true");
        button.addEventListener("click", () => {
          index = dotIndex;
          render();
          start();
        });
        dots.appendChild(button);
      });
    };

    function render() {
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === index;
        slide.hidden = !active;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", String(!active));
      });
      carousel.classList.toggle("is-single", slides.length < 2);
      previous.disabled = slides.length < 2;
      next.disabled = slides.length < 2;
      status.textContent = `${index + 1} / ${slides.length}`;
      renderDots();
    }

    const move = (direction) => {
      if (slides.length < 2) return;
      index = (index + direction + slides.length) % slides.length;
      render();
      start();
    };

    previous.addEventListener("click", () => move(-1));
    next.addEventListener("click", () => move(1));
    stage?.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      move(event.key === "ArrowLeft" ? -1 : 1);
    });
    document.addEventListener("visibilitychange", start);
    reducedMotion.addEventListener?.("change", start);

    render();
    start();
  };

  const initGfmStory = (story) => {
    const canvas = story.querySelector(".gfm-canvas");
    const coreLabel = story.querySelector(".gfm-core small");
    const captionNumber = story.querySelector(".gfm-caption span");
    const captionTitle = story.querySelector(".gfm-caption strong");
    const captionLabel = story.querySelector(".gfm-caption small");
    if (!canvas || !coreLabel || !captionNumber || !captionTitle || !captionLabel) return;

    const nodes = [
      [12,27],[23,15],[31,34],[18,50],[38,54],[45,26],[54,42],[63,20],
      [72,37],[83,18],[87,51],[66,64],[48,72],[28,72],[77,76]
    ];
    const edges = [
      [0,1],[0,2],[0,3],[1,2],[2,3],[2,4],[2,5],[4,5],[4,13],[5,6],[5,7],[6,7],
      [6,8],[6,11],[7,8],[7,9],[8,9],[8,10],[8,11],[10,11],[11,12],[11,14],[12,13],[12,14]
    ];
    const stages = [
      ["01", "Describe structural role", "structural prompts"],
      ["02", "Encode two views", "text + graph streams"],
      ["03", "Align across graphs", "shared representation"],
      ["04", "Adapt to a new graph", "zero-shot transfer"]
    ];

    edges.forEach(([from, to], edgeIndex) => {
      const [ax, ay] = nodes[from];
      const [bx, by] = nodes[to];
      const dx = bx - ax;
      const dy = by - ay;
      const edge = document.createElement("i");
      edge.className = "gfm-edge";
      edge.style.left = `${ax}%`;
      edge.style.top = `${ay}%`;
      edge.style.width = `${Math.hypot(dx, dy)}%`;
      edge.style.transform = `rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg)`;
      edge.style.setProperty("--edge-delay", `${edgeIndex * 35}ms`);
      canvas.appendChild(edge);
    });

    const nodeElements = nodes.map(([x, y], nodeIndex) => {
      const node = document.createElement("span");
      node.className = `gfm-node community-${nodeIndex % 4}`;
      node.style.left = `${x}%`;
      node.style.top = `${y}%`;
      node.style.setProperty("--node-delay", `${nodeIndex * 70}ms`);
      node.appendChild(document.createElement("b"));
      canvas.appendChild(node);
      return node;
    });

    let stageIndex = 2;
    let timer;
    const render = () => {
      const [number, title, label] = stages[stageIndex];
      story.dataset.gfmStage = String(stageIndex);
      captionNumber.textContent = number;
      captionTitle.textContent = title;
      captionLabel.textContent = label;
      coreLabel.textContent = label;
      nodeElements.forEach((node, nodeIndex) => {
        node.firstElementChild.textContent = stageIndex === 1 && nodeIndex % 5 === 0
          ? ["deg", "core", "pr"][nodeIndex % 3]
          : "";
      });
    };
    const stop = () => window.clearInterval(timer);
    const start = () => {
      stop();
      if (reducedMotion.matches) return;
      timer = window.setInterval(() => {
        stageIndex = (stageIndex + 1) % stages.length;
        render();
      }, 2600);
    };

    story.addEventListener("mouseenter", stop);
    story.addEventListener("mouseleave", start);
    story.addEventListener("focusin", stop);
    story.addEventListener("focusout", start);
    render();
    start();
  };

  const projectCarousels = [...document.querySelectorAll("[data-project-carousel]")];

  const synchronizeProjectHeights = () => {
    const stages = projectCarousels
      .map((carousel) => carousel.querySelector(".project-stage"))
      .filter(Boolean);
    stages.forEach((stage) => { stage.style.height = "auto"; });

    let tallest = 0;
    projectCarousels.forEach((carousel) => {
      const stage = carousel.querySelector(".project-stage");
      if (!stage) return;
      carousel.querySelectorAll(".project-slide").forEach((slide) => {
        const measurement = slide.cloneNode(true);
        measurement.hidden = false;
        measurement.removeAttribute("aria-hidden");
        measurement.classList.add("is-active", "project-measure");
        stage.appendChild(measurement);
        tallest = Math.max(tallest, Math.ceil(measurement.getBoundingClientRect().height));
        measurement.remove();
      });
    });

    if (tallest > 0) stages.forEach((stage) => { stage.style.height = `${tallest}px`; });
  };

  let resizeTimer;
  const scheduleHeightSync = () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(synchronizeProjectHeights, 80);
  };

  projectCarousels.forEach(initProjectCarousel);
  document.querySelectorAll(".gfm-story").forEach(initGfmStory);
  window.requestAnimationFrame(synchronizeProjectHeights);
  window.addEventListener("load", synchronizeProjectHeights);
  window.addEventListener("resize", scheduleHeightSync);
  document.fonts?.ready.then(synchronizeProjectHeights);
})();
