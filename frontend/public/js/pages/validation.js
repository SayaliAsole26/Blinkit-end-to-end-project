/** Validation metrics — GET /api/validation */
(function () {
  const UI = window.BlinkitUI;

  function metricCard(label, value, suffix = "") {
    const display = value != null ? `${UI.formatPercent(value)}${suffix}` : "—";
    return `<div class="bg-surface-container-lowest p-6 rounded-lg border border-outline-variant">
      <p class="text-label-md text-secondary uppercase mb-2">${label}</p>
      <p class="font-headline-lg text-headline-lg">${display}</p>
    </div>`;
  }

  function render(data) {
    const grid = document.getElementById("validation-metrics");
    if (!grid) return;
    grid.innerHTML = [
      metricCard("Overall Agreement", data.agreement_rate),
      metricCard("Barrier Agreement", data.barrier_agreement),
      metricCard("Funnel Agreement", data.funnel_agreement),
      metricCard("Competitor Agreement", data.competitor_agreement),
      `<div class="bg-surface-container-lowest p-6 rounded-lg border border-outline-variant">
        <p class="text-label-md text-secondary uppercase mb-2">Validation Sample</p>
        <p class="font-headline-lg">${UI.formatNumber(data.sample_size)} clusters</p>
      </div>`,
    ].join("");

    const tiers = document.getElementById("confidence-tiers");
    if (tiers && data.confidence_tiers) {
      tiers.innerHTML = Object.entries(data.confidence_tiers)
        .map(
          ([tier, count]) => `<div class="flex justify-between py-2 border-b border-outline-variant/30">
            <span class="capitalize font-medium">${tier}</span>
            <span class="font-bold">${UI.formatNumber(count)} insights</span>
          </div>`
        )
        .join("");
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("validation");
    const main = document.querySelector("main");
    try {
      render(await BlinkitAPI.validation());
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
