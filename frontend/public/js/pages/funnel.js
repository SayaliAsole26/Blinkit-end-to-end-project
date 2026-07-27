/** Funnel Breakdown — GET /api/charts/funnel */
(function () {
  const UI = window.BlinkitUI;

  function render(data) {
    const root = document.getElementById("funnel-chart");
    if (!root) return;
    const raw = data.raw || {};
    const max = Math.max(...Object.values(raw), 1);
    root.innerHTML = (data.stages || Object.keys(raw))
      .map((stage) => {
        const count = raw[stage] || 0;
        const pct = Math.round((count / max) * 100);
        return `<div class="space-y-2">
          <div class="flex justify-between text-body-md">
            <span class="font-medium">${UI.funnelLabel(stage)}</span>
            <span class="text-secondary">${UI.formatNumber(count)} insights</span>
          </div>
          <div class="h-10 w-full bg-surface-container rounded-full overflow-hidden">
            <div class="h-full bg-primary-container flex items-center px-4 transition-all" style="width:${pct}%">
              <span class="text-label-md font-bold">${pct}%</span>
            </div>
          </div>
        </div>`;
      })
      .join("");
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("funnel");
    const main = document.querySelector("main");
    try {
      render(await BlinkitAPI.funnel());
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
