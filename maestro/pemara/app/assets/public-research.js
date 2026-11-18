(() => {
  "use strict";
  const base = "/api/studio/api/research";
  const $ = (id) => document.getElementById(id);
  const form = $("research-form");
  if (!form) return;
  const state = { active: "", page: 1, jobs: [], total: 0, timer: null, loaded: false, submitting: false };
  const statuses = { QUEUED: "Aguardando início", RUNNING: "Pesquisando e verificando", READY_FOR_REVIEW: "Pronta para revisão", INTERRUPTED_REVIEW_REQUIRED: "Interrompida: confira as evidências antes de reenviar", INTEGRITY_CHANGED: "Evidência alterada: revisão bloqueada" };
  const findings = { SUPPORTED: "Sustentada pelas fontes", CONTRADICTED_REVIEW_REQUIRED: "Contradita pelas fontes", UNSUPPORTED_OR_UNCERTAIN: "Sem sustentação ou incerta", QUOTE_NOT_FOUND: "Citação não encontrada", NO_ELIGIBLE_SOURCE: "Fonte não elegível para verificação", INVALID_MODEL_RESPONSE: "Resposta de verificação inválida" };
  const lines = (value) => value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const id = () => crypto.randomUUID().replaceAll("-", "");
  const node = (tag, value, className) => { const element = document.createElement(tag); if (value !== undefined) element.textContent = value; if (className) element.className = className; return element; };
  function message(text, error = false) { $("research-message").textContent = text; $("research-message").dataset.error = String(error); }
  async function api(path, options = {}) {
    const response = await fetch(base + path, { credentials: "same-origin", cache: "no-store", ...options,
      headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" } : {}), ...options.headers } });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Não foi possível concluir a operação. Confira os campos e tente novamente.");
    return result;
  }
  async function requestId(payload) {
    const bytes = new TextEncoder().encode(JSON.stringify(payload));
    const signature = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (byte) => byte.toString(16).padStart(2, "0")).join("");
    let previous;
    try { previous = JSON.parse(sessionStorage.getItem("maestro-public-research-request")); } catch { previous = null; }
    if (previous?.signature === signature && /^[a-f0-9]{32}$/.test(previous.id)) return previous.id;
    const value = id();
    sessionStorage.setItem("maestro-public-research-request", JSON.stringify({ signature, id: value }));
    return value;
  }
  function reference() {
    const character = $("research-kind").value === "character";
    $("research-reference").hidden = !character;
    ["work", "edition", "incarnation"].forEach((field) => { $("research-" + field).required = character; });
  }
  function renderJobs(total) {
    const list = node("div", undefined, "research-jobs-list");
    if (!state.jobs.length) list.append(node("p", "Nenhuma pesquisa salva ainda."));
    for (const job of state.jobs) {
      const button = node("button", undefined, "btn secondary research-job"); button.type = "button";
      button.append(node("strong", job.topic), node("small", statuses[job.status] || "Consultar resultado"));
      button.addEventListener("click", () => void select(job.id, true)); list.append(button);
    }
    $("research-jobs").replaceChildren(list); $("research-more").hidden = state.jobs.length >= total;
  }
  async function loadJobs(reset = true) {
    if (reset) state.page = 1;
    const result = await api(`/jobs?page=${state.page}&pageSize=20`);
    state.jobs = reset ? result.jobs : [...state.jobs, ...result.jobs]; state.total = result.total; renderJobs(state.total);
  }
  async function loadProjects() {
    try {
      const response = await fetch("/api/studio/api/video-projects?pageSize=100", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      for (const project of data.data || data.projects || data.items || []) {
        const projectId = project.projectId || project.id;
        if (!projectId) continue;
        const option = node("option", project.title || project.name || projectId); option.value = projectId;
        $("research-project").append(option);
      }
    } catch { /* A project link is optional; the research form remains usable. */ }
  }
  function safeSourceUrl(value) {
    try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password ? url.href : null; } catch { return null; }
  }
  function render(job) {
    $("research-detail").hidden = false; $("research-detail-title").textContent = job.topic;
    $("research-detail-status").textContent = statuses[job.status] || "Consultar resultado";
    const container = $("research-detail-body"); container.replaceChildren();
    if (job.status !== "READY_FOR_REVIEW") {
      container.append(node("p", job.status === "INTEGRITY_CHANGED" ? "As fontes salvas precisam ser conferidas. Não há revisão disponível enquanto a integridade estiver alterada." : "O resultado é preservado aqui. Uma interrupção não dispara outro envio automático.", "research-help")); return;
    }
    if (job.projectId) container.append(node("p", "Projeto vinculado: " + job.projectId, "research-meta"));
    if (job.reference?.kind === "character") container.append(node("p", [job.reference.work, job.reference.edition, job.reference.incarnation].join(" · "), "research-meta"));
    const download = node("a", "Baixar dossiê com as evidências"); download.href = `${base}/jobs/${job.id}/dossier`; container.append(download);
    const wrap = node("div", undefined, "research-table-wrap"), table = node("table", undefined, "research-table");
    const caption = node("caption", "Afirmações e relação com as fontes"); table.append(caption);
    const head = node("tr"); ["Afirmação", "Resultado", "Fonte"].forEach((text) => head.append(node("th", text)));
    const thead = node("thead"); thead.append(head); table.append(thead);
    const tbody = node("tbody");
    for (const finding of job.findings) {
      const tr = node("tr"); tr.append(node("td", finding.text), node("td", findings[finding.status] || "Revisão necessária"), node("td", finding.checks?.map((check) => check.sourceId).join(", ") || "Sem evidência elegível")); tbody.append(tr);
    }
    table.append(tbody); wrap.append(table); container.append(wrap);
    container.append(node("h3", "Fontes preservadas"));
    for (const source of job.sources) {
      const section = node("section", undefined, "research-source"); section.append(node("h4", source.id));
      const href = safeSourceUrl(source.url);
      if (href) { const link = node("a", source.url); link.href = href; link.target = "_blank"; link.rel = "noopener noreferrer"; section.append(link); }
      section.append(node("p", `Coleta: ${new Date(source.fetchedAt).toLocaleString("pt-BR")} · ${source.cacheState === "hit" ? "conteúdo de cache" : "cache não informado"} · ${source.verificationEligible ? "avaliada" : "não avaliada: " + (source.verificationReason === "SOURCE_TOO_LARGE" ? "fonte acima do limite de leitura" : "confira as evidências")}`, "research-meta"));
      section.append(node("p", "SHA-256: " + (source.markdownSha256 || "indisponível"), "research-meta"));
      if (source.ok && /^S[1-3]$/.test(source.id)) {
        const details = node("details"), summary = node("summary", "Ler conteúdo salvo"), pre = node("pre", "Abra para carregar a fonte."); details.append(summary, pre);
        let loaded = false;
        details.addEventListener("toggle", async () => {
          if (!details.open || loaded) return;
          try { const response = await fetch(`${base}/jobs/${job.id}/sources/${source.id}`, { credentials: "same-origin", cache: "no-store" }); if (!response.ok) throw new Error(); pre.textContent = await response.text(); loaded = true; }
          catch { pre.textContent = "Não foi possível carregar a fonte salva."; }
        }); section.append(details);
      }
      container.append(section);
    }
    const usage = job.verification?.usage;
    container.append(node("p", `Verificação: ${job.verification?.model || "não executada"}${usage ? ` · ${usage.input_tokens} tokens de entrada e ${usage.output_tokens} de saída` : ""}${job.durationMs ? ` · ${(job.durationMs / 1000).toFixed(1)} s` : ""}`, "research-meta"));
    renderReview(job, container);
  }
  function renderReview(job, container) {
    const review = node("form", undefined, "research-review"); review.append(node("h3", "Revisão da pesquisa"), node("p", "Confira as fontes. Somente afirmações sustentadas podem ser aceitas; as demais precisam ser excluídas ou receber novas fontes. Esta revisão é separada da aprovação da produção.", "research-help"));
    if (job.review) review.append(node("p", job.review.decision === "reviewed" ? "Pesquisa revisada. " + job.review.note : "Novas fontes solicitadas: " + job.review.note));
    for (const finding of job.findings) {
      const label = node("label", finding.id + ": " + finding.text), select = node("select"); select.dataset.claimId = finding.id;
      for (const [value, text] of [["", "Selecione a decisão"], ...(finding.status === "SUPPORTED" ? [["accept", "Aceitar com base nas fontes"]] : []), ["exclude", "Excluir da pesquisa revisada"]]) {
        const option = node("option", text); option.value = value; select.append(option);
      }
      if (job.review?.acceptedClaimIds.includes(finding.id)) select.value = "accept";
      if (job.review?.excludedClaimIds.includes(finding.id)) select.value = "exclude";
      label.append(select); review.append(label);
    }
    const label = node("label", "Notas e informações que faltam"), notes = node("textarea"); notes.maxLength = 2000; notes.rows = 3; label.append(notes); review.append(label);
    const actions = node("div", undefined, "research-actions"), complete = node("button", "Concluir revisão", "btn primary"), needs = node("button", "Pedir novas fontes", "btn secondary");
    complete.type = "submit"; needs.type = "button"; actions.append(complete, needs); review.append(actions);
    async function submit(decision) {
      const accepted = [], excluded = [];
      review.querySelectorAll("select[data-claim-id]").forEach((select) => { if (select.value === "accept") accepted.push(select.dataset.claimId); if (select.value === "exclude") excluded.push(select.dataset.claimId); });
      complete.disabled = needs.disabled = true;
      try {
        const result = await api(`/jobs/${job.id}/reviews`, { method: "POST", body: JSON.stringify({ requestId: id(), decision, acceptedClaimIds: accepted, excludedClaimIds: excluded, note: notes.value.trim() }) });
        render(result); message(decision === "reviewed" ? "Revisão da pesquisa registrada." : "Necessidade de novas fontes registrada. Nenhuma pesquisa foi reenviada.");
      } catch (error) { message(error.message, true); complete.disabled = needs.disabled = false; }
    }
    review.addEventListener("submit", (event) => { event.preventDefault(); void submit("reviewed"); }); needs.addEventListener("click", () => void submit("needs_sources")); container.append(review);
  }
  async function select(jobId, focus = false) {
    if (!/^[a-f0-9]{32}$/.test(jobId)) return;
    state.active = jobId; clearTimeout(state.timer);
    try {
      const job = await api(`/jobs/${jobId}`); if (state.active !== jobId) return;
      if (state.jobs.some((item) => item.id === jobId && item.status !== job.status)) {
        state.jobs = state.jobs.map((item) => item.id === jobId ? { ...item, status: job.status } : item); renderJobs(state.total);
      }
      render(job); if (focus) $("research-detail-title").focus();
      if (["QUEUED", "RUNNING"].includes(job.status) && $("section-research").classList.contains("active")) state.timer = setTimeout(() => void select(jobId), 2500);
    } catch (error) { message(error.message, true); }
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); if (state.submitting || !form.reportValidity()) return;
    state.submitting = true; $("research-submit").disabled = true; message("Enviando a pesquisa…");
    try {
      const claims = lines($("research-claims").value);
      if (!claims.length || claims.length > 12 || claims.some((text) => text.length > 1000)) throw new Error("Informe até 12 afirmações, com no máximo 1.000 caracteres cada.");
      const payload = { topic: $("research-topic").value.trim(), publicOnly: $("research-public-only").checked, allowedDomains: lines($("research-domains").value), urls: lines($("research-urls").value),
        claims: claims.map((text, index) => ({ id: "C" + (index + 1), text })), maxSources: Number($("research-limit").value),
        reference: { kind: $("research-kind").value, work: $("research-work").value.trim(), edition: $("research-edition").value.trim(), incarnation: $("research-incarnation").value.trim() } };
      if ($("research-query").value.trim()) payload.query = $("research-query").value.trim();
      if ($("research-project").value) payload.projectId = $("research-project").value;
      const job = await api("/jobs", { method: "POST", body: JSON.stringify({ requestId: await requestId(payload), ...payload }) });
      message("Pesquisa registrada. Você pode acompanhar o resultado abaixo."); await loadJobs(); await select(job.id, true);
    } catch (error) { message(error.message || "Não foi possível enviar a pesquisa.", true); }
    finally { state.submitting = false; $("research-submit").disabled = false; }
  });
  $("research-kind").addEventListener("change", reference);
  $("research-new").addEventListener("click", () => { form.reset(); sessionStorage.removeItem("maestro-public-research-request"); reference(); message("Preencha os dados para uma nova pesquisa."); $("research-topic").focus(); });
  $("research-refresh").addEventListener("click", () => void loadJobs().then(() => { message("Pesquisas atualizadas."); if (state.active) void select(state.active); }).catch((error) => message(error.message, true)));
  $("research-more").addEventListener("click", () => { state.page++; void loadJobs(false).catch((error) => message(error.message, true)); });
  const section = $("section-research");
  new MutationObserver(() => {
    if (section.classList.contains("active")) {
      if (!state.loaded) { state.loaded = true; void loadProjects(); }
      void loadJobs().catch((error) => message(error.message, true)); if (state.active) void select(state.active);
    } else clearTimeout(state.timer);
  }).observe(section, { attributes: true, attributeFilter: ["class"] });
  reference();
})();
