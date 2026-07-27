/** Segments — GET /api/segments */
(function () {
  const UI = window.BlinkitUI;

  function render(data) {
    const root = document.getElementById("segments-list");
    if (!root) return;
    const segments = data.segments || {};
    const names = Object.keys(segments).sort((a, b) => segments[b].length - segments[a].length);
    if (!names.length) {
      root.innerHTML = `<p class="text-secondary text-center py-12">No segment data available.</p>`;
      return;
    }
    root.innerHTML = names
      .map((name) => {
        const items = segments[name];
        const rows = items
          .slice(0, 5)
          .map(
            (item) => `<li class="py-2 border-b border-outline-variant/30 last:border-0">
              <a href="/evidence.html?id=${item.insight_id}" class="hover:text-primary">${item.statement}</a>
              <span class="text-secondary text-label-md ml-2">· ${UI.formatNumber(item.evidence_count)} evidence</span>
            </li>`
          )
          .join("");
        return `<div class="bg-surface-container-lowest rounded-lg border border-outline-variant/30 overflow-hidden">
          <div class="px-5 py-3 bg-surface-container-low flex justify-between items-center">
            <h3 class="font-headline-sm capitalize">${name.replace(/_/g, " ")}</h3>
            <span class="text-label-md font-bold">${UI.formatNumber(items.length)} insights</span>
          </div>
          <ul class="px-5 py-3 text-body-md">${rows}</ul>
        </div>`;
      })
      .join("");
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("segments");
    const main = document.querySelector("main");
    try {
      render(await BlinkitAPI.segments());
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
