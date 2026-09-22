(() => {
  const STORAGE_KEY = "fp_backend_base_url";
  const TOKEN_KEY = "access_token";
  const originalFetch = window.fetch.bind(window);

  function normalize(value) {
    return String(value || "").trim().replace(/\/+$/, "");
  }

  function configuredBase() {
    return normalize(window.FP_API_BASE || localStorage.getItem(STORAGE_KEY) || "");
  }

  function isApiPath(url) {
    if (typeof url !== "string") return false;
    try {
      if (url.startsWith("/api/v1")) return true;
      const parsed = new URL(url, location.href);
      return parsed.pathname.startsWith("/api/v1");
    } catch (_) { return false; }
  }

  function rewriteApiUrl(url) {
    if (typeof url !== "string") return url;
    const base = configuredBase();
    if (!base || !url.startsWith("/api/v1")) return url;
    if (base.endsWith("/api/v1")) return base + url.slice("/api/v1".length);
    return base + url;
  }

  function withAuth(init = {}) {
    const headers = new Headers(init.headers || {});
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
    return {...init, headers};
  }

  window.fetch = function(input, init = {}) {
    if (typeof input === "string") {
      const apiRequest = isApiPath(input);
      const rewritten = rewriteApiUrl(input);
      return originalFetch(rewritten, apiRequest ? withAuth(init) : init);
    }

    if (input instanceof Request) {
      const current = new URL(input.url, location.href);
      const apiPath = current.pathname + current.search;
      if (apiPath.startsWith("/api/v1")) {
        const nextUrl = rewriteApiUrl(apiPath);
        const nextHeaders = new Headers(input.headers);
        const token = localStorage.getItem(TOKEN_KEY);
        if (token && !nextHeaders.has("Authorization")) nextHeaders.set("Authorization", `Bearer ${token}`);
        const next = new Request(nextUrl, input);
        return originalFetch(new Request(next, {headers: nextHeaders}), init);
      }
    }
    return originalFetch(input, init);
  };

  window.fpGetApiBase = () => configuredBase();
  window.fpSetApiBase = value => {
    const normalized = normalize(value);
    if (normalized) localStorage.setItem(STORAGE_KEY, normalized);
    else localStorage.removeItem(STORAGE_KEY);
    window.FP_API_BASE = normalized;
    return normalized;
  };
  window.fpOriginalFetch = originalFetch;
})();