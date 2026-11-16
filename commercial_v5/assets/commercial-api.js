/* Facil Pedido V5 - conexao autenticada, timeouts e deduplicacao de consultas. */
(() => {
  "use strict";
  const CFG = window.FP_COMMERCIAL_CONFIG || {};
  const KEY = "fp_commercial_access_token_v5_amarelo";
  function base() {
    const configured = location.pathname.startsWith("/comercial")
      ? CFG.API_BASE
      : (localStorage.getItem("fp_commercial_api_base_v5_amarelo") || CFG.API_BASE || "");
    return String(configured || "").replace(/\/+$/, "");
  }
  function token() { return sessionStorage.getItem(KEY) || ""; }
  function setToken(value) {
    if (value) sessionStorage.setItem(KEY, String(value));
    else sessionStorage.removeItem(KEY);
  }
  function setBase(value) {
    if (location.pathname.startsWith("/comercial")) return base();
    value = String(value || "").trim().replace(/\/+$/, "");
    if (value && location.protocol === "https:" && !value.startsWith("https://"))
      throw new Error("A API deve usar HTTPS.");
    if (value) localStorage.setItem("fp_commercial_api_base_v5_amarelo", value);
    else localStorage.removeItem("fp_commercial_api_base_v5_amarelo");
    return base();
  }
  const MAX_READS = 3;
  let active = 0;
  const queue = [];
  const inflight = new Map();
  function pump() {
    while (active < MAX_READS && queue.length) {
      const job = queue.shift(); active++;
      Promise.resolve().then(job.work).then(job.resolve, job.reject)
        .finally(() => { active--; pump(); });
    }
  }
  function read(work) {
    return new Promise((resolve, reject) => {
      queue.push({work, resolve, reject});
      pump();
    });
  }
  async function send(path, opts = {}) {
    if (!base()) throw new Error("API do ERP nao configurada.");
    const headers = new Headers(opts.headers || {});
    const currentToken = token();
    if (currentToken) headers.set("Authorization", `Bearer ${currentToken}`);
    if (opts.body && !(opts.body instanceof FormData) && !headers.has("Content-Type"))
      headers.set("Content-Type", "application/json");
    const isLogin = path === "/auth/login";
    const timeoutMs = Math.min(60000, Math.max(1000, Number(opts.timeoutMs) || (isLogin ? 30000 : 18000)));
    const controller = new AbortController();
    const external = opts.signal;
    let expired = false;
    const timer = setTimeout(() => { expired = true; controller.abort(); }, timeoutMs);
    const stopOnAbort = () => controller.abort();
    if (external) external.addEventListener("abort", stopOnAbort, {once:true});
    try {
      const { timeoutMs: _discard, signal: _signal, ...fetchOptions } = opts;
      const response = await fetch(base() + path, { ...fetchOptions, headers, signal: controller.signal });
      if (response.status === 204) return null;
      const raw = await response.text();
      let data;
      try { data = raw ? JSON.parse(raw) : null; } catch { data = raw; }
      if (!response.ok) {
        const detail = data?.detail?.message || data?.detail || data?.message || `Erro HTTP ${response.status}`;
        const message = typeof detail === "string" ? detail : JSON.stringify(detail);
        const e = new Error(message);
        e.status = response.status;
        if (response.status === 429) {
          const sec = Number(response.headers.get("Retry-After") || 0);
          e.retryAfter = Number.isFinite(sec) && sec > 0 ? Math.ceil(sec) : null;
          e.message = e.retryAfter ? `Muitas requisicoes ao ERP. Tente novamente em ${e.retryAfter} segundos.` : "ERP limitou requisicoes. Tente novamente em instantes.";
        }
        throw e;
      }
      return data;
    } catch (e) {
      if (expired) {
        const timeout = new Error(isLogin
          ? "A autenticacao demorou mais de 30 segundos. Verifique os logs do Render e tente novamente."
          : "O ERP demorou para responder. Verifique o Render ou tente sincronizar novamente.");
        timeout.status = 504;
        throw timeout;
      }
      if (e.name === "AbortError") throw new Error("Solicitacao cancelada.");
      if (e instanceof TypeError) throw new Error("Nao foi possivel conectar ao ERP. Confira a rede e o status do Render.");
      throw e;
    } finally {
      clearTimeout(timer);
      if (external) external.removeEventListener("abort", stopOnAbort);
    }
  }
  function request(path, options = {}) {
    const method = String(options.method || "GET").toUpperCase();
    // Operacoes que alteram dados nao sao repetidas nem postas na fila de leituras.
    if (method !== "GET") return send(path, options);
    const key = `${base()}::${token()}::${path}`;
    if (inflight.has(key)) return inflight.get(key);
    const promise = read(() => send(path, options));
    inflight.set(key, promise);
    promise.finally(() => { if (inflight.get(key) === promise) inflight.delete(key); }).catch(() => {});
    return promise;
  }
  window.CommercialAPI = {base, token, setToken, setBase, request};
})();
