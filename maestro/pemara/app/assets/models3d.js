/* Dedicated 3D workspace; reuse the authenticated, local project/job contracts. */
(() => {
  "use strict";
  const base = "/api/studio/api/zico/games";
  const el = name => document.getElementById(`models3d-${name}`);
  const labels = { trellis2: "TRELLIS.2", pixal3d: "Pixal3D" };
  const statusLabels = { queued: "Na fila", running: "Gerando", done: "Pronto para revisão", error: "Falhou" };
  const state = { projects: [], engines: [], jobs: [], loading: null, generating: false, creating: false, previewUrl: "", signature: "" };
  const active = () => document.getElementById("section-models3d")?.classList.contains("active");
  const api = (path, options = {}) => fetchJson(base + path, options);
  const message = error => error.status === 404 ? "A criação 3D está indisponível no serviço. Tente atualizar os dados." : error.message;
  function syncSubmit() {
    const selected = state.engines.find(engine => engine.id === el("engine").value);
    el("submit").disabled = state.generating || !selected?.available || !el("project").value || !el("image").files.length;
  }
  function renderProjects(selected = el("project").value) {
    el("project").replaceChildren(new Option(state.projects.length ? "Escolha o projeto" : "Crie um projeto primeiro", ""));
    for (const project of state.projects) el("project").append(new Option(project.name, project.id));
    el("project").value = state.projects.some(project => project.id === selected) ? selected : "";
    el("project-help").textContent = state.projects.length ? "Cada modelo fica guardado no projeto escolhido." : "Crie seu primeiro projeto no formulário Novo projeto 3D.";
    syncSubmit();
  }
  function renderEngines() {
    const selected = el("engine").value;
    el("engine").replaceChildren(new Option("Escolha o motor", ""));
    el("engines").replaceChildren();
    for (const engine of state.engines) {
      const name = labels[engine.id] || engine.id;
      const option = new Option(name + (engine.available ? "" : " — indisponível"), engine.id);
      option.disabled = !engine.available;
      el("engine").append(option);
      const item = document.createElement("li");
      const title = document.createElement("strong"); title.textContent = name;
      const detail = document.createElement("span"); detail.textContent = engine.available ? "Configurado no servidor" : "Indisponível para geração";
      item.append(title, detail); el("engines").append(item);
    }
    if (!state.engines.length) el("engines").textContent = "Nenhum motor 3D encontrado.";
    el("engine").value = state.engines.some(engine => engine.id === selected && engine.available) ? selected : "";
    syncSubmit();
  }
  function renderJobs() {
    const jobs = state.jobs.filter(job => job.kind !== "image_jobs");
    el("history-status").textContent = jobs.length ? "Acompanhe os trabalhos e baixe os modelos concluídos." : "Nenhum modelo neste histórico. Comece com uma imagem de referência.";
    const signature = JSON.stringify([jobs, state.projects]);
    if (signature === state.signature) return;
    state.signature = signature;
    el("history").replaceChildren();
    el("history-count").textContent = String(jobs.length);
    for (const job of jobs) {
      const item = document.createElement("li"); item.className = "models3d-job";
      const title = document.createElement("strong");
      title.textContent = state.projects.find(project => project.id === job.projectId)?.name || "Modelo 3D";
      const detail = document.createElement("p");
      detail.textContent = `${labels[job.engine] || job.engine || "3D"} · ${statusLabels[job.status] || job.status} · ${job.jobId}`;
      item.append(title, detail);
      if (job.message) { const error = document.createElement("p"); error.textContent = job.message; item.append(error); }
      if (job.status === "done" && /^\/api\/zico\/games\/assets\/[a-f0-9]{32}\/output$/.test(job.url || "")) {
        const link = document.createElement("a"); link.className = "btn secondary";
        link.textContent = "Baixar modelo GLB"; link.href = "/api/studio" + job.url; link.download = "";
        item.append(link);
      }
      el("history").append(item);
    }
  }
  async function refreshJobs() {
    try {
      const data = await api("/jobs");
      state.jobs = data.jobs || []; renderJobs();
      return true;
    } catch (error) { el("history-status").textContent = message(error); return false; }
  }
  async function activate() {
    if (state.loading) return state.loading;
    state.loading = (async () => {
      el("refresh").disabled = true; el("status").textContent = "Consultando projetos e motores…";
      try {
        const [projects, engines] = await Promise.all([api("/projects"), api("/3d/engines")]);
        state.projects = projects.projects || []; state.engines = engines.engines || [];
        renderProjects(); renderEngines();
        el("status").textContent = state.engines.some(engine => engine.available) ? "Escolha a imagem e o motor para criar seu modelo." : "Nenhum motor está disponível para gerar agora.";
        await poller.run();
        return true;
      } catch (error) { el("status").textContent = message(error); return false; }
      finally { el("refresh").disabled = false; state.loading = null; }
    })();
    return state.loading;
  }
  el("project-form").addEventListener("submit", async event => {
    event.preventDefault(); if (state.creating) return;
    const name = el("project-name").value.trim(); if (!name) return;
    state.creating = true; el("project-submit").disabled = true;
    el("project-status").textContent = "Salvando projeto…";
    try {
      const project = await api("/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, brief: el("project-brief").value.trim() }) });
      state.projects = [project, ...state.projects.filter(item => item.id !== project.id)];
      renderProjects(project.id);
      el("project-form").reset(); el("project-status").textContent = `Projeto ${project.name} criado e selecionado.`;
    } catch (error) { el("project-status").textContent = message(error); }
    finally { state.creating = false; el("project-submit").disabled = false; }
  });
  el("form").addEventListener("submit", async event => {
    event.preventDefault(); if (state.generating) return;
    const file = el("image").files[0];
    if (!file || file.size > 20 * 1024 * 1024 || !/\.(png|jpe?g|webp)$/i.test(file.name)) {
      el("generate-status").textContent = "Selecione uma imagem PNG, JPG ou WebP de até 20 MB."; return;
    }
    if (!state.engines.some(engine => engine.id === el("engine").value && engine.available) || !el("project").value) return;
    state.generating = true; syncSubmit(); el("submit").textContent = "Enviando imagem…";
    el("generate-status").textContent = "Registrando a geração no projeto…";
    const data = new FormData(); data.append("image", file); data.append("project_id", el("project").value); data.append("engine", el("engine").value);
    try {
      const job = await api("/3d", { method: "POST", body: data });
      state.jobs = [job, ...state.jobs.filter(item => item.jobId !== job.jobId)]; renderJobs();
      el("generate-status").textContent = `Pedido ${job.jobId} registrado. Acompanhe em Meus modelos; você pode navegar por outras áreas.`;
    } catch (error) { el("generate-status").textContent = message(error) + " Confira Meus modelos antes de reenviar."; void poller.run(); }
    finally { state.generating = false; el("submit").textContent = "Gerar modelo 3D"; syncSubmit(); }
  });
  el("image").addEventListener("change", () => {
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = ""; el("image-preview").hidden = true; el("image-preview").removeAttribute("src");
    const file = el("image").files[0];
    if (file && file.size <= 20 * 1024 * 1024 && /^image\/(png|jpeg|webp)$/.test(file.type)) {
      state.previewUrl = URL.createObjectURL(file); el("image-preview").src = state.previewUrl; el("image-preview").hidden = false;
    }
    syncSubmit();
  });
  el("project").addEventListener("change", syncSubmit);
  el("engine").addEventListener("change", syncSubmit);
  el("new-project").addEventListener("click", () => {
    el("project-name").focus();
    el("project-form").scrollIntoView({ behavior: "auto", block: "center" });
  });
  el("refresh").addEventListener("click", () => void activate());
  const poller = window.MaestroResilience.createPoller(refreshJobs, 5000, active);
  window.addEventListener("online", () => { if (active()) void activate(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && active()) void poller.run(); });
  window.addEventListener("beforeunload", () => { if (state.previewUrl) URL.revokeObjectURL(state.previewUrl); poller.stop(); });
  poller.start();
  window.MaestroModels3D = { activate };
})();
