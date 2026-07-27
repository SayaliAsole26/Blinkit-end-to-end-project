/** Evidence drill-down — GET /api/insights/{id} from ?id= query param */
(function () {
  const UI = window.BlinkitUI;

  function getInsightId() {
    return new URLSearchParams(window.location.search).get("id");
  }

  function renderBarrierBar(split) {
    const container = document.getElementById("barrier-breakdown");
    if (!container || !split) return;

    const entries = Object.entries(split).sort((a, b) => b[1] - a[1]);
    const colors = ["bg-primary-container", "bg-surface-container-highest", "bg-surface-container-high"];

    const bar = entries
      .map(([id, val], i) => {
        const pct = Math.round(val * 100);
        return `<div class="h-full ${colors[i] || "bg-surface-container"} border-r border-white/20" style="width:${pct}%" title="${UI.barrierLabel(id)}"></div>`;
      })
      .join("");

    const legend = entries
      .map(([id, val], i) => {
        const pct = Math.round(val * 100);
        return `<div class="flex items-center gap-1.5">
          <div class="w-2.5 h-2.5 rounded-full ${colors[i] || "bg-surface-container"}"></div>
          <span class="${i === 0 ? "text-on-surface" : "text-secondary"}">${UI.barrierLabel(id)} (${pct}%)</span>
        </div>`;
      })
      .join("");

    container.innerHTML = `
      <div class="w-full h-8 flex rounded-full overflow-hidden mb-2">${bar}</div>
      <div class="flex flex-wrap gap-4 text-[12px]">${legend}</div>`;
  }

  function renderSnippets(snippets) {
    const container = document.getElementById("evidence-snippets");
    if (!container) return;
    const items = (snippets || []).slice(0, 3);
    container.innerHTML =
      items
        .map(
          (s) =>
            `<div class="p-4 rounded-lg border border-outline-variant bg-surface-container-lowest italic text-on-surface-variant font-body-md">"${s}"</div>`
        )
        .join("") ||
      `<p class="text-secondary text-body-md">No paraphrased evidence available.</p>`;
  }

  function renderCompetitors(mentions) {
    const tbody = document.getElementById("competitor-rows");
    const badge = document.getElementById("competitor-count");
    if (!tbody) return;
    const list = mentions || [];
    if (badge) badge.textContent = `${list.length} Entities Found`;
    tbody.innerHTML =
      list
        .map(
          (m) => `<tr>
        <td class="px-4 py-3 font-medium">${m.entity}</td>
        <td class="px-4 py-3 text-secondary">${m.advantage.replace(/_/g, " ")}</td>
        <td class="px-4 py-3 text-right">${UI.formatNumber(m.count)}</td>
      </tr>`
        )
        .join("") ||
      `<tr><td colspan="3" class="px-4 py-6 text-center text-secondary">No competitor mentions</td></tr>`;
  }

  function renderInsight(item) {
    document.getElementById("insight-statement").textContent = item.statement;
    document.getElementById("confidence-badge").innerHTML = UI.confidenceCardBadge(item.confidence_tier);
    document.getElementById("funnel-stage-label").textContent = UI.funnelLabel(
      item.dominant_funnel_leak_stage
    ).toUpperCase();
    document.getElementById("funnel-stage-desc").textContent =
      `Evidence from ${UI.formatNumber(item.evidence_count)} mentions across ${item.source_diversity} platform(s).`;

    const staleEl = document.getElementById("stale-badge");
    if (staleEl) staleEl.classList.toggle("hidden", !item.is_stale);

    const rqEl = document.getElementById("rq-tags");
    if (rqEl) {
      rqEl.innerHTML = (item.related_RQs || [])
        .map((rq) => `<span class="px-2 py-0.5 bg-secondary-container rounded text-label-sm">${rq}</span>`)
        .join("");
    }

    renderBarrierBar(item.cognitive_barrier_split);
    renderSnippets(item.example_snippets);
    renderCompetitors(item.competitor_mentions);
  }

  function wireClose() {
    const close = () => {
      if (document.referrer.includes("insights")) window.location.href = "/insights.html";
      else window.location.href = "/";
    };
    document.getElementById("close-drawer")?.addEventListener("click", close);
    document.getElementById("drawer-overlay")?.addEventListener("click", (e) => {
      if (e.target.id === "drawer-overlay") close();
    });
    document.getElementById("copy-link")?.addEventListener("click", () => {
      navigator.clipboard?.writeText(window.location.href);
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("evidence");
    wireClose();

    const id = getInsightId();
    if (!id) {
      UI.showError(document.body, "Missing insight id — open from Overview or Insight Explorer.");
      return;
    }

    try {
      const item = await BlinkitAPI.insight(id);
      renderInsight(item);
    } catch (err) {
      UI.showError(document.body, err.message);
    }
  });
})();
