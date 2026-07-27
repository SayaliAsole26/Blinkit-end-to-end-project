/** Competitor Benchmark — GET /api/charts/competitors */
(function () {
  const UI = window.BlinkitUI;

  function renderChart(matrix) {
    const chart = document.getElementById("competitor-chart");
    if (!chart) return;

    const entities = Object.entries(matrix || {})
      .map(([entity, advantages]) => ({
        entity,
        total: Object.values(advantages).reduce((a, b) => a + b, 0),
        topAdvantage: Object.entries(advantages).sort((a, b) => b[1] - a[1])[0],
      }))
      .sort((a, b) => b.total - a.total);

    if (!entities.length) {
      chart.innerHTML = `<p class="text-secondary text-body-md">No competitor mentions in corpus.</p>`;
      return;
    }

    const max = entities[0].total || 1;
    chart.innerHTML = entities
      .map((entry) => {
        const pct = Math.round((entry.total / max) * 100);
        const advantage = entry.topAdvantage ? entry.topAdvantage[0].replace(/_/g, " ") : "—";
        return `<div class="space-y-2">
          <div class="flex justify-between text-body-md">
            <span class="font-semibold">${entry.entity}</span>
            <span class="text-secondary">${UI.formatNumber(entry.total)} mentions · Top: ${advantage}</span>
          </div>
          <div class="h-10 w-full bg-surface-container rounded-full overflow-hidden flex items-center">
            <div class="h-full bg-primary-container flex items-center px-4 transition-all duration-700" style="width:${pct}%">
              <span class="text-label-md text-on-primary-container font-bold">${pct}%</span>
            </div>
          </div>
        </div>`;
      })
      .join("");
  }

  function renderTable(matrix) {
    const tbody = document.getElementById("competitor-body");
    if (!tbody) return;
    const entities = Object.keys(matrix || {}).sort();
    if (!entities.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-secondary">No competitor mentions in corpus.</td></tr>`;
      return;
    }
    tbody.innerHTML = entities
      .map((entity) => {
        const adv = matrix[entity];
        const total = Object.values(adv).reduce((a, b) => a + b, 0);
        const top = Object.entries(adv).sort((a, b) => b[1] - a[1])[0];
        return `<tr class="hover:bg-surface-container-low">
          <td class="px-6 py-4 font-semibold">${entity}</td>
          <td class="px-6 py-4">${top ? top[0].replace(/_/g, " ") : "—"}</td>
          <td class="px-6 py-4 text-center font-bold">${UI.formatNumber(total)}</td>
          <td class="px-6 py-4 text-secondary">${Object.keys(adv).join(", ").replace(/_/g, " ")}</td>
        </tr>`;
      })
      .join("");
  }

  function render(data) {
    const matrix = data.matrix || {};
    renderChart(matrix);
    renderTable(matrix);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("competitors");
    const main = document.querySelector("main");
    try {
      render(await BlinkitAPI.competitors());
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
