/* Shared transport and recovery. No mutation is retried automatically. */
(() => {
  "use strict";
  let pendingWrites = 0;
  let requestStatus = () => {};
  class ApiError extends Error {
    constructor(message, code, status = 0) {
      super(message); this.name = "ApiError"; this.code = code; this.status = status;
    }
  }
  async function requestJson(url, options = {}) {
    const { timeoutMs, signal, ...fetchOptions } = options;
    const method = String(options.method || "GET").toUpperCase();
    const writing = !["GET", "HEAD"].includes(method);
    const controller = new AbortController();
    const abort = () => controller.abort();
    if (signal?.aborted) controller.abort();
    else signal?.addEventListener("abort", abort, { once: true });
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs ?? (writing ? 60000 : 15000));
    if (writing) pendingWrites++;
    try {
      const response = await fetch(url, { cache: "no-store", credentials: "same-origin", ...fetchOptions, signal: controller.signal });
      const text = await response.text();
      let payload = {};
      if (text.trim()) {
        try { payload = JSON.parse(text); }
        catch {
          throw new ApiError(response.ok ? "O serviço retornou uma resposta inesperada. Tente atualizar os dados." : `O serviço está indisponível (HTTP ${response.status}).`, "INVALID_RESPONSE", response.status);
        }
      }
      if (!response.ok) {
        const detail = payload?.error?.message || payload?.erro || payload?.detail;
        throw new ApiError(response.status === 401 ? "Sua sessão expirou. Entre novamente para continuar." : typeof detail === "string" ? detail : `Não foi possível concluir a consulta (HTTP ${response.status}).`, "HTTP_ERROR", response.status);
      }
      requestStatus(url, null);
      return payload;
    } catch (failure) {
      let error = failure;
      if (!(failure instanceof ApiError)) {
        error = new ApiError(timedOut ? "O serviço demorou para responder. Confira o estado antes de reenviar uma ação." : controller.signal.aborted ? "Consulta cancelada." : "Conexão interrompida. Confira sua rede e tente novamente.", timedOut ? "TIMEOUT" : controller.signal.aborted ? "ABORTED" : "NETWORK_ERROR");
      }
      if (error.code !== "ABORTED") requestStatus(url, error);
      throw error;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
      if (writing) pendingWrites--;
    }
  }
  function createPoller(task, interval, enabled = () => true) {
    let timer = null, inFlight = null, failures = 0, stopped = false;
    function run() {
      if (stopped) return Promise.resolve();
      if (inFlight) return inFlight;
      clearTimeout(timer);
      inFlight = (async () => {
        if (document.hidden || navigator.onLine === false || !enabled()) return;
        try { failures = await task() === false ? failures + 1 : 0; }
        catch { failures++; }
      })().finally(() => {
        inFlight = null;
        if (!stopped) timer = setTimeout(run, Math.min(60000, interval * 2 ** Math.min(failures, 5)));
      });
      return inFlight;
    }
    return { run, start() { stopped = false; timer = setTimeout(run, interval); }, stop() { stopped = true; clearTimeout(timer); } };
  }
  const draftIds = ["gen-prompt", "gen-negative", "gen-music-lyrics", "film-director-reason", "film-director-category"];
  const draftKey = (id, scope) => `maestro-draft-v1:${id}:${scope || "creation"}`;
  function saveDraft(id, scope = "") {
    if (!draftIds.includes(id)) return;
    const input = document.getElementById(id);
    if (!input) return;
    try {
      if (input.value) localStorage.setItem(draftKey(id, scope), JSON.stringify({ value: input.value.slice(0, 20000), savedAt: Date.now() }));
      else localStorage.removeItem(draftKey(id, scope));
    } catch { /* Editing remains available if browser storage is blocked. */ }
  }
  function restoreDraft(id, scope = "") {
    if (!draftIds.includes(id)) return;
    const input = document.getElementById(id);
    if (!input || input.value) return;
    try {
      const saved = JSON.parse(localStorage.getItem(draftKey(id, scope)) || "null");
      if (typeof saved?.value === "string" && Date.now() - saved.savedAt < 7 * 86400000) input.value = saved.value;
    } catch { /* Invalid/local legacy data never prevents opening the form. */ }
  }
  function forgetDraft(id, scope = "") {
    if (!draftIds.includes(id)) return;
    try { localStorage.removeItem(draftKey(id, scope)); } catch {}
  }
  function offerUpdate() {
    const bar = document.getElementById("maestro-update-status");
    if (bar) bar.hidden = false;
  }
  function initRecovery(directorScope) {
    for (const id of draftIds.filter(id => id.startsWith("gen-"))) restoreDraft(id);
    document.addEventListener("input", event => {
      const id = event.target.id;
      if (draftIds.includes(id)) saveDraft(id, id.startsWith("film-") ? directorScope() : "");
    });
    document.addEventListener("change", event => {
      if (event.target.id === "film-director-category") saveDraft(event.target.id, directorScope());
    });
    const notice = document.getElementById("maestro-connection-status");
    const failedCore = new Map();
    function renderConnection() {
      if (!notice) return;
      const offline = navigator.onLine === false;
      notice.hidden = !offline && !failedCore.size;
      notice.textContent = offline ? "Sem conexão. Sua edição permanece nesta tela. A consulta será retomada quando a rede voltar." : [...failedCore.values()].some(e => e.status === 401) ? "Sua sessão expirou. Entre novamente para continuar; seus rascunhos ficam neste navegador." : "Não foi possível atualizar o Maestro. Tentaremos consultar novamente; confira o estado antes de reenviar uma ação.";
    }
    requestStatus = (url, error) => {
      if (!String(url).startsWith("/api/studio/")) return;
      if (!error) failedCore.delete(url);
      else if (!error.status || error.status >= 500 || error.status === 401) failedCore.set(url, error);
      renderConnection();
    };
    window.addEventListener("offline", renderConnection);
    window.addEventListener("online", renderConnection);
    const update = document.getElementById("maestro-update-now");
    update?.addEventListener("click", () => {
      if (pendingWrites) { update.textContent = "Aguarde o envio terminar"; return; }
      if (!window.confirm("Atualizar o Maestro agora? Conclua edições e gravações em andamento antes de continuar.")) return;
      for (const id of draftIds) saveDraft(id, id.startsWith("film-") ? directorScope() : "");
      window.location.reload();
    });
    renderConnection();
  }
  window.MaestroResilience = { ApiError, requestJson, createPoller, initRecovery, offerUpdate, saveDraft, restoreDraft, forgetDraft,
    get pendingWrites() { return pendingWrites; } };
})();
