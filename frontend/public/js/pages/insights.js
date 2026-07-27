/** Insight Explorer — live data from GET /api/insights with filters + pagination */
(function () {
  const UI = window.BlinkitUI;
  const PAGE_SIZE = 12;

  const state = {
    page: 1,
    q: "",
    rq: "",
    barrier: "",
    funnel_stage: "",
    confidence: "",
    segment: "",
  };

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    state.q = params.get("q") || "";
    state.rq = params.get("rq") || "";
    state.page = parseInt(params.get("page") || "1", 10);
    if (state.q) {
      const search = document.querySelector('header input[type="text"]');
      if (search) search.value = state.q;
    }
  }

  function buildParams() {
    const p = { page: state.page, page_size: PAGE_SIZE };
    if (state.q) p.q = state.q;
    if (state.rq) p.rq = state.rq;
    if (state.barrier) p.barrier = state.barrier;
    if (state.funnel_stage) p.funnel_stage = state.funnel_stage;
    if (state.confidence) p.confidence = state.confidence;
    if (state.segment) p.segment = state.segment;
    return p;
  }

  function renderCard(item) {
    const barrier = UI.dominantBarrier(item.cognitive_barrier_split);
    const impact = Math.round((barrier.value || 0) * 100);
    const rqTags = (item.related_RQs || [])
      .slice(0, 2)
      .map((rq) => `<span class="px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded text-label-sm">${rq}</span>`)
      .join("");
    const segTags = (item.segment_relevance || [])
      .slice(0, 2)
      .map((s) => `<span class="px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded text-label-sm">${s.replace(/_/g, " ")}</span>`)
      .join("");

    return `<div class="bg-surface-container-lowest rounded-lg p-5 shadow-sm border border-outline-variant/30 insight-card-hover transition-all duration-300 flex flex-col gap-4 cursor-pointer"
        data-insight-id="${item.insight_id}">
      <div class="flex justify-between items-start">
        ${UI.confidenceCardBadge(item.confidence_tier)}
        ${item.is_stale ? '<span class="material-symbols-outlined text-orange-500 text-[20px]" title="Stale">history</span>' : ""}
      </div>
      <h3 class="font-headline-sm text-on-surface leading-snug">${item.statement}</h3>
      <div class="space-y-3">
        <div class="flex flex-col gap-1">
          <div class="flex justify-between text-label-sm uppercase tracking-wider text-on-surface-variant">
            <span>Cognitive Barrier: ${barrier.label}</span>
            <span>${impact}% Impact</span>
          </div>
          <div class="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
            <div class="h-full bg-primary-container" style="width: ${impact}%"></div>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <span class="px-2 py-0.5 bg-secondary-container text-on-secondary-container rounded text-label-sm">${UI.funnelLabel(item.dominant_funnel_leak_stage)}</span>
          ${segTags}${rqTags}
        </div>
      </div>
      <div class="mt-auto pt-4 border-t border-outline-variant/30 flex items-center justify-between">
        <div class="flex items-center gap-4 text-on-surface-variant">
          <div class="flex items-center gap-1">
            <span class="material-symbols-outlined text-[18px]">description</span>
            <span class="text-label-md font-bold">${UI.formatNumber(item.evidence_count)} Evidence</span>
          </div>
          <div class="flex items-center gap-1">
            <span class="material-symbols-outlined text-[18px]">devices</span>
            <span class="text-label-md font-bold">${item.source_diversity} Platforms</span>
          </div>
        </div>
        <button class="text-primary font-bold text-label-md hover:underline view-details-btn" data-id="${item.insight_id}">View Details</button>
      </div>
    </div>`;
  }

  function renderGrid(items) {
    const grid = document.getElementById("insights-grid");
    if (!grid) return;

    if (!items.length) {
      grid.innerHTML = `<div class="col-span-full py-16 text-center text-secondary">
        <span class="material-symbols-outlined text-[48px] mb-2 block">search_off</span>
        No insights match your filters.</div>`;
      return;
    }

    grid.innerHTML = items.map(renderCard).join("");

    grid.querySelectorAll("[data-insight-id]").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".view-details-btn")) return;
        const id = card.dataset.insightId;
        window.location.href = `/evidence.html?id=${id}`;
      });
    });
    grid.querySelectorAll(".view-details-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        window.location.href = `/evidence.html?id=${btn.dataset.id}`;
      });
    });
  }

  function renderPagination(total) {
    const footer = document.getElementById("insights-pagination");
    if (!footer) return;

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    const start = (state.page - 1) * PAGE_SIZE + 1;
    const end = Math.min(state.page * PAGE_SIZE, total);

    footer.querySelector("[data-page-info]").textContent =
      total === 0 ? "No insights" : `Showing ${start} to ${end} of ${total} insights`;

    const controls = footer.querySelector("[data-page-controls]");
    if (!controls) return;

    let buttons = `<button class="p-2 rounded-lg border border-outline hover:bg-surface-container-high disabled:opacity-30" data-page-prev ${state.page <= 1 ? "disabled" : ""}>
      <span class="material-symbols-outlined">chevron_left</span></button>`;

    const maxButtons = 5;
    let startPage = Math.max(1, state.page - 2);
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    startPage = Math.max(1, endPage - maxButtons + 1);

    for (let i = startPage; i <= endPage; i++) {
      const active = i === state.page;
      buttons += `<button class="w-10 h-10 rounded-lg ${active ? "bg-primary-container text-on-primary-container font-bold shadow-sm" : "border border-outline hover:bg-surface-container-high font-bold transition-colors"}"
        data-page="${i}">${i}</button>`;
    }

    buttons += `<button class="p-2 rounded-lg border border-outline hover:bg-surface-container-high disabled:opacity-30" data-page-next ${state.page >= totalPages ? "disabled" : ""}>
      <span class="material-symbols-outlined">chevron_right</span></button>`;

    controls.innerHTML = buttons;

    controls.querySelector("[data-page-prev]")?.addEventListener("click", () => goToPage(state.page - 1));
    controls.querySelector("[data-page-next]")?.addEventListener("click", () => goToPage(state.page + 1));
    controls.querySelectorAll("[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => goToPage(parseInt(btn.dataset.page, 10)));
    });
  }

  function goToPage(page) {
    state.page = Math.max(1, page);
    loadInsights();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function loadInsights() {
    const grid = document.getElementById("insights-grid");
    if (grid) {
      grid.innerHTML = `<div class="col-span-full py-16 text-center text-secondary">Loading insights…</div>`;
    }
    try {
      const data = await BlinkitAPI.insights(buildParams());
      renderGrid(data.items || []);
      renderPagination(data.total || 0);
    } catch (err) {
      const main = document.querySelector("main") || document.body;
      UI.showError(main, err.message);
      if (grid) grid.innerHTML = "";
    }
  }

  function wireFilters() {
    UI.renderRqFilterChips("rq-chips", (chip) => {
      document.querySelectorAll("[data-rq-chip]").forEach((c) => c.classList.remove("active-filter-chip"));
      chip.classList.add("active-filter-chip");
      state.rq = chip.dataset.rqChip || "";
      state.page = 1;
      loadInsights();
    });
    if (state.rq) {
      const active = document.querySelector(`[data-rq-chip="${state.rq}"]`);
      if (active) {
        document.querySelectorAll("[data-rq-chip]").forEach((c) => c.classList.remove("active-filter-chip"));
        active.classList.add("active-filter-chip");
      }
    }

    const filterMap = [
      ["filter-barrier", "barrier"],
      ["filter-funnel", "funnel_stage"],
      ["filter-confidence", "confidence"],
      ["filter-segment", "segment"],
    ];
    filterMap.forEach(([id, key]) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", () => {
        state[key] = el.value;
        state.page = 1;
        loadInsights();
      });
    });

    const search = document.querySelector('header input[type="text"]');
    if (search) {
      let debounce;
      search.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => {
          state.q = search.value.trim();
          state.page = 1;
          loadInsights();
        }, 350);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    UI.wireSidebar("insights");
    readUrlParams();
    wireFilters();
    loadInsights();
  });
})();
