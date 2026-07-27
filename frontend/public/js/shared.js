/** Shared formatters and UI helpers for Stitch dashboard pages. */
(function () {
  const BARRIER_LABELS = {
    AWARENESS_DEFICIT: "Awareness Deficit",
    AUTHENTICITY_DISTRUST: "Authenticity Distrust",
    ASSORTMENT_GAP: "Assortment Gap",
    CONVENIENCE_MISMATCH: "Convenience Mismatch",
    RETURN_POLICY_ANXIETY: "Return Policy Anxiety",
    NONE_GROCERY_LOYAL: "Grocery Loyal",
  };

  const FUNNEL_LABELS = {
    DISCOVERY: "Discovery",
    CONSIDERATION: "Consideration",
    CONVERSION: "Conversion",
    POST_PURCHASE_RETENTION: "Post-Purchase Retention",
  };

  const RQ_LABELS = {
    RQ1: "Same-category repeat",
    RQ2: "Blocks exploration",
    RQ3: "Discovery methods",
    RQ4: "Habit / regulars",
    RQ5: "Trust to try new",
    RQ6: "Recurring frustrations",
    RQ7: "Segments that experiment",
    RQ8: "Unmet needs",
  };

  function barrierLabel(id) {
    return BARRIER_LABELS[id] || id.replace(/_/g, " ");
  }

  function funnelLabel(id) {
    return FUNNEL_LABELS[id] || id;
  }

  function formatNumber(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return new Intl.NumberFormat().format(n);
  }

  function formatPercent(rate) {
    if (rate == null) return "—";
    return `${Math.round(rate * 100)}%`;
  }

  function dominantBarrier(split) {
    if (!split || !Object.keys(split).length) return { id: "UNKNOWN", value: 0 };
    const id = Object.entries(split).reduce((a, b) => (a[1] >= b[1] ? a : b))[0];
    return { id, value: split[id], label: barrierLabel(id) };
  }

  function confidenceBadge(tier) {
    const map = {
      high: { cls: "bg-green-100 text-green-800", label: "High" },
      medium: { cls: "bg-yellow-100 text-yellow-800", label: "Medium" },
      low: { cls: "bg-gray-100 text-gray-700", label: "Low" },
    };
    const m = map[tier] || map.low;
    return `<span class="px-3 py-1 ${m.cls} rounded-full font-label-md text-label-md">${m.label}</span>`;
  }

  function confidenceCardBadge(tier) {
    const map = {
      high: { cls: "bg-green-100 text-green-700", icon: "verified", label: "High Confidence" },
      medium: { cls: "bg-yellow-100 text-yellow-700", icon: "rule", label: "Med Confidence" },
      low: { cls: "bg-gray-100 text-gray-700", icon: "help", label: "Low Confidence" },
    };
    const m = map[tier] || map.low;
    return `<span class="${m.cls} px-3 py-1 rounded-full text-label-sm font-bold flex items-center gap-1">
      <span class="material-symbols-outlined text-[14px]">${m.icon}</span> ${m.label}
    </span>`;
  }

  function staleIcon(isStale) {
    if (isStale) {
      return `<span class="material-symbols-outlined text-orange-500" title="Stale (&gt;12 months)">history</span>`;
    }
    return `<span class="material-symbols-outlined text-green-500" title="Current">check_circle</span>`;
  }

  function funnelDots(stage) {
    const stages = ["DISCOVERY", "CONSIDERATION", "CONVERSION", "POST_PURCHASE_RETENTION"];
    const idx = stages.indexOf(stage);
    return stages
      .map((s, i) => {
        const filled = i <= idx && idx >= 0;
        return `<div class="w-8 h-2 rounded-full ${filled ? "bg-primary-container" : "bg-surface-container"}"></div>`;
      })
      .join("");
  }

  function showError(container, message) {
    const el = document.createElement("div");
    el.className =
      "mb-6 flex items-center gap-3 p-4 bg-red-50 border-l-4 border-red-400 rounded-r-lg";
    el.innerHTML = `<span class="material-symbols-outlined text-red-600">error</span>
      <p class="font-body-md text-red-900"><span class="font-bold">API Error:</span> ${message}</p>`;
    container.prepend(el);
  }

  function fixNavigation(activePage) {
    const routes = {
      overview: "/",
      insights: "/insights.html",
      barriers: "/barriers.html",
      evidence: "/evidence.html",
    };
    document.querySelectorAll("aside nav a, aside a[href]").forEach((link) => {
      const text = link.textContent.trim().toLowerCase();
      if (text.includes("overview")) link.href = routes.overview;
      else if (text.includes("insight explorer")) link.href = routes.insights;
      else if (text.includes("barrier chart")) link.href = routes.barriers;
    });
    const activeMap = {
      overview: "overview",
      insights: "insight explorer",
      barriers: "barrier chart",
    };
    const activeText = activeMap[activePage];
    if (!activeText) return;
    document.querySelectorAll("aside nav a").forEach((link) => {
      const isActive = link.textContent.trim().toLowerCase().includes(activeText);
      link.classList.toggle("bg-primary-container", isActive);
      link.classList.toggle("text-on-primary-container", isActive);
      link.classList.toggle("font-bold", isActive);
      link.classList.toggle("rounded-lg", isActive);
    });
  }

  window.BlinkitUI = {
    BARRIER_LABELS,
    FUNNEL_LABELS,
    RQ_LABELS,
    barrierLabel,
    funnelLabel,
    formatNumber,
    formatPercent,
    dominantBarrier,
    confidenceBadge,
    confidenceCardBadge,
    staleIcon,
    funnelDots,
    showError,
    fixNavigation,
  };
})();
