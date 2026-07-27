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

  const NAV_ROUTES = {
    overview: "/",
    insights: "/insights.html",
    barriers: "/barriers.html",
    funnel: "/funnel.html",
    competitors: "/competitors.html",
    rqmap: "/rq-map.html",
    segments: "/segments.html",
    validation: "/validation.html",
  };

  const NAV_MATCHERS = [
    { key: "overview", texts: ["overview"] },
    { key: "insights", texts: ["insight explorer"] },
    { key: "barriers", texts: ["barrier chart"] },
    { key: "funnel", texts: ["funnel breakdown"] },
    { key: "competitors", texts: ["competitor benchmark"] },
    { key: "rqmap", texts: ["rq map"] },
    { key: "segments", texts: ["segments"] },
    { key: "validation", texts: ["validation"] },
  ];

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

  function formatDate(iso) {
    if (!iso) return "—";
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) return "—";
    return dt.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDurationDays(days) {
    if (days == null || Number.isNaN(days)) return "—";
    if (days < 31) return `${days} days`;
    const months = Math.round(days / 30.44);
    if (months < 24) return `${months} months (${days} days)`;
    const years = (days / 365.25).toFixed(1);
    return `${years} years (${days} days)`;
  }

  function formatPlatformName(id) {
    return String(id).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function formatDataCollection(dc) {
    if (!dc || !dc.evidence_date_min || !dc.evidence_date_max) return null;
    const minDt = new Date(dc.evidence_date_min);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const minYear = minDt.getFullYear();
    const todayYear = today.getFullYear();
    const yearRange = minYear === todayYear ? String(minYear) : `${minYear}–${todayYear}`;
    const min = formatDate(dc.evidence_date_min);
    const max = formatDate(today.toISOString());
    const durationDays = Math.max(0, Math.round((today - minDt) / (1000 * 60 * 60 * 24)));
    const span = formatDurationDays(durationDays);
    const records = dc.record_count != null ? `${formatNumber(dc.record_count)} records` : null;
    const platformNames = Array.isArray(dc.platforms) && dc.platforms.length
      ? dc.platforms.map(formatPlatformName).join(", ")
      : dc.platform_count != null
        ? `${formatNumber(dc.platform_count)} platforms`
        : null;
    const parts = [yearRange, `${min} → ${max}`, span, records, platformNames].filter(Boolean);
    return parts.join(" · ");
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
    const existing = container.querySelector("[data-blinkit-api-error]");
    if (existing) {
      existing.querySelector("p").innerHTML = `<span class="font-bold">API Error:</span> ${message}`;
      return;
    }
    const el = document.createElement("div");
    el.dataset.blinkitApiError = "1";
    el.className =
      "mb-6 flex items-center gap-3 p-4 bg-red-50 border-l-4 border-red-400 rounded-r-lg";
    el.innerHTML = `<span class="material-symbols-outlined text-red-600">error</span>
      <p class="font-body-md text-red-900"><span class="font-bold">API Error:</span> ${message}</p>`;
    container.prepend(el);
  }

  function fixNavigation(activePage) {
    wireSidebar(activePage);
  }

  function wireSidebar(activePage) {
    document.querySelectorAll("aside nav a, aside a[href]").forEach((link) => {
      const text = link.textContent.trim().toLowerCase();
      for (const item of NAV_MATCHERS) {
        if (item.texts.some((t) => text.includes(t))) {
          link.href = NAV_ROUTES[item.key];
          const isActive = item.key === activePage;
          link.classList.toggle("bg-primary-container", isActive);
          link.classList.toggle("text-on-primary-container", isActive);
          link.classList.toggle("font-bold", isActive);
          link.classList.toggle("rounded-lg", isActive);
          break;
        }
      }
    });
  }

  function renderRqFilterChips(containerId, onSelect) {
    const row = document.getElementById(containerId);
    if (!row) return;
    row.innerHTML = "";
    const all = document.createElement("button");
    all.type = "button";
    all.dataset.rqChip = "";
    all.className =
      "px-3 py-1 rounded-full border border-outline text-label-md hover:bg-surface-container-high transition-colors active-filter-chip";
    all.textContent = "All Research";
    all.addEventListener("click", () => onSelect(all));
    row.appendChild(all);

    Object.keys(RQ_LABELS).forEach((rq) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.rqChip = rq;
      btn.title = RQ_LABELS[rq];
      btn.className =
        "px-3 py-1 rounded-full border border-outline text-label-md hover:bg-surface-container-high transition-colors";
      btn.textContent = rq;
      btn.addEventListener("click", () => onSelect(btn));
      row.appendChild(btn);
    });
  }

  function initResponsiveLayout() {
    if (!document.getElementById("blinkit-responsive-css")) {
      const link = document.createElement("link");
      link.id = "blinkit-responsive-css";
      link.rel = "stylesheet";
      link.href = "/css/responsive.css";
      document.head.appendChild(link);
    }

    const aside = document.querySelector("aside");
    if (!aside || document.getElementById("sidebar-overlay")) return;

    aside.id = aside.id || "app-sidebar";

    const overlay = document.createElement("div");
    overlay.id = "sidebar-overlay";
    overlay.className = "sidebar-overlay";
    overlay.setAttribute("aria-hidden", "true");
    document.body.appendChild(overlay);

    const mq = window.matchMedia("(max-width: 1023px)");

    function closeSidebar() {
      document.body.classList.remove("sidebar-open");
      document.body.style.overflow = "";
      overlay.setAttribute("aria-hidden", "true");
    }

    function openSidebar() {
      if (!mq.matches) return;
      document.body.classList.add("sidebar-open");
      document.body.style.overflow = "hidden";
      overlay.setAttribute("aria-hidden", "false");
    }

    function toggleSidebar() {
      if (document.body.classList.contains("sidebar-open")) closeSidebar();
      else openSidebar();
    }

    overlay.addEventListener("click", closeSidebar);

    function attachToggle(btn) {
      if (!btn || btn.dataset.navBound) return;
      btn.dataset.navBound = "1";
      btn.addEventListener("click", toggleSidebar);
    }

    document.querySelectorAll("header").forEach((header) => {
      if (header.querySelector(".mobile-nav-toggle")) return;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "mobile-nav-toggle";
      btn.setAttribute("aria-label", "Open navigation menu");
      btn.innerHTML = '<span class="material-symbols-outlined">menu</span>';
      header.classList.add("flex", "items-center");
      header.insertBefore(btn, header.firstChild);
      attachToggle(btn);
    });

    if (!document.querySelector(".mobile-nav-toggle")) {
      const main = document.querySelector("main");
      const titleEl = document.querySelector("main h2, header h2");
      if (main) {
        const bar = document.createElement("div");
        bar.className = "mobile-top-bar";
        bar.innerHTML =
          '<button type="button" class="mobile-nav-toggle" aria-label="Open navigation menu"><span class="material-symbols-outlined">menu</span></button>' +
          `<span class="mobile-page-title font-headline-sm font-bold text-on-surface">${titleEl ? titleEl.textContent.trim() : "Menu"}</span>`;
        main.insertBefore(bar, main.firstChild);
        attachToggle(bar.querySelector(".mobile-nav-toggle"));
      }
    }

    aside.querySelectorAll("nav a").forEach((link) => {
      link.addEventListener("click", () => {
        if (mq.matches) closeSidebar();
      });
    });

    mq.addEventListener("change", (e) => {
      if (!e.matches) closeSidebar();
    });

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeSidebar();
    });

    window.addEventListener("resize", () => {
      if (!mq.matches) closeSidebar();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initResponsiveLayout);
  } else {
    initResponsiveLayout();
  }

  window.BlinkitUI = {
    BARRIER_LABELS,
    FUNNEL_LABELS,
    RQ_LABELS,
    barrierLabel,
    funnelLabel,
    formatNumber,
    formatPercent,
    formatDate,
    formatDurationDays,
    formatDataCollection,
    dominantBarrier,
    confidenceBadge,
    confidenceCardBadge,
    staleIcon,
    funnelDots,
    showError,
    fixNavigation,
    wireSidebar,
    renderRqFilterChips,
    NAV_ROUTES,
    RQ_LABELS,
  };
})();
