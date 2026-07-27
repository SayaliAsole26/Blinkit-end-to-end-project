/** Overview dashboard — live data from GET /api/overview */
(function () {
  const UI = window.BlinkitUI;

  function renderKpis(data) {
    const kpis = document.querySelectorAll("[data-kpi]");
    kpis.forEach((el) => {
      const key = el.dataset.kpi;
      switch (key) {
        case "insights":
          el.textContent = UI.formatNumber(data.insight_count);
          break;
        case "evidence":
          el.textContent = UI.formatNumber(data.evidence_mentions);
          break;
        case "platforms":
          el.textContent = UI.formatNumber(data.max_source_diversity || 5);
          break;
        case "high_confidence":
          el.textContent = `${data.high_confidence_pct ?? "—"}%`;
          break;
        case "agreement":
          el.textContent =
            data.agreement_rate != null
              ? `${UI.formatPercent(data.agreement_rate)} agreement`
              : "— agreement";
          break;
        default:
          break;
      }
    });

    const highBar = document.querySelector("[data-kpi-bar='high_confidence']");
    if (highBar && data.high_confidence_pct != null) {
      highBar.style.width = `${Math.min(data.high_confidence_pct, 100)}%`;
    }
  }

  function renderDataCollectionBanner(data) {
    const banner = document.getElementById("data-collection-banner");
    if (!banner) return;
    const msg = banner.querySelector("[data-collection-msg]");
    const text = UI.formatDataCollection(data.data_collection);
    if (text) {
      banner.classList.remove("hidden");
      if (msg) msg.textContent = text;
    } else {
      banner.classList.add("hidden");
    }
  }

  function renderConfidenceChart(data) {
    const container = document.getElementById("confidence-chart");
    if (!container) return;

    const tiers = data.confidence_tiers || {};
    const total = Object.values(tiers).reduce((a, b) => a + b, 0) || 1;
    const colors = { high: "bg-green-500", medium: "bg-yellow-500", low: "bg-gray-400" };

    const legend = Object.entries(tiers)
      .map(([tier, count]) => {
        const pct = Math.round((count / total) * 100);
        return `<div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full ${colors[tier] || "bg-secondary"}"></div>
          <span class="text-body-md capitalize">${tier} (${pct}% · ${count})</span>
        </div>`;
      })
      .join("");

    container.innerHTML = `
      <div class="flex items-center justify-center relative h-64">
        <div class="text-center">
          <span class="block font-headline-md text-headline-md">${UI.formatNumber(data.insight_count)}</span>
          <span class="text-label-sm text-secondary">Total Insights</span>
        </div>
      </div>
      <div class="ml-0 mt-4 space-y-3">${legend}</div>`;
  }

  function renderBarrierChart(data) {
    const container = document.getElementById("barrier-chart");
    if (!container) return;

    const raw = data.barrier_distribution || {};
    const entries = Object.entries(raw)
      .map(([id, weight]) => ({ id, weight: Number(weight), label: UI.barrierLabel(id) }))
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 6);

    const max = entries[0]?.weight || 1;

    container.innerHTML = entries
      .map((entry) => {
        const pct = Math.round((entry.weight / max) * 100);
        return `<div class="space-y-2">
          <div class="flex justify-between text-body-md">
            <span class="font-medium">${entry.label}</span>
            <span class="text-secondary">${entry.weight.toFixed(1)} weight</span>
          </div>
          <div class="h-8 w-full bg-surface-container rounded-full overflow-hidden flex items-center">
            <div class="h-full bg-primary-container flex items-center px-4 transition-all duration-700" style="width:${pct}%">
              <span class="text-label-md text-on-primary-container">${pct}%</span>
            </div>
          </div>
        </div>`;
      })
      .join("");
  }

  function renderTopInsights(data) {
    const tbody = document.getElementById("top-insights-body");
    if (!tbody) return;

    const rows = (data.top_insights || [])
      .map((item) => {
        const barrier = UI.dominantBarrier(item.cognitive_barrier_split);
        return `<tr class="hover:bg-surface-container-low transition-colors group cursor-pointer"
            onclick="window.location.href='/evidence.html?id=${item.insight_id}'">
          <td class="px-6 py-4">
            <div class="flex items-start gap-3">
              <span class="material-symbols-outlined text-primary mt-0.5">lightbulb</span>
              <div>
                <p class="font-body-md text-on-surface font-semibold">${item.statement}</p>
                <p class="text-label-sm text-secondary mt-1">${UI.barrierLabel(barrier.id)} · ${item.source_diversity} platform(s)</p>
              </div>
            </div>
          </td>
          <td class="px-6 py-4">${UI.confidenceBadge(item.confidence_tier)}</td>
          <td class="px-6 py-4">
            <div class="flex gap-1">${UI.funnelDots(item.dominant_funnel_leak_stage)}</div>
            <span class="text-label-sm text-secondary mt-1 block">${UI.funnelLabel(item.dominant_funnel_leak_stage)}</span>
          </td>
          <td class="px-6 py-4 text-center"><span class="font-body-md font-bold">${UI.formatNumber(item.evidence_count)}</span></td>
          <td class="px-6 py-4"><span class="material-symbols-outlined text-green-500" title="Validated insight">verified</span></td>
        </tr>`;
      })
      .join("");

    tbody.innerHTML = rows || `<tr><td colspan="5" class="px-6 py-8 text-center text-secondary">No insights loaded</td></tr>`;
  }

  function wireSearch() {
    const input = document.querySelector('header input[type="text"]');
    if (!input) return;
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && input.value.trim()) {
        window.location.href = `/insights.html?q=${encodeURIComponent(input.value.trim())}`;
      }
    });
  }

  function wireViewAll() {
    const btn = document.getElementById("view-all-insights");
    if (btn) btn.addEventListener("click", () => (window.location.href = "/insights.html"));
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("overview");
    wireSearch();
    wireViewAll();

    const main = document.querySelector("main") || document.body;
    try {
      const data = await BlinkitAPI.overview();
      renderKpis(data);
      renderDataCollectionBanner(data);
      renderConfidenceChart(data);
      renderBarrierChart(data);
      renderTopInsights(data);

      const runLabel = document.getElementById("pipeline-run-id");
      if (runLabel && data.run_id) runLabel.textContent = data.run_id;
    } catch (err) {
      UI.showError(main, err.message + " — start API with: uvicorn api.main:app --port 8000");
    }
  });
})();
