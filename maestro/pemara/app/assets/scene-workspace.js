/* Episode workbench. All production and review actions retain Studio's own gates. */
(() => {
  const id = name => document.getElementById(name);
  const desk = id("scene-desk");
  const models = id("episode-models");
  const player = id("scene-player");
  const compare = id("scene-compare-player");
  const version = id("scene-version");
  const alternative = id("scene-compare");
  const api = API.studio + "/api";
  const feedback = message => { id("scene-feedback").textContent = message; };
  const post = (url, data) => fetchJson(url, {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
  });
  const resumeButton = id("scene-resume");
  function lastEpisode() {
    try { return JSON.parse(localStorage.getItem("maestro.lastEpisode") || "null"); } catch { return null; }
  }
  function updateResume() {
    const last = lastEpisode();
    resumeButton.hidden = !last?.projectId;
    if (last?.projectId) resumeButton.textContent = "Continuar " + last.name;
  }
  updateResume();
  resumeButton.onclick = async () => {
    const last = lastEpisode();
    if (!last) return;
    switchSection("films");
    if (!await loadFilmProjects()) return;
    if (!state.films.projects.some(p => p.projectId === last.projectId)) {
      try {
        const p = await fetchFilmMetadata(api + "/video-projects/" + encodeURIComponent(last.projectId));
        state.films.projects.push(p);
      } catch (error) { return toast(error.message); }
    }
    if (state.films.activeProjectId !== last.projectId) await loadFilmProject(last.projectId);
    if (state.films.activeProjectId === last.projectId) id("scene-workspace-open").click();
  };
  let project, scenes = [], marks = [], index = 0, selection = 0, context = false;
  const take = () => scenes[index];
  const path = s => api + "/video-projects/" + encodeURIComponent(project.projectId) + "/takes/" + encodeURIComponent(s.takeId);
  function clearMedia(video) {
    video.pause();
    video.removeAttribute("src");
    video.load();
  }
  function setControls() {
    const scene = take();
    const current = version.selectedOptions[0]?.dataset.current === "true";
    id("scene-frame").disabled = !scene || !current || context || player.readyState < 2 ||
      !["APPROVED","FINAL"].includes(scene.status);
    id("scene-correct").disabled = !scene || !current || context || scene.hasUpscalePreview ||
      !["READY","APPROVED","REJECTED"].includes(scene.status);
    id("scene-context").disabled = !version.value || !scenes[index-1]?.hasPreview || context;
    id("scene-mark").disabled = !version.value || context || player.readyState < 2;
  }
  function sync(play = false) {
    if (!alternative.value || context || compare.readyState < 1) return;
    const target = Math.min(player.currentTime, compare.duration || 0);
    if (Math.abs(compare.currentTime - target) > 0.09) compare.currentTime = target;
    compare.playbackRate = player.playbackRate;
    if (play && !player.paused && target < compare.duration) compare.play().catch(() => {});
    else if (player.paused || target >= compare.duration) compare.pause();
  }
  for (const type of ["play","seeked","timeupdate","ratechange","pause"]) player.addEventListener(type, () => sync(true));
  compare.addEventListener("loadedmetadata", () => sync(true));
  player.addEventListener("loadeddata", setControls);
  player.addEventListener("error", () => {
    if (desk.open && player.hasAttribute("src")) { context = false; feedback("Não foi possível reproduzir esta versão."); setControls(); }
  });
  function displayComparison() {
    compare.hidden = !alternative.value || context;
    if (compare.hidden) clearMedia(compare);
    else compare.src = alternative.value;
  }
  function showVersion() {
    context = false;
    clearMedia(player);
    if (version.value) player.src = version.value;
    for (const opt of alternative.options) opt.disabled = !!opt.value && opt.value === version.value;
    if (alternative.value === version.value) alternative.value = "";
    displayComparison();
    renderMarks();
    feedback(version.value ? "" : "Esta cena ainda não tem vídeo para revisar.");
    setControls();
  }
  version.onchange = showVersion;
  alternative.onchange = displayComparison;
  function renderMarks() {
    const key = version.selectedOptions[0]?.dataset.version;
    id("scene-marks").replaceChildren(...marks.filter(m => m.versionId === key).map(m => {
      const button = document.createElement("button");
      button.className = "btn secondary small";
      button.textContent = m.seconds.toLocaleString("pt-BR") + " s";
      button.setAttribute("aria-label", "Voltar ao quadro em " + button.textContent);
      button.onclick = () => { if (!context && player.readyState >= 1) { player.pause(); player.currentTime = m.seconds; } };
      return button;
    }));
  }
  id("scene-mark").onclick = async () => {
    const ticket = selection;
    player.pause();
    try {
      const mark = await post(path(take()) + "/frame-marks", {versionId:version.selectedOptions[0].dataset.version,seconds:player.currentTime});
      if (ticket !== selection) return;
      if (!marks.some(m => m.versionId === mark.versionId && m.seconds === mark.seconds)) marks.push(mark);
      renderMarks();
      feedback("Quadro marcado no projeto.");
    } catch (error) { if (ticket === selection) feedback(error.message); }
  };

  async function selectScene(i) {
    const ticket = ++selection;
    index = i;
    context = false;
    const scene = take();
    clearMedia(player);
    clearMedia(compare);
    compare.hidden = true;
    version.replaceChildren();
    marks = [];
    renderMarks();
    alternative.replaceChildren(new Option("Sem comparação", ""));
    id("scene-title").textContent = scene ? scene.takeId + " · " + scene.name : "Nenhuma cena cadastrada";
    document.querySelectorAll("#scene-strip button").forEach((b, n) => b.setAttribute("aria-current", String(n === i)));
    setControls();
    const ref = id("scene-ref");
    ref.hidden = !(scene?.hasKeyframe && scene.keyframeApproved);
    ref.open = false;
    const anchor = id("scene-anchor");
    anchor.removeAttribute("src");
    if (!ref.hidden) anchor.src = path(scene) + (filmTakeHasRegisteredAnchor(scene) ? "/anchor-image" : "/thumbnail");
    window.MaestroCinema?.activate(project, scene);
    if (!scene) { feedback(""); return; }
    try {
      localStorage.setItem("maestro.scene." + project.projectId, scene.takeId);
      localStorage.setItem("maestro.lastEpisode", JSON.stringify({projectId:project.projectId,name:project.name}));
      updateResume();
    } catch {}
    feedback("Carregando versões…");
    try {
      const [result, saved] = await Promise.all([fetchFilmMetadata(path(scene) + "/versions"),fetchFilmMetadata(path(scene) + "/frame-marks")]);
      if (ticket !== selection || !desk.open) return;
      marks = saved.data;
      for (const item of result.data) {
        const url = path(scene) + "/versions/" + encodeURIComponent(item.versionId);
        const opt = new Option(item.label + " · " + item.file, url);
        opt.dataset.current = String(item.label === "Versão atual");
        opt.dataset.version = item.versionId;
        version.add(opt);
        alternative.add(new Option(opt.text, url));
      }
      showVersion();
    } catch (error) { if (ticket === selection) feedback(error.message); }
  }
  id("scene-workspace-open").onclick = () => {
    project = state.films.projects.find(p => p.projectId === state.films.activeProjectId);
    if (!project || state.films.projectDataLoading || state.films.projectDataError) return toast("Carregue um projeto para abrir as cenas.");
    scenes = state.films.takes.slice();
    id("scene-project").textContent = project.name;
    const steps = {direction:["Direção","film-takes-list"], references:["Fotos-base","film-anchor-batch"],
      production:["Produção","film-batch-production"], review:["Revisão","film-preview-panel"], finishing:["Acabamento","film-upscale-resolution"]};
    const order = project.episodeWorkflow?.length ? project.episodeWorkflow : Object.keys(steps);
    id("scene-stages").replaceChildren(...order.filter(k => Object.hasOwn(steps,k)).map(k => {
      const button = document.createElement("button");
      button.className = "btn secondary small";
      button.textContent = steps[k][0];
      button.onclick = () => {
        if (project.projectId !== state.films.activeProjectId) return feedback("Reabra o projeto.");
        desk.close();
        setFilmWorkflowView(["direction","review"].includes(k) ? "all" : "production");
        if (take() && k === "review") openFilmTakePreview(take().takeId, {autoplay:false,scroll:false});
        const target = k === "direction" && take() ? id("film-prompt-" + take().takeId) : null;
        if (target?.closest("details")) target.closest("details").open = true;
        (target || id(steps[k][1])).scrollIntoView({block:"center"});
        (target || id(steps[k][1])).focus({preventScroll:true});
      };
      return button;
    }));
    id("scene-strip").replaceChildren(...scenes.map((s,i) => {
      const button = document.createElement("button");
      button.className = "btn secondary";
      button.textContent = s.takeId;
      button.title = s.name + " · " + filmTakeStatusLabel(s.status);
      button.onclick = () => selectScene(i);
      return button;
    }));
    let previous;
    try { previous = localStorage.getItem("maestro.scene." + project.projectId); } catch {}
    const resume = scenes.findIndex(s => s.takeId === (previous || state.films.activeTakeId));
    desk.showModal();
    selectScene(Math.max(0,resume));
  };
  window.MaestroSceneContext = {
    selection() {
      return {takeId:take()?.takeId || "",versionId:context ? "" : version.selectedOptions[0]?.dataset.version || "",
        seconds:context || !version.value ? 0 : player.currentTime};
    },
    async restore(saved) {
      const n = scenes.findIndex(s => s.takeId === saved.takeId);
      if (n < 0) return;
      await selectScene(n);
      if (!saved.versionId || take()?.takeId !== saved.takeId) return;
      const opt = Array.from(version.options).find(o => o.dataset.version === saved.versionId);
      if (!opt) return feedback("A versão da mensagem está indisponível.");
      version.value = opt.value;
      showVersion();
      const expected = opt.value;
      player.addEventListener("loadedmetadata",() => {
        if (version.value===expected && !context) player.currentTime = Math.min(saved.seconds,player.duration);
      },{once:true});
    }
  };
  desk.addEventListener("close", () => { ++selection; context = false; clearMedia(player); clearMedia(compare); });
  document.querySelectorAll("[data-close-dialog]").forEach(b => b.onclick = () => b.closest("dialog").close());

  id("scene-context").onclick = () => {
    context = true;
    setControls();
    displayComparison();
    feedback("Reproduzindo o fim de " + scenes[index-1].takeId + " e depois " + take().takeId + ".");
    player.src = path(scenes[index-1]) + "/preview";
    player.play().catch(() => { if (context) feedback("Pressione reproduzir para assistir à passagem."); });
  };
  player.addEventListener("loadedmetadata", () => {
    if (context && Number.isFinite(player.duration)) player.currentTime = Math.max(0,player.duration-3);
  });
  player.addEventListener("ended", () => {
    if (!context) return;
    showVersion();
    player.play().catch(() => feedback("Pressione reproduzir para continuar."));
  });

  id("scene-correct").onclick = () => {
    if (project.projectId !== state.films.activeProjectId) return feedback("Reabra o projeto para pedir a correção.");
    const tid = take().takeId;
    desk.close();
    openFilmDirectorDialog(tid);
  };
  id("scene-frame").onclick = async () => {
    const ticket = selection;
    const original = version.value;
    const scene = take();
    player.pause();
    const moment = player.currentTime;
    const canvas = document.createElement("canvas");
    canvas.width = player.videoWidth;
    canvas.height = player.videoHeight;
    try {
      canvas.getContext("2d").drawImage(player, 0, 0);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
      if (!blob || ticket !== selection || original !== version.value || !desk.open) return;
      const input = id("gen-base-image");
      if (input.files.length && !confirm("Substituir a imagem de origem no formulário de criação?")) return;
      const transfer = new DataTransfer();
      transfer.items.add(new File([blob], project.projectId + "_" + scene.takeId + "_" + Math.round(moment*1000) + "ms.png", {type:"image/png"}));
      desk.close();
      switchSection("gen");
      document.querySelector('[data-gen-mode="video"]').click();
      input.files = transfer.files;
      input.dispatchEvent(new Event("change", {bubbles:true}));
      id("gen-content-kind").value = project.contentKind || "unknown";
      toast("Quadro carregado como ponto de partida de movimento.");
    } catch (error) { feedback("Falha ao capturar o quadro. " + error.message); }
  };

  let modelSession = 0;
  const modelMessage = message => { id("episode-feedback").textContent = message; };
  async function refreshModels(session) {
    const result = await fetchFilmMetadata(api + "/episode-templates");
    if (session !== modelSession || !models.open) return;
    const select = id("episode-create").elements.template;
    select.replaceChildren(...result.data.map(m => new Option(m.name + " · " + m.sceneCount + " cenas",m.templateId)));
    id("episode-create").querySelector("button").disabled = !select.options.length;
  }
  id("episode-templates-open").onclick = async () => {
    const session = ++modelSession;
    modelMessage("");
    models.showModal();
    const save = id("episode-save");
    save.hidden = state.films.projectDataLoading || !state.films.takes.length;
    id("episode-create").querySelector("button").disabled = true;
    try { await refreshModels(session); } catch (error) { modelMessage(error.message); }
  };
  id("episode-save").onsubmit = async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button");
    const p = state.films.projects.find(entry => entry.projectId === state.films.activeProjectId);
    if (!p || p.contentKind === "unknown") return modelMessage("Defina o tipo da produção no projeto.");
    button.disabled = true;
    try {
      await post(api + "/episode-templates", {name: form.elements.name.value, sourceProjectId:p.projectId});
      await refreshModels(modelSession);
      form.reset();
      modelMessage("Modelo disponível para novos episódios.");
    } catch (error) { modelMessage(error.message); } finally { button.disabled = false; }
  };
  id("episode-create").onsubmit = async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button");
    button.disabled = true;
    try {
      const p = await post(api + "/episode-templates/" + encodeURIComponent(form.elements.template.value) + "/episodes",
        {name:form.elements.name.value});
      models.close();
      form.reset();
      state.films.activeProjectId = p.projectId;
      await loadFilmProjects();
      toast("Episódio criado com as cenas do modelo.");
    } catch (error) { modelMessage(error.message); } finally { button.disabled = false; }
  };
})();

