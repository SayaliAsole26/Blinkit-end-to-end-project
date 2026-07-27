/** Cognitive Barrier Chart — GET /api/charts/barriers */
(function () {
  const UI = window.BlinkitUI;

  const BARRIER_COLORS = {
    AWARENESS_DEFICIT: "#FFE141",
    AUTHENTICITY_DISTRUST: "#B3E5FC",
    ASSORTMENT_GAP: "#E1BEE7",
    CONVENIENCE_MISMATCH: "#FFCCBC",
    RETURN_POLICY_ANXIETY: "#C8E6C9",
    NONE_GROCERY_LOYAL: "#D1C4E9",
  };

  let chartData = null;

  function formatCategory(id) {
    return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function renderLegend(barriers) {
    const el = document.getElementById("barrier-legend");
    if (!el) return;
    el.innerHTML = barriers
      .map(
        (b) => `<div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full" style="background:${BARRIER_COLORS[b] || "#ccc"}"></span>
          <span class="text-label-md text-secondary">${UI.barrierLabel(b)}</span>
        </div>`
      )
      .join("");
  }

  function renderCategoryRows(byCategory) {
    const container = document.getElementById("barrier-chart-rows");
    if (!container) return;

    const entries = Object.entries(byCategory || {}).sort((a, b) => {
      const totalA = Object.values(a[1]).reduce((s, v) => s + v, 0);
      const totalB = Object.values(b[1]).reduce((s, v) => s + v, 0);
      return totalB - totalA;
    });

    if (!entries.length) {
      container.innerHTML = `<p class="text-secondary text-body-md">No barrier data for this filter.</p>`;
      return;
    }

    const allBarriers = [...new Set(entries.flatMap(([, split]) => Object.keys(split)))];
    renderLegend(allBarriers);

    container.innerHTML = entries
      .map(([category, split]) => {
        const sorted = Object.entries(split).sort((a, b) => b[1] - a[1]);
        const total = sorted.reduce((s, [, v]) => s + v, 0) || 1;
        const countLabel = sorted.map(([, v]) => `${Math.round(v * 100)}%`).join(" · ");

        const bar = sorted
          .map(([barrier, weight]) => {
            const pct = Math.round((weight / total) * 100);
            if (pct === 0) return "";
            return `<div class="h-full flex items-center justify-center text-[11px] font-bold text-on-surface border-r border-white/20"
              style="width:${pct}%;background:${BARRIER_COLORS[barrier] || "#ccc"}" title="${UI.barrierLabel(barrier)}">${pct}%</div>`;
          })
          .join("");

        return `<div class="space-y-2">
          <div class="flex justify-between items-end">
            <span class="font-bold text-on-surface">${formatCategory(category)}</span>
            <span class="text-label-md text-secondary uppercase tracking-wider">${countLabel}</span>
          </div>
          <div class="h-10 w-full flex rounded-full overflow-hidden bg-surface-container-low border border-outline-variant/30">${bar}</div>
        </div>`;
      })
      .join("");
  }

  function renderTopInsight(insight) {
    const el = document.getElementById("barrier-top-insight");
    if (!el || !insight) return;
    const barrier = UI.dominantBarrier(insight.cognitive_barrier_split);
    el.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-md font-bold uppercase">Top Insight</span>
        ${UI.confidenceCardBadge(insight.confidence_tier)}
      </div>
      <p class="font-headline-sm mb-3">${insight.statement}</p>
      <p class="text-on-surface-variant font-body-md mb-4">
        Dominant barrier: <strong>${barrier.label}</strong> · ${UI.formatNumber(insight.evidence_count)} evidence mentions
      </p>
      <a href="/evidence.html?id=${insight.insight_id}" class="w-full py-3 bg-primary text-white rounded-lg font-bold hover:brightness-110 transition-all flex items-center justify-center gap-2">
        View Evidence <span class="material-symbols-outlined text-[18px]">open_in_new</span>
      </a>`;
  }

  function renderDefinitions() {
    const el = document.getElementById("barrier-definitions");
    if (!el) return;
    el.innerHTML = Object.entries(UI.BARRIER_LABELS)
      .map(
        ([id, label], i) => `<div class="group" ${i === 0 ? 'data-open="true"' : ""}>
          <button type="button" class="w-full p-4 flex items-center justify-between text-left hover:bg-surface-container-low definition-toggle">
            <div class="flex items-center gap-3">
              <div class="w-2 h-2 rounded-full" style="background:${BARRIER_COLORS[id] || "#ccc"}"></div>
              <span class="font-bold">${label}</span>
            </div>
            <span class="material-symbols-outlined">expand_more</span>
          </button>
          <div class="px-4 pb-4 text-secondary text-body-md definition-content">${label} — cognitive friction identified in cross-category shopping feedback (not sentiment).</div>
        </div>`
      )
      .join("");

    el.querySelectorAll(".definition-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const parent = btn.closest(".group");
        const open = parent.getAttribute("data-open") === "true";
        el.querySelectorAll(".group").forEach((g) => g.removeAttribute("data-open"));
        if (!open) parent.setAttribute("data-open", "true");
      });
    });
  }

  async function loadChart() {
    chartData = await BlinkitAPI.barriers("");
    renderCategoryRows(chartData.by_category);
    renderTopInsight(chartData.top_insight);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("barriers");
    renderDefinitions();

    const main = document.querySelector("main");
    try {
      await loadChart();
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
