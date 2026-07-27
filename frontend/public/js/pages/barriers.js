/** Cognitive Barrier Chart — GET /api/charts/barriers */
(function () {
  const UI = window.BlinkitUI;
  const MAX_ROWS = 5;

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
    other: "Other",
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

  function formatCategory(id) {
    if (CATEGORY_LABELS[id]) return CATEGORY_LABELS[id];
    const pretty = id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    return pretty.length > 22 ? `${pretty.slice(0, 20)}…` : pretty;
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

  function normalizeCompetitorEntity(entity) {
    return String(entity || "Unknown")
      .split(/,\s*/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function normalizeCategoryEntries(byCategory, categoryCounts) {
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
    const top = entries.filter((e) => e.category !== "general" && e.category !== "all_categories").slice(0, MAX_ROWS);
    const rest = entries.filter((e) => !top.includes(e));

    if (!rest.length) return top.length ? top : entries.slice(0, MAX_ROWS);

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
    return top.slice(0, MAX_ROWS);
  }

  function renderSharedLegend(barrierIds) {
    const el = document.getElementById("barrier-legend");
    if (!el) return;
    el.innerHTML = barrierIds
      .map(
        (b) => `<div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-outline-variant/40">
          <span class="w-2 h-2 rounded-full shrink-0" style="background:${BARRIER_COLORS[b] || "#ccc"}"></span>
          <span class="text-label-md text-secondary">${UI.barrierLabel(b)}</span>
        </div>`
      )
      .join("");
  }

  function renderBarSegments(sorted, total) {
    return sorted
      .map(([barrier, weight]) => {
        const pct = Math.round((weight / total) * 100);
        if (pct <= 0) return "";
        return `<div class="barrier-segment h-full shrink-0" style="width:${pct}%;min-width:${pct > 0 ? "2px" : "0"};background:${
          BARRIER_COLORS[barrier] || "#ccc"
        }" title="${UI.barrierLabel(barrier)}: ${pct}%"></div>`;
      })
      .join("");
  }

  function renderCompactRows(containerId, entries, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!entries.length) {
      container.innerHTML = `<p class="text-secondary text-body-md py-8 text-center">${emptyMessage}</p>`;
      return;
    }

    container.innerHTML = entries
      .map(({ label, meta, split }) => {
        const sorted = Object.entries(split).sort((a, b) => b[1] - a[1]);
        const total = sorted.reduce((s, [, v]) => s + v, 0) || 1;
        const dominant = sorted[0];
        const dominantPct = dominant ? Math.round((dominant[1] / total) * 100) : 0;

        return `<div class="py-2.5 px-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/20">
          <div class="flex justify-between items-center gap-2 mb-2">
            <span class="font-semibold text-body-md truncate">${label}</span>
            <span class="text-label-md text-secondary whitespace-nowrap shrink-0">${meta || `${dominantPct}%`}</span>
          </div>
          <div class="h-7 w-full flex rounded-full overflow-hidden bg-white border border-outline-variant/20">${renderBarSegments(
            sorted,
            total
          )}</div>
        </div>`;
      })
      .join("");
  }

  function renderSummary(categoryEntries, competitorEntries, raw) {
    const el = document.getElementById("barrier-summary");
    if (!el) return;

    const corpus = raw || {};
    const corpusTotal = Object.values(corpus).reduce((s, v) => s + v, 0) || 1;
    const topBarrier = Object.entries(corpus).sort((a, b) => b[1] - a[1])[0];
    const topLabel = topBarrier ? UI.barrierLabel(topBarrier[0]) : "—";
    const topPct = topBarrier ? Math.round((topBarrier[1] / corpusTotal) * 100) : 0;
    const catInsights = categoryEntries.reduce((s, e) => s + e.insightCount, 0);

    el.innerHTML = `<div class="flex flex-wrap gap-x-6 gap-y-1 text-body-md text-secondary">
      <span><strong class="text-on-surface">${categoryEntries.length}</strong> categories</span>
      <span><strong class="text-on-surface">${competitorEntries.length}</strong> competitors</span>
      <span><strong class="text-on-surface">${UI.formatNumber(catInsights)}</strong> insights</span>
      <span>Top barrier: <strong class="text-on-surface">${topLabel}</strong> (${topPct}%)</span>
    </div>`;
  }

  function buildByCategoryFromInsights(items) {
    const byCategory = {};
    const categoryCounts = {};

    for (const card of items || []) {
      const split = card.cognitive_barrier_split || {};
      if (!Object.keys(split).length) continue;
      for (const cat of inferCategories(card)) {
        categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
        const bucket = byCategory[cat] || (byCategory[cat] = {});
        for (const [barrier, weight] of Object.entries(split)) {
          bucket[barrier] = (bucket[barrier] || 0) + Number(weight);
        }
      }
    }

    for (const cat of Object.keys(byCategory)) {
      const total = Object.values(byCategory[cat]).reduce((s, v) => s + v, 0) || 1;
      byCategory[cat] = Object.fromEntries(
        Object.entries(byCategory[cat]).map(([k, v]) => [k, Math.round((v / total) * 10000) / 10000])
      );
    }
    return { byCategory, categoryCounts };
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
      const total = Object.values(byCompetitor[entity]).reduce((s, v) => s + v, 0) || 1;
      byCompetitor[entity] = Object.fromEntries(
        Object.entries(byCompetitor[entity]).map(([k, v]) => [k, Math.round((v / total) * 10000) / 10000])
      );
    }
    return { byCompetitor, mentionCounts };
  }

  function buildByCategoryFromRaw(raw) {
    if (!raw || !Object.keys(raw).length) return { byCategory: {}, categoryCounts: {} };
    const total = Object.values(raw).reduce((s, v) => s + v, 0) || 1;
    const split = Object.fromEntries(
      Object.entries(raw).map(([barrier, count]) => [barrier, Math.round((count / total) * 10000) / 10000])
    );
    return { byCategory: { all_categories: split }, categoryCounts: { all_categories: total } };
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
    }

    if (!topInsight) {
      try {
        topInsight = (await BlinkitAPI.overview()).top_insights?.[0] || null;
      } catch (_) {
        topInsight = null;
      }
    }

    return { ...initial, by_category: byCategory, category_counts: categoryCounts, top_insight: topInsight };
  }

  function renderCharts(byCategory, categoryCounts, items, raw) {
    const categoryEntries = normalizeCategoryEntries(byCategory, categoryCounts);
    const { byCompetitor, mentionCounts } = buildCompetitorBarrierFromInsights(items);
    const competitorEntries = Object.entries(byCompetitor)
      .map(([entity, split]) => ({ entity, split, mentions: mentionCounts[entity] || 0 }))
      .sort((a, b) => b.mentions - a.mentions)
      .slice(0, MAX_ROWS);

    const allBarriers = [
      ...new Set([
        ...categoryEntries.flatMap((e) => Object.keys(e.split)),
        ...competitorEntries.flatMap((e) => Object.keys(e.split)),
        ...Object.keys(raw || {}),
      ]),
    ];
    renderSharedLegend(allBarriers);
    renderSummary(categoryEntries, competitorEntries, raw);

    renderCompactRows(
      "barrier-chart-rows",
      categoryEntries.map(({ category, split, insightCount }) => ({
        label: formatCategory(category),
        meta: `${insightCount} insights`,
        split,
      })),
      "No category barrier data."
    );

    renderCompactRows(
      "competitor-barrier-rows",
      competitorEntries.map(({ entity, split, mentions }) => ({
        label: entity,
        meta: `${UI.formatNumber(Math.round(mentions))} mentions`,
        split,
      })),
      "No competitor comparison data."
    );
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
      <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
        <span class="bg-primary-container text-on-primary-container px-3 py-1 rounded-full text-label-md font-bold uppercase">Top Insight</span>
        ${UI.confidenceCardBadge(insight.confidence_tier)}
      </div>
      <p class="font-headline-sm mb-2 leading-snug line-clamp-3">${insight.statement}</p>
      <p class="text-on-surface-variant text-body-md mb-3">
        <strong>${barrier.label}</strong> · ${UI.formatNumber(insight.evidence_count)} evidence mentions
      </p>
      <a href="/evidence.html?id=${insight.insight_id}" class="inline-flex items-center gap-1 text-primary font-bold text-label-md hover:underline">
        View Evidence <span class="material-symbols-outlined text-[16px]">open_in_new</span>
      </a>`;
  }

  function renderDefinitions() {
    const el = document.getElementById("barrier-definitions");
    if (!el) return;
    el.innerHTML = Object.entries(UI.BARRIER_LABELS)
      .map(
        ([id, label], i) => `<div class="group" ${i === 0 ? 'data-open="true"' : ""}>
          <button type="button" class="w-full px-3 py-2.5 flex items-center justify-between text-left hover:bg-surface-container-low definition-toggle">
            <div class="flex items-center gap-2 min-w-0">
              <div class="w-2 h-2 rounded-full shrink-0" style="background:${BARRIER_COLORS[id] || "#ccc"}"></div>
              <span class="font-semibold text-body-md truncate">${label}</span>
            </div>
            <span class="material-symbols-outlined definition-chevron text-[18px] shrink-0">expand_more</span>
          </button>
          <div class="px-3 pb-2 text-secondary text-label-md definition-content">${label} — cognitive friction in cross-category feedback.</div>
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

  document.addEventListener("DOMContentLoaded", async () => {
    UI.wireSidebar("barriers");
    renderDefinitions();

    const main = document.querySelector("main");
    try {
      const initial = await BlinkitAPI.barriers("");
      let items = [];
      try {
        items = await fetchAllInsights();
      } catch (_) {}
      const chartData = await resolveChartData(initial, items);
      renderCharts(chartData.by_category, chartData.category_counts || {}, items, chartData.raw);
      renderTopInsight(chartData.top_insight);
    } catch (err) {
      UI.showError(main, err.message);
    }
  });
})();
