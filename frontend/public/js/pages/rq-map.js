/** RQ Map — GET /api/rq */
(function () {
  const UI = window.BlinkitUI;

  function render(data) {
    const grid = document.getElementById("rq-grid");
    if (!grid) return;
    const counts = data.counts || {};
    grid.innerHTML = Object.keys(UI.RQ_LABELS)
      .map((rq) => {
        const count = counts[rq] || 0;
        const top = (data.top_by_rq || {})[rq];
        const link = top
          ? `<a href="/evidence.html?id=${top.insight_id}" class="text-primary font-bold text-label-md hover:underline mt-2 inline-block">View top insight →</a>`
          : `<span class="text-secondary text-label-md mt-2 block">No insights mapped</span>`;
        return `<div class="bg-surface-container-lowest rounded-lg p-5 border border-outline-variant/30 hover:border-primary transition-colors">
          <div class="flex justify-between items-start mb-2">
            <span class="font-headline-sm">${rq}</span>
            <span class="px-2 py-0.5 bg-primary-container rounded-full text-label-md font-bold">${UI.formatNumber(count)}</span>
          </div>
          <p class="text-secondary text-body-md mb-3">${UI.RQ_LABELS[rq]}</p>
          ${top ? `<p class="text-body-md line-clamp-2">${top.statement}</p>` : ""}
          ${link}
        </div>`;
      })
      .join("");
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("rqmap");
    const main = document.querySelector("main");
    try {
      render(await BlinkitAPI.rqMap());
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
