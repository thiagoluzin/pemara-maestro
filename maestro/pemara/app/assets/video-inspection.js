(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const form = $("inspection-form");
  if (!form) return;
  const base = "/api/studio/api/video-inspection";
  const pendingKey = "pemara.inspection.pending";
  const state = { job: null, active: "", timer: null, busy: false, selected: "", loaded: false };
  const names = { identity: "Identidade", anatomy: "Anatomia", continuity: "Continuidade", physics: "Física", lighting: "Iluminação", synchronization: "Sincronismo" };
  const statuses = { QUEUED: "Na fila", RUNNING: "Decision analisando", CANCELING: "Cancelando após a operação atual", CANCELED: "Cancelada", FAILED: "Falha — confira o relatório", INTERRUPTED: "Interrompida", AWAITING_CODEX: "Triagem pronta · aguardando explicação no Codex", REVIEW_READY: "Pronta para sua revisão" };
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const clock = seconds => { const ms = Math.round(Number(seconds) * 1000); return `${String(Math.floor(ms / 60000)).padStart(2, "0")}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}.${String(ms % 1000).padStart(3, "0")}`; };
  function message(text) { $("inspection-message").textContent = text; }
  async function api(path, options = {}) {
    const response = await fetch(base + path, { cache: "no-store", credentials: "same-origin", ...options,
      headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest", ...(typeof options.body === "string" ? { "Content-Type": "application/json" } : {}), ...options.headers } });
    const result = await response.json();
    if (!response.ok) {
      const error = new Error(typeof result.detail === "string" ? result.detail : "Não foi possível concluir. Confira os campos.");
      error.status = response.status;
      throw error;
    }
    return result;
  }
  async function list() {
    const result = await api("/jobs");
    $("inspection-history").replaceChildren(...result.jobs.map(job => {
      const button = node("button", `${job.name} · ${statuses[job.status] || job.status}`, "btn secondary"); button.type = "button";
      button.addEventListener("click", () => select(job.id).catch(e => message(e.message))); return button;
    }));
  }
  function selectMarker(marker, movePlayback = true) {
    state.selected = marker.id;
    const player = $("inspection-video");
    if (movePlayback) {
      const seek = () => { player.currentTime = marker.sourceStart; player.pause(); };
      if (player.readyState) seek();
      else player.addEventListener("loadedmetadata", seek, { once: true });
    }
    const detail = $("inspection-marker-detail");
    detail.replaceChildren(node("h3", `${names[marker.category]} · ${clock(marker.sourceStart)}–${clock(marker.sourceEnd)}`));
    const p = marker.answer.probabilities;
    detail.append(node("p", `Probabilidade de defeito: ${(p.defect*100).toFixed(1)}% · evidência insuficiente: ${(p.unknown*100).toFixed(1)}%.`));
    const exp = marker.explanation;
    if (exp) {
      const verdicts = { observed_defect: "Defeito observado pelo Codex", false_positive: "Falso positivo segundo o Codex", uncertain: "Evidência inconclusiva" };
      detail.append(node("strong", verdicts[exp.verdict]), node("p", exp.observed));
      if (exp.hypothesis) detail.append(node("p", "Hipótese: " + exp.hypothesis));
      if (exp.correction) detail.append(node("p", "Correção sugerida: " + exp.correction));
    } else detail.append(node("p", "Aguardando investigação no Codex. Este marcador ainda é uma suspeita ou incerteza."));
    detail.append(node("small", "Intervalo da janela analisada; não representa a localização exata do defeito em milissegundos. Aprovação humana pendente."));
  }
  function render(job) {
    state.job = job;
    $("inspection-result").hidden = false;
    $("inspection-title").textContent = job.name;
    $("inspection-status").textContent = `${statuses[job.status] || job.status} · ${job.progress}%`;
    $("inspection-cancel").disabled = !["QUEUED", "RUNNING"].includes(job.status);
    $("inspection-copy").disabled = !job.evidenceSha256;
    $("inspection-report").href = `${base}/jobs/${job.id}/report`;
    const player = $("inspection-video");
    if (player.dataset.job !== job.id) { player.src = `${base}/jobs/${job.id}/source`; player.dataset.job = job.id; }
    const coverage = job.coverage;
    $("inspection-coverage").textContent = `${coverage.reviewedWindows}/${coverage.plannedWindows} janelas · amostragem solicitada: ${coverage.sampleFps} FPS · ${job.markers.length} marcador(es). Análise por amostragem; limiares ainda experimentais.`;
    if (job.consumption) $("inspection-coverage").textContent += ` Uso reportado: ${job.consumption.reportedInputTokens} tokens de entrada · estimativa US$ ${Number(job.consumption.estimatedInputUsd).toFixed(4)} (preço de referência: 13/11/2026).`;
    $("inspection-error").textContent = job.error ? `Erro: ${job.error}. Resultados parciais foram preservados.` : "";
    const timeline = $("inspection-timeline");
    const total = Math.max(.01, job.clip.sourceEnd - job.clip.sourceStart);
    const tracks = Object.keys(names).map(category => {
      const row = node("div", undefined, "inspection-track"); row.append(node("span", names[category]));
      const lane = node("div", undefined, "inspection-lane");
      for (const marker of job.markers.filter(m => m.category === category && m.visible !== false)) {
        const button = node("button", "", "inspection-marker"); button.type = "button";
        button.dataset.status = marker.status;
        button.style.left = `${100*(marker.sourceStart-job.clip.sourceStart)/total}%`;
        button.style.width = `${Math.min(100, 100*(marker.sourceEnd-marker.sourceStart)/total)}%`;
        button.title = `${names[category]} ${clock(marker.sourceStart)}–${clock(marker.sourceEnd)} · ${marker.status}`;
        button.setAttribute("aria-label", button.title); button.addEventListener("click", () => selectMarker(marker)); lane.append(button);
      }
      row.append(lane); return row;
    });
    timeline.replaceChildren(...tracks);
    const items = job.markers.map(marker => {
      const button = node("button", `${clock(marker.sourceStart)}–${clock(marker.sourceEnd)} · ${names[marker.category]} · ${marker.explanation ? "explicado" : "pendente"}`, "btn secondary");
      button.type = "button"; button.addEventListener("click", () => selectMarker(marker)); return button;
    });
    $("inspection-markers").replaceChildren(...items);
    if (!items.length) $("inspection-markers").append(node("p", job.status === "REVIEW_READY" ? "Nenhuma suspeita foi marcada nesta amostragem. Isso não constitui aprovação do vídeo." : "Os marcadores aparecerão após a análise de cada janela."));
    const chosen = job.markers.find(m => m.id === state.selected);
    if (chosen) selectMarker(chosen, false);
    else $("inspection-marker-detail").replaceChildren(node("p", "Selecione um marcador para ver a evidência e a explicação."));
  }
  async function select(id) {
    clearTimeout(state.timer); state.active = id;
    const job = await api(`/jobs/${id}`);
    if (state.active !== id) return;
    render(job);
    if (["QUEUED", "RUNNING", "CANCELING"].includes(job.status)) state.timer = setTimeout(() => select(id).catch(e => message(e.message)), 1500);
  }
  form.addEventListener("submit", async event => {
    event.preventDefault(); if (state.busy) return;
    state.busy = true; $("inspection-submit").disabled = true;
    try {
      let spec = JSON.parse(sessionStorage.getItem(pendingKey) || "null");
      if (!spec) {
        const video = $("inspection-file").files[0]; if (!video) throw new Error("Selecione o vídeo.");
        const data = new FormData(); data.append("video", video);
        for (const file of $("inspection-references").files) data.append("references", file);
        message("Importando uma cópia para inspeção…");
        const prepared = await api("/uploads", { method: "POST", body: data });
        spec = { requestId: crypto.randomUUID().replaceAll("-", ""), projectId: prepared.projectId, clipId: prepared.clipId,
          expectedRevision: prepared.expectedRevision, referenceAssetIds: prepared.referenceAssetIds,
          contentKind: $("inspection-kind").value, expectedState: $("inspection-context").value,
          sampleFps: Number($("inspection-fps").value), maxDecisionCalls: 40 };
        sessionStorage.setItem(pendingKey, JSON.stringify(spec));
      }
      message("Confirmando a solicitação de inspeção…");
      let job;
      try {
        job = await api(`/jobs/${spec.requestId}`);
      } catch (error) {
        if (error.status !== 404) throw error;
        try {
          job = await api("/jobs", { method: "POST", body: JSON.stringify(spec) });
        } catch (submitError) {
          if ([400, 422].includes(submitError.status)) {
            sessionStorage.removeItem(pendingKey);
            form.noValidate = false;
          }
          throw submitError;
        }
      }
      sessionStorage.removeItem(pendingKey);
      form.noValidate = false;
      $("inspection-file").value = "";
      message("Inspeção registrada.");
      await Promise.all([list(), select(job.id)]).catch(() => {
        message(`Inspeção ${job.id} registrada. Use Atualizar para consultar o andamento.`);
      });
    } catch (error) { message(error.message); }
    finally { state.busy = false; $("inspection-submit").disabled = false; }
  });
  if (sessionStorage.getItem(pendingKey)) {
    form.noValidate = true;
    message("Há uma inspeção pendente. Use Analisar para consultar a mesma solicitação.");
  }
  $("inspection-refresh").addEventListener("click", () => { list().catch(e => message(e.message)); if (state.active) select(state.active).catch(e => message(e.message)); });
  $("inspection-cancel").addEventListener("click", () => {
    if (state.active) api(`/jobs/${state.active}/cancel`, { method: "POST" }).then(render).catch(e => message(e.message));
  });
  $("inspection-copy").addEventListener("click", async () => {
    if (!state.job) return;
    const text = `Use $pemara-video-inspection para explicar a inspeção ${state.job.id}, lendo ${state.job.codexRequestPath}. Examine as evidências reais e devolva as explicações aos marcadores, sem gerar mídia.`;
    try { await navigator.clipboard.writeText(text); message("Pedido copiado. Cole no Codex para investigar os trechos."); }
    catch { $("inspection-codex-prompt").value = text; $("inspection-codex-prompt").hidden = false; }
  });
  async function activate() {
    try { const capabilities = await api("/capabilities"); $("inspection-connection").textContent = capabilities.configured ? "Decision configurado · explicações no Codex" : "Configure a credencial Google no computador do PEMARA"; await list(); }
    catch (error) { message(error.message); }
  }
  new MutationObserver(() => {
    if ($("section-inspection").classList.contains("active") && !state.loaded) { state.loaded = true; activate(); }
  }).observe($("section-inspection"), { attributes: true, attributeFilter: ["class"] });
})();
