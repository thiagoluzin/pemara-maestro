/* Local publication preparation. No social login, analytics tracker or GPU API. */
(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const panel = byId("film-internet-publication");
  if (!panel) return;
  const platforms = {
    youtube: "YouTube", youtube_shorts: "YouTube Shorts", instagram_reels: "Instagram Reels",
    threads: "Threads", tiktok: "TikTok", facebook: "Facebook",
  };
  const fields = {
    audience: ["Público", "Quem deve entender e querer assistir?"],
    promise: ["Promessa do vídeo", "O que a abertura promete e o vídeo entrega?"],
    emotion: ["Emoção pretendida", "Curiosidade, tensão, beleza, humor…"],
    opening: ["Abertura recomendada", "Descreva o primeiro acontecimento e por que continuar assistindo."],
    alternativeOpening: ["Abertura alternativa", "Uma segunda ideia escrita, sem gerar outro filme automaticamente."],
    progression: ["Progressão e consequências", "Como cada beat muda a situação, preservando a continuidade?"],
    payoff: ["Recompensa final", "Como a promessa será cumprida?"],
    mobileFraming: ["Enquadramento para o destino", "Composição legível no celular; preserve o formato solicitado."],
    silentComprehension: ["Compreensão sem som", "O que permite entender a cena mesmo com áudio desligado?"],
    constraints: ["Instruções que devem ser preservadas", "Duração, silêncio, estilo, formato e outras decisões explícitas."],
  };
  const metrics = {
    views: "Visualizações", engagedViews: "Visualizações engajadas", reach: "Contas alcançadas",
    nonFollowerReach: "Não seguidores alcançados", shownInFeed: "Exibições no feed",
    choseToWatch: "Escolheram assistir", eligibleStarts: "Inícios elegíveis para retenção",
    viewersAt3Seconds: "Chegaram aos 3 segundos", completions: "Conclusões",
    averageWatchSeconds: "Tempo médio assistido (s)", averageWatchPercent: "Percentual médio assistido (%)",
    shares: "Compartilhamentos", saves: "Salvamentos", comments: "Comentários", newFollowers: "Novos seguidores",
  };
  const rateLabels = {
    choseToWatchPercent: "Escolheram assistir / exibições no feed",
    retainedAt3SecondsPercent: "Chegaram aos 3 s / inícios elegíveis",
    completionPercent: "Conclusões / inícios elegíveis",
    sharesPerReachPercent: "Compartilhamentos / contas alcançadas",
    followersPerReachPercent: "Novos seguidores / contas alcançadas",
  };
  let project = null;
  let snapshot = null;
  let loadSequence = 0;
  const busy = new Set();
  const drafts = new Map();
  const element = (tag, text) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const option = (value, text) => {
    const node = element("option", text);
    node.value = value;
    return node;
  };
  const endpoint = (id, suffix = "") => `${API.studio}/api/video-projects/${encodeURIComponent(id)}/internet-publication${suffix}`;
  const post = (url, body, method = "POST") => fetchJson(url, {
    method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  function message(text, error = false) {
    byId("ip-message").textContent = text;
    byId("ip-message").dataset.error = String(error);
  }
  Object.entries(fields).forEach(([key, [title, placeholder]]) => {
    const label = element("label", title);
    const input = element("textarea");
    input.id = `ip-plan-${key}`;
    input.rows = 3;
    input.maxLength = 2400;
    input.placeholder = placeholder;
    label.htmlFor = input.id;
    label.append(input);
    byId("ip-plan-fields").append(label);
  });
  Object.entries(metrics).forEach(([key, title]) => {
    const label = element("label", title);
    const input = element("input");
    input.id = `ip-metric-${key}`;
    input.type = "number";
    input.min = "0";
    input.max = key === "averageWatchPercent" ? "1000" : key === "averageWatchSeconds" ? "72000" : "1000000000000";
    input.step = key.startsWith("average") ? "0.01" : "1";
    input.placeholder = "Não informado";
    label.htmlFor = input.id;
    label.append(input);
    byId("ip-metric-fields").append(label);
  });
  Object.entries(platforms).forEach(([key, title]) => byId("ip-package-platform").append(option(key, title)));

  function masterReady() {
    const final = project?.finalOutput;
    return final?.ready && !final.stale && final.reviewStatus === "APPROVED_BY_OWNER";
  }
  function controls() {
    const working = !snapshot || busy.has(project?.projectId);
    panel.querySelectorAll("fieldset, #ip-apply-mode, #ip-refresh, #ip-copy-brief, #ip-mode").forEach((node) => { node.disabled = working; });
    byId("ip-prepare-package").disabled = working || !masterReady() || !snapshot?.readiness?.readyForExistingGates;
    byId("ip-save-measurement").disabled = working || !snapshot?.packages?.some((item) => item.status !== "FAILED");
    byId("ip-package-gate").textContent = !masterReady()
      ? "Aguardando revisão e aprovação do master exato pelo proprietário."
      : !snapshot?.readiness?.readyForExistingGates ? "Complete e salve a direção primeiro."
        : "Master aprovado. O pacote terá uma cópia idêntica, sem recorte nem conversão automática.";
  }
  function render(data, fillPlan = true) {
    snapshot = data;
    const enabled = data.intent.mode === "internet";
    byId("ip-enabled").hidden = !enabled;
    byId("ip-mode").value = data.intent.mode;
    byId("ip-badge").textContent = enabled ? "Modo ativo" : "Fluxo habitual";
    byId("ip-readiness").textContent = data.readiness.readyForExistingGates
      ? "Direção preenchida. Continuam valendo as aprovações, a admissão da GPU e a revisão do vídeo."
      : `Antes da geração, definir: ${data.readiness.missingFields.join("; ")}. Rascunhos podem ser salvos.`;
    if (fillPlan) {
      const source = drafts.get(data.projectId)?.plan || data.plan;
      Object.keys(fields).forEach((key) => { byId(`ip-plan-${key}`).value = source[key] || ""; });
    }
    byId("ip-checklist").replaceChildren(...data.checklist.map((text) => element("li", text)));
    const selectedPackage = byId("ip-measurement-package").value;
    const usablePackages = data.packages.filter((item) => item.status !== "FAILED");
    byId("ip-measurement-package").replaceChildren(option("", "Selecione um pacote"), ...usablePackages.map((item) => option(item.id, `${platforms[item.platform]} · ${item.variantLabel} · ${item.title}`)));
    if (usablePackages.some((item) => item.id === selectedPackage)) byId("ip-measurement-package").value = selectedPackage;
    byId("ip-packages").replaceChildren(...data.packages.slice().reverse().map((item) => {
      const row = element("li");
      row.append(element("strong", `${platforms[item.platform]} · ${item.title}`));
      row.append(element("p", item.status === "FAILED" ? "Preparação falhou; arquivos parciais preservados." : `Preparado para revisão · ${item.width}×${item.height} · ${item.durationSeconds.toFixed(2)} s`));
      row.append(element("p", `Vídeo SHA-256: ${item.sourceSha256}`));
      if (item.status !== "FAILED") {
        const link = element("a", "Baixar pacote ZIP");
        link.href = endpoint(data.projectId, `/packages/${encodeURIComponent(item.id)}/download`);
        link.download = `${data.projectId}-${item.id}.zip`;
        row.append(link);
      }
      return row;
    }));
    const summary = data.measurementSummary;
    byId("ip-result-summary").textContent = `${summary.distinctPosts} publicação(ões), ${summary.snapshots} observação(ões). ${summary.status === "INCONCLUSIVE" ? "Ainda sem dados comparáveis suficientes. " : "Comparações descritivas disponíveis. "}${summary.note}`;
    byId("ip-measurements").replaceChildren(...data.measurements.slice().reverse().map((item) => {
      const row = element("li");
      row.append(element("strong", `${platforms[item.platform]} · ${item.windowHours} h após publicar`));
      const link = element("a", "Abrir publicação");
      // The backend allows HTTPS links only on the platform's official domains.
      link.href = item.postUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      row.append(link);
      const observed = Object.entries(item.metrics).filter(([, value]) => value !== null).map(([key, value]) => `${metrics[key]}: ${value}`);
      row.append(element("p", observed.join(" · ")));
      Object.entries(item.rates).forEach(([key, rate]) => row.append(element("p", `${rateLabels[key]}: ${rate.value}%`)));
      const comparison = summary.comparisons.find((entry) => entry.measurementId === item.id);
      if (comparison) row.append(element("p", `${comparison.hypothesis} Mediana de ${comparison.comparablePosts} outros posts comparáveis: ${comparison.peerMedian}%. Não demonstra causa.`));
      if (item.notes) row.append(element("p", item.notes));
      return row;
    }));
    controls();
  }
  async function load(id) {
    const sequence = ++loadSequence;
    try {
      const data = await fetchJson(endpoint(id));
      if (sequence !== loadSequence || project?.projectId !== id) return;
      render(data);
      message(drafts.has(id) ? "Rascunho local preservado. Salve ou descarte explicitamente para recarregar o plano salvo." : "Dados locais carregados. Nenhuma renderização ou publicação foi iniciada.");
    } catch (error) {
      if (sequence === loadSequence && project?.projectId === id) message(error.message, true);
    }
  }
  async function mutate(action, payload, onSuccess) {
    const id = project?.projectId;
    if (!id || !snapshot || busy.has(id)) return;
    busy.add(id);
    controls();
    message(action === "packages" ? "Preparando e conferindo o ZIP local…" : "Salvando…");
    try {
      const data = await post(endpoint(id, `/${action}`), payload);
      if (onSuccess) onSuccess(id);
      if (project?.projectId === id) {
        render(data);
        message(action === "packages" ? "Pacote preparado. Revise os arquivos antes de publicar." : "Salvo. Nenhuma publicação foi feita.");
      }
    } catch (error) {
      if (project?.projectId === id) {
        await load(id);
        message(error.message, true);
      }
    } finally {
      busy.delete(id);
      controls();
    }
  }
  window.addEventListener("maestro:film-project", (event) => {
    const next = event.detail;
    const changed = next?.projectId !== project?.projectId;
    const intentChanged = JSON.stringify(next?.distributionIntent) !== JSON.stringify(project?.distributionIntent);
    project = next;
    panel.hidden = !next;
    if (!next) { snapshot = null; ++loadSequence; return; }
    if (changed) {
      snapshot = null;
      byId("ip-enabled").hidden = true;
      byId("ip-details").open = next.distributionIntent?.mode === "internet";
      byId("ip-package-form").reset();
      byId("ip-measurement-form").reset();
      byId("ip-package-title").value = next.name || "";
    }
    controls();
    if (changed || (intentChanged && !busy.has(next.projectId))) load(next.projectId);
  });
  byId("ip-refresh").addEventListener("click", () => { if (project) load(project.projectId); });
  byId("ip-discard").addEventListener("click", () => {
    if (!project) return;
    drafts.delete(project.projectId);
    load(project.projectId);
  });
  byId("ip-plan-form").addEventListener("input", () => {
    if (!project || !snapshot) return;
    const previous = drafts.get(project.projectId);
    drafts.set(project.projectId, {
      revision: previous?.revision ?? snapshot.revision,
      plan: Object.fromEntries(Object.keys(fields).map((key) => [key, byId(`ip-plan-${key}`).value])),
    });
    message("Rascunho alterado; salve a direção antes de gerar.");
  });
  byId("ip-plan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!snapshot) return;
    const draft = drafts.get(project.projectId);
    mutate("plan", { expectedRevision: draft?.revision ?? snapshot.revision,
      plan: Object.fromEntries(Object.keys(fields).map((key) => [key, byId(`ip-plan-${key}`).value])),
    }, (id) => drafts.delete(id));
  });
  byId("ip-apply-mode").addEventListener("click", async () => {
    const id = project?.projectId;
    if (!id || busy.has(id)) return;
    const mode = byId("ip-mode").value;
    busy.add(id);
    controls();
    try {
      const updated = await post(`${API.studio}/api/video-projects/${encodeURIComponent(id)}`, { distributionMode: mode }, "PATCH");
      if (project?.projectId === id) { project = updated; await load(id); }
      if (typeof refreshFilmProjectData === "function") await refreshFilmProjectData();
    } catch (error) { if (project?.projectId === id) message(error.message, true); }
    finally { busy.delete(id); controls(); }
  });
  byId("ip-copy-brief").addEventListener("click", async () => {
    if (!snapshot) return;
    try { await navigator.clipboard.writeText(snapshot.directorBrief); message("Instrução salva copiada. O diretor deve completar o roteiro e seguir as aprovações existentes."); }
    catch { message("O navegador não permitiu copiar. Use os campos de direção acima.", true); }
  });
  byId("ip-package-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!snapshot) return;
    mutate("packages", { expectedRevision: snapshot.revision, platform: byId("ip-package-platform").value,
      title: byId("ip-package-title").value, description: byId("ip-package-description").value,
      variantLabel: byId("ip-package-label").value, coverTimeSeconds: Number(byId("ip-cover-time").value),
      captionsSrt: byId("ip-package-captions").value,
    });
  });
  byId("ip-measurement-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!snapshot) return;
    const selected = snapshot.packages.find((item) => item.id === byId("ip-measurement-package").value);
    if (!selected) { message("Escolha o pacote que foi publicado.", true); return; }
    const observed = Object.fromEntries(Object.keys(metrics).map((key) => {
      const value = byId(`ip-metric-${key}`).value;
      return [key, value === "" ? null : Number(value)];
    }));
    mutate("measurements", { expectedRevision: snapshot.revision, packageId: selected.id, platform: selected.platform,
      postUrl: byId("ip-post-url").value, windowHours: Number(byId("ip-window-hours").value),
      metrics: observed, notes: byId("ip-measurement-notes").value,
    });
  });
  let previewTimer;
  let previewSequence = 0;
  function preview() {
    clearTimeout(previewTimer);
    const sequence = ++previewSequence;
    previewTimer = setTimeout(async () => {
      try {
        const data = await post(`${API.studio}/api/video-projects/briefing-preview`, {
          brief: `${byId("film-name").value}\n${byId("film-objective").value}`,
          distributionMode: byId("film-distribution-mode").value,
        });
        if (sequence !== previewSequence) return;
        byId("film-distribution-preview").textContent = data.intent.mode === "internet"
          ? "Publicação na internet detectada: o projeto exigirá direção para alcance antes da geração."
          : "Fluxo habitual. Você pode ativar Publicação na internet explicitamente no seletor.";
      } catch { if (sequence === previewSequence) byId("film-distribution-preview").textContent = "A confirmação do modo será feita pelo servidor ao criar o projeto."; }
    }, 350);
  }
  ["film-name", "film-objective", "film-distribution-mode"].forEach((id) => byId(id)?.addEventListener("input", preview));
  byId("film-create-form")?.addEventListener("reset", () => { ++previewSequence; clearTimeout(previewTimer); byId("film-distribution-preview").textContent = "Descreva o destino no objetivo ou escolha o modo acima."; });
})();
