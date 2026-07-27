(function () {
  function resolveApiBase() {
    const isLocal =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    if (isLocal) {
      const cfg = (window.BLINKIT_CONFIG && window.BLINKIT_CONFIG.API_URL) || "";
      return cfg.replace(/\/$/, "") || "http://localhost:8000";
    }
    // Deployed sites: always same-origin /api proxy (Vercel → Railway)
    return "";
  }

  const base = resolveApiBase();

  async function apiGet(path) {
    const url = `${base}${path}`;
    const res = await fetch(url, { method: "GET", headers: { Accept: "application/json" } });
    if (!res.ok) {
      throw new Error(`API ${path} failed: ${res.status}`);
    }
    return res.json();
  }

  window.BlinkitAPI = {
    overview: () => apiGet("/api/overview"),
    insights: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return apiGet(`/api/insights${q ? `?${q}` : ""}`);
    },
    insight: (id) => apiGet(`/api/insights/${id}`),
    barriers: (query = "") => apiGet(`/api/charts/barriers${query}`),
    funnel: () => apiGet("/api/charts/funnel"),
    competitors: () => apiGet("/api/charts/competitors"),
    validation: () => apiGet("/api/validation"),
    segments: () => apiGet("/api/segments"),
    rqMap: () => apiGet("/api/rq"),
    rq: (rqId) => apiGet(`/api/rq/${rqId}`),
    filterMeta: () => apiGet("/api/filters/meta"),
  };
})();
