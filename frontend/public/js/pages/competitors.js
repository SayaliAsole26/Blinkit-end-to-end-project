/** Competitor Benchmark — GET /api/charts/competitors */
(function () {
  const UI = window.BlinkitUI;

  const ADVANTAGE_LABELS = {
    ASSORTMENT: "broader product range and category depth",
    PRICE: "lower or more competitive pricing",
    TRUST: "stronger brand trust and purchase confidence",
    DELIVERY_SPEED: "faster or more reliable delivery",
  };

  function formatAdvantage(key) {
    return ADVANTAGE_LABELS[key] || key.replace(/_/g, " ").toLowerCase();
  }

  function renderTable(matrix) {
    const tbody = document.getElementById("competitor-body");
    if (!tbody) return [];
    const entities = Object.keys(matrix).sort();
    if (!entities.length) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-secondary">No competitor mentions in corpus.</td></tr>`;
      return [];
    }

    const rows = entities.map((entity) => {
      const adv = matrix[entity];
      const total = Object.values(adv).reduce((a, b) => a + b, 0);
      const sorted = Object.entries(adv).sort((a, b) => b[1] - a[1]);
      return { entity, total, top: sorted[0], advantages: sorted };
    });

    tbody.innerHTML = rows
      .map(
        ({ entity, total, top, advantages }) => `<tr class="hover:bg-surface-container-low">
          <td class="px-6 py-4 font-semibold">${entity}</td>
          <td class="px-6 py-4">${top ? top[0].replace(/_/g, " ") : "—"}</td>
          <td class="px-6 py-4 text-center font-bold">${UI.formatNumber(total)}</td>
          <td class="px-6 py-4 text-secondary">${advantages.map(([k]) => k.replace(/_/g, " ")).join(", ")}</td>
        </tr>`
      )
      .join("");

    return rows.sort((a, b) => b.total - a.total);
  }

  function renderInterpretation(rows) {
    const panel = document.getElementById("competitor-interpretation");
    const body = document.getElementById("competitor-interpretation-body");
    if (!panel || !body) return;

    if (!rows.length) {
      panel.classList.add("hidden");
      return;
    }

    panel.classList.remove("hidden");

    const totalMentions = rows.reduce((s, r) => s + r.total, 0);
    const leader = rows[0];
    const leaderShare = Math.round((leader.total / totalMentions) * 100);
    const topAdvCounts = {};
    for (const row of rows) {
      for (const [adv, count] of row.advantages) {
        topAdvCounts[adv] = (topAdvCounts[adv] || 0) + count;
      }
    }
    const dominantAdv = Object.entries(topAdvCounts).sort((a, b) => b[1] - a[1])[0];
    const advKey = dominantAdv?.[0] || "ASSORTMENT";

    const competitorBullets = rows.slice(0, 3).map((row) => {
      const advLabel = row.top ? formatAdvantage(row.top[0]) : "unspecified reasons";
      return `<li><strong>${row.entity}</strong> (${UI.formatNumber(row.total)} mentions) — users most often cite <strong>${row.top ? row.top[0].replace(/_/g, " ") : "—"}</strong>, meaning ${advLabel}.</li>`;
    });

    body.innerHTML = `
      <p>This table shows where shoppers <strong>explicitly compare Blinkit to a rival</strong> in reviews and social feedback. It is not a market-share estimate — it reflects <strong>why users say they go elsewhere</strong>.</p>
      <ul class="list-disc pl-5 space-y-2">
        <li><strong>Mentions</strong> count how many insight clusters reference that competitor when describing cross-shopping behaviour.</li>
        <li><strong>Top Advantage</strong> is the most-cited reason users prefer that rival (e.g. Assortment = wider range, Trust = confidence in product quality).</li>
        <li><strong>Advantages cited</strong> lists every advantage type mentioned for that competitor across the corpus.</li>
      </ul>
      <p class="font-semibold text-on-surface mt-4">Key takeaways from this corpus</p>
      <ul class="list-disc pl-5 space-y-2">
        <li><strong>${leader.entity}</strong> is the most referenced rival (${leaderShare}% of competitor mentions, ${UI.formatNumber(leader.total)} total).</li>
        <li>Across all rivals, <strong>${advKey.replace(/_/g, " ")}</strong> is the dominant cited advantage — users switch mainly for ${formatAdvantage(advKey)}, not sentiment scores.</li>
        ${competitorBullets.join("")}
      </ul>
      <p class="text-label-md text-secondary pt-2 border-t border-outline-variant/40">
        Use with the <a href="/barriers.html" class="text-primary font-semibold hover:underline">Barrier Chart</a> to see which cognitive barriers (Assortment Gap, Awareness Deficit, etc.) align with each competitor comparison.
      </p>`;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("competitors");
    const main = document.querySelector("main");
    try {
      const data = await BlinkitAPI.competitors();
      const rows = renderTable(data.matrix || {});
      renderInterpretation(rows);
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
