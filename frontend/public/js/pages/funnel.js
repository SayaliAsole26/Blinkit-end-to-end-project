/** Funnel Breakdown — GET /api/charts/funnel */
(function () {
  const UI = window.BlinkitUI;

  const STAGE_DESCRIPTIONS = {
    DISCOVERY:
      "users struggle to find products or categories in the app (search, browse, awareness)",
    CONSIDERATION:
      "users compare Blinkit to alternatives but hesitate before adding to cart",
    CONVERSION: "friction at checkout or final purchase decision",
    POST_PURCHASE_RETENTION:
      "issues affecting repeat orders or loyalty after the first buy",
  };

  function render(data) {
    const root = document.getElementById("funnel-chart");
    if (!root) return null;
    const raw = data.raw || {};
    const stages = data.stages || Object.keys(raw);
    const max = Math.max(...Object.values(raw), 1);
    root.innerHTML = stages
      .map((stage) => {
        const count = raw[stage] || 0;
        const pct = Math.round((count / max) * 100);
        return `<div class="space-y-2">
          <div class="flex justify-between text-body-md">
            <span class="font-medium">${UI.funnelLabel(stage)}</span>
            <span class="text-secondary">${UI.formatNumber(count)} insights</span>
          </div>
          <div class="h-10 w-full bg-surface-container rounded-full overflow-hidden">
            <div class="h-full bg-primary-container flex items-center px-4 transition-all" style="width:${Math.max(pct, count > 0 ? 8 : 0)}%">
              <span class="text-label-md font-bold">${pct}%</span>
            </div>
          </div>
        </div>`;
      })
      .join("");

    return { raw, stages, max };
  }

  function renderInterpretation(meta) {
    const panel = document.getElementById("funnel-interpretation");
    const body = document.getElementById("funnel-interpretation-body");
    if (!panel || !body || !meta) return;

    const { raw, stages } = meta;
    const entries = stages
      .map((stage) => ({ stage, count: raw[stage] || 0, label: UI.funnelLabel(stage) }))
      .sort((a, b) => b.count - a.count);
    const total = entries.reduce((s, e) => s + e.count, 0);

    if (!total) {
      panel.classList.add("hidden");
      return;
    }

    panel.classList.remove("hidden");
    const leader = entries[0];
    const leaderShare = Math.round((leader.count / total) * 100);
    const stageBullets = entries
      .filter((e) => e.count > 0)
      .map(
        (e) =>
          `<li><strong>${e.label}</strong> — ${UI.formatNumber(e.count)} insights (${Math.round((e.count / total) * 100)}% of corpus): ${STAGE_DESCRIPTIONS[e.stage] || "dominant leak stage for this cluster."}</li>`
      );

    body.innerHTML = `
      <p>Each bar shows how many validated insight cards leak at that <strong>funnel stage</strong>. Every insight has one dominant stage — where users drop off or hesitate in the shopping journey.</p>
      <ul class="list-disc pl-5 space-y-2">
        <li><strong>Insight count</strong> — number of clusters tagged with that stage as the primary leak (not unique users).</li>
        <li><strong>Bar length (%)</strong> — relative to the busiest stage (100% = highest count), so you can compare stages at a glance.</li>
        <li><strong>Discovery → Consideration → Conversion → Retention</strong> — left-to-top order follows the shopper journey from finding products to repeat purchase.</li>
      </ul>
      <p class="font-semibold text-on-surface mt-4">Key takeaways from this corpus</p>
      <ul class="list-disc pl-5 space-y-2">
        <li><strong>${leader.label}</strong> dominates (${UI.formatNumber(leader.count)} insights, ${leaderShare}% of ${UI.formatNumber(total)} total) — most friction happens when ${STAGE_DESCRIPTIONS[leader.stage] || "users interact at this stage"}.</li>
        ${stageBullets.join("")}
      </ul>
      <p class="text-label-md text-secondary pt-2 border-t border-outline-variant/40">
        Filter by funnel stage in <a href="/insights.html" class="text-primary font-semibold hover:underline">Insight Explorer</a>, or cross-check with the <a href="/barriers.html" class="text-primary font-semibold hover:underline">Barrier Chart</a> to see which cognitive barriers drive leaks at each stage.
      </p>`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("funnel");
    const main = document.querySelector("main");
    try {
      const data = await BlinkitAPI.funnel();
      const meta = render(data);
      renderInterpretation(meta);
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
