(function () {
  const base = (window.BLINKIT_CONFIG && window.BLINKIT_CONFIG.API_URL) || "";

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
    barriers: () => apiGet("/api/charts/barriers"),
    funnel: () => apiGet("/api/charts/funnel"),
    competitors: () => apiGet("/api/charts/competitors"),
    validation: () => apiGet("/api/validation"),
    segments: () => apiGet("/api/segments"),
    rqMap: () => apiGet("/api/rq"),
    rq: (rqId) => apiGet(`/api/rq/${rqId}`),
  };
})();
