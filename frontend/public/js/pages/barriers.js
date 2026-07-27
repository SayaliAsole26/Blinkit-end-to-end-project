/** Cognitive Barrier Chart — GET /api/charts/barriers */
(function () {
  const UI = window.BlinkitUI;

  const BARRIER_COLORS = {
    AWARENESS_DEFICIT: "#FFE141",
    AUTHENTICITY_DISTRUST: "#B3E5FC",
    ASSORTMENT_GAP: "#E1BEE7",
    CONVENIENCE_MISMATCH: "#FFCCBC",
    RETURN_POLICY_ANXIETY: "#C8E6C9",
    NONE_GROCERY_LOYAL: "#D1C4E9",
  };

  const CATEGORY_LABELS = {
    personal_care: "Personal Care",
    groceries: "Groceries",
    health_pharmacy: "Health & Pharmacy",
    baby_care: "Baby Care",
    pet_supplies: "Pet Supplies",
    stationery: "Stationery",
    electronics: "Electronics",
    snacks: "Snacks",
    beverages: "Beverages",
    household: "Household",
    general: "General",
    all_categories: "Overall Corpus",
    other: "Other Categories",
  };

  const CATEGORY_KEYWORDS = [
    ["personal care", "personal_care"],
    ["grocer", "groceries"],
    ["grocery", "groceries"],
    ["vitamin", "health_pharmacy"],
    ["pharmacy", "health_pharmacy"],
    ["health", "health_pharmacy"],
    ["baby", "baby_care"],
    ["pet", "pet_supplies"],
    ["stationery", "stationery"],
    ["electronic", "electronics"],
    ["snack", "snacks"],
    ["beverage", "beverages"],
    ["household", "household"],
  ];

  let chartData = null;

  function formatCategory(id) {
    if (CATEGORY_LABELS[id]) return CATEGORY_LABELS[id];
    const pretty = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return pretty.length > 28 ? `${pretty.slice(0, 26)}…` : pretty;
  }

  function inferCategories(card) {
    if (Array.isArray(card.category_tags) && card.category_tags.length) {
      return card.category_tags;
    }
    const haystack = `${(card.theme_tags || []).join(" ")} ${card.statement || ""}`.toLowerCase();
    const found = [];
    for (const [keyword, slug] of CATEGORY_KEYWORDS) {
      if (haystack.includes(keyword) && !found.includes(slug)) found.push(slug);
    }
    return found.length ? found : ["general"];
  }

  function normalizeEntries(byCategory, categoryCounts) {
    const entries = Object.entries(byCategory || {}).map(([category, split]) => ({
      category,
      split,
      insightCount: categoryCounts[category] || 0,
      weight: Object.values(split).reduce((s, v) => s + v, 0),
    }));

    if (entries.length === 1 && entries[0].category === "all_categories") {
      return [{ ...entries[0], category: "all_categories" }];
    }

    entries.sort((a, b) => b.insightCount - a.insightCount || b.weight - a.weight);

    const top = entries.filter((e) => e.category !== "general" && e.category !== "all_categories").slice(0, 7);
    const rest = entries.filter((e) => !top.includes(e));

    if (!rest.length) return top.length ? top : entries.slice(0, 8);

    const otherSplit = {};
    let otherCount = 0;
    for (const entry of rest) {
      otherCount += entry.insightCount;
      for (const [barrier, weight] of Object.entries(entry.split)) {
        otherSplit[barrier] = (otherSplit[barrier] || 0) + weight * Math.max(entry.insightCount, 1);
      }
    }
    const otherTotal = Object.values(otherSplit).reduce((s, v) => s + v, 0) || 1;
    const normalizedOther = Object.fromEntries(
      Object.entries(otherSplit).map(([k, v]) => [k, Math.round((v / otherTotal) * 10000) / 10000])
    );

    if (otherCount > 0) {
      top.push({ category: "other", split: normalizedOther, insightCount: otherCount, weight: 1 });
    }
    return top;
  }

  function normalizeCompetitorEntity(entity) {
    return String(entity || "Unknown")
      .split(/,\s*/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function renderLegendInto(elId, barriers) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.innerHTML = barriers
      .map(
        (b) => `<div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container-low border border-outline-variant/30">
          <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:${BARRIER_COLORS[b] || "#ccc"}"></span>
          <span class="text-label-md text-on-surface-variant">${UI.barrierLabel(b)}</span>
        </div>`
      )
      .join("");
  }

  function renderLegend(barriers) {
    renderLegendInto("barrier-legend", barriers);
  }

  function renderBarSegments(sorted, total) {
    return sorted
      .map(([barrier, weight]) => {
        const pct = Math.round((weight / total) * 100);
        if (pct <= 0) return "";
        return `<div class="barrier-segment h-full shrink-0" style="width:${pct}%;min-width:${
          pct > 0 ? "3px" : "0"
        };background:${BARRIER_COLORS[barrier] || "#ccc"}" title="${UI.barrierLabel(barrier)}: ${pct}%"></div>`;
      })
      .join("");
  }

  function renderSegmentChips(sorted, total) {
    return sorted
      .map(([barrier, weight]) => {
        const pct = Math.round((weight / total) * 100);
        if (pct <= 0) return "";
        const color = BARRIER_COLORS[barrier] || "#ccc";
        return `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border border-outline-variant/20"
          style="background:${color}22;color:#1a1c1c">
          <span class="w-2 h-2 rounded-full" style="background:${color}"></span>
          ${UI.barrierLabel(barrier)} ${pct}%
        </span>`;
      })
      .join("");
  }

  function renderSummary(entries, raw) {
    const el = document.getElementById("barrier-summary");
    if (!el) return;

    const totalInsights = entries.reduce((s, e) => s + e.insightCount, 0);
    const corpus = raw || {};
    const corpusTotal = Object.values(corpus).reduce((s, v) => s + v, 0) || 1;
    const topBarrier = Object.entries(corpus).sort((a, b) => b[1] - a[1])[0];
    const topLabel = topBarrier ? UI.barrierLabel(topBarrier[0]) : "—";
    const topPct = topBarrier ? Math.round((topBarrier[1] / corpusTotal) * 100) : 0;

    el.innerHTML = `
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div class="rounded-xl border border-outline-variant/40 bg-surface-container-low p-4">
          <p class="text-label-md text-secondary uppercase tracking-wide mb-1">Categories</p>
          <p class="font-headline-sm font-bold">${entries.length}</p>
        </div>
        <div class="rounded-xl border border-outline-variant/40 bg-surface-container-low p-4">
          <p class="text-label-md text-secondary uppercase tracking-wide mb-1">Insights mapped</p>
          <p class="font-headline-sm font-bold">${UI.formatNumber(totalInsights)}</p>
        </div>
        <div class="rounded-xl border border-outline-variant/40 bg-surface-container-low p-4">
          <p class="text-label-md text-secondary uppercase tracking-wide mb-1">Top barrier</p>
          <p class="font-headline-sm font-bold">${topLabel} <span class="text-secondary font-normal text-body-md">(${topPct}%)</span></p>
        </div>
      </div>`;
  }

  function renderOverallBar(raw) {
    const el = document.getElementById("barrier-overall");
    if (!el || !raw || !Object.keys(raw).length) {
      if (el) el.innerHTML = "";
      return;
    }

    const sorted = Object.entries(raw).sort((a, b) => b[1] - a[1]);
    const total = sorted.reduce((s, [, v]) => s + v, 0) || 1;

    el.innerHTML = `
      <div class="mb-6 p-4 rounded-xl bg-surface-container-low border border-outline-variant/30">
        <div class="flex justify-between items-center mb-3">
          <span class="font-bold text-on-surface">Overall Corpus</span>
          <span class="text-label-md text-secondary">${UI.formatNumber(total)} weighted insights</span>
        </div>
        <div class="h-10 w-full flex rounded-full overflow-hidden bg-white border border-outline-variant/30 shadow-inner">${renderBarSegments(
          sorted,
          total
        )}</div>
        <div class="flex flex-wrap gap-2 mt-3">${renderSegmentChips(sorted, total)}</div>
      </div>`;
  }

  function renderSplitRows(containerId, entries, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const { emptyMessage = "No data available.", legendId = null } = options;

    if (!entries.length) {
      container.innerHTML = `<p class="text-secondary text-body-md py-6 text-center">${emptyMessage}</p>`;
      if (legendId) renderLegendInto(legendId, []);
      return;
    }

    const allBarriers = [...new Set(entries.flatMap((e) => Object.keys(e.split)))];
    if (legendId) renderLegendInto(legendId, allBarriers);

    container.innerHTML = entries
      .map(({ label, subtitle, split }) => {
        const sorted = Object.entries(split).sort((a, b) => b[1] - a[1]);
        const total = sorted.reduce((s, [, v]) => s + v, 0) || 1;
        const dominant = sorted[0];
        const dominantPct = dominant ? Math.round((dominant[1] / total) * 100) : 0;

        return `<article class="barrier-row p-4 rounded-xl border border-outline-variant/30 bg-white hover:shadow-sm transition-shadow">
          <div class="flex flex-wrap justify-between items-start gap-2 mb-3">
            <div>
              <h4 class="font-bold text-on-surface">${label}</h4>
              ${subtitle ? `<p class="text-label-md text-secondary mt-0.5">${subtitle}</p>` : ""}
            </div>
            <span class="px-2.5 py-1 rounded-full text-label-md font-semibold bg-primary-container/40 text-on-primary-container">
              ${UI.barrierLabel(dominant?.[0])} · ${dominantPct}%
            </span>
          </div>
          <div class="h-10 w-full flex rounded-full overflow-hidden bg-surface-container-low border border-outline-variant/30">${renderBarSegments(
            sorted,
            total
          )}</div>
          <div class="flex flex-wrap gap-2 mt-3">${renderSegmentChips(sorted, total)}</div>
        </article>`;
      })
      .join("");
  }

  function renderCategoryRows(byCategory, categoryCounts, raw) {
    const container = document.getElementById("barrier-chart-rows");
    if (!container) return;

    const entries = normalizeEntries(byCategory, categoryCounts);

    if (!entries.length) {
      container.innerHTML = `<p class="text-secondary text-body-md py-8 text-center">No barrier data available.</p>`;
      renderSummary([], raw);
      renderOverallBar(raw);
      renderLegend([]);
      return;
    }

    renderLegend([...new Set(entries.flatMap((e) => Object.keys(e.split)))]);
    renderSummary(entries, raw);
    if (entries.length !== 1 || entries[0].category !== "all_categories") {
      renderOverallBar(raw);
    } else {
      const overallEl = document.getElementById("barrier-overall");
      if (overallEl) overallEl.innerHTML = "";
    }

    renderSplitRows(
      "barrier-chart-rows",
      entries.map(({ category, split, insightCount }) => ({
        label: formatCategory(category),
        subtitle: `${UI.formatNumber(insightCount)} insight${insightCount === 1 ? "" : "s"}`,
        split,
      })),
      { emptyMessage: "No barrier data available." }
    );
  }

  function buildCompetitorBarrierFromInsights(items) {
    const byCompetitor = {};
    const mentionCounts = {};

    for (const card of items || []) {
      const mentions = card.competitor_mentions || [];
      const split = card.cognitive_barrier_split || {};
      if (!mentions.length || !Object.keys(split).length) continue;

      for (const mention of mentions) {
        const entities = normalizeCompetitorEntity(mention.entity);
        const share = (Number(mention.count) || 1) / entities.length;
        for (const entity of entities) {
          mentionCounts[entity] = (mentionCounts[entity] || 0) + share;
          const bucket = byCompetitor[entity] || (byCompetitor[entity] = {});
          for (const [barrier, weight] of Object.entries(split)) {
            bucket[barrier] = (bucket[barrier] || 0) + Number(weight) * share;
          }
        }
      }
    }

    for (const entity of Object.keys(byCompetitor)) {
      const barriers = byCompetitor[entity];
      const total = Object.values(barriers).reduce((s, v) => s + v, 0) || 1;
      byCompetitor[entity] = Object.fromEntries(
        Object.entries(barriers).map(([k, v]) => [k, Math.round((v / total) * 10000) / 10000])
      );
    }

    return { byCompetitor, mentionCounts };
  }

  function renderCompetitorBarrierChart(items) {
    const { byCompetitor, mentionCounts } = buildCompetitorBarrierFromInsights(items);
    const entries = Object.entries(byCompetitor)
      .map(([entity, split]) => ({
        label: entity,
        subtitle: `${UI.formatNumber(Math.round(mentionCounts[entity] || 0))} comparison mention${Math.round(mentionCounts[entity] || 0) === 1 ? "" : "s"}`,
        split,
        mentions: mentionCounts[entity] || 0,
      }))
      .sort((a, b) => b.mentions - a.mentions)
      .slice(0, 8);

    renderSplitRows("competitor-barrier-rows", entries, {
      emptyMessage: "No competitor comparison insights in corpus.",
      legendId: "competitor-barrier-legend",
    });
  }

  function buildByCategoryFromInsights(items) {
    const byCategory = {};
    const categoryCounts = {};

    for (const card of items || []) {
      const split = card.cognitive_barrier_split || {};
      if (!Object.keys(split).length) continue;
      const cats = inferCategories(card);
      for (const cat of cats) {
        categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
        const bucket = byCategory[cat] || (byCategory[cat] = {});
        for (const [barrier, weight] of Object.entries(split)) {
          bucket[barrier] = (bucket[barrier] || 0) + Number(weight);
        }
      }
    }

    for (const cat of Object.keys(byCategory)) {
      const barriers = byCategory[cat];
      const total = Object.values(barriers).reduce((s, v) => s + v, 0) || 1;
      byCategory[cat] = Object.fromEntries(
        Object.entries(barriers).map(([k, v]) => [k, Math.round((v / total) * 10000) / 10000])
      );
    }

    return { byCategory, categoryCounts };
  }

  function buildByCategoryFromRaw(raw) {
    if (!raw || !Object.keys(raw).length) return { byCategory: {}, categoryCounts: {} };
    const total = Object.values(raw).reduce((s, v) => s + v, 0) || 1;
    const split = Object.fromEntries(
      Object.entries(raw).map(([barrier, count]) => [barrier, Math.round((count / total) * 10000) / 10000])
    );
    return {
      byCategory: { all_categories: split },
      categoryCounts: { all_categories: total },
    };
  }

  async function fetchAllInsights() {
    const first = await BlinkitAPI.insights({ page: 1, page_size: 100 });
    const items = [...(first.items || [])];
    const totalPages = Math.ceil((first.total || 0) / 100);
    for (let page = 2; page <= totalPages; page++) {
      const next = await BlinkitAPI.insights({ page, page_size: 100 });
      items.push(...(next.items || []));
    }
    return items;
  }

  async function resolveChartData(initial, items) {
    let byCategory = initial?.by_category;
    let categoryCounts = {};
    let topInsight = initial?.top_insight;

    if (!byCategory || !Object.keys(byCategory).length) {
      try {
        const insightItems = items?.length ? items : await fetchAllInsights();
        const built = buildByCategoryFromInsights(insightItems);
        byCategory = built.byCategory;
        categoryCounts = built.categoryCounts;
      } catch (_) {
        byCategory = {};
      }
      if (!Object.keys(byCategory).length || (Object.keys(byCategory).length === 1 && byCategory.general)) {
        const fromRaw = buildByCategoryFromRaw(initial?.raw);
        if (Object.keys(fromRaw.byCategory).length) {
          byCategory = fromRaw.byCategory;
          categoryCounts = fromRaw.categoryCounts;
        }
      }
    } else {
      categoryCounts = Object.fromEntries(
        Object.keys(byCategory).map((cat) => [cat, Math.round((byCategory[cat] ? Object.values(byCategory[cat]).reduce((a, b) => a + b, 0) : 0) * 10)])
      );
    }

    if (!topInsight) {
      try {
        const overview = await BlinkitAPI.overview();
        topInsight = overview.top_insights?.[0] || null;
      } catch (_) {
        topInsight = null;
      }
    }

    return { ...initial, by_category: byCategory, category_counts: categoryCounts, top_insight: topInsight };
  }

  function renderTopInsight(insight) {
    const el = document.getElementById("barrier-top-insight");
    if (!el) return;
    if (!insight) {
      el.innerHTML = `<p class="text-secondary text-body-md">No top insight available.</p>`;
      return;
    }
    const barrier = UI.dominantBarrier(insight.cognitive_barrier_split);
    el.innerHTML = `
      <div class="flex items-center justify-between mb-4">
        <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-md font-bold uppercase">Top Insight</span>
        ${UI.confidenceCardBadge(insight.confidence_tier)}
      </div>
      <p class="font-headline-sm mb-3 leading-snug">${insight.statement}</p>
      <p class="text-on-surface-variant font-body-md mb-4">
        Dominant barrier: <strong>${barrier.label}</strong> · ${UI.formatNumber(insight.evidence_count)} evidence mentions
      </p>
      <a href="/evidence.html?id=${insight.insight_id}" class="w-full py-3 bg-primary text-white rounded-lg font-bold hover:brightness-110 transition-all flex items-center justify-center gap-2">
        View Evidence <span class="material-symbols-outlined text-[18px]">open_in_new</span>
      </a>`;
  }

  function renderDefinitions() {
    const el = document.getElementById("barrier-definitions");
    if (!el) return;
    el.innerHTML = Object.entries(UI.BARRIER_LABELS)
      .map(
        ([id, label], i) => `<div class="group" ${i === 0 ? 'data-open="true"' : ""}>
          <button type="button" class="w-full p-4 flex items-center justify-between text-left hover:bg-surface-container-low definition-toggle">
            <div class="flex items-center gap-3">
              <div class="w-2 h-2 rounded-full" style="background:${BARRIER_COLORS[id] || "#ccc"}"></div>
              <span class="font-bold">${label}</span>
            </div>
            <span class="material-symbols-outlined definition-chevron transition-transform">expand_more</span>
          </button>
          <div class="px-4 pb-4 text-secondary text-body-md definition-content">${label} — cognitive friction identified in cross-category shopping feedback (not sentiment).</div>
        </div>`
      )
      .join("");

    el.querySelectorAll(".definition-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const parent = btn.closest(".group");
        const open = parent.getAttribute("data-open") === "true";
        el.querySelectorAll(".group").forEach((g) => {
          g.removeAttribute("data-open");
          g.querySelector(".definition-chevron")?.classList.remove("rotate-180");
        });
        if (!open) {
          parent.setAttribute("data-open", "true");
          btn.querySelector(".definition-chevron")?.classList.add("rotate-180");
        }
      });
    });
  }

  async function loadChart() {
    const initial = await BlinkitAPI.barriers("");
    let items = [];
    try {
      items = await fetchAllInsights();
    } catch (_) {
      items = [];
    }
    chartData = await resolveChartData(initial, items);
    renderCategoryRows(chartData.by_category, chartData.category_counts || {}, chartData.raw);
    renderCompetitorBarrierChart(items);
    renderTopInsight(chartData.top_insight);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("barriers");
    renderDefinitions();

    const main = document.querySelector("main");
    try {
      await loadChart();
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
