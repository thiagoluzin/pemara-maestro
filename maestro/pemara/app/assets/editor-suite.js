(function () {
  "use strict";

  const TERMINAL_JOB_STATES = new Set(["completed", "failed", "canceled", "interrupted"]);
  const TRACK_LABELS = {
    video: "Vídeo",
    voice: "Voz",
    music: "Música",
    sfx: "SFX",
    text: "Texto",
  };

  const state = {
    initialized: false,
    active: false,
    apiRoot: "/api/editor",
    studioBase: "",
    notify: null,
    capabilities: null,
    voices: null,
    projects: [],
    project: null,
    selectedAssetId: "",
    selectedClipId: "",
    assetKind: "",
    panel: "clip",
    pendingProposal: null,
    pendingInstruction: "",
    activeJobId: "",
    activeJobProjectId: "",
    pollController: null,
    captionJobBusy: false,
    previewEnd: null,
    captionHighlightTimer: null,
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  class EditorApiError extends Error {
    constructor(message, options = {}) {
      super(message);
      this.name = "EditorApiError";
      this.status = options.status || 0;
      this.code = options.code || "";
      this.details = options.details;
    }
  }

  function html(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[character]));
  }

  function editorPath(value) {
    return encodeURIComponent(String(value || ""));
  }

  function number(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function clamp(value, minimum, maximum, fallback = minimum) {
    return Math.min(maximum, Math.max(minimum, number(value, fallback)));
  }

  function elevenLabsCapability() {
    const voice = state.voices || state.capabilities?.voice || {};
    const capability = voice.elevenlabs
      || voice.providers?.elevenlabs
      || voice.cloud?.elevenlabs
      || {};
    const configured = Boolean(
      capability.configured
      ?? capability.apiKeyConfigured
      ?? capability.available,
    );
    return {
      ...capability,
      configured,
      enabled: configured && capability.enabled !== false,
      voices: Array.isArray(capability.voices) ? capability.voices : [],
      models: Array.isArray(capability.models) ? capability.models : [],
    };
  }

  function hasElevenLabsCloud() {
    const capability = elevenLabsCapability();
    return capability.configured && capability.enabled;
  }

  function formatTime(value) {
    const seconds = Math.max(0, number(value));
    const whole = Math.floor(seconds);
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    const remainder = whole % 60;
    if (hours) {
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }

  function formatBytes(value) {
    const bytes = Math.max(0, number(value));
    if (bytes >= 1024 ** 3) return `${(bytes / (1024 ** 3)).toFixed(1)} GB`;
    if (bytes >= 1024 ** 2) return `${(bytes / (1024 ** 2)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
  }

  function announce(message, tone = "") {
    if (typeof state.notify === "function") state.notify(message);
    const summary = $("#editor-project-summary");
    if (summary) {
      summary.textContent = message;
      summary.dataset.tone = tone;
    }
  }

  function setBusy(button, busy, label = "Processando") {
    if (!button) return;
    button.setAttribute("aria-busy", busy ? "true" : "false");
    if (busy) {
      if (!button.dataset.editorLabel) button.dataset.editorLabel = button.textContent;
      button.textContent = label;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.editorLabel || button.textContent;
      delete button.dataset.editorLabel;
      button.disabled = false;
    }
  }

  function setSuiteBusy(busy) {
    const effectiveBusy = Boolean(busy || state.captionJobBusy);
    $("#editor-suite")?.setAttribute("aria-busy", effectiveBusy ? "true" : "false");
  }

  function stopActiveJobPolling() {
    state.pollController?.abort();
    state.pollController = null;
    state.activeJobId = "";
    state.activeJobProjectId = "";
    state.captionJobBusy = false;
    setSuiteBusy(false);
    $("#editor-job-panel")?.classList.add("hidden");
  }

  function guardCaptionMutation() {
    if (!state.captionJobBusy) return false;
    announce(
      "Aguarde a conclusão das legendas antes de alterar este projeto.",
      "warn",
    );
    return true;
  }

  async function request(path, options = {}) {
    const method = options.method || "GET";
    const headers = new Headers(options.headers || {});
    let body = options.body;
    if (body && !(body instanceof FormData) && typeof body !== "string") {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }
    let response;
    try {
      response = await fetch(`${state.apiRoot}${path}`, {
        method,
        headers,
        body,
        signal: options.signal,
      });
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      throw new EditorApiError("Não foi possível acessar o Editor local.");
    }
    const contentType = response.headers.get("Content-Type") || "";
    let payload = null;
    if (contentType.includes("application/json")) {
      payload = await response.json().catch(() => null);
    } else {
      const text = await response.text();
      payload = text ? { raw: text } : {};
    }
    if (!response.ok) {
      const validation = Array.isArray(payload?.detail)
        ? payload.detail.map((item) => item.msg).filter(Boolean).join("; ")
        : "";
      throw new EditorApiError(
        payload?.error?.message || validation || payload?.detail || response.statusText || "Falha no Editor.",
        {
          status: response.status,
          code: payload?.error?.code || "",
          details: payload?.error?.details,
        },
      );
    }
    return payload || {};
  }

  function resolveContentUrl(path, download = false) {
    if (!path) return "";
    let result = String(path);
    if (!/^https?:\/\//i.test(result)) {
      result = result.startsWith("/api/editor/")
        ? `${state.studioBase}${result}`
        : `${state.apiRoot}${result.startsWith("/") ? "" : "/"}${result}`;
    }
    if (download) result += `${result.includes("?") ? "&" : "?"}download=true`;
    return result;
  }

  function projectAsset(assetId) {
    return state.project?.assets?.find((asset) => asset.assetId === assetId) || null;
  }

  function projectClip(clipId) {
    return state.project?.clips?.find((clip) => clip.clipId === clipId) || null;
  }

  async function handleError(error, context = "Operação") {
    if (error?.name === "AbortError") return;
    if (error?.code === "REVISION_CONFLICT" && state.project?.projectId) {
      announce("O projeto mudou em outra tela. Recarregando a revisão mais recente.", "warn");
      await loadProject(state.project.projectId).catch(() => {});
      return;
    }
    announce(`${context}: ${error?.message || "falha inesperada"}`, "bad");
  }

  function renderCapabilityStatus() {
    const target = $("#editor-capability-status");
    if (!target) return;
    if (!state.capabilities) {
      target.className = "editor-capability";
      target.textContent = "Verificando recursos locais";
      return;
    }
    const editor = state.capabilities.editor || {};
    const voice = state.capabilities.voice || {};
    const assistant = state.capabilities.assistant || {};
    const captions = state.capabilities.captions || {};
    const cloudVoiceReady = hasElevenLabsCloud();
    const pieces = [
      editor.ffmpeg ? "FFmpeg pronto" : "FFmpeg indisponível",
      editor.nvenc ? "NVENC disponível" : "CPU como padrão",
      voice.system?.installed || voice.chatterbox?.installed || cloudVoiceReady
        ? "voz com IA pronta"
        : "voz indisponível",
      assistant.ollama ? "Ollama pronto" : "Ollama sem modelo",
      captions.offlineCpuAsr ? "legendas CPU prontas" : "legendas offline indisponíveis",
    ];
    target.textContent = pieces.join(" · ");
    target.className = `editor-capability ${editor.ffmpeg ? (assistant.ollama ? "ok" : "warn") : "bad"}`;
  }

  async function loadCapabilities() {
    try {
      state.capabilities = await request("/capabilities");
      renderCapabilityStatus();
      renderCapabilityControls();
    } catch (error) {
      const target = $("#editor-capability-status");
      if (target) {
        target.className = "editor-capability bad";
        target.textContent = error.message;
      }
    }
  }

  function renderProjectOptions(preferredId = "") {
    const select = $("#editor-project-select");
    if (!select) return;
    const activeId = preferredId || state.project?.projectId || "";
    select.innerHTML = [
      '<option value="">Selecione ou crie um projeto</option>',
      ...state.projects.map((project) => (
        `<option value="${html(project.projectId)}">${html(project.name)} · ${project.clipCount || 0} clipes</option>`
      )),
    ].join("");
    select.value = state.projects.some((project) => project.projectId === activeId) ? activeId : "";
  }

  async function loadProjects(options = {}) {
    const select = $("#editor-project-select");
    if (select) select.disabled = true;
    try {
      const payload = await request("/projects?page=1&pageSize=100");
      state.projects = payload.items || [];
      let preferredId = options.preferredId || state.project?.projectId || "";
      if (!preferredId) {
        try {
          preferredId = window.localStorage.getItem("maestro-editor-project") || "";
        } catch (_error) {
          preferredId = "";
        }
      }
      renderProjectOptions(preferredId);
      if (preferredId && state.projects.some((project) => project.projectId === preferredId)) {
        await loadProject(preferredId);
      } else if (options.openFirst && state.projects[0]) {
        await loadProject(state.projects[0].projectId);
      } else if (!state.project) {
        renderProject();
      }
    } catch (error) {
      await handleError(error, "Projetos");
    } finally {
      if (select) select.disabled = false;
    }
  }

  async function loadProject(projectId, options = {}) {
    if (!projectId) {
      stopActiveJobPolling();
      state.project = null;
      state.selectedAssetId = "";
      state.selectedClipId = "";
      renderProject();
      return;
    }
    if (
      (state.project?.projectId && state.project.projectId !== projectId)
      || (state.activeJobProjectId && state.activeJobProjectId !== projectId)
    ) {
      stopActiveJobPolling();
    }
    if (!options.silent) setSuiteBusy(true);
    try {
      const payload = await request(`/projects/${editorPath(projectId)}`);
      setProject(payload.project);
      await resumeActiveJob();
    } catch (error) {
      await handleError(error, "Abrir projeto");
    } finally {
      if (!options.silent) setSuiteBusy(false);
    }
  }

  function setProject(project) {
    const nextProjectId = project?.projectId || "";
    if (
      (state.project?.projectId && state.project.projectId !== nextProjectId)
      || (state.activeJobProjectId && state.activeJobProjectId !== nextProjectId)
    ) {
      stopActiveJobPolling();
    }
    state.project = project || null;
    if (state.selectedClipId && !projectClip(state.selectedClipId)) state.selectedClipId = "";
    if (state.selectedAssetId && !projectAsset(state.selectedAssetId)) state.selectedAssetId = "";
    if (project?.projectId) {
      try {
        window.localStorage.setItem("maestro-editor-project", project.projectId);
      } catch (_error) {
        // O editor continua sem persistência de preferência quando o WebView bloqueia storage.
      }
      renderProjectOptions(project.projectId);
    }
    renderProject();
  }

  function projectSummaryText() {
    if (!state.project) return "Selecione um projeto para abrir a biblioteca e a timeline.";
    const settings = state.project.settings || {};
    return [
      `Revisão ${state.project.revision}`,
      `${settings.width || 0}×${settings.height || 0}`,
      `${number(settings.fps).toLocaleString("pt-BR")} FPS`,
      `${state.project.assets?.length || 0} arquivos`,
      `${state.project.clips?.length || 0} clipes`,
      formatTime(state.project.duration),
    ].join(" · ");
  }

  function renderProject() {
    const hasProject = Boolean(state.project?.projectId);
    const summary = $("#editor-project-summary");
    if (summary) summary.textContent = projectSummaryText();
    const rename = $("#editor-project-rename");
    if (rename) rename.disabled = !hasProject;
    const upload = $("#editor-upload-submit");
    if (upload) upload.disabled = !hasProject || !$("#editor-upload-files")?.files?.length;
    const select = $("#editor-project-select");
    if (select && hasProject) select.value = state.project.projectId;
    const stage = $("#editor-preview-stage");
    const settings = state.project?.settings;
    if (stage && settings?.width && settings?.height) {
      stage.style.setProperty("--editor-aspect", `${settings.width} / ${settings.height}`);
    }
    renderLibrary();
    renderTimeline();
    renderClipInspector();
    renderExports();
    renderCaptionControls();
    updateProjectBoundControls();
  }

  function updateProjectBoundControls() {
    const hasProject = Boolean(state.project);
    const selectedVoiceEngine = $("#editor-voice-engine")?.value || "auto";
    const hasLocalVoice = Boolean(
      state.voices?.chatterbox?.installed || state.voices?.system?.installed,
    );
    const hasVoice = selectedVoiceEngine === "elevenlabs_cloud"
      ? hasElevenLabsCloud()
      : selectedVoiceEngine === "chatterbox"
        ? Boolean(state.voices?.chatterbox?.installed)
        : selectedVoiceEngine === "system"
          ? Boolean(state.voices?.system?.installed)
          : hasLocalVoice;
    const hasModel = Boolean(state.capabilities?.assistant?.models?.length);
    const hasFfmpeg = state.capabilities ? Boolean(state.capabilities.editor?.ffmpeg) : true;
    const hasVideoClip = Boolean(state.project?.clips?.some((clip) => clip.track === "video"));
    if ($("#editor-voice-generate")) $("#editor-voice-generate").disabled = !hasProject || !hasVoice;
    if ($("#editor-voice-preview")) $("#editor-voice-preview").disabled = !hasProject || !hasVoice;
    if ($("#editor-copilot-review")) $("#editor-copilot-review").disabled = !hasProject || !hasModel;
    if ($("#editor-export-submit")) {
      $("#editor-export-submit").disabled = !hasProject || !hasFfmpeg || !hasVideoClip;
    }
    if ($("#editor-capcut-handoff-submit")) {
      $("#editor-capcut-handoff-submit").disabled = !hasProject;
    }
    if ($("#editor-timeline-refresh")) $("#editor-timeline-refresh").disabled = !hasProject;
    syncCaptionSource();
  }

  async function createProject(event) {
    event.preventDefault();
    const button = $("#editor-project-create");
    const format = ($("#editor-project-format")?.value || "1920x1080").split("x");
    const body = {
      name: $("#editor-project-name")?.value.trim() || "Novo projeto",
      width: number(format[0], 1920),
      height: number(format[1], 1080),
      fps: number($("#editor-project-fps")?.value, 30),
    };
    try {
      setBusy(button, true, "Criando");
      const payload = await request("/projects", { method: "POST", body });
      closeProjectCreate();
      setProject(payload.project);
      await loadProjects({ preferredId: payload.project.projectId });
      announce(`Projeto “${payload.project.name}” criado.`, "ok");
    } catch (error) {
      await handleError(error, "Criar projeto");
    } finally {
      setBusy(button, false);
    }
  }

  function openProjectCreate() {
    $("#editor-project-create-form")?.classList.remove("hidden");
    $("#editor-project-new-toggle")?.setAttribute("aria-expanded", "true");
    $("#editor-project-name")?.focus();
  }

  function closeProjectCreate({ restoreFocus = false } = {}) {
    $("#editor-project-create-form")?.classList.add("hidden");
    $("#editor-project-new-toggle")?.setAttribute("aria-expanded", "false");
    if (restoreFocus) $("#editor-project-new-toggle")?.focus();
  }

  async function renameProject() {
    if (!state.project) return;
    if (guardCaptionMutation()) return;
    const name = window.prompt("Novo nome do projeto", state.project.name || "");
    if (!name?.trim() || name.trim() === state.project.name) return;
    const button = $("#editor-project-rename");
    try {
      setBusy(button, true, "Salvando");
      const payload = await request(`/projects/${editorPath(state.project.projectId)}`, {
        method: "PATCH",
        body: { expectedRevision: state.project.revision, name: name.trim() },
      });
      setProject(payload.project);
      await loadProjects({ preferredId: payload.project.projectId });
      announce("Projeto renomeado.", "ok");
    } catch (error) {
      await handleError(error, "Renomear projeto");
    } finally {
      setBusy(button, false);
    }
  }

  async function uploadAssets(event) {
    event.preventDefault();
    if (!state.project) return announce("Abra um projeto antes de enviar mídia.", "warn");
    if (guardCaptionMutation()) return;
    const files = Array.from($("#editor-upload-files")?.files || []);
    if (!files.length) return announce("Escolha ao menos um arquivo.", "warn");
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    const button = $("#editor-upload-submit");
    try {
      setBusy(button, true, "Enviando");
      setSuiteBusy(true);
      const payload = await request(`/projects/${editorPath(state.project.projectId)}/assets`, {
        method: "POST",
        body: form,
      });
      setProject(payload.project);
      $("#editor-upload-form")?.reset();
      announce(`${payload.assets?.length || files.length} arquivo(s) adicionado(s).`, "ok");
    } catch (error) {
      await handleError(error, "Enviar mídia");
      if (state.project?.projectId) await loadProject(state.project.projectId, { silent: true });
    } finally {
      setBusy(button, false);
      setSuiteBusy(false);
      updateUploadButton();
    }
  }

  function updateUploadButton() {
    const files = Array.from($("#editor-upload-files")?.files || []);
    const button = $("#editor-upload-submit");
    if (button) button.disabled = !state.project || files.length === 0;
    const action = $(".editor-upload-action");
    if (action) action.textContent = files.length ? `${files.length} selecionado(s)` : "Escolher";
  }

  function renderLibrary() {
    const grid = $("#editor-library-grid");
    const count = $("#editor-library-count");
    if (!grid || !count) return;
    if (!state.project) {
      count.textContent = "Nenhum projeto aberto";
      grid.innerHTML = '<div class="editor-empty" role="status">Abra um projeto para ver os arquivos.</div>';
      return;
    }
    const allAssets = state.project.assets || [];
    const assets = state.assetKind
      ? allAssets.filter((asset) => asset.kind === state.assetKind)
      : allAssets;
    count.textContent = `${allAssets.length} arquivo(s) · ${assets.length} neste filtro`;
    if (!assets.length) {
      grid.innerHTML = '<div class="editor-empty" role="status">Nenhum arquivo neste filtro.</div>';
      return;
    }
    grid.innerHTML = assets.map((asset) => {
      const contentUrl = resolveContentUrl(asset.url);
      const downloadUrl = resolveContentUrl(asset.url, true);
      const preview = asset.kind === "image"
        ? `<img src="${html(contentUrl)}" alt="" loading="lazy">`
        : `<span class="editor-asset-kind">${html(asset.kind === "video" ? "VÍDEO" : "ÁUDIO")}</span>`;
      return `
        <article class="editor-asset-card" role="listitem">
          <button class="editor-asset-preview" type="button" data-editor-preview-asset="${html(asset.assetId)}" aria-label="Visualizar ${html(asset.name)}">
            ${preview}
          </button>
          <div class="editor-asset-copy">
            <strong title="${html(asset.name)}">${html(asset.name)}</strong>
            <small>${html(formatTime(asset.duration))} · ${html(formatBytes(asset.size))}</small>
            <div class="editor-asset-actions">
              <button class="btn secondary" type="button" data-editor-add-asset="${html(asset.assetId)}">Adicionar</button>
              <a class="btn secondary" href="${html(downloadUrl)}" download aria-label="Baixar ${html(asset.name)}">↓</a>
            </div>
          </div>
        </article>
      `;
    }).join("");
  }

  function selectAssetKind(button) {
    state.assetKind = button.dataset.editorKind || "";
    $$("[data-editor-kind]").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", active ? "true" : "false");
    });
    renderLibrary();
  }

  function timelineGeometry() {
    const duration = Math.max(15, number(state.project?.duration));
    const pixelsPerSecond = duration > 900 ? 8 : duration > 300 ? 12 : duration > 120 ? 20 : 40;
    return {
      duration,
      pixelsPerSecond,
      width: Math.min(30000, Math.max(640, Math.ceil(duration * pixelsPerSecond) + 40)),
    };
  }

  function renderTimelineRuler(geometry) {
    const ruler = $("#editor-timeline-ruler");
    if (!ruler) return;
    const step = geometry.duration > 900 ? 120
      : geometry.duration > 300 ? 60
        : geometry.duration > 120 ? 30
          : geometry.duration > 60 ? 10
            : 5;
    const labels = [];
    for (let second = 0; second <= geometry.duration; second += step) {
      labels.push(
        `<span class="editor-ruler-label" style="left:${Math.round(second * geometry.pixelsPerSecond)}px">${html(formatTime(second))}</span>`,
      );
    }
    ruler.innerHTML = labels.join("");
  }

  function renderTimeline() {
    const timeline = $("#editor-timeline");
    const meta = $("#editor-timeline-meta");
    if (!timeline || !meta) return;
    const geometry = timelineGeometry();
    timeline.style.setProperty("--editor-timeline-width", `${geometry.width}px`);
    renderTimelineRuler(geometry);
    const clips = state.project?.clips || [];
    meta.textContent = `${clips.length} clipe(s) · ${formatTime(state.project?.duration || 0)}`;
    Object.keys(TRACK_LABELS).forEach((track) => {
      const target = $(`[data-editor-track="${track}"]`);
      if (!target) return;
      const trackClips = clips.filter((clip) => clip.track === track);
      target.innerHTML = trackClips.map((clip) => {
        const asset = projectAsset(clip.assetId);
        const label = clip.label || asset?.name || (track === "text" ? clip.text : "Clipe");
        const left = Math.max(0, number(clip.timelineStart) * geometry.pixelsPerSecond);
        const width = Math.max(44, number(clip.duration, 0.05) * geometry.pixelsPerSecond);
        const active = clip.clipId === state.selectedClipId;
        return `
          <button
            class="editor-timeline-clip${active ? " active" : ""}"
            type="button"
            data-editor-clip="${html(clip.clipId)}"
            data-track="${html(track)}"
            aria-pressed="${active ? "true" : "false"}"
            style="--clip-left:${Math.round(left)}px;--clip-width:${Math.round(width)}px"
            title="${html(label)} · ${html(formatTime(clip.duration))}"
          >
            <strong>${html(label)}</strong>
            <small>${html(formatTime(clip.timelineStart))} · ${html(formatTime(clip.duration))}</small>
          </button>
        `;
      }).join("");
    });
  }

  function renderClipInspector() {
    const clip = projectClip(state.selectedClipId);
    const empty = $("#editor-clip-empty");
    const form = $("#editor-clip-form");
    if (!empty || !form) return;
    if (!clip) {
      empty.classList.remove("hidden");
      form.classList.add("hidden");
      return;
    }
    const asset = projectAsset(clip.assetId);
    const isText = clip.track === "text";
    const isImage = asset?.kind === "image";
    empty.classList.add("hidden");
    form.classList.remove("hidden");
    $("#editor-clip-track").textContent = TRACK_LABELS[clip.track] || clip.track;
    $("#editor-clip-name").textContent = clip.label || asset?.name || "Clipe";
    $("#editor-clip-label").value = clip.label || "";
    $("#editor-clip-text").value = clip.text || "";
    $("#editor-clip-text-field").classList.toggle("hidden", !isText);
    $("#editor-clip-source-start").value = number(clip.sourceStart).toFixed(2);
    $("#editor-clip-source-end").value = number(clip.sourceEnd).toFixed(2);
    $("#editor-clip-timeline-start").value = number(clip.timelineStart).toFixed(2);
    $("#editor-clip-duration").value = number(clip.duration).toFixed(2);
    $("#editor-clip-volume").value = number(clip.volume, 1);
    $("#editor-clip-volume-value").textContent = `${Math.round(number(clip.volume, 1) * 100)}%`;
    $("#editor-clip-muted").checked = Boolean(clip.muted);
    $("#editor-clip-source-start").disabled = isText || isImage;
    $("#editor-clip-source-end").disabled = isText || isImage;
    $("#editor-clip-timeline-start").disabled = clip.track === "video";
    $("#editor-clip-duration").disabled = !isText && !isImage;
    $("#editor-clip-volume").disabled = isText;
    $("#editor-clip-muted").disabled = isText;
    const videoClips = (state.project?.clips || []).filter((item) => item.track === "video");
    const videoIndex = videoClips.findIndex((item) => item.clipId === clip.clipId);
    $("#editor-clip-earlier").disabled = clip.track !== "video" || videoIndex <= 0;
    $("#editor-clip-later").disabled = clip.track !== "video" || videoIndex < 0 || videoIndex >= videoClips.length - 1;
  }

  function clearPreview() {
    ["#editor-preview-video", "#editor-preview-audio"].forEach((selector) => {
      const media = $(selector);
      if (!media) return;
      media.pause();
      media.removeAttribute("src");
      media.load();
      media.classList.add("hidden");
    });
    const image = $("#editor-preview-image");
    if (image) {
      image.removeAttribute("src");
      image.classList.add("hidden");
    }
    $("#editor-preview-text")?.classList.add("hidden");
    $("#editor-preview-empty")?.classList.remove("hidden");
    $("#editor-preview-download")?.classList.add("hidden");
    $("#editor-preview-play").disabled = true;
    $("#editor-preview-scrubber").disabled = true;
    $("#editor-preview-scrubber").value = "0";
    $("#editor-preview-scrubber").max = "0";
    $("#editor-preview-time").textContent = "00:00 / 00:00";
    state.previewEnd = null;
  }

  function showPreview(asset, clip = null) {
    clearPreview();
    if (!asset && clip?.track === "text") {
      const text = $("#editor-preview-text");
      text.textContent = clip.text || "";
      text.classList.remove("hidden");
      $("#editor-preview-empty").classList.add("hidden");
      $("#editor-preview-meta").textContent = clip.label || "Texto";
      return;
    }
    if (!asset) return;
    const url = resolveContentUrl(asset.url);
    const start = clip ? number(clip.sourceStart) : 0;
    const end = clip ? number(clip.sourceEnd, asset.duration) : number(asset.duration);
    state.previewEnd = end > start ? end : null;
    $("#editor-preview-empty").classList.add("hidden");
    $("#editor-preview-meta").textContent = [
      asset.name,
      TRACK_LABELS[clip?.track] || asset.kind,
      formatTime(clip?.duration ?? asset.duration),
    ].filter(Boolean).join(" · ");
    const download = $("#editor-preview-download");
    download.href = resolveContentUrl(asset.url, true);
    download.download = asset.name || "";
    download.classList.remove("hidden");
    if (asset.kind === "video") {
      const media = $("#editor-preview-video");
      media.src = url;
      media.dataset.editorStart = String(start);
      media.classList.remove("hidden");
      media.addEventListener("loadedmetadata", () => {
        media.currentTime = Math.min(start, media.duration || start);
        syncPreviewTransport(media);
      }, { once: true });
      $("#editor-preview-play").disabled = false;
    } else if (asset.kind === "audio") {
      const media = $("#editor-preview-audio");
      media.src = url;
      media.dataset.editorStart = String(start);
      media.classList.remove("hidden");
      media.addEventListener("loadedmetadata", () => {
        media.currentTime = Math.min(start, media.duration || start);
        syncPreviewTransport(media);
      }, { once: true });
      $("#editor-preview-play").disabled = false;
    } else {
      const image = $("#editor-preview-image");
      image.src = url;
      image.alt = asset.name || "Preview";
      image.classList.remove("hidden");
    }
  }

  function activePreviewMedia() {
    return ["#editor-preview-video", "#editor-preview-audio"]
      .map((selector) => $(selector))
      .find((media) => media && !media.classList.contains("hidden")) || null;
  }

  function syncPreviewTransport(media = activePreviewMedia()) {
    if (!media) return;
    const start = number(media.dataset.editorStart);
    const naturalEnd = Number.isFinite(media.duration) ? media.duration : 0;
    const end = state.previewEnd && state.previewEnd > start
      ? Math.min(state.previewEnd, naturalEnd || state.previewEnd)
      : naturalEnd;
    const scrubber = $("#editor-preview-scrubber");
    scrubber.min = String(start);
    scrubber.max = String(Math.max(start, end));
    scrubber.value = String(Math.max(start, Math.min(end, media.currentTime || start)));
    scrubber.disabled = end <= start;
    $("#editor-preview-time").textContent = `${formatTime(media.currentTime || start)} / ${formatTime(end)}`;
    $("#editor-preview-play").textContent = media.paused ? "Reproduzir" : "Pausar";
    if (end && media.currentTime >= end) {
      media.pause();
      media.currentTime = start;
    }
  }

  function previewAsset(assetId) {
    const asset = projectAsset(assetId);
    if (!asset) return;
    state.selectedAssetId = assetId;
    showPreview(asset);
  }

  function selectClip(clipId) {
    const clip = projectClip(clipId);
    if (!clip) return;
    state.selectedClipId = clipId;
    state.selectedAssetId = clip.assetId || "";
    renderTimeline();
    renderClipInspector();
    showPreview(projectAsset(clip.assetId), clip);
    setToolPanel("clip");
  }

  async function addAssetToTimeline(assetId, button) {
    if (!state.project) return;
    if (guardCaptionMutation()) return;
    const asset = projectAsset(assetId);
    if (!asset) return;
    const track = asset.kind === "audio"
      ? ($("#editor-audio-track-target")?.value || "music")
      : "video";
    const body = {
      expectedRevision: state.project.revision,
      track,
      assetId,
      sourceStart: 0,
      volume: 1,
      label: asset.name,
    };
    if (asset.kind === "image") body.duration = 4;
    else if (number(asset.duration) > 0) body.sourceEnd = number(asset.duration);
    if (track !== "video") body.timelineStart = 0;
    try {
      setBusy(button, true, "Adicionando");
      const payload = await request(`/projects/${editorPath(state.project.projectId)}/clips`, {
        method: "POST",
        body,
      });
      const previousIds = new Set((state.project.clips || []).map((clip) => clip.clipId));
      setProject(payload.project);
      const created = (payload.project.clips || []).find((clip) => !previousIds.has(clip.clipId));
      if (created) selectClip(created.clipId);
      announce(`${asset.name} adicionado à trilha ${TRACK_LABELS[track]}.`, "ok");
    } catch (error) {
      await handleError(error, "Adicionar clipe");
    } finally {
      setBusy(button, false);
    }
  }

  async function saveClip(event) {
    event.preventDefault();
    if (guardCaptionMutation()) return;
    const clip = projectClip(state.selectedClipId);
    if (!clip || !state.project) return;
    const asset = projectAsset(clip.assetId);
    const body = {
      expectedRevision: state.project.revision,
      label: $("#editor-clip-label").value.trim(),
    };
    if (clip.track === "text") {
      body.text = $("#editor-clip-text").value.trim();
      body.timelineStart = number($("#editor-clip-timeline-start").value);
      body.duration = number($("#editor-clip-duration").value);
    } else if (asset?.kind === "image") {
      body.duration = number($("#editor-clip-duration").value);
      body.muted = $("#editor-clip-muted").checked;
      body.volume = number($("#editor-clip-volume").value, 1);
    } else {
      body.sourceStart = number($("#editor-clip-source-start").value);
      body.sourceEnd = number($("#editor-clip-source-end").value);
      body.volume = number($("#editor-clip-volume").value, 1);
      body.muted = $("#editor-clip-muted").checked;
      if (clip.track !== "video") {
        body.timelineStart = number($("#editor-clip-timeline-start").value);
      }
    }
    const button = $("#editor-clip-save");
    try {
      setBusy(button, true, "Salvando");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/clips/${editorPath(clip.clipId)}`,
        { method: "PATCH", body },
      );
      setProject(payload.project);
      selectClip(clip.clipId);
      announce("Clipe atualizado.", "ok");
    } catch (error) {
      await handleError(error, "Salvar clipe");
    } finally {
      setBusy(button, false);
    }
  }

  async function removeSelectedClip() {
    if (guardCaptionMutation()) return;
    const clip = projectClip(state.selectedClipId);
    if (!clip || !state.project) return;
    if (!window.confirm(`Remover “${clip.label || "clipe"}” da timeline? O arquivo continuará na biblioteca.`)) return;
    const button = $("#editor-clip-delete");
    try {
      setBusy(button, true, "Removendo");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/clips/${editorPath(clip.clipId)}`,
        {
          method: "DELETE",
          body: { expectedRevision: state.project.revision },
        },
      );
      state.selectedClipId = "";
      setProject(payload.project);
      clearPreview();
      announce("Clipe removido; o arquivo foi preservado.", "ok");
    } catch (error) {
      await handleError(error, "Remover clipe");
    } finally {
      setBusy(button, false);
    }
  }

  async function reorderSelectedClip(delta, button) {
    if (guardCaptionMutation()) return;
    const clip = projectClip(state.selectedClipId);
    if (!clip || clip.track !== "video" || !state.project) return;
    const destination = Math.max(0, number(clip.order) + delta);
    try {
      setBusy(button, true, "Movendo");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/clips/${editorPath(clip.clipId)}`,
        {
          method: "PATCH",
          body: { expectedRevision: state.project.revision, order: destination },
        },
      );
      setProject(payload.project);
      selectClip(clip.clipId);
      announce("Ordem da trilha de vídeo atualizada.", "ok");
    } catch (error) {
      await handleError(error, "Reordenar clipe");
    } finally {
      setBusy(button, false);
    }
  }

  function setToolPanel(name) {
    state.panel = name;
    $$("[data-editor-panel]").forEach((button) => {
      const active = button.dataset.editorPanel === name;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
      button.tabIndex = active ? 0 : -1;
      $(`#editor-panel-${button.dataset.editorPanel}`)?.classList.toggle("hidden", !active);
    });
  }

  function navigateToolTabs(event) {
    const tabs = $$("[data-editor-panel]");
    const current = tabs.indexOf(event.currentTarget);
    if (current < 0) return;
    let destination = current;
    if (event.key === "ArrowRight") destination = (current + 1) % tabs.length;
    else if (event.key === "ArrowLeft") destination = (current - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") destination = 0;
    else if (event.key === "End") destination = tabs.length - 1;
    else return;
    event.preventDefault();
    const next = tabs[destination];
    setToolPanel(next.dataset.editorPanel);
    next.focus();
  }

  function bindTimelineEvents() {
    $("#editor-library-grid")?.addEventListener("click", (event) => {
      const preview = event.target.closest("[data-editor-preview-asset]");
      if (preview) {
        previewAsset(preview.dataset.editorPreviewAsset);
        return;
      }
      const add = event.target.closest("[data-editor-add-asset]");
      if (add) addAssetToTimeline(add.dataset.editorAddAsset, add);
    });
    $("#editor-timeline")?.addEventListener("click", (event) => {
      const clip = event.target.closest("[data-editor-clip]");
      if (clip) selectClip(clip.dataset.editorClip);
    });
    $$("[data-editor-panel]").forEach((button) => {
      button.addEventListener("click", () => setToolPanel(button.dataset.editorPanel));
      button.addEventListener("keydown", navigateToolTabs);
    });
    $("#editor-clip-form")?.addEventListener("submit", saveClip);
    $("#editor-clip-delete")?.addEventListener("click", removeSelectedClip);
    $("#editor-clip-earlier")?.addEventListener("click", (event) => reorderSelectedClip(-1, event.currentTarget));
    $("#editor-clip-later")?.addEventListener("click", (event) => reorderSelectedClip(1, event.currentTarget));
    $("#editor-clip-volume")?.addEventListener("input", (event) => {
      $("#editor-clip-volume-value").textContent = `${Math.round(number(event.target.value, 1) * 100)}%`;
    });
    $("#editor-timeline-refresh")?.addEventListener("click", () => {
      if (state.project?.projectId) loadProject(state.project.projectId);
    });
    $("#editor-preview-play")?.addEventListener("click", () => {
      const media = activePreviewMedia();
      if (!media) return;
      if (media.paused) media.play().catch(() => {});
      else media.pause();
      syncPreviewTransport(media);
    });
    $("#editor-preview-scrubber")?.addEventListener("input", (event) => {
      const media = activePreviewMedia();
      if (!media) return;
      media.currentTime = number(event.target.value);
      syncPreviewTransport(media);
    });
    ["#editor-preview-video", "#editor-preview-audio"].forEach((selector) => {
      const media = $(selector);
      media?.addEventListener("timeupdate", () => syncPreviewTransport(media));
      media?.addEventListener("play", () => syncPreviewTransport(media));
      media?.addEventListener("pause", () => syncPreviewTransport(media));
    });
  }

  function captionAssets() {
    return (state.project?.assets || []).filter(
      (asset) => asset.hasAudio && (asset.kind === "audio" || asset.kind === "video"),
    );
  }

  function syncCaptionSource() {
    const sourceSelect = $("#editor-caption-source");
    if (!sourceSelect) return;
    const usesAsset = sourceSelect.value !== "project";
    const assetField = $("#editor-caption-asset-field");
    const startField = $("#editor-caption-start-field");
    const assetSelect = $("#editor-caption-asset");
    const startInput = $("#editor-caption-start");
    const languageSelect = $("#editor-caption-language");
    const replaceInput = $("#editor-caption-replace");
    const button = $("#editor-caption-generate");
    const available = Boolean(state.capabilities?.captions?.offlineCpuAsr);
    const hasProject = Boolean(state.project?.projectId);
    const eligibleAssets = captionAssets();

    assetField?.classList.toggle("hidden", !usesAsset);
    startField?.classList.toggle("hidden", !usesAsset);
    assetField?.setAttribute("aria-hidden", usesAsset ? "false" : "true");
    startField?.setAttribute("aria-hidden", usesAsset ? "false" : "true");
    sourceSelect.disabled = !available || !hasProject;
    if (assetSelect) assetSelect.disabled = !available || !hasProject || !usesAsset || !eligibleAssets.length;
    if (startInput) startInput.disabled = !available || !hasProject || !usesAsset;
    if (languageSelect) languageSelect.disabled = !available || !hasProject;
    if (replaceInput) replaceInput.disabled = !available || !hasProject;
    if (button) {
      const busy = Boolean(button.dataset.editorLabel);
      button.disabled = busy
        || !available
        || !hasProject
        || (usesAsset && (!eligibleAssets.length || !assetSelect?.value));
    }
  }

  function renderCaptionControls() {
    const assetSelect = $("#editor-caption-asset");
    const status = $("#editor-caption-status");
    const eligibleAssets = captionAssets();
    if (assetSelect) {
      const current = assetSelect.value;
      const preferred = eligibleAssets.some((asset) => asset.assetId === current)
        ? current
        : eligibleAssets.some((asset) => asset.assetId === state.selectedAssetId)
          ? state.selectedAssetId
          : eligibleAssets[0]?.assetId || "";
      assetSelect.innerHTML = [
        '<option value="">Selecione um arquivo</option>',
        ...eligibleAssets.map((asset) => (
          `<option value="${html(asset.assetId)}">${html(asset.name)} · ${html(formatTime(asset.duration))}</option>`
        )),
      ].join("");
      assetSelect.value = preferred;
    }
    if (status) {
      const captions = state.capabilities?.captions;
      if (!state.capabilities) {
        status.className = "editor-callout";
        status.textContent = "Verificando transcrição local.";
      } else if (captions?.offlineCpuAsr) {
        status.className = "editor-callout ok";
        status.textContent = `${captions.model || "Faster Whisper"} pronto em CPU ${captions.computeType || "int8"}. O áudio permanece local.`;
      } else {
        status.className = "editor-callout warn";
        status.textContent = "A transcrição offline em CPU não está disponível neste ambiente.";
      }
    }
    syncCaptionSource();
  }

  function highlightCaptionTrack(clipIds = []) {
    const track = $('[data-editor-track="text"]');
    if (!track) return;
    if (state.captionHighlightTimer) window.clearTimeout(state.captionHighlightTimer);
    track.classList.add("editor-track-highlight");
    const identifiers = new Set(Array.isArray(clipIds) ? clipIds : []);
    const highlighted = $$('[data-editor-track="text"] [data-editor-clip]').filter((clip) => {
      const matches = identifiers.size === 0 || identifiers.has(clip.dataset.editorClip);
      clip.classList.toggle("caption-highlight", matches);
      return matches;
    });
    const first = highlighted[0];
    const scroller = $("#editor-timeline-scroll");
    if (first && scroller) scroller.scrollLeft = Math.max(0, first.offsetLeft - 100);
    state.captionHighlightTimer = window.setTimeout(() => {
      track.classList.remove("editor-track-highlight");
      highlighted.forEach((clip) => clip.classList.remove("caption-highlight"));
      state.captionHighlightTimer = null;
    }, 2600);
  }

  function providerItemId(item, keys) {
    if (typeof item === "string") return item;
    for (const key of keys) {
      if (item?.[key]) return String(item[key]);
    }
    return "";
  }

  function renderElevenLabsCloudControls() {
    const capability = elevenLabsCapability();
    const ready = capability.configured && capability.enabled;
    const engineOption = $("#editor-voice-engine")
      ?.querySelector('option[value="elevenlabs_cloud"]');
    if (engineOption) {
      engineOption.disabled = !ready;
      engineOption.textContent = ready
        ? "ElevenLabs cloud (opcional)"
        : capability.configured
          ? "ElevenLabs cloud desativada"
          : "ElevenLabs cloud não configurada";
    }

    const voiceSelect = $("#editor-voice-provider-id");
    if (voiceSelect) {
      const current = voiceSelect.value;
      const voices = capability.voices
        .map((item) => ({
          id: providerItemId(item, ["voiceId", "voice_id", "id"]),
          name: typeof item === "string" ? item : item?.name,
          category: typeof item === "string" ? "" : item?.category,
        }))
        .filter((item) => item.id);
      const defaultVoiceId = String(
        capability.defaultVoiceId || capability.default_voice_id || "",
      );
      const optionIds = new Set(voices.map((item) => item.id));
      const options = ['<option value="">Voz padrão do servidor</option>'];
      if (defaultVoiceId && !optionIds.has(defaultVoiceId)) {
        options.push(`<option value="${html(defaultVoiceId)}">Voz padrão · ${html(defaultVoiceId)}</option>`);
      }
      options.push(...voices.map((item) => {
        const label = [item.name || item.id, item.category].filter(Boolean).join(" · ");
        return `<option value="${html(item.id)}">${html(label)}</option>`;
      }));
      voiceSelect.innerHTML = options.join("");
      const preferred = optionIds.has(current) || current === defaultVoiceId
        ? current
        : defaultVoiceId;
      voiceSelect.value = preferred || "";
      voiceSelect.disabled = !ready;
    }

    const modelSelect = $("#editor-voice-model-id");
    if (modelSelect) {
      const current = modelSelect.value;
      const models = capability.models
        .map((item) => ({
          id: providerItemId(item, ["modelId", "model_id", "id"]),
          name: typeof item === "string" ? item : item?.name,
        }))
        .filter((item) => item.id);
      const defaultModelId = String(
        capability.defaultModelId || capability.default_model_id || "",
      );
      const optionIds = new Set(models.map((item) => item.id));
      const options = ['<option value="">Modelo padrão do servidor</option>'];
      if (defaultModelId && !optionIds.has(defaultModelId)) {
        options.push(`<option value="${html(defaultModelId)}">${html(defaultModelId)}</option>`);
      }
      options.push(...models.map((item) => (
        `<option value="${html(item.id)}">${html(item.name || item.id)}</option>`
      )));
      modelSelect.innerHTML = options.join("");
      const preferred = optionIds.has(current) || current === defaultModelId
        ? current
        : defaultModelId;
      modelSelect.value = preferred || "";
      modelSelect.disabled = !ready;
    }
  }

  function setVoiceControlGroup(root, visible) {
    if (!root) return;
    root.classList.toggle("hidden", !visible);
    root.setAttribute("aria-hidden", visible ? "false" : "true");
  }

  function syncVoiceEngineControls() {
    const engine = $("#editor-voice-engine")?.value || "auto";
    const voice = state.voices || state.capabilities?.voice || {};
    const showSystem = engine === "auto" || engine === "system";
    const showLocal = engine === "auto" || engine === "chatterbox";
    const showCloud = engine === "elevenlabs_cloud";
    const cloudReady = hasElevenLabsCloud();

    setVoiceControlGroup($("#editor-voice-system-controls"), showSystem);
    setVoiceControlGroup($("#editor-voice-local-controls"), showLocal);
    setVoiceControlGroup($("#editor-voice-cloud-controls"), showCloud);

    const systemSelect = $("#editor-system-voice");
    if (systemSelect) systemSelect.disabled = !showSystem || !voice.system?.installed;
    const profileSelect = $("#editor-voice-profile");
    if (profileSelect) {
      profileSelect.disabled = !showLocal || !voice.chatterbox?.supportsVoiceClone;
    }
    ["#editor-voice-exaggeration", "#editor-voice-cfg-weight", "#editor-voice-temperature"]
      .forEach((selector) => {
        const input = $(selector);
        if (input) input.disabled = !showLocal;
      });
    ["#editor-voice-provider-id", "#editor-voice-model-id", "#editor-voice-performance-direction"]
      .forEach((selector) => {
        const input = $(selector);
        if (input) input.disabled = !showCloud || !cloudReady;
      });

    const generate = $("#editor-voice-generate");
    if (generate) {
      generate.textContent = showCloud ? "Gerar voz via cloud" : "Gerar voz local";
    }
    const preview = $("#editor-voice-preview");
    if (preview) {
      preview.textContent = showCloud ? "Ouvir prévia via cloud" : "Ouvir prévia curta";
    }
  }

  function syncVoiceIntensityOutput() {
    const input = $("#editor-voice-intensity");
    const output = $("#editor-voice-intensity-value");
    if (!input || !output) return;
    output.value = clamp(input.value, 0, 1, 0.5).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function renderCapabilityControls() {
    if (!state.capabilities) return;
    state.voices = state.capabilities.voice || state.voices;
    const editor = state.capabilities.editor || {};
    const voice = state.voices || {};
    const assistant = state.capabilities.assistant || {};
    const nvenc = $("#editor-export-encoder")?.querySelector('option[value="nvenc"]');
    if (nvenc) {
      nvenc.disabled = !editor.nvenc;
      nvenc.textContent = editor.nvenc ? "NVENC (GPU)" : "NVENC indisponível";
    }
    if ($("#editor-export-encoder")?.value === "nvenc" && !editor.nvenc) {
      $("#editor-export-encoder").value = "cpu";
    }
    const chatterbox = $("#editor-voice-engine")?.querySelector('option[value="chatterbox"]');
    if (chatterbox) {
      chatterbox.disabled = !voice.chatterbox?.installed;
      chatterbox.textContent = voice.chatterbox?.installed
        ? "Chatterbox local"
        : "Chatterbox não instalado";
    }
    const system = $("#editor-voice-engine")?.querySelector('option[value="system"]');
    if (system) {
      system.disabled = !voice.system?.installed;
      system.textContent = voice.system?.installed
        ? "Voz do Windows"
        : "Voz do Windows indisponível";
    }
    renderElevenLabsCloudControls();
    const systemSelect = $("#editor-system-voice");
    if (systemSelect) {
      const current = systemSelect.value;
      const systemVoices = voice.system?.voices || [];
      systemSelect.innerHTML = [
        '<option value="">Automática</option>',
        ...systemVoices.map((name) => `<option value="${html(name)}">${html(name)}</option>`),
      ].join("");
      if (systemVoices.includes(current)) systemSelect.value = current;
      systemSelect.disabled = !voice.system?.installed;
    }
    const profileSelect = $("#editor-voice-profile");
    if (profileSelect) {
      const current = profileSelect.value;
      const profiles = voice.profiles || [];
      profileSelect.innerHTML = [
        '<option value="">Sem clonagem</option>',
        ...profiles.map((profile) => (
          `<option value="${html(profile.voiceProfileId)}">${html(profile.name)} · ${html(formatTime(profile.duration))}</option>`
        )),
      ].join("");
      if (profiles.some((profile) => profile.voiceProfileId === current)) profileSelect.value = current;
      profileSelect.disabled = !voice.chatterbox?.supportsVoiceClone;
    }
    const voiceStatus = $("#editor-voice-status");
    if (voiceStatus) {
      const cloudReady = hasElevenLabsCloud();
      const neuralReadiness = voice.chatterbox?.readiness;
      if (voice.chatterbox?.installed && neuralReadiness && !neuralReadiness.ready) {
        voiceStatus.className = "editor-callout warn";
        const fallback = voice.system?.installed
          ? " No modo automático, o Maestro usará temporariamente a Voz do Windows."
          : " Aguarde a GPU ficar livre para gerar.";
        voiceStatus.textContent = `${neuralReadiness.message || "A voz neural está aguardando a GPU."}${fallback}`;
      } else if (voice.chatterbox?.installed) {
        voiceStatus.className = "editor-callout ok";
        const freeVramValue = neuralReadiness?.freeVramGb;
        const freeVram = Number(freeVramValue);
        const gpuDetail = freeVramValue !== null && freeVramValue !== undefined && Number.isFinite(freeVram)
          ? ` RTX com ${freeVram.toLocaleString("pt-BR")} GB livres.`
          : "";
        voiceStatus.textContent = cloudReady
          ? "Chatterbox local disponível. A conexão ElevenLabs cloud opcional também está pronta."
          : `Chatterbox local disponível. Perfis autorizados podem ser usados para clonagem.${gpuDetail}`;
      } else if (voice.system?.installed) {
        voiceStatus.className = "editor-callout warn";
        voiceStatus.textContent = cloudReady
          ? "Voz do Windows e conexão ElevenLabs cloud disponíveis."
          : "Voz do Windows disponível. Clonagem neural não está instalada.";
      } else if (cloudReady) {
        voiceStatus.className = "editor-callout ok";
        voiceStatus.textContent = "A conexão ElevenLabs cloud opcional está pronta. Nenhum motor neural local está instalado.";
      } else {
        voiceStatus.className = "editor-callout bad";
        voiceStatus.textContent = "Nenhum motor de voz local está disponível.";
      }
    }
    const models = assistant.models || [];
    const modelSelect = $("#editor-copilot-model");
    if (modelSelect) {
      modelSelect.innerHTML = models.length
        ? models.map((model) => `<option value="${html(model)}">${html(model)}</option>`).join("")
        : '<option value="">Nenhum modelo local</option>';
      if (models.includes(assistant.defaultModel)) modelSelect.value = assistant.defaultModel;
      modelSelect.disabled = models.length === 0;
    }
    const copilotStatus = $("#editor-copilot-status");
    if (copilotStatus) {
      copilotStatus.className = `editor-callout ${models.length ? "ok" : "warn"}`;
      copilotStatus.textContent = models.length
        ? `${models.length} modelo(s) Ollama disponível(is). Sugestões nunca são aplicadas sem revisão.`
        : "Ollama está offline ou não possui modelo instalado.";
    }
    const review = $("#editor-copilot-review");
    if (review) review.disabled = !state.project || models.length === 0;
    syncVoiceEngineControls();
    syncVoiceIntensityOutput();
    renderCaptionControls();
    updateProjectBoundControls();
  }

  async function refreshVoices() {
    try {
      const payload = await request("/voices");
      const { ok: _ok, ...freshVoice } = payload;
      const previousVoice = state.capabilities?.voice || state.voices || {};
      const voice = {
        ...previousVoice,
        ...freshVoice,
        elevenlabs: freshVoice.elevenlabs || previousVoice.elevenlabs,
      };
      state.voices = voice;
      if (state.capabilities) state.capabilities.voice = voice;
      renderCapabilityControls();
    } catch (error) {
      await handleError(error, "Vozes locais");
    }
  }

  async function createVoiceProfile(event) {
    event.preventDefault();
    const file = $("#editor-voice-profile-file")?.files?.[0];
    if (!file) return announce("Escolha uma amostra de voz.", "warn");
    if (!$("#editor-voice-consent")?.checked) {
      return announce("O consentimento explícito é obrigatório para criar o perfil.", "warn");
    }
    const form = new FormData();
    form.append("name", $("#editor-voice-profile-name").value.trim());
    form.append("consent", "true");
    form.append("file", file);
    const button = $("#editor-voice-profile-create");
    try {
      setBusy(button, true, "Preparando");
      const payload = await request("/voices", { method: "POST", body: form });
      $("#editor-voice-profile-form").reset();
      await refreshVoices();
      $("#editor-voice-profile").value = payload.voiceProfile.voiceProfileId;
      $("#editor-voice-engine").value = "chatterbox";
      announce(`Perfil “${payload.voiceProfile.name}” salvo localmente.`, "ok");
    } catch (error) {
      await handleError(error, "Criar perfil de voz");
    } finally {
      setBusy(button, false);
    }
  }

  async function startVoice(event, { preview = false } = {}) {
    event.preventDefault();
    if (!state.project) return announce("Abra um projeto para gerar voz.", "warn");
    if (guardCaptionMutation()) return;
    const text = $("#editor-voice-text").value.trim();
    if (!text) return announce("Digite o texto da narração.", "warn");
    const engine = $("#editor-voice-engine")?.value || "auto";
    if (engine === "elevenlabs_cloud" && !hasElevenLabsCloud()) {
      return announce(
        "A conexão ElevenLabs cloud não está configurada ou está desativada no servidor.",
        "warn",
      );
    }
    const body = {
      expectedRevision: state.project.revision,
      text,
      engine,
      mode: preview ? "preview" : "final",
      language: $("#editor-voice-language")?.value || "pt",
      speed: clamp($("#editor-voice-speed")?.value, 0.5, 2, 1),
      timelineStart: clamp($("#editor-voice-start")?.value, 0, 86400, 0),
      addToTimeline: preview ? false : Boolean($("#editor-voice-add-timeline")?.checked),
      preset: $("#editor-voice-preset")?.value || "natural",
      intensity: clamp($("#editor-voice-intensity")?.value, 0, 1, 0.5),
    };
    const profile = $("#editor-voice-profile")?.value || "";
    const systemVoice = $("#editor-system-voice")?.value || "";
    if (engine === "auto" || engine === "chatterbox") {
      body.exaggeration = clamp($("#editor-voice-exaggeration")?.value, 0, 1, 0.5);
      body.cfgWeight = clamp($("#editor-voice-cfg-weight")?.value, 0, 1, 0.5);
      body.temperature = clamp($("#editor-voice-temperature")?.value, 0.05, 2, 0.8);
    }
    if (profile && (engine === "auto" || engine === "chatterbox")) {
      body.voiceProfileId = profile;
      body.engine = "chatterbox";
    }
    if (systemVoice && (body.engine === "auto" || body.engine === "system")) {
      body.systemVoice = systemVoice;
    }
    if (body.engine === "elevenlabs_cloud") {
      const providerVoiceId = $("#editor-voice-provider-id")?.value || "";
      const modelId = $("#editor-voice-model-id")?.value || "";
      const performanceDirection = $("#editor-voice-performance-direction")?.value.trim() || "";
      if (providerVoiceId) body.providerVoiceId = providerVoiceId;
      if (modelId) body.modelId = modelId;
      if (performanceDirection) body.performanceDirection = performanceDirection;
    }
    const button = preview ? $("#editor-voice-preview") : $("#editor-voice-generate");
    const otherButton = preview ? $("#editor-voice-generate") : $("#editor-voice-preview");
    try {
      setBusy(button, true, preview ? "Preparando prévia" : "Enfileirando");
      if (otherButton) otherButton.disabled = true;
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/voices`,
        { method: "POST", body },
      );
      await pollJob(payload.job);
    } catch (error) {
      await handleError(error, preview ? "Prévia de voz" : "Gerar voz");
    } finally {
      setBusy(button, false);
      updateProjectBoundControls();
    }
  }

  async function startCaptions(event) {
    event.preventDefault();
    if (!state.project) return announce("Abra um projeto para gerar legendas.", "warn");
    if (!state.capabilities?.captions?.offlineCpuAsr) {
      return announce("A transcrição offline em CPU não está disponível.", "warn");
    }
    const source = $("#editor-caption-source")?.value === "project" ? "project" : "asset";
    const body = {
      expectedRevision: state.project.revision,
      source,
      language: $("#editor-caption-language")?.value || "pt",
      timelineStart: source === "asset" ? number($("#editor-caption-start")?.value) : 0,
      replaceExisting: Boolean($("#editor-caption-replace")?.checked),
    };
    if (source === "asset") {
      const assetId = $("#editor-caption-asset")?.value || "";
      if (!assetId) return announce("Escolha um arquivo com áudio para transcrever.", "warn");
      body.assetId = assetId;
    }
    const button = $("#editor-caption-generate");
    try {
      setBusy(button, true, "Enfileirando");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/captions`,
        { method: "POST", body },
      );
      await pollJob(payload.job);
    } catch (error) {
      await handleError(error, "Gerar legendas");
    } finally {
      setBusy(button, false);
      syncCaptionSource();
    }
  }

  function assistantActionLabel(action) {
    const clip = action.clipId ? projectClip(action.clipId) : null;
    const clipName = clip?.label || clip?.clipId?.slice(0, 8) || "clipe";
    const descriptions = {
      rename_project: `Renomear projeto para “${action.name || ""}”`,
      trim_clip: `Cortar ${clipName}: ${formatTime(action.start)}–${formatTime(action.end)}`,
      move_clip: clip?.track === "video"
        ? `Mover ${clipName} para a posição ${number(action.order) + 1}`
        : `Mover ${clipName} para ${formatTime(action.start)}`,
      set_volume: `Volume de ${clipName}: ${Math.round(number(action.volume, 1) * 100)}%`,
      delete_clip: `Remover ${clipName} da timeline`,
      add_text: `Adicionar texto “${String(action.text || "").slice(0, 80)}”`,
    };
    return descriptions[action.type] || action.type;
  }

  function renderCopilotProposal() {
    const root = $("#editor-copilot-proposal");
    const proposal = state.pendingProposal;
    if (!root || !proposal) {
      root?.classList.add("hidden");
      return;
    }
    $("#editor-copilot-summary").textContent = proposal.summary || "Sugestão do copiloto";
    $("#editor-copilot-reply").textContent = proposal.reply || "";
    $("#editor-copilot-actions").innerHTML = (proposal.actions || [])
      .map((action) => `<li>${html(assistantActionLabel(action))}</li>`)
      .join("") || "<li>Nenhuma alteração proposta.</li>";
    $("#editor-copilot-apply").disabled = !(proposal.actions || []).length;
    root.classList.remove("hidden");
  }

  async function reviewCopilot(event) {
    event.preventDefault();
    if (!state.project) return;
    const instruction = $("#editor-copilot-instruction").value.trim();
    if (!instruction) return announce("Descreva o que o copiloto deve revisar.", "warn");
    const button = $("#editor-copilot-review");
    try {
      setBusy(button, true, "Consultando");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/assistant`,
        {
          method: "POST",
          body: {
            expectedRevision: state.project.revision,
            instruction,
            apply: false,
            model: $("#editor-copilot-model").value || undefined,
          },
        },
      );
      state.pendingProposal = payload.proposal;
      state.pendingInstruction = instruction;
      renderCopilotProposal();
      announce("Sugestão pronta para sua revisão. Nada foi alterado.", "ok");
    } catch (error) {
      await handleError(error, "Copiloto");
    } finally {
      setBusy(button, false);
    }
  }

  async function applyReviewedAction(action) {
    const projectId = state.project.projectId;
    if (action.type === "rename_project") {
      const payload = await request(`/projects/${editorPath(projectId)}`, {
        method: "PATCH",
        body: {
          expectedRevision: state.project.revision,
          name: String(action.name || "").trim(),
        },
      });
      setProject(payload.project);
      return;
    }
    if (action.type === "add_text") {
      const payload = await request(`/projects/${editorPath(projectId)}/clips`, {
        method: "POST",
        body: {
          expectedRevision: state.project.revision,
          track: "text",
          text: String(action.text || "").trim(),
          timelineStart: Math.max(0, number(action.start)),
          duration: Math.max(0.5, number(action.duration, 3)),
          label: "Texto do copiloto",
        },
      });
      setProject(payload.project);
      return;
    }
    const clip = projectClip(action.clipId);
    if (!clip) return;
    const clipPath = `/projects/${editorPath(projectId)}/clips/${editorPath(clip.clipId)}`;
    if (action.type === "delete_clip") {
      const payload = await request(clipPath, {
        method: "DELETE",
        body: { expectedRevision: state.project.revision },
      });
      setProject(payload.project);
      return;
    }
    const body = { expectedRevision: state.project.revision };
    if (action.type === "trim_clip") {
      if (action.start !== undefined) body.sourceStart = Math.max(0, number(action.start));
      if (action.end !== undefined) body.sourceEnd = Math.max(0.05, number(action.end, 0.05));
    } else if (action.type === "move_clip") {
      if (clip.track === "video") body.order = Math.max(0, Math.round(number(action.order)));
      else body.timelineStart = Math.max(0, number(action.start));
    } else if (action.type === "set_volume") {
      body.volume = Math.max(0, Math.min(4, number(action.volume, 1)));
    } else {
      return;
    }
    const payload = await request(clipPath, { method: "PATCH", body });
    setProject(payload.project);
  }

  async function applyCopilotProposal() {
    if (!state.project || !state.pendingProposal?.actions?.length) return;
    if (guardCaptionMutation()) return;
    const projectId = state.project.projectId;
    const actions = state.pendingProposal.actions;
    const button = $("#editor-copilot-apply");
    try {
      setBusy(button, true, "Aplicando");
      const payload = await request(
        `/projects/${editorPath(projectId)}/assistant/apply`,
        {
          method: "POST",
          body: {
            expectedRevision: state.project.revision,
            actions,
          },
        },
      );
      setProject(payload.project);
      state.pendingProposal = null;
      state.pendingInstruction = "";
      renderCopilotProposal();
      announce(`${actions.length} alteração(ões) revisada(s) aplicada(s).`, "ok");
    } catch (error) {
      await handleError(error, "Aplicar sugestão");
    } finally {
      setBusy(button, false);
    }
  }

  function showJob(job) {
    const panel = $("#editor-job-panel");
    if (!panel || !job) return;
    const progress = Math.max(0, Math.min(100, number(job.progress)));
    panel.classList.remove("hidden");
    $("#editor-job-title").textContent = ({
      voice: "Voz local",
      render: "Exportação",
      captions: "Legendas offline",
    })[job.kind] || "Processamento local";
    $("#editor-job-message").textContent = job.message || job.status || "Processando";
    $("#editor-job-percent").textContent = `${Math.round(progress)}%`;
    $("#editor-job-progress-bar").style.width = `${progress}%`;
    $("#editor-job-progress").setAttribute("aria-valuenow", String(Math.round(progress)));
    const cancel = $("#editor-job-cancel");
    cancel.disabled = TERMINAL_JOB_STATES.has(job.status) || job.status === "canceling";
    cancel.textContent = job.status === "canceling" ? "Cancelando" : "Cancelar";
  }

  function waitForPoll(milliseconds, signal) {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(resolve, milliseconds);
      signal?.addEventListener("abort", () => {
        window.clearTimeout(timer);
        reject(new DOMException("Cancelado", "AbortError"));
      }, { once: true });
    });
  }

  async function pollJob(initialJob) {
    const currentProjectId = state.project?.projectId || "";
    if (!initialJob?.projectId || initialJob.projectId !== currentProjectId) return initialJob;
    state.pollController?.abort();
    const controller = new AbortController();
    state.pollController = controller;
    state.activeJobId = initialJob.jobId;
    state.activeJobProjectId = initialJob.projectId;
    const captionJob = initialJob.kind === "captions";
    state.captionJobBusy = captionJob;
    if (captionJob) {
      setSuiteBusy(true);
      if (!TERMINAL_JOB_STATES.has(initialJob.status)) {
        announce("Legendas em processamento. O Editor ficará ocupado até o job terminar.", "warn");
      }
    } else {
      setSuiteBusy(false);
    }
    let job = initialJob;
    showJob(job);
    try {
      while (!TERMINAL_JOB_STATES.has(job.status)) {
        if (job.projectId !== state.project?.projectId) {
          controller.abort();
          return job;
        }
        await waitForPoll(1200, controller.signal);
        const payload = await request(`/jobs/${editorPath(job.jobId)}`, {
          signal: controller.signal,
        });
        job = payload.job;
        if (job.projectId !== state.project?.projectId) {
          controller.abort();
          return job;
        }
        showJob(job);
      }
      if (job.projectId !== state.project?.projectId) return job;
      if (job.status === "completed") {
        if (job.result?.project) setProject(job.result.project);
        else if (state.project?.projectId) await loadProject(state.project.projectId, { silent: true });
        if (job.kind === "captions") {
          highlightCaptionTrack(job.result?.captionClipIds || []);
          const captionCount = number(job.result?.captionCount);
          announce(
            job.message || `${captionCount} legenda(s) adicionada(s) à faixa de texto.`,
            "ok",
          );
        } else if (job.result?.asset) {
          previewAsset(job.result.asset.assetId);
          announce(job.message || "Voz pronta.", "ok");
        } else if (job.result?.export) {
          announce(job.message || "Exportação concluída.", "ok");
          renderExports();
        }
      } else {
        const message = job.error?.message || job.message || `Job ${job.status}.`;
        announce(message, job.status === "canceled" ? "warn" : "bad");
      }
      return job;
    } catch (error) {
      if (error?.name !== "AbortError") await handleError(error, "Acompanhar job");
      return job;
    } finally {
      if (state.pollController === controller) {
        state.pollController = null;
        state.activeJobId = "";
        state.activeJobProjectId = "";
        if (captionJob) {
          state.captionJobBusy = false;
          setSuiteBusy(false);
        }
      }
    }
  }

  async function resumeActiveJob() {
    if (!state.project?.projectId || state.activeJobId) return;
    try {
      const payload = await request(
        `/jobs?projectId=${editorPath(state.project.projectId)}&limit=10`,
      );
      const active = (payload.items || []).find((job) => !TERMINAL_JOB_STATES.has(job.status));
      if (active) pollJob(active);
    } catch (_error) {
      // Falha ao recuperar jobs não impede a edição do projeto.
    }
  }

  async function cancelActiveJob() {
    if (!state.activeJobId) return;
    const jobId = state.activeJobId;
    state.pollController?.abort();
    state.pollController = null;
    try {
      const payload = await request(`/jobs/${editorPath(jobId)}/cancel`, { method: "POST" });
      showJob(payload.job);
      await pollJob(payload.job);
    } catch (error) {
      await handleError(error, "Cancelar job");
    }
  }

  function renderExports() {
    const root = $("#editor-export-list");
    if (!root) return;
    const exports = state.project?.exports || [];
    if (!exports.length) {
      root.innerHTML = '<div class="editor-empty">Nenhuma exportação neste projeto.</div>';
      return;
    }
    root.innerHTML = exports.map((item) => {
      const viewUrl = resolveContentUrl(item.url);
      const downloadUrl = resolveContentUrl(item.url, true);
      return `
        <article class="editor-export-item">
          <strong title="${html(item.filename)}">${html(item.filename)}</strong>
          <small>${html(formatTime(item.duration))} · ${html(formatBytes(item.size))} · ${html(String(item.encoder || "").toUpperCase())}</small>
          <div class="editor-export-actions">
            <a class="btn secondary" href="${html(viewUrl)}" target="_blank" rel="noopener">Assistir</a>
            <a class="btn primary" href="${html(downloadUrl)}" download>Baixar</a>
          </div>
        </article>
      `;
    }).join("");
  }

  async function startExport(event) {
    event.preventDefault();
    if (!state.project) return announce("Abra um projeto para exportar.", "warn");
    if (guardCaptionMutation()) return;
    if (!(state.project.clips || []).some((clip) => clip.track === "video")) {
      return announce("Adicione ao menos um clipe à trilha de vídeo antes de exportar.", "warn");
    }
    const encoder = $("#editor-export-encoder").value;
    if (encoder === "nvenc" && !state.capabilities?.editor?.nvenc) {
      return announce("NVENC não está disponível; use CPU.", "warn");
    }
    const button = $("#editor-export-submit");
    try {
      setBusy(button, true, "Enfileirando");
      const payload = await request(
        `/projects/${editorPath(state.project.projectId)}/renders`,
        {
          method: "POST",
          body: {
            expectedRevision: state.project.revision,
            profile: $("#editor-export-profile").value,
            encoder,
          },
        },
      );
      await pollJob(payload.job);
    } catch (error) {
      await handleError(error, "Exportar");
    } finally {
      setBusy(button, false);
    }
  }

  function downloadFilename(response, fallback) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    let value = utf8Match?.[1] || plainMatch?.[1] || fallback;
    try {
      value = decodeURIComponent(value);
    } catch (_error) {
      // Mantém o nome legível fornecido pelo servidor quando não for URL encoded.
    }
    return String(value || fallback).split(/[\\/]/).pop().replace(/[\r\n]/g, "") || fallback;
  }

  async function downloadCapCutLocalHandoff(event) {
    event.preventDefault();
    if (!state.project) {
      return announce("Abra um projeto para criar o pacote do CapCut Local.", "warn");
    }
    if (guardCaptionMutation()) return;
    const requestedMode = $("#editor-capcut-handoff-mode")?.value || "quick";
    const mode = requestedMode === "editable" ? "editable" : "quick";
    const button = $("#editor-capcut-handoff-submit");
    let response;
    try {
      setBusy(button, true, "Preparando pacote");
      response = await fetch(
        `${state.apiRoot}/projects/${editorPath(state.project.projectId)}/handoffs/capcut-local?mode=${mode}`,
        {
          method: "GET",
          headers: { Accept: "application/zip, application/json" },
        },
      );
      if (!response.ok) {
        const contentType = response.headers.get("Content-Type") || "";
        let message = response.statusText || "Falha ao criar o pacote.";
        if (contentType.includes("application/json")) {
          const payload = await response.json().catch(() => null);
          const validation = Array.isArray(payload?.detail)
            ? payload.detail.map((item) => item.msg).filter(Boolean).join("; ")
            : "";
          message = payload?.error?.message || validation || payload?.detail || message;
        } else {
          const text = await response.text().catch(() => "");
          if (text) message = text.slice(0, 400);
        }
        throw new EditorApiError(message, { status: response.status });
      }
      const blob = await response.blob();
      if (!blob.size) throw new EditorApiError("O servidor retornou um pacote vazio.");
      const filename = downloadFilename(
        response,
        `capcut-local-${state.project.projectId}-${mode}.zip`,
      );
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      link.hidden = true;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 5000);
      announce(`Pacote “${filename}” pronto para o CapCut Local.`, "ok");
    } catch (error) {
      await handleError(error, "Pacote do CapCut Local");
    } finally {
      setBusy(button, false);
      updateProjectBoundControls();
    }
  }

  function bindVoiceEvents() {
    $("#editor-voice-form")?.addEventListener("submit", startVoice);
    $("#editor-voice-preview")?.addEventListener("click", (event) => {
      startVoice(event, { preview: true });
    });
    $("#editor-voice-profile-form")?.addEventListener("submit", createVoiceProfile);
    $("#editor-caption-form")?.addEventListener("submit", startCaptions);
    $("#editor-caption-source")?.addEventListener("change", syncCaptionSource);
    $("#editor-caption-asset")?.addEventListener("change", syncCaptionSource);
    $("#editor-voice-profile")?.addEventListener("change", (event) => {
      if (event.target.value) {
        $("#editor-voice-engine").value = "chatterbox";
        syncVoiceEngineControls();
        updateProjectBoundControls();
      }
    });
    $("#editor-voice-engine")?.addEventListener("change", () => {
      syncVoiceEngineControls();
      updateProjectBoundControls();
    });
    $("#editor-voice-intensity")?.addEventListener("input", syncVoiceIntensityOutput);
  }

  function bindCopilotEvents() {
    $("#editor-copilot-form")?.addEventListener("submit", reviewCopilot);
    $("#editor-copilot-apply")?.addEventListener("click", applyCopilotProposal);
  }

  function bindExportEvents() {
    $("#editor-export-form")?.addEventListener("submit", startExport);
    $("#editor-capcut-handoff-form")?.addEventListener("submit", downloadCapCutLocalHandoff);
    $("#editor-job-cancel")?.addEventListener("click", cancelActiveJob);
  }

  function bindBaseEvents() {
    $("#editor-project-new-toggle")?.addEventListener("click", openProjectCreate);
    $("#editor-project-new-cancel")?.addEventListener("click", () => closeProjectCreate({ restoreFocus: true }));
    $("#editor-project-create-form")?.addEventListener("submit", createProject);
    $("#editor-project-refresh")?.addEventListener("click", () => loadProjects({
      preferredId: state.project?.projectId || "",
    }));
    $("#editor-project-rename")?.addEventListener("click", renameProject);
    $("#editor-project-select")?.addEventListener("change", (event) => loadProject(event.target.value));
    $("#editor-upload-files")?.addEventListener("change", updateUploadButton);
    $("#editor-upload-form")?.addEventListener("submit", uploadAssets);
    $$("[data-editor-kind]").forEach((button) => {
      button.addEventListener("click", () => selectAssetKind(button));
    });
  }

  function init(options = {}) {
    if (state.initialized) return;
    const configuredRoot = String(options.apiBase || "/api/editor").replace(/\/+$/, "");
    state.apiRoot = configuredRoot.endsWith("/api/editor")
      ? configuredRoot
      : `${configuredRoot}/api/editor`;
    state.studioBase = state.apiRoot.slice(0, -"/api/editor".length);
    state.notify = typeof options.notify === "function" ? options.notify : null;
    state.initialized = true;
    bindBaseEvents();
    bindTimelineEvents();
    bindVoiceEvents();
    bindCopilotEvents();
    bindExportEvents();
    syncVoiceEngineControls();
    syncVoiceIntensityOutput();
    renderProject();
    renderCapabilityStatus();
  }

  async function activate() {
    if (!state.initialized) init();
    state.active = true;
    if (!state.capabilities) await loadCapabilities();
    await loadProjects({ preferredId: state.project?.projectId || "" });
  }

  window.MaestroEditorSuite = { init, activate };
})();
