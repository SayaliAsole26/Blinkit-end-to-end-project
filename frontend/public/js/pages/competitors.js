/** Competitor Benchmark — GET /api/charts/competitors */
(function () {
  const UI = window.BlinkitUI;

  function render(data) {
    const tbody = document.getElementById("competitor-body");
    if (!tbody) return;
    const matrix = data.matrix || {};
    const entities = Object.keys(matrix).sort();
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
