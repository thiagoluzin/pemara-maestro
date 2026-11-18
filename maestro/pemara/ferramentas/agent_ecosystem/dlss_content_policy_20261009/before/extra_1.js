function studioApiBase() {
  return "/api/studio";
}

const API = {
  maestro: "/api/maestro",
  dashboard: "/api/dashboard",
  org: "/api/org",
  studio: studioApiBase(),
  cadastro: "/api/cadastro",
  doc: "/api/doc",
  historico: "/api/historico",
  localAi: "/api/local-ai",
};

const MAESTRO_FRONTEND_BUILD = "20261008-ltx-removed-v1";
const MAESTRO_BUILD_MANIFEST = "/assets/maestro-build.json";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const DICTATION_MAX_BYTES = 16 * 1024 * 1024;
const DICTATION_MAX_RECORDING_MS = 120000;
const DICTATION_MEDIA_TYPES = new Set([
  "audio/aac", "audio/flac", "audio/m4a", "audio/mp4", "audio/mpeg",
  "audio/ogg", "audio/opus", "audio/wav", "audio/webm", "audio/x-m4a",
  "audio/x-wav", "video/mp4", "video/webm",
]);
const voiceInputState = { active: null, sequence: 0 };

const state = {
  health: null,
  qwen: null,
  qwenAutoRelease: null,
  qwenLoading: false,
  qwenSettingsSaving: false,
  genStatus: null,
  videoEngines: [],
  selectedVideoEngineId: "",
  orgTimer: null,
  films: {
    projects: [],
    activeProjectId: "",
    activeTakeId: "",
    view: "",
    takes: [],
    pollingJobs: {},
    terminalJobs: {},
    productionQueueSignature: "",
    productionQueueData: null,
    liveRefreshInFlight: false,
    projectsLoadPromise: null,
    projectDataLoading: false,
    projectDataError: "",
    projectLoadSequence: 0,
    takeUpdateSequence: 0,
    videoSoundProviders: [],
    videoSoundProviderId: "",
    videoSoundJobs: {},
    assemblyJob: null,
    finalViewedFingerprint: "",
    batchInFlight: { production: false, upscale: false },
  },
  assets: {
    kind: "",
    page: 1,
    pageSize: 48,
    total: 0,
  },
  hyperframes: {
    startAttempted: false,
    pollTimer: null,
  },
};

const GEN_MODE_COPY = {
  image: {
    kicker: "IMAGEM",
    title: "Crie uma imagem",
    help: "Descreva o que você quer ver. O Studio escolhe o motor recomendado.",
    promptLabel: "Descreva a imagem",
    placeholder: "Ex.: rua noturna cinematográfica, luz refletida no asfalto molhado",
    submit: "Criar imagem",
  },
  edit: {
    kicker: "EDIÇÃO",
    title: "Edite uma imagem",
    help: "Envie a imagem original e descreva somente a alteração desejada.",
    promptLabel: "O que deve mudar",
    placeholder: "Ex.: trocar apenas o fundo, preservando produto, cores e proporções",
    submit: "Editar imagem",
  },
  video: {
    kicker: "VÍDEO",
    title: "Anime uma foto",
    help: "Escolha uma imagem inicial e descreva o movimento desejado.",
    promptLabel: "Como a foto deve se mover",
    placeholder: "Descreva a ação, o movimento da câmera e a evolução da cena.",
    submit: "Animar foto",
  },
  text_video: {
    kicker: "VÍDEO",
    title: "Crie um vídeo a partir de texto",
    help: "Nenhuma imagem é necessária. Você escolhe MiniMax H3 antes de gerar.",
    promptLabel: "Descreva o vídeo",
    placeholder: "Ex.: uma raposa vermelha atravessa uma clareira nevada ao nascer do sol, plano cinematográfico",
    submit: "Criar vídeo",
  },
  marketing_card: {
    kicker: "CARD",
    title: "Crie um card com a foto real",
    help: "Envie a foto do produto e informe o texto comercial exato.",
    promptLabel: "Texto e direção do card",
    placeholder: "Produto, preço, parcelamento e chamada exatamente como devem aparecer",
    submit: "Criar card",
  },
  music: {
    kicker: "MÚSICA",
    title: "Crie uma música",
    help: "Conte a ideia da música. A IA cria a letra e o áudio em sequência.",
    promptLabel: "Descreva a música que quer ouvir",
    placeholder: "Ex.: rock pesado com voz masculina em português sobre vencer o medo, com refrão marcante",
    submit: "Criar música",
  },
  sfx: {
    kicker: "SFX",
    title: "Crie um efeito sonoro",
    help: "Descreva o som, o ambiente e sua evolução no tempo.",
    promptLabel: "Descrição do efeito",
    placeholder: "Ex.: pulso elétrico curto que cresce e termina em impacto metálico",
    submit: "Criar SFX",
  },
};

function friendlyModelName(name) {
  const labels = {
    "minimax_h3_fl2va_pruned_int8_convrot.safetensors": "MiniMax H3 FL2VA · 720p · vídeo + áudio",
  };
  return labels[name] || name;
}

function selectableVideoModels(models) {
  return [...new Set((models || []).filter(Boolean))];
}

const GEN_PRESETS = {
  minimax_h3_720p_take_6s: {
    mode: "video", model: "minimax_h3_fl2va_pruned_int8_convrot.safetensors", width: 1280, height: 720,
    duration: 6, frames: 141, fps: 24, steps: 20, guidance: 1, prompt: "",
    negative: "European Portuguese, Portugal accent, pt-PT, unstable final pose, malformed anatomy, duplicated subjects, subtitles, watermark, UI",
  },
  minimax_h3_720p_take_10s: {
    mode: "video", model: "minimax_h3_fl2va_pruned_int8_convrot.safetensors", width: 1280, height: 720,
    duration: 10, frames: 243, fps: 24, steps: 20, guidance: 1, prompt: "",
    negative: "European Portuguese, Portugal accent, pt-PT, unstable final pose, malformed anatomy, duplicated subjects, subtitles, watermark, UI",
  },
};

const H3_QUALITY_PROFILES = {
  h3_draft: { width: 1024, height: 576, verticalWidth: 576, verticalHeight: 1024, steps: 6, audio: false },
  h3_production: { width: 1088, height: 608, verticalWidth: 608, verticalHeight: 1088, steps: 10, audio: false },
  h3_hero: { width: 1344, height: 768, verticalWidth: 768, verticalHeight: 1344, steps: 12, audio: false },
  h3_master: { width: 1344, height: 768, verticalWidth: 768, verticalHeight: 1344, steps: 20, audio: false },
  h3_master_fbc20: { width: 1344, height: 768, verticalWidth: 768, verticalHeight: 1344, steps: 20, audio: false },
  h3_master_spectrum20: { width: 1344, height: 768, verticalWidth: 768, verticalHeight: 1344, steps: 20, audio: false },
};

const FAST_H3_VARIANT = "fasth3_8step_v2";

function serviceState(service) {
  if (service.online) {
    return { label: "online", className: "ok" };
  }
  return { label: "off", className: "bad" };
}

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function toast(message) {
  const box = $("#toast");
  box.textContent = message;
  box.classList.add("show");
  clearTimeout(box._timer);
  box._timer = setTimeout(() => box.classList.remove("show"), 3200);
}

async function fetchJson(url, options = {}) {
  let response;
  try {
    response = await fetch(url, { cache: "no-store", ...options });
  } catch (error) {
    throw new Error(`Falha ao acessar ${url}`);
  }
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { raw: text };
  }
  if (!response.ok) {
    throw new Error(payload.error?.message || payload.erro || payload.detail || response.statusText || "Falha na requisicao");
  }
  return payload;
}

async function fetchFilmMetadata(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);
  try {
    return await fetchJson(url, { signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("O serviço de takes demorou para responder. Tentaremos novamente automaticamente.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchFilmDirectorRequest(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetchJson(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("O envio demorou para responder. Seu texto foi preservado. Atualize os takes para conferir se o pedido foi registrado antes de reenviar.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function voiceInputLabel(textarea) {
  return textarea.dataset.voiceLabel
    || document.querySelector(`label[for="${CSS.escape(textarea.id || "")}"]`)?.textContent?.trim()
    || "este campo";
}

function voiceInputStatus(toolbar, message, tone = "") {
  const status = toolbar.querySelector("[data-voice-status]");
  if (status) status.textContent = message;
  toolbar.dataset.tone = tone;
}

function canRecordVoice() {
  return Boolean(
    window.isSecureContext
    && navigator.mediaDevices?.getUserMedia
    && window.MediaRecorder,
  );
}

function refreshVoiceInputControls() {
  const active = voiceInputState.active;
  $$('[data-voice-tools]').forEach((toolbar) => {
    const textarea = toolbar.previousElementSibling;
    const recordButton = toolbar.querySelector("[data-voice-record]");
    const uploadButton = toolbar.querySelector("[data-voice-upload]");
    const isCurrent = active?.toolbar === toolbar;
    const isRecording = isCurrent && active?.phase === "recording";
    const blocked = Boolean(textarea?.disabled || (active && !isRecording));
    recordButton.disabled = blocked || !canRecordVoice();
    uploadButton.disabled = blocked;
    recordButton.textContent = isRecording ? "Parar" : "Falar";
    recordButton.setAttribute("aria-pressed", isRecording ? "true" : "false");
    recordButton.setAttribute(
      "aria-label",
      isRecording
        ? `Parar gravação para ${voiceInputLabel(textarea)}`
        : `Gravar áudio para ${voiceInputLabel(textarea)}`,
    );
    toolbar.setAttribute("aria-busy", isCurrent && active?.phase === "processing" ? "true" : "false");
  });
}

function voiceAudioContentType(audio) {
  const declared = String(audio?.type || "").split(";", 1)[0].trim().toLowerCase();
  if (DICTATION_MEDIA_TYPES.has(declared)) return audio.type || declared;
  const extension = String(audio?.name || "").toLowerCase().match(/\.([a-z0-9]+)$/)?.[1] || "";
  return ({
    aac: "audio/aac",
    flac: "audio/flac",
    m4a: "audio/mp4",
    mp3: "audio/mpeg",
    mp4: "audio/mp4",
    ogg: "audio/ogg",
    opus: "audio/opus",
    wav: "audio/wav",
    webm: "audio/webm",
  })[extension] || "";
}

function insertVoiceTranscription(textarea, transcription) {
  const clean = String(transcription || "").replace(/\s+/g, " ").trim();
  if (!clean) return { inserted: false, truncated: false };
  const start = Number.isInteger(textarea.selectionStart) ? textarea.selectionStart : textarea.value.length;
  const end = Number.isInteger(textarea.selectionEnd) ? textarea.selectionEnd : start;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  const prefix = before && !/\s$/.test(before) ? " " : "";
  const suffix = after && !/^\s/.test(after) ? " " : "";
  let insertion = `${prefix}${clean}${suffix}`;
  let truncated = false;
  if (textarea.maxLength > 0) {
    const available = Math.max(0, textarea.maxLength - (textarea.value.length - (end - start)));
    if (insertion.length > available) {
      insertion = insertion.slice(0, available).trimEnd();
      truncated = true;
    }
  }
  if (!insertion) return { inserted: false, truncated };
  textarea.setRangeText(insertion, start, end, "end");
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
  textarea.dispatchEvent(new Event("change", { bubbles: true }));
  textarea.focus({ preventScroll: true });
  return { inserted: true, truncated };
}

async function transcribeVoiceAudio(session, audio) {
  const { textarea, toolbar } = session;
  session.phase = "processing";
  const timer = toolbar.querySelector("[data-voice-timer]");
  if (timer) timer.textContent = "";
  refreshVoiceInputControls();
  if (!audio || audio.size < 256) {
    throw new Error("O áudio ficou vazio. Grave novamente mais perto do microfone.");
  }
  if (audio.size > DICTATION_MAX_BYTES) {
    throw new Error("O áudio ultrapassou o limite de 16 MB.");
  }
  const contentType = voiceAudioContentType(audio);
  if (!contentType) {
    throw new Error("Formato de áudio não compatível. Use WAV, MP3, M4A, OGG, Opus, WebM ou MP4.");
  }
  voiceInputStatus(toolbar, "Transcrevendo localmente com Faster Whisper…", "working");
  const payload = await fetchJson(`${API.studio}/api/dictation/transcriptions?language=pt`, {
    method: "POST",
    headers: { "Content-Type": contentType },
    body: audio,
  });
  const result = insertVoiceTranscription(textarea, payload.transcription?.text);
  if (!result.inserted) throw new Error("A transcrição não retornou texto utilizável.");
  voiceInputStatus(
    toolbar,
    result.truncated
      ? "Texto inserido até o limite deste campo."
      : "Texto transcrito e inserido. O áudio não foi guardado.",
    result.truncated ? "warn" : "ok",
  );
  toast("Ditado inserido no campo");
}

function releaseVoiceStream(session) {
  session?.stream?.getTracks?.().forEach((track) => track.stop());
  clearTimeout(session?.stopTimer);
  clearInterval(session?.elapsedTimer);
}

async function finishVoiceSession(session, audio) {
  try {
    await transcribeVoiceAudio(session, audio);
  } catch (error) {
    voiceInputStatus(session.toolbar, error.message || "Não foi possível transcrever o áudio.", "error");
    toast(error.message || "Não foi possível transcrever o áudio");
  } finally {
    releaseVoiceStream(session);
    if (voiceInputState.active === session) voiceInputState.active = null;
    refreshVoiceInputControls();
  }
}

function stopVoiceRecording(session, automatic = false) {
  if (!session || session.phase !== "recording") return;
  session.phase = "stopping";
  voiceInputStatus(
    session.toolbar,
    automatic ? "Limite de 120 segundos atingido. Preparando transcrição…" : "Preparando transcrição…",
    "working",
  );
  releaseVoiceStream(session);
  refreshVoiceInputControls();
  if (session.recorder.state !== "inactive") session.recorder.stop();
}

function preferredVoiceRecordingType() {
  return [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ].find((type) => MediaRecorder.isTypeSupported?.(type)) || "";
}

async function startVoiceRecording(textarea, toolbar) {
  if (voiceInputState.active) return;
  voiceInputStatus(toolbar, "Solicitando acesso ao microfone…", "working");
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    });
    const mimeType = preferredVoiceRecordingType();
    const recorder = new MediaRecorder(
      stream,
      mimeType ? { mimeType, audioBitsPerSecond: 64000 } : { audioBitsPerSecond: 64000 },
    );
    const session = {
      textarea,
      toolbar,
      stream,
      recorder,
      chunks: [],
      phase: "recording",
      startedAt: Date.now(),
      stopTimer: null,
      elapsedTimer: null,
    };
    voiceInputState.active = session;
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) session.chunks.push(event.data);
    });
    recorder.addEventListener("error", () => {
      voiceInputStatus(toolbar, "O navegador interrompeu a gravação.", "error");
    });
    recorder.addEventListener("stop", () => {
      const audio = new Blob(session.chunks, { type: recorder.mimeType || mimeType || "audio/webm" });
      void finishVoiceSession(session, audio);
    }, { once: true });
    recorder.start(250);
    session.stopTimer = setTimeout(() => stopVoiceRecording(session, true), DICTATION_MAX_RECORDING_MS);
    session.elapsedTimer = setInterval(() => {
      const timer = toolbar.querySelector("[data-voice-timer]");
      if (timer) timer.textContent = `${Math.min(120, Math.floor((Date.now() - session.startedAt) / 1000))} s`;
    }, 1000);
    voiceInputStatus(toolbar, "Gravando. Toque em Parar quando terminar.", "recording");
    refreshVoiceInputControls();
  } catch (error) {
    stream?.getTracks?.().forEach((track) => track.stop());
    const denied = error?.name === "NotAllowedError" || error?.name === "SecurityError";
    voiceInputStatus(
      toolbar,
      denied
        ? "Microfone não autorizado. Toque em Falar para tentar novamente ou use Enviar áudio."
        : "Não foi possível abrir o microfone. Use Enviar áudio.",
      "error",
    );
    refreshVoiceInputControls();
  }
}

async function uploadVoiceFile(textarea, toolbar, file) {
  if (!file || voiceInputState.active) return;
  const session = { textarea, toolbar, phase: "processing" };
  voiceInputState.active = session;
  refreshVoiceInputControls();
  await finishVoiceSession(session, file);
}

function enhanceVoiceInputs(root = document) {
  const inputs = [
    ...(root.matches?.("textarea[data-voice-input]") ? [root] : []),
    ...(root.querySelectorAll ? root.querySelectorAll("textarea[data-voice-input]") : []),
  ];
  inputs.forEach((textarea) => {
    if (textarea.dataset.voiceReady === "true") return;
    textarea.dataset.voiceReady = "true";
    const label = voiceInputLabel(textarea);
    const statusId = `voice-input-status-${++voiceInputState.sequence}`;
    const toolbar = document.createElement("div");
    toolbar.className = "voice-input-tools";
    toolbar.dataset.voiceTools = "";
    toolbar.setAttribute("role", "group");
    toolbar.setAttribute("aria-label", `Entrada por áudio para ${label}`);

    const recordButton = document.createElement("button");
    recordButton.className = "voice-input-action voice-input-record";
    recordButton.type = "button";
    recordButton.dataset.voiceRecord = "";
    recordButton.textContent = "Falar";

    const uploadButton = document.createElement("button");
    uploadButton.className = "voice-input-action";
    uploadButton.type = "button";
    uploadButton.dataset.voiceUpload = "";
    uploadButton.textContent = "Enviar áudio";
    uploadButton.setAttribute("aria-label", `Enviar arquivo de áudio para ${label}`);

    const fileInput = document.createElement("input");
    fileInput.className = "sr-only";
    fileInput.type = "file";
    fileInput.accept = "audio/*,video/mp4,video/webm";
    fileInput.tabIndex = -1;
    fileInput.dataset.voiceFile = "";
    fileInput.setAttribute("aria-hidden", "true");

    const status = document.createElement("span");
    status.className = "voice-input-status";
    status.id = statusId;
    status.dataset.voiceStatus = "";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.textContent = canRecordVoice()
      ? "Ditado local em português. O áudio não é guardado."
      : "Gravação indisponível aqui; use Enviar áudio.";

    const timer = document.createElement("span");
    timer.className = "voice-input-timer";
    timer.dataset.voiceTimer = "";
    timer.setAttribute("aria-hidden", "true");

    toolbar.append(recordButton, uploadButton, fileInput, status, timer);
    textarea.insertAdjacentElement("afterend", toolbar);
    textarea.setAttribute(
      "aria-describedby",
      [textarea.getAttribute("aria-describedby"), statusId].filter(Boolean).join(" "),
    );

    recordButton.addEventListener("click", () => {
      const active = voiceInputState.active;
      if (active?.toolbar === toolbar && active.phase === "recording") {
        stopVoiceRecording(active);
      } else if (!active) {
        void startVoiceRecording(textarea, toolbar);
      }
    });
    uploadButton.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", () => {
      const [file] = fileInput.files || [];
      fileInput.value = "";
      if (file) void uploadVoiceFile(textarea, toolbar, file);
    });
  });
  refreshVoiceInputControls();
}

function fileNameFromResponse(response, fallback) {
  const header = response.headers.get("Content-Disposition") || "";
  const match = header.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)["']?/i);
  return match ? decodeURIComponent(match[1]) : fallback;
}

async function downloadResponse(response, fallbackName) {
  if (!response.ok) {
    let err = "Falha no processamento";
    try {
      const data = await response.json();
      err = data.erro || data.detail || err;
    } catch {}
    throw new Error(err);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileNameFromResponse(response, fallbackName);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function setBusy(button, busy, label) {
  if (!button) return;
  button.setAttribute("aria-busy", busy ? "true" : "false");
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = label || "Processando";
    button.disabled = true;
  } else {
    button.textContent = button.dataset.label || button.textContent;
    button.disabled = false;
  }
}

function switchSection(name, { focusHeading = false } = {}) {
  $$(".section").forEach((section) => section.classList.toggle("active", section.id === `section-${name}`));
  $$(".nav-link[data-section]").forEach((button) => {
    const active = button.dataset.section === name;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  const activeNavButton = $(`.nav-link[data-section="${name}"]`);
  const navList = $(".nav-list");
  if (activeNavButton && navList && navList.scrollWidth > navList.clientWidth + 1) {
    window.requestAnimationFrame(() => activeNavButton.scrollIntoView({ block: "nearest", inline: "center" }));
  }
  document.body.classList.toggle("editor-suite-active", name === "studio");
  const active = $(`#section-${name}`);
  const heading = $("#view-title");
  heading.textContent = active?.dataset.title || "Maestro";
  window.scrollTo({ top: 0, behavior: "auto" });
  if (focusHeading) window.requestAnimationFrame(() => heading.focus({ preventScroll: true }));

  if (name === "gen") loadGenStatus();
  if (name === "cad") loadCad();
  if (name === "hist") loadHist();
  if (name === "org") loadOrgModels();
  if (name === "films") loadFilmProjects();
  if (name === "studio") void window.MaestroEditorSuite?.activate();
  if (name === "hyperframes") void loadHyperFramesStatus({ autoStart: true });
}

async function openTool(name, port) {
  const host = window.location.hostname || "127.0.0.1";
  const remote = host.includes("pemaratech.com.br");
  if (remote) {
    if (name === "hyperframes") {
      window.open("https://maestro.pemaratech.com.br:8443/", "_blank", "noopener");
      return;
    }
    const publicTools = new Set(["comfy", "sprunki", "perplexica", "hyperframes"]);
    if (publicTools.has(name)) {
      const popup = window.open("about:blank", "_blank");
      if (!popup) {
        toast("O navegador bloqueou a nova janela. Permita pop-ups para o Maestro.");
        return;
      }
      popup.opener = null;
      try {
        const data = await fetchJson(`/api/maestro/tool-link?tool=${encodeURIComponent(name)}`);
        popup.location.replace(data.url);
      } catch (error) {
        popup.close();
        toast(error.message || "Nao foi possivel abrir a ferramenta.");
      }
      return;
    }
    const section = { ollama: "gen", studio: "studio", dashboard: "home" }[name] || "home";
    switchSection(section);
    toast("Este servico e operado dentro do Maestro e nao expoe uma porta publica.");
    return;
  }
  const target = `http://${host}:${port}`;
  window.open(target, "_blank", "noopener");
}

function hyperFramesRenderLabel(status) {
  return {
    queued: "na fila",
    checking: "validando",
    rendering: "renderizando",
    ready_pending_human_qc: "pronto, aguardando QC humano",
    error: "erro",
  }[status] || "aguardando";
}

function renderHyperFramesStatus(data) {
  const online = Boolean(data?.online);
  const installed = Boolean(data?.installed);
  const health = $("#hyperframes-health");
  if (health) health.dataset.state = online ? "online" : "offline";
  $("#hyperframes-health-label").textContent = online
    ? "online"
    : installed ? "offline" : "não instalado";
  $("#hyperframes-version").textContent = data?.version ? `v${data.version}` : "--";
  $("#hyperframes-project").textContent = data?.project || "--";
  $("#hyperframes-origin").textContent = `${data?.bind || "127.0.0.1"}:${data?.port || 8032}`;

  const render = data?.render || {};
  const renderStatus = render.status || "";
  const active = ["queued", "checking", "rendering"].includes(renderStatus);
  const progress = Math.max(0, Math.min(100, Number(render.progress || 0)));
  $("#hyperframes-render-state").textContent = hyperFramesRenderLabel(renderStatus);
  $("#hyperframes-progress").hidden = !renderStatus;
  $("#hyperframes-progress-label").textContent = render.message || hyperFramesRenderLabel(renderStatus);
  $("#hyperframes-progress-percent").textContent = `${progress}%`;
  setWidth("#hyperframes-progress-bar", progress);
  $("#hyperframes-render").disabled = active || !installed;
  $("#hyperframes-download").disabled = !data?.output?.available;

  clearTimeout(state.hyperframes.pollTimer);
  if (active) {
    state.hyperframes.pollTimer = setTimeout(() => loadHyperFramesStatus(), 2200);
  }
}

async function loadHyperFramesStatus({ autoStart = false } = {}) {
  try {
    let data = await fetchJson(`${API.studio}/api/hyperframes/status`);
    if (
      autoStart
      && data.installed
      && !data.online
      && !state.hyperframes.startAttempted
    ) {
      state.hyperframes.startAttempted = true;
      try {
        data = await fetchJson(`${API.studio}/api/hyperframes/start`, { method: "POST" });
      } catch (error) {
        toast(error.message);
      }
    }
    if (data.online) state.hyperframes.startAttempted = false;
    renderHyperFramesStatus(data);
    return data;
  } catch (error) {
    renderHyperFramesStatus({ installed: false, online: false, render: {} });
    toast(error.message);
    return null;
  }
}

async function hyperFramesAccessUrl() {
  const host = window.location.hostname || "127.0.0.1";
  if (host.includes("pemaratech.com.br")) {
    return "https://maestro.pemaratech.com.br:8443/";
  }
  return `http://${host}:8032/`;
}

async function embedHyperFrames() {
  const button = $("#hyperframes-embed");
  setBusy(button, true, "Abrindo editor");
  try {
    const url = await hyperFramesAccessUrl();
    const panel = $("#hyperframes-studio-panel");
    const frame = $("#hyperframes-frame");
    panel.hidden = false;
    frame.src = url;
    panel.scrollIntoView({ block: "start", behavior: "smooth" });
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function closeHyperFrames() {
  const panel = $("#hyperframes-studio-panel");
  const frame = $("#hyperframes-frame");
  frame.src = "about:blank";
  panel.hidden = true;
}

async function startHyperFramesRender() {
  const button = $("#hyperframes-render");
  setBusy(button, true, "Reservando render");
  try {
    await fetchJson(`${API.studio}/api/hyperframes/render`, { method: "POST" });
    toast("Render HyperFrames iniciado.");
    await loadHyperFramesStatus();
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

async function downloadHyperFramesPilot() {
  const button = $("#hyperframes-download");
  setBusy(button, true, "Baixando MP4");
  try {
    const response = await fetch(`${API.studio}/api/hyperframes/pilot-output`, { cache: "no-store" });
    await downloadResponse(response, "maestro-hyperframes-pilot.mp4");
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function setWidth(id, value) {
  const node = $(id);
  if (node) node.style.width = `${Math.max(0, Math.min(100, Number(value) || 0))}%`;
}

function hasTelemetryValue(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

function renderGpuUnavailable(label = "Sensores NVIDIA indisponíveis") {
  $("#gpu-load").textContent = "--";
  $("#gpu-load-top").textContent = "indisponível";
  $("#gpu-vram").textContent = "-- / -- GB";
  $("#gpu-vram-top").textContent = "--";
  $("#gpu-extra").textContent = label;
  $("#gpu-temp").textContent = "-- C / Fan --";
  setWidth("#bar-gpu-load", 0);
  setWidth("#bar-gpu-vram", 0);
}

function renderSystemUnavailable() {
  $("#cpu-load").textContent = "--";
  $("#cpu-extra").textContent = "Sensor indisponível";
  $("#ram-load").textContent = "--";
  $("#ram-extra").textContent = "Sensor indisponível";
  setWidth("#bar-cpu-load", 0);
  setWidth("#bar-ram-load", 0);
}

async function loadTelemetry() {
  try {
    const data = await fetchJson(`${API.dashboard}/snapshot`);
    const gpu = data.gpu || {};
    const sys = data.sistema || {};

    const gpuAvailable = data.gpu_disponivel !== false
      && !gpu.erro
      && hasTelemetryValue(gpu.load)
      && hasTelemetryValue(gpu.vram_u)
      && hasTelemetryValue(gpu.vram_t)
      && Number(gpu.vram_t) > 0;
    if (gpuAvailable) {
      const power = hasTelemetryValue(gpu.power_w) ? `${gpu.power_w}W` : "Potência --";
      const temp = hasTelemetryValue(gpu.temp) ? `${gpu.temp} C` : "-- C";
      const fan = hasTelemetryValue(gpu.fan) ? `${gpu.fan}%` : "--";
      $("#gpu-load").textContent = `${gpu.load}%`;
      $("#gpu-load-top").textContent = `${gpu.load}%`;
      $("#gpu-vram").textContent = `${gpu.vram_u} / ${gpu.vram_t} GB`;
      $("#gpu-vram-top").textContent = `${gpu.vram_u} GB`;
      $("#gpu-extra").textContent = power;
      $("#gpu-temp").textContent = `${temp} / Fan ${fan}`;
      setWidth("#bar-gpu-load", gpu.load);
      setWidth("#bar-gpu-vram", gpu.vram_pct);
    } else {
      renderGpuUnavailable();
    }

    const systemAvailable = !sys.erro
      && hasTelemetryValue(sys.cpu_pct)
      && hasTelemetryValue(sys.ram_pct);
    if (systemAvailable) {
      $("#cpu-load").textContent = `${sys.cpu_pct}%`;
      $("#cpu-extra").textContent = hasTelemetryValue(sys.cpu_freq_mhz)
        ? `${sys.cpu_freq_mhz} MHz`
        : "Clock --";
      setWidth("#bar-cpu-load", sys.cpu_pct);

      $("#ram-load").textContent = `${sys.ram_pct}%`;
      $("#ram-extra").textContent = hasTelemetryValue(sys.ram_used_gb)
        && hasTelemetryValue(sys.ram_total_gb)
        ? `${sys.ram_used_gb} / ${sys.ram_total_gb} GB`
        : "Uso --";
      setWidth("#bar-ram-load", sys.ram_pct);
    } else {
      renderSystemUnavailable();
    }
  } catch {
    renderGpuUnavailable("Telemetria offline");
    renderSystemUnavailable();
  }
}

function renderQwenStatus(data) {
  const qwen = data?.qwen || {
    state: "unknown",
    stateLabel: "ESTADO NÃO CONFIRMADO",
    summary: "O monitor não retornou o estado do Qwen.",
    source: "--",
    activeWork: [],
    canRelease: false,
  };
  const autoRelease = data?.autoRelease || {
    enabled: true,
    idleSeconds: 30,
    waiting: false,
    remainingSeconds: 0,
    eligible: false,
  };
  state.qwen = qwen;
  state.qwenAutoRelease = autoRelease;

  const badge = $("#qwen-runtime-badge");
  badge.dataset.state = qwen.state || "unknown";
  badge.textContent = qwen.stateLabel || "ESTADO NÃO CONFIRMADO";
  $("#qwen-runtime-summary").textContent = qwen.summary || "Sem detalhes.";
  $("#qwen-runtime-source").textContent = qwen.source || "--";

  const runner = qwen.runner || {};
  $("#qwen-runtime-sm").textContent = runner.available
    ? `${Number(runner.smUtilization) || 0}%`
    : "sensor indisponível";

  const work = Array.isArray(qwen.activeWork) ? qwen.activeWork : [];
  const first = work[0];
  const location = $("#qwen-runtime-location");
  location.hidden = !first;
  if (first) {
    $("#qwen-runtime-location-label").textContent = qwen.state === "active"
      ? "Está usando aonde"
      : "Sessão ainda marcada no OpenCode";
    $("#qwen-runtime-task").textContent = first.title || "Tarefa OpenCode ativa";
    $("#qwen-runtime-path").textContent = first.directory || "Diretório não informado";
  }

  const workDetails = $("#qwen-runtime-work");
  const workList = $("#qwen-runtime-work-list");
  workDetails.hidden = work.length < 2;
  workList.replaceChildren();
  if (work.length >= 2) {
    $("#qwen-runtime-work-summary").textContent =
      `${qwen.activeCount || work.length} sessões marcadas — ver todas`;
    work.forEach((item) => {
      const row = document.createElement("div");
      row.className = "qwen-runtime-work-item";
      const title = document.createElement("strong");
      title.textContent = item.title || "Tarefa OpenCode ativa";
      const directory = document.createElement("small");
      directory.textContent = item.directory || "Diretório não informado";
      row.append(title, directory);
      workList.append(row);
    });
  }

  const decision = $("#qwen-runtime-decision");
  const release = $("#qwen-release-button");
  release.disabled = !qwen.canRelease;
  if (qwen.canRelease) {
    decision.textContent = "Ocioso confirmado";
    release.textContent = "Liberar agora";
  } else if (qwen.state === "active") {
    decision.textContent = "Não mexer";
    release.textContent = "Qwen em uso — não liberar";
  } else if (qwen.state === "unloaded") {
    decision.textContent = "GPU já livre";
    release.textContent = "GPU já livre";
  } else if (qwen.state === "stopping") {
    decision.textContent = "Liberação em curso";
    release.textContent = "Liberando GPU…";
  } else if (qwen.state === "loaded_idle") {
    decision.textContent = "Confirmando ociosidade";
    release.textContent = "Aguardando confirmação…";
  } else {
    decision.textContent = "Bloqueado por segurança";
    release.textContent = "Estado não confirmado";
  }

  const automaticToggle = $("#qwen-auto-release-enabled");
  const automaticDelay = $("#qwen-auto-release-delay");
  const automaticStatus = $("#qwen-auto-release-status");
  if (!state.qwenSettingsSaving) {
    automaticToggle.checked = Boolean(autoRelease.enabled);
    automaticDelay.value = String(autoRelease.idleSeconds || 30);
  }
  automaticToggle.disabled = state.qwenSettingsSaving;
  automaticDelay.disabled = state.qwenSettingsSaving || !automaticToggle.checked;
  if (state.qwenSettingsSaving) {
    automaticStatus.textContent = "Salvando configuração…";
  } else if (!autoRelease.enabled) {
    automaticStatus.textContent = "Desativada. Use “Liberar agora” quando quiser.";
  } else if (qwen.state === "active") {
    automaticStatus.textContent = "Ativa; aguardando o Qwen parar de calcular.";
  } else if (qwen.state === "loaded_idle") {
    const remaining = Math.max(0, Number(autoRelease.remainingSeconds) || 0);
    automaticStatus.textContent = remaining > 0
      ? `GPU será liberada em ${remaining} s se continuar ocioso.`
      : "Ociosidade confirmada; liberando a GPU…";
  } else if (qwen.state === "unloaded") {
    automaticStatus.textContent = "Ativa. A GPU já está livre.";
  } else if (qwen.state === "stopping") {
    automaticStatus.textContent = "Ollama está descarregando o modelo.";
  } else {
    automaticStatus.textContent = "Pausada até os sensores confirmarem o estado.";
  }
}

function renderQwenUnavailable() {
  renderQwenStatus({
    qwen: {
      state: "unknown",
      stateLabel: "ESTADO NÃO CONFIRMADO",
      summary: "Não foi possível consultar o OpenCode e o Ollama.",
      source: "--",
      activeWork: [],
      canRelease: false,
      runner: { available: false },
    },
  });
}

async function loadQwenStatus() {
  if (state.qwenLoading) return;
  state.qwenLoading = true;
  try {
    renderQwenStatus(await fetchJson(`${API.localAi}/api/status`));
  } catch {
    renderQwenUnavailable();
  } finally {
    state.qwenLoading = false;
  }
}

async function releaseQwenForComfyUi() {
  if (!state.qwen?.canRelease) {
    toast("A liberação está bloqueada enquanto o Qwen estiver ativo ou sem confirmação.");
    return;
  }
  if (!confirm("O Qwen está ocioso. Liberar sua memória para o ComfyUI?")) return;

  const button = $("#qwen-release-button");
  button.disabled = true;
  button.textContent = "Validando e liberando…";
  try {
    const response = await fetch(`${API.localAi}/api/actions/release-qwen`, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "X-Pemara-Action": "release-qwen-v1",
      },
    });
    const payload = await response.json();
    if (payload.status) renderQwenStatus(payload.status);
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "A liberação foi recusada.");
    }
    toast(payload.message || "Liberação solicitada.");
  } catch (error) {
    toast(error.message || "Não foi possível liberar o Qwen.");
  } finally {
    await loadQwenStatus();
  }
}

async function saveQwenAutoRelease() {
  if (state.qwenSettingsSaving) return;
  const toggle = $("#qwen-auto-release-enabled");
  const delay = $("#qwen-auto-release-delay");
  const previous = state.qwenAutoRelease;
  state.qwenSettingsSaving = true;
  toggle.disabled = true;
  delay.disabled = true;
  $("#qwen-auto-release-status").textContent = "Salvando configuração…";
  try {
    const response = await fetch(`${API.localAi}/api/settings/qwen-auto-release`, {
      method: "POST",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Pemara-Action": "configure-qwen-auto-release-v1",
      },
      body: JSON.stringify({
        enabled: toggle.checked,
        idleSeconds: Number(delay.value),
      }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "A configuração foi recusada.");
    }
    if (payload.status) renderQwenStatus(payload.status);
    toast(payload.message || "Liberação automática atualizada.");
  } catch (error) {
    if (previous) {
      toggle.checked = Boolean(previous.enabled);
      delay.value = String(previous.idleSeconds || 30);
    }
    toast(error.message || "Não foi possível salvar a liberação automática.");
  } finally {
    state.qwenSettingsSaving = false;
    await loadQwenStatus();
  }
}

async function loadHealth() {
  try {
    const data = await fetchJson(`${API.maestro}/health`);
    try {
      const studioStatus = await fetchJson(`${API.studio}/api/generative/status`);
      (data.services || []).forEach((service) => {
        if (service.id === "studio") {
          service.port = 8027;
          service.online = true;
          service.status = "online";
          service.latency_ms = 0;
          service.detail = "Studio atual";
        }
        if (service.id === "generative") {
          service.port = 8027;
          service.online = Boolean(studioStatus.ok);
          service.status = studioStatus.ok ? "online" : "off";
          service.latency_ms = 0;
          service.detail = studioStatus.comfy_online ? "ComfyUI online" : "ComfyUI offline";
        }
      });
    } catch {}
    state.health = data;
    const online = (data.services || []).filter((item) => item.online).length;
    const total = (data.services || []).length;
    $("#global-status").textContent = `${online}/${total} online`;
    const globalState = total && online === total ? "ok" : (online ? "warn" : "bad");
    $("#global-dot").className = `status-dot ${globalState}`;
    $("#health-time").textContent = data.checked_at || "--";
    $("#health-grid").innerHTML = (data.services || []).map((service) => {
      const status = serviceState(service);
      return `
      <div class="service-item ${status.className}">
        <strong>${html(service.label)} <span class="pill ${status.className}">${status.label}</span></strong>
        <small>${service.port} - ${service.latency_ms}ms - ${html(service.detail || "")}</small>
      </div>
    `;
    }).join("");
  } catch (error) {
    $("#global-status").textContent = "erro";
    $("#global-dot").className = "status-dot bad";
    $("#health-grid").innerHTML = `<div class="service-item"><strong>Maestro <span class="pill bad">erro</span></strong><small>${html(error.message)}</small></div>`;
  }
}

async function loadOrgModels() {
  try {
    const data = await fetchJson(`${API.org}/modelos_ollama`);
    const models = data.modelos || [];
    $("#org-model").innerHTML = models.length
      ? models.map((model) => `<option value="${html(model)}">${html(model)}</option>`).join("")
      : '<option value="">Nenhum modelo encontrado</option>';
  } catch (error) {
    $("#org-model").innerHTML = `<option value="">${html(error.message)}</option>`;
  }
}

async function pickFolder(targetId) {
  try {
    const data = await fetchJson(`${API.org}/selecionar_pasta`);
    if (data.pasta) $(`#${targetId}`).value = data.pasta;
  } catch (error) {
    toast(error.message);
  }
}

async function runOrg(event) {
  event.preventDefault();
  const button = event.submitter;
  const body = {
    pasta: $("#org-source").value.trim(),
    pasta_destino: $("#org-dest").value.trim(),
    modelo_ollama: $("#org-model").value,
    diretrizes: $("#org-rules").value,
    modo_dry_run: false,
    modo: $("#org-mode").value,
    qtd_pastas: Number($("#org-count").value || 5),
  };
  if (!body.pasta) return toast("Informe a pasta de origem");

  try {
    setBusy(button, true, "Iniciando");
    const data = await fetchJson(`${API.org}/organizar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!data.ok) throw new Error(data.mensagem || "Organizador recusou a tarefa");
    $("#org-console").textContent = "Organizacao iniciada.";
    if (state.orgTimer) clearInterval(state.orgTimer);
    state.orgTimer = setInterval(pollOrg, 1200);
    pollOrg();
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

async function pollOrg() {
  try {
    const data = await fetchJson(`${API.org}/progresso`);
    const pct = Math.round((Number(data.pct) || 0) * 100);
    $("#org-progress").style.width = `${pct}%`;
    $("#org-pct").textContent = `${pct}% - ${data.etapa || ""}`;
    if (data.erro) {
      $("#org-console").textContent += `\nERRO: ${data.erro}`;
      clearInterval(state.orgTimer);
    }
    if (!data.ativo && pct >= 100) {
      $("#org-console").textContent += "\nConcluido.";
      clearInterval(state.orgTimer);
    }
    const logs = await fetchJson(`${API.org}/log`);
    if (logs.logs?.length) $("#org-console").textContent = logs.logs.join("\n");
  } catch (error) {
    $("#org-console").textContent += `\nFalha ao consultar progresso: ${error.message}`;
  }
}

async function loadCad() {
  try {
    const data = await fetchJson(`${API.cadastro}/campos`);
    $("#cad-body").innerHTML = data.map((row) => `
      <tr>
        <td>${html(row.categoria)}</td>
        <td>${html(row.campo)}</td>
        <td><input data-cad-id="${row.id}" value="${html(row.valor)}" aria-label="Valor de ${html(row.categoria)}: ${html(row.campo)}"></td>
        <td><button class="btn secondary small" data-del-cad="${row.id}" type="button" aria-label="Apagar ${html(row.campo)} de ${html(row.categoria)}">Apagar</button></td>
      </tr>
    `).join("");
  } catch (error) {
    toast(error.message);
  }
}

async function saveCad(id, value) {
  await fetchJson(`${API.cadastro}/campos/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ valor: value }),
  });
}

async function addCad(event) {
  event.preventDefault();
  const categoria = $("#cad-cat").value.trim();
  const campo = $("#cad-key").value.trim();
  if (!categoria || !campo) return toast("Informe categoria e campo");
  await fetchJson(`${API.cadastro}/campos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ categoria, campo, valor: "" }),
  });
  event.currentTarget.reset();
  loadCad();
}

async function loadHist() {
  try {
    const [hist, orgHist] = await Promise.all([
      fetchJson(`${API.historico}/registros?limit=80`).catch(() => []),
      fetchJson(`${API.org}/historico?limit=80`).catch(() => []),
    ]);
    $("#hist-body").innerHTML = (hist || []).map((row) => `
      <tr><td>${html(row.data_hora)}</td><td>${html(row.arquivo)}</td><td>${html(row.operacao)}</td></tr>
    `).join("") || '<tr><td colspan="3">Sem registros.</td></tr>';
    $("#org-hist-body").innerHTML = (orgHist || []).map((row) => `
      <tr><td>${html(row.data_hora)}</td><td>${html(row.origem)}</td><td>${html(row.destino)}</td><td>${html(row.status)}</td></tr>
    `).join("") || '<tr><td colspan="4">Sem registros.</td></tr>';
  } catch (error) {
    toast(error.message);
  }
}

async function runDoc(event) {
  event.preventDefault();
  const file = $("#doc-file").files[0];
  if (!file) return toast("Selecione um PDF");
  const fd = new FormData();
  fd.append("arquivo", file);
  try {
    setBusy(event.submitter, true, "Preenchendo");
    const response = await fetch(`${API.doc}/preencher`, { method: "POST", body: fd });
    await downloadResponse(response, "Documento_Preenchido.pdf");
    $("#doc-result").textContent = "Documento gerado.";
  } catch (error) {
    $("#doc-result").textContent = error.message;
  } finally {
    setBusy(event.submitter, false);
  }
}

async function runVideo(event) {
  event.preventDefault();
  const files = Array.from($("#video-files").files || []);
  if (!files.length) return toast("Selecione ao menos um video");
  const action = $("#video-action").value;
  const fd = new FormData();
  files.forEach((file) => fd.append("files", file));
  fd.append("formato_saida", action === "extract" ? "mp3" : "mp4");
  fd.append("codec", $("#video-codec").value);
  fd.append("crf", $("#video-crf").value);
  fd.append("inicio", $("#video-start").value);
  fd.append("fim", $("#video-end").value);
  fd.append("extrair_audio", action === "extract" ? "true" : "false");

  let endpoint = `${API.studio}/api/video/editor`;
  if (action === "transcribe") endpoint = `${API.studio}/api/audio/transcrever`;
  if (action === "remaster") {
    endpoint = `${API.studio}/api/video/remasterizar`;
    fd.delete("files");
    fd.append("file", files[0]);
    fd.append("escala", "2");
    fd.append("modo", "rapido");
  }

  try {
    setBusy(event.submitter, true, "Executando");
    $("#studio-result").textContent = "Processando video...";
    const response = await fetch(endpoint, { method: "POST", body: fd });
    await downloadResponse(response, "Studio_Resultado.zip");
    $("#studio-result").textContent = "Processamento concluido.";
  } catch (error) {
    $("#studio-result").textContent = error.message;
  } finally {
    setBusy(event.submitter, false);
  }
}

async function runAudio(event) {
  event.preventDefault();
  const files = Array.from($("#audio-files").files || []);
  if (!files.length) return toast("Selecione ao menos um arquivo");
  const action = $("#audio-action").value;
  const fd = new FormData();
  let endpoint = `${API.studio}/api/audio/transcrever`;
  let fallback = "Audio_Resultado.zip";

  if (action === "isolate") {
    endpoint = `${API.studio}/api/audio/isolar`;
    fd.append("file", files[0]);
    fallback = "VOZ.wav";
  } else if (action === "forense") {
    endpoint = `${API.studio}/api/audio/forense_custom`;
    fd.append("file", files[0]);
    fallback = "TRATADO.wav";
  } else if (action === "convert") {
    endpoint = `${API.studio}/api/audio/converter`;
    files.forEach((file) => fd.append("files", file));
    fd.append("formato_saida", $("#audio-format").value === "wav" ? "wav" : "mp3");
  } else {
    files.forEach((file) => fd.append("files", file));
    fd.append("idioma", $("#audio-lang").value);
    fd.append("formato_saida", $("#audio-format").value);
  }

  try {
    setBusy(event.submitter, true, "Executando");
    $("#studio-result").textContent = "Processando audio...";
    const response = await fetch(endpoint, { method: "POST", body: fd });
    await downloadResponse(response, fallback);
    $("#studio-result").textContent = "Processamento concluido.";
  } catch (error) {
    $("#studio-result").textContent = error.message;
  } finally {
    setBusy(event.submitter, false);
  }
}

function syncAudioAction() {
  const action = $("#audio-action")?.value || "transcribe";
  const select = $("#audio-format");
  if (!select) return;
  const current = select.value;
  const formats = action === "convert"
    ? [["mp3", "MP3"], ["wav", "WAV"]]
    : [["txt", "TXT"], ["srt", "SRT"], ["vtt", "VTT"]];
  select.innerHTML = formats.map(([value, label]) => `<option value="${value}">${label}</option>`).join("");
  select.value = formats.some(([value]) => value === current) ? current : formats[0][0];
}

async function runImage(event) {
  event.preventDefault();
  const file = $("#image-file").files[0];
  if (!file) return toast("Selecione uma imagem");
  const params = {
    brilho: Number($("#image-brilho").value || 1),
    contraste: Number($("#image-contraste").value || 1),
  };
  const fd = new FormData();
  fd.append("file", file);
  fd.append("acao", $("#image-action").value);
  fd.append("params_json", JSON.stringify(params));
  fd.append("formato_saida", "png");

  try {
    setBusy(event.submitter, true, "Executando");
    $("#studio-result").textContent = "Processando imagem...";
    const response = await fetch(`${API.studio}/api/imagem/processar`, { method: "POST", body: fd });
    await downloadResponse(response, "Imagem_Processada.png");
    $("#studio-result").textContent = "Imagem processada.";
  } catch (error) {
    $("#studio-result").textContent = error.message;
  } finally {
    setBusy(event.submitter, false);
  }
}

async function loadStudioLog() {
  try {
    const data = await fetchJson(`${API.studio}/api/log`);
    $("#studio-result").textContent = (data.logs || []).join("\n") || "Sem logs recentes.";
  } catch (error) {
    $("#studio-result").textContent = error.message;
  }
}

function audioMp3Output(item) {
  const title = String(item.title || String(item.filename || "Musica").replace(/\.[^.]+$/, ""));
  const filename = (title.replace(/[^\p{L}\p{N} _()-]/gu, "_").trim().slice(0, 120) || "Musica") + ".mp3";
  const base = `${API.studio}/api/generative/audio-export/${encodeURIComponent(filename)}?source=${encodeURIComponent(item.url)}`;
  return { filename, play: `${base}&download=false`, download: `${base}&download=true`, archive: `${base}&download=true&archive=true` };
}

function setVerifiedDownloadLink(link) {
  if (!link) return;
  let archive = link.nextElementSibling;
  if (!archive?.hasAttribute("data-verified-download")) {
    archive = document.createElement("a");
    archive.setAttribute("data-verified-download", "1");
    archive.textContent = "Baixar ZIP verificado";
    archive.title = "Extraia o ZIP no app Arquivos. Uma transferência incompleta será detectada na extração.";
    link.insertAdjacentElement("afterend", archive);
  }
  archive.className = link.className;
  archive.hidden = !link.hasAttribute("href") || link.classList.contains("hidden");
  if (!archive.hidden) {
    const url = new URL(link.href, window.location.href);
    url.searchParams.set("archive", "true");
    url.searchParams.set("download", "true");
    archive.href = url.href;
    archive.setAttribute("download", `${link.getAttribute("download") || "maestro"}.zip`);
  } else {
    archive.removeAttribute("href");
  }
}

function audioProductionLinks(item) {
  const links = [
    [item.master_url, "Baixar master WAV", "master.wav"],
    [item.native_url, "Baixar fonte original", item.native_filename || ""],
    [item.production_plan_url, "Plano da música", "plano_da_musica.json"],
  ];
  return links.filter(([url]) => String(url || "").startsWith("/api/")).map(([url, label, filename]) =>
    `<a class="output-link" href="${html(API.studio + url)}" ${filename ? `download="${html(filename)}"` : 'target="_blank" rel="noopener"'}>${html(label)}</a>`
  ).join("");
}

function appendMessage(role, text, outputs = []) {
  const msg = document.createElement("div");
  msg.className = `message ${role}`;
  let content = `<div>${html(text).replace(/\n/g, "<br>")}</div>`;
  if (outputs.length) {
    content += '<div class="output-grid">';
    outputs.forEach((item) => {
      const src = `${API.studio}${item.url}`;
      if (item.kind === "video") {
        content += `<div><video src="${html(src)}" controls loop playsinline></video><a class="output-link" href="${html(src)}" target="_blank" rel="noopener">Abrir MP4</a></div>`;
      } else if (item.kind === "audio") {
        const mp3 = audioMp3Output(item);
        content += `<div class="audio-output"><audio src="${html(mp3.play)}" controls preload="metadata"></audio><a class="output-link" href="${html(mp3.play)}" target="_blank" rel="noopener">Abrir &aacute;udio</a><a class="output-link" href="${html(mp3.download)}" download="${html(mp3.filename)}">Baixar MP3</a><a class="output-link" href="${html(mp3.archive)}" download="${html(mp3.filename)}.zip">Baixar ZIP verificado</a>${audioProductionLinks(item)}</div>`;
      } else {
        content += `<div><a href="${html(src)}" target="_blank" rel="noopener"><img src="${html(src)}" alt="${html(item.filename || "saida")}"></a><a class="output-link" href="${html(src)}" target="_blank" rel="noopener">Abrir imagem</a></div>`;
      }
    });
    content += "</div>";
  }
  msg.innerHTML = content;
  $("#gen-chat").appendChild(msg);
  $("#gen-chat").scrollTop = $("#gen-chat").scrollHeight;
}

function setGenProgress(percent, label) {
  const wrap = $("#gen-progress-wrap");
  const bar = $("#gen-progress-bar");
  const pct = $("#gen-progress-percent");
  const text = $("#gen-progress-label");
  if (!wrap || !bar || !pct || !text) return;
  const value = Math.max(0, Math.min(100, Number(percent) || 0));
  wrap.classList.remove("hidden");
  bar.style.width = `${value}%`;
  pct.textContent = `${value}%`;
  text.textContent = label || "Gerando";
}

function hideGenProgress() {
  const wrap = $("#gen-progress-wrap");
  if (wrap) wrap.classList.add("hidden");
}

function genAudioProvidersForMode(mode) {
  const providers = state.genStatus?.providers?.audio || {};
  return Object.entries(providers).filter(([id, info]) => {
    if (Array.isArray(info.modes)) return info.modes.includes(mode);
    if (mode === "sfx") return id === "eleven_sfx" || id === "stable_audio" || id === "audiogen";
    return id !== "eleven_sfx" && id !== "audiogen";
  });
}

function syncGenAudioProviderDetails({ resetDuration = false } = {}) {
  const mode = $("#gen-mode")?.value;
  const providerId = $("#gen-provider")?.value;
  const info = state.genStatus?.providers?.audio?.[providerId] || {};
  const duration = $("#gen-duration");
  const help = $("#gen-provider-help");
  if (!duration || !help || !["music", "sfx"].includes(mode)) return;

  const minimum = Number(info.min_duration_seconds ?? (mode === "sfx" ? 0.5 : 1));
  const maximum = Number(info.max_duration_seconds ?? (mode === "sfx" ? 30 : 600));
  const fallback = Number(info.default_duration_seconds ?? (mode === "sfx"
    ? state.genStatus?.defaults?.sfx_duration
    : state.genStatus?.defaults?.audio_duration));
  duration.min = String(minimum);
  duration.max = String(maximum);
  const modelDecidesDuration = mode === "music" && providerId === "yue2_local"
    && $("#gen-music-duration-auto")?.checked;
  $("#gen-music-duration-auto-field")?.classList.toggle("hidden", mode !== "music" || providerId !== "yue2_local");
  duration.disabled = Boolean(modelDecidesDuration);
  const current = Number(duration.value);
  if (resetDuration || !Number.isFinite(current) || current < minimum || current > maximum) {
    duration.value = String(Math.max(minimum, Math.min(maximum, fallback || minimum)));
  }

  const parts = [info.message || (info.configured ? "Motor pronto." : "Motor ainda n&atilde;o configurado.")];
  if (info.pilot_only) parts.push(`Piloto de ${minimum}&ndash;${maximum} s; nenhuma aprova&ccedil;&atilde;o &eacute; autom&aacute;tica.`);
  if (info.requires_human_listening) parts.push(mode === "music" ? "Ou&ccedil;a o resultado para avaliar a m&uacute;sica." : "Escuta humana obrigat&oacute;ria antes de continuar.");
  if (info.license_scope === "internal_noncommercial_research_only") parts.push("Uso interno, n&atilde;o comercial e de pesquisa.");
  help.innerHTML = parts.join(" ");
  help.dataset.ready = info.configured ? "true" : "false";
  help.classList.remove("hidden");
  $("#gen-engine-pill").textContent = info.label || "Escolha um motor de áudio";
  const copy = GEN_MODE_COPY[mode] || GEN_MODE_COPY.image;
  const localMusic = mode === "music" && ["ace_step_local", "yue2_local", "levo2_local"].includes(providerId);
  $("#gen-music-fields")?.classList.toggle("hidden", !localMusic);
  $("#gen-yue-fields")?.classList.toggle("hidden", !localMusic || providerId !== "yue2_local");
  $("#gen-music-model-field")?.classList.toggle("hidden", providerId !== "ace_step_local");
  $("#gen-music-bpm-field")?.classList.toggle("hidden", providerId !== "ace_step_local");
  if (providerId === "ace_step_local" && info.models) {
    const modelSelect = $("#gen-music-model");
    const previousModel = modelSelect.value;
    modelSelect.innerHTML = Object.entries(info.models).map(([id, label]) => `<option value="${html(id)}">${html(label)}</option>`).join("");
    if (info.models[previousModel]) modelSelect.value = previousModel;
  }
  $("#gen-submit").textContent = providerId === "yue2_local" && $("#gen-music-action").value === "plan" ? "Planejar composição"
    : localMusic ? "Gerar música" : copy.submit;
}

function syncGenAudioProviderOptions(mode, { resetDuration = false } = {}) {
  const select = $("#gen-provider");
  if (!select) return;
  const entries = genAudioProvidersForMode(mode);
  const previous = select.value;
  select.innerHTML = entries.map(([id, info]) => {
    const suffix = info.configured ? "" : " (indispon&iacute;vel)";
    return `<option value="${html(id)}"${info.configured ? "" : " disabled"}>${html(info.label || id)}${suffix}</option>`;
  }).join("") || '<option value="">Nenhum motor dispon&iacute;vel</option>';
  const preferred = mode === "sfx"
    ? state.genStatus?.defaults?.sfx_provider
    : state.genStatus?.defaults?.audio_provider;
  const selectable = entries.filter(([, info]) => info.configured).map(([id]) => id);
  if (selectable.includes(previous)) select.value = previous;
  else if (selectable.includes(preferred)) select.value = preferred;
  else if (selectable.length) select.value = selectable[0];
  syncGenAudioProviderDetails({ resetDuration });
}

function videoEngineById(engineId) {
  return (state.videoEngines || []).find((engine) => engine.id === engineId) || null;
}

function videoEngineTechnicalModel(engineId) {
  if (engineId === "minimax_h3") {
    return (state.genStatus?.models?.video || []).find((name) => (
      String(name).toLowerCase().includes("minimax_h3_fl2va")
    )) || "minimax_h3_fl2va_pruned_int8_convrot.safetensors";
  }
  return "";
}

function videoEngineStateLabel(engine) {
  const readiness = engine?.readiness || {};
  if (readiness.production_ready) return "Pronto para produção";
  if (readiness.state === "READY_FOR_GPU_SMOKE") return "Instalado · smoke GPU pendente";
  if (readiness.state === "PARTIAL") return "Instalação parcial";
  return readiness.state === "MISSING" ? "Componentes ausentes" : "Indisponível";
}

function renderVideoEnginePicker() {
  const container = $("#gen-video-engines");
  if (!container) return;
  container.innerHTML = (state.videoEngines || []).map((engine) => {
    const selected = engine.id === state.selectedVideoEngineId;
    const stateName = engine.readiness?.state || "UNKNOWN";
    const description = engine.id === "minimax_h3"
      ? "Fidelidade por âncoras, first/last frame e áudio nativo."
      : "T2V/I2V, áudio nativo, dois estágios e IC-LoRAs autorizadas.";
    return `<button class="gen-video-engine-card${selected ? " selected" : ""}" type="button"
      role="radio" aria-checked="${selected ? "true" : "false"}"
      data-video-engine-id="${html(engine.id)}" data-state="${html(stateName)}"
      ${engine.selectable === false ? "disabled" : ""}>
      <strong>${html(engine.display_name || engine.id)}</strong>
      <span>${html(videoEngineStateLabel(engine))}</span>
      <small>${html(description)}</small>
    </button>`;
  }).join("") || '<p>Nenhum motor autorizado foi carregado.</p>';
}

function selectVideoEngine(engineId) {
  const engine = videoEngineById(engineId);
  if (!engine || engine.selectable === false) return;
  state.selectedVideoEngineId = engine.id;
  $("#gen-engine-id").value = engine.id;
  const technicalModel = videoEngineTechnicalModel(engine.id);
  const modelSelect = $("#gen-model");
  if (modelSelect && technicalModel) {
    if (!Array.from(modelSelect.options).some((option) => option.value === technicalModel)) {
      modelSelect.insertAdjacentHTML(
        "beforeend",
        `<option value="${html(technicalModel)}">${html(friendlyModelName(technicalModel))}</option>`,
      );
    }
    modelSelect.value = technicalModel;
  }
  renderVideoEnginePicker();
  const readiness = engine.readiness || {};
  const status = $("#gen-video-engine-status");
  if (status) status.textContent = `${engine.display_name}: ${readiness.message || videoEngineStateLabel(engine)}`;
  $("#gen-engine-pill").textContent = engine.display_name;
  applyGenModelPreset();
}

function clearVideoEngineSelection() {
  state.selectedVideoEngineId = "";
  if ($("#gen-engine-id")) $("#gen-engine-id").value = "";
  if ($("#gen-video-engine-status")) $("#gen-video-engine-status").textContent = "Nenhum motor selecionado.";
  renderVideoEnginePicker();
}

async function loadGenStatus() {
  try {
    const data = await fetchJson(`${API.studio}/api/generative/status`);
    state.genStatus = data;

    syncH3VariantControls();
    state.videoEngines = data.videoEngines?.engines || [];
    const route = "Studio via Maestro";
    $("#gen-status").textContent = data.comfy_online ? `ComfyUI: online | ${route}` : `ComfyUI: offline | ${route}`;
    $("#gen-status").style.color = data.comfy_online ? "var(--green)" : "var(--red)";
    const loras = data.models?.loras || [];
    const currentLora = $("#gen-lora").value;
    $("#gen-lora").innerHTML = '<option value="">Sem LoRA</option>' + loras.map((name) => `<option value="${html(name)}">${html(name)}</option>`).join("");
    if (currentLora) $("#gen-lora").value = currentLora;
    renderGenH3Workflow(data.h3Workflow);
    renderVideoEnginePicker();
    syncGenMode();
    if (state.films.takes.length) renderFilmTakes();
  } catch (error) {
    $("#gen-status").textContent = error.message;
    $("#gen-status").style.color = "var(--red)";
  }
}

function genJobLabel(value) {
  return ({
    image: "Imagem",
    edit: "Edicao",
    marketing_card: "Card",
    video: "Video",
    music: "Musica",
    sfx: "SFX",
  })[value] || "Criacao";
}

function genJobState(value) {
  return ({
    running: ["Em andamento", "warn"],
    queued: ["Na fila", "warn"],
    canceling: ["Cancelando", "warn"],
    canceled: ["Cancelado", "bad"],
    done: ["Concluido", "ok"],
    error: ["Erro", "bad"],
    interrupted: ["Interrompido", "bad"],
  })[value] || [value || "Desconhecido", "warn"];
}

function renderGenH3Workflow(workflow) {
  const stateNode = $("#gen-h3-workflow-state");
  const summary = $("#gen-h3-workflow-summary");
  const stages = $("#gen-h3-workflow-stages");
  if (!stateNode || !summary || !stages) return;
  if (!workflow) {
    stateNode.textContent = "Indisponivel";
    summary.textContent = "O contrato unificado do MiniMax H3 nao foi carregado.";
    stages.innerHTML = "";
    return;
  }
  const ready = workflow.productionReady === true;
  stateNode.textContent = ready ? "Pronto" : "Requer ajuste";
  stateNode.className = ready ? "ok" : "warn";
  const catalog = workflow.catalog || {};
  summary.textContent = `${workflow.videoEngine || "MiniMax H3"} disponível quando você o seleciona; ${catalog.installedSkills || 0} skills e ${catalog.installedProfiles || 0} perfis inventariados, com roteamento por etapa e aprovação humana.`;
  if (workflow.faceRefine?.enabled) {
    summary.textContent += workflow.faceRefine.runtimeReady
      ? " Face Refine automático ativo em todos os workflows H3; original e áudio preservados."
      : " Face Refine configurado; aguardando disponibilidade no ComfyUI.";
  }
  stages.innerHTML = (workflow.stages || []).map((stage) => (
    `<li><strong>${html(stage.label)}</strong><span>${html(stage.output)}</span><small>Gate: ${html(stage.gate)}</small></li>`
  )).join("");
}

function movaApprovalState(value) {
  return ({
    PENDING_PT_BR_VOICE_REVIEW: ["Escutar PT-BR", "warn"],
    PENDING_HUMAN_REVIEW: ["Revisar", "warn"],
    AUTO_REJECTED_MOTION: ["Reprovado: movimento", "bad"],
    AUTO_REJECTED_AUDIO: ["Reprovado: áudio", "bad"],
    REJECTED_QC: ["Reprovado", "bad"],
    APPROVED: ["Aprovado", "ok"],
  })[value] || null;
}

function genJobTime(timestamp) {
  const date = new Date(Number(timestamp || 0) * 1000);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

async function loadGenJobs() {
  const list = $("#gen-history-list");
  if (!list) return;
  try {
    const payload = await fetchJson(`${API.studio}/api/generative/jobs?page=1&page_size=12`);
    const jobs = payload.items || [];
    $("#gen-history-count").textContent = String(payload.total || 0);
    if (!jobs.length) {
      list.innerHTML = '<div class="gen-history-empty" role="status">Nenhum trabalho gerado ainda.</div>';
      return;
    }
    list.innerHTML = jobs.map((job) => {
      const approvalState = job.mode === "video" && job.result?.approval_status
        ? movaApprovalState(job.result?.approval_status)
        : null;
      const [statusLabel, statusClass] = approvalState || genJobState(job.status);
      const prompt = job.prompt || job.message || "Sem descricao";
      const firstOutput = job.result?.outputs?.[0];
      const outputUrl = firstOutput?.url?.startsWith("/api/") ? `${API.studio}${firstOutput.url}` : "";
      const mp3 = outputUrl && firstOutput?.kind === "audio" ? audioMp3Output(firstOutput) : null;
      const outputLink = outputUrl
        ? `<a class="output-link" href="${html(mp3?.play || outputUrl)}" target="_blank" rel="noopener">Abrir resultado</a>`
        : "";
      const audioPlayer = outputUrl && firstOutput?.kind === "audio"
        ? `<audio controls preload="metadata" src="${html(mp3.play)}" aria-label="Ouvir ${html(job.result?.title || 'música gerada')}" style="width:100%;margin-top:10px"></audio>` : "";
      const downloadButton = mp3
        ? `<a class="output-link" href="${html(mp3.download)}" download="${html(mp3.filename)}">Baixar MP3</a><a class="output-link" href="${html(mp3.archive)}" download="${html(mp3.filename)}.zip">Baixar ZIP verificado</a>${audioProductionLinks(firstOutput)}` : "";
      const cancelButton = job.actions?.can_cancel
        ? `<button type="button" class="btn secondary small" data-gen-job-action="cancel" data-job-id="${html(job.job_id)}">Cancelar</button>`
        : "";
      const retryLabel = job.status === "done" ? "Repetir" : "Tentar novamente";
      const retryButton = job.actions?.can_retry
        ? `<button type="button" class="btn secondary small" data-gen-job-action="retry" data-job-id="${html(job.job_id)}">${retryLabel}</button>`
        : "";
      const scoreButton = job.result?.music_abc
        ? `<button type="button" class="btn secondary small" data-gen-job-action="score" data-job-id="${html(job.job_id)}">${job.result.music_action === "auto" ? "Ver partitura" : "Revisar partitura"}</button>` : "";
      const listenButton = audioPlayer
        ? `<button type="button" class="btn secondary small" data-gen-job-action="listen" data-job-id="${html(job.job_id)}">Ouvir no painel</button>` : "";
      const actions = outputLink || cancelButton || retryButton || scoreButton || listenButton
        ? `<div class="gen-history-actions">${listenButton}${downloadButton}${outputLink}${cancelButton}${retryButton}${scoreButton}</div>`
        : "";
      return `<article class="gen-history-item" role="listitem">
        <div class="gen-history-meta">
          <strong>${html(genJobLabel(job.mode))}</strong>
          <span class="pill ${statusClass}">${html(statusLabel)}</span>
          <time>${html(genJobTime(job.updated_at))}</time>
        </div>
        <p>${html(prompt)}</p>
        ${job.message ? `<small>${html(job.message)}</small>` : ""}
        ${audioPlayer}
        ${actions}
      </article>`;
    }).join("");
  } catch (error) {
    list.innerHTML = `<div class="gen-history-empty" role="alert">${html(error.message)}</div>`;
  }
}

async function handleGenJobAction(button) {
  const jobId = button.dataset.jobId;
  const action = button.dataset.genJobAction;
  if (!jobId || !action) return;
  if (action === "listen") {
    try {
      const job = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}`);
      appendMessage("assistant", job.result?.message || job.prompt || "Música gerada", job.result?.outputs || []);
    } catch (error) { toast(error.message); }
    return;
  }
  if (action === "score") {
    try {
      const job = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}`);
      if (!job.result?.music_abc) return toast("Este trabalho não contém partitura ABC.");
      $("#gen-mode").value = "music";
      syncGenMode();
      $("#gen-provider").value = "yue2_local";
      syncGenAudioProviderDetails();
      const spec = job.request_spec || {};
      $("#gen-prompt").value = spec.prompt || job.prompt || "";
      $("#gen-duration").value = spec.duration || 30;
      $("#gen-music-duration-auto").checked = spec.music_duration_auto === true;
      $("#gen-music-instrumental").checked = job.result.music_instrumental ?? (spec.music_instrumental !== false);
      $("#gen-music-lyrics").value = job.result.music_lyrics || spec.music_lyrics || "";
      $("#gen-music-lyrics").disabled = $("#gen-music-instrumental").checked;
      $("#gen-music-abc").value = job.result.music_abc;
      $("#gen-music-abc-reviewed").checked = false;
      $("#gen-music-action").value = "generate";
      $("#gen-music-advanced").open = true;
      syncGenAudioProviderDetails();
      $("#gen-music-abc").focus();
    } catch (error) { toast(error.message); }
    return;
  }
  if (action === "retry" && !confirm("Repetir este trabalho com os mesmos parametros e arquivos?")) return;
  try {
    setBusy(button, true, action === "cancel" ? "Cancelando" : "Enfileirando");
    const result = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}/${action}`, {
      method: "POST",
    });
    toast(action === "cancel" ? "Cancelamento solicitado" : "Novo trabalho enfileirado");
    await loadGenJobs();
    return result;
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

function syncGenMode({ resetVideoEngine = false } = {}) {
  if (!state.genStatus) return;
  const mode = $("#gen-mode").value;
  const isVideoMode = mode === "video" || mode === "text_video";
  const isTextVideoMode = mode === "text_video";
  const isAudioMode = mode === "music" || mode === "sfx";
  let models = state.genStatus.models?.image || [];
  let fallback = state.genStatus.defaults?.image_model;
  if (isVideoMode) {
    models = (state.videoEngines || []).map((engine) => videoEngineTechnicalModel(engine.id)).filter(Boolean);
    fallback = resetVideoEngine ? "" : videoEngineTechnicalModel(state.selectedVideoEngineId);
  } else if (mode === "edit") {
    models = state.genStatus.models?.qwen_edit || [];
    fallback = state.genStatus.defaults?.qwen_edit_model;
  } else if (isAudioMode) {
    models = mode === "music" ? ["audio-music-provider"] : ["audio-sfx-provider"];
    fallback = models[0];
  }
  $("#gen-model").innerHTML = models.length
    ? `${isVideoMode ? '<option value="">Escolha o motor acima</option>' : ""}${models.map((name) => `<option value="${html(name)}">${html(friendlyModelName(name))}</option>`).join("")}`
    : '<option value="">Nenhum motor disponível</option>';
  if (fallback) $("#gen-model").value = fallback;
  if (isVideoMode && resetVideoEngine) clearVideoEngineSelection();

  const copy = GEN_MODE_COPY[mode] || GEN_MODE_COPY.image;
  $("#gen-mode-kicker").textContent = copy.kicker;
  $("#gen-mode-title").textContent = copy.title;
  $("#gen-mode-help").textContent = copy.help;
  $("#gen-prompt-label").textContent = copy.promptLabel;
  $("#gen-prompt").placeholder = copy.placeholder;
  $("#gen-submit").textContent = copy.submit;
  $$('[data-gen-mode]').forEach((button) => {
    const active = button.dataset.genMode === mode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });

  const needsBaseImage = mode === "edit" || mode === "video" || mode === "marketing_card";
  $("#gen-media-row").classList.toggle("hidden", !needsBaseImage);
  $("#gen-base-image-label").classList.toggle("hidden", !needsBaseImage);
  $("#gen-end-image-label").classList.toggle("hidden", mode !== "video");
  $("#gen-video-direction").classList.toggle("hidden", !isVideoMode);
  $("#gen-video-engine-picker")?.classList.toggle("hidden", !isVideoMode);
  $("#gen-h3-workflow")?.classList.toggle("hidden", !isVideoMode || state.selectedVideoEngineId !== "minimax_h3");
  $("#gen-video-conditioning-field").classList.toggle("hidden", isTextVideoMode);
  $("#gen-provider-fields").classList.toggle("hidden", !isAudioMode);
  $("#gen-music-fields")?.classList.toggle("hidden", mode !== "music");
  $("#gen-sfx-fields").classList.toggle("hidden", mode !== "sfx");
  $("#gen-base-image-label").classList.toggle("hidden", isAudioMode);
  $("#gen-lora-label").classList.toggle("hidden", isAudioMode);
  $$(".gen-advanced").forEach((node) => node.classList.toggle("hidden", isAudioMode));
  $("#gen-video-fields").classList.toggle("hidden", !isVideoMode);
  $("#gen-video-timing-help").classList.toggle("hidden", !isVideoMode);
  $("#gen-model").disabled = isAudioMode || isVideoMode;
  $("#gen-width").value = isVideoMode ? (state.genStatus.defaults?.video_width || 1280) : (state.genStatus.defaults?.width || 1024);
  $("#gen-height").value = isVideoMode ? (state.genStatus.defaults?.video_height || 720) : (state.genStatus.defaults?.height || 1024);
  $("#gen-frames").value = isVideoMode ? (state.genStatus.defaults?.video_frames || 241) : 121;
  $("#gen-fps").value = isVideoMode ? (state.genStatus.defaults?.video_fps || 30) : 30;
  $("#gen-video-duration").value = isVideoMode ? (state.genStatus.defaults?.video_duration || 6) : 6;
  $("#gen-steps").value = isVideoMode ? 28 : (mode === "edit" ? 40 : 28);
  $("#gen-guidance").value = isVideoMode ? 6 : (mode === "edit" ? 4 : 3.5);
  if (isAudioMode) syncGenAudioProviderOptions(mode, { resetDuration: true });
  else $("#gen-provider-help")?.classList.add("hidden");
  if (isVideoMode) {
    $("#gen-engine-pill").textContent = videoEngineById(state.selectedVideoEngineId)?.display_name || "Escolha o motor";
  }
  applyGenModelPreset();
}

function nearestTemporalFrames(duration, fps, { stride, offset, minimum, maximum }) {
  const target = Math.max(1, Math.round(duration * fps) + 1);
  const first = offset + Math.max(0, Math.ceil((minimum - offset) / stride)) * stride;
  let selected = first;
  for (let candidate = first; candidate <= maximum; candidate += stride) {
    const candidateKey = [Math.abs(candidate - target), candidate >= target ? 0 : 1, candidate];
    const selectedKey = [Math.abs(selected - target), selected >= target ? 0 : 1, selected];
    if (
      candidateKey[0] < selectedKey[0]
      || (candidateKey[0] === selectedKey[0] && candidateKey[1] < selectedKey[1])
      || (candidateKey[0] === selectedKey[0] && candidateKey[1] === selectedKey[1] && candidateKey[2] < selectedKey[2])
    ) selected = candidate;
  }
  return selected;
}

function syncGenDurationPresets(duration, minimum, maximum) {
  $$('[data-gen-duration]').forEach((button) => {
    const value = Number(button.dataset.genDuration || 0);
    const available = value >= minimum - 0.01 && value <= maximum + 0.01;
    button.disabled = !available;
    const active = available && Math.abs(value - duration) <= 0.02;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function syncGenVideoTiming() {
  if (!["video", "text_video"].includes($("#gen-mode").value)) return;
  const engineId = state.selectedVideoEngineId;
  const fpsField = $("#gen-fps");
  const durationField = $("#gen-video-duration");
  const framesField = $("#gen-frames");
  const help = $("#gen-video-timing-help");
  const isH3 = engineId === "minimax_h3";

  if (isH3) fpsField.value = 24;
  fpsField.disabled = isH3;
  const fps = Math.max(24, Math.min(60, Number(fpsField.value || 24)));
  fpsField.value = String(fps);

  const grid = isH3
    ? {
      stride: Number(state.genStatus?.defaults?.minimax_h3_temporal_stride || 17),
      offset: Number(state.genStatus?.defaults?.minimax_h3_temporal_offset || 5),
      minimum: Number(state.genStatus?.defaults?.minimax_h3_min_frames || 124),
      maximum: Number(state.genStatus?.defaults?.minimax_h3_max_frames || 362),
      label: "grade H3 17k+5",
    }
    : { stride: 8, offset: 1, minimum: 25, maximum: 721, label: "selecione um motor" };
  const minimumDuration = (grid.minimum - 1) / fps;
  const gridMaximumDuration = (grid.maximum - 1) / fps;
  const maximumDuration = isH3
    ? Math.min(Number(state.genStatus?.defaults?.minimax_h3_max_duration || 15), gridMaximumDuration)
    : gridMaximumDuration;
  durationField.min = minimumDuration.toFixed(2);
  durationField.max = maximumDuration.toFixed(2);
  let duration = Number(durationField.value || minimumDuration);
  if (!Number.isFinite(duration)) duration = minimumDuration;
  duration = Math.max(minimumDuration, Math.min(maximumDuration, duration));
  durationField.value = duration.toFixed(2).replace(/\.00$/, "");

  const frames = nearestTemporalFrames(duration, fps, grid);
  const effectiveDuration = (frames - 1) / fps;
  framesField.value = String(frames);
  syncGenDurationPresets(duration, minimumDuration, maximumDuration);
  help.textContent = !engineId
    ? "Escolha MiniMax H3; nenhum motor será aplicado automaticamente."
    : isH3
    ? `MiniMax H3: 24 FPS nativos automaticos; ${frames} quadros na ${grid.label}; duracao efetiva ${effectiveDuration.toFixed(2)} s.`
    : "Selecione MiniMax H3 para configurar a duração.";
}

function syncGenMinimaxAudio() {
  const mode = $("#gen-mode").value;
  const isMinimaxH3Video = ["video", "text_video"].includes(mode)
    && state.selectedVideoEngineId === "minimax_h3";
  const field = $("#gen-minimax-native-audio-field");
  const checkbox = $("#gen-minimax-native-audio");
  const previewField = $("#gen-minimax-live-preview-field");
  const previewCheckbox = $("#gen-minimax-live-preview");
  field?.classList.toggle("hidden", !isMinimaxH3Video);
  previewField?.classList.toggle("hidden", !isMinimaxH3Video);
  if (previewCheckbox) previewCheckbox.disabled = !isMinimaxH3Video;
  if (!checkbox) return;
  checkbox.disabled = !isMinimaxH3Video;
  if (isMinimaxH3Video) {
    const profileId = $("#gen-h3-quality-profile")?.value || "h3_production";
    if (profileId === "h3_draft") checkbox.checked = false;
    checkbox.disabled = !isMinimaxH3Video || profileId === "h3_draft";
  }
}

function applyH3QualityProfile() {
  if (state.selectedVideoEngineId !== "minimax_h3") return;
  const profileId = $("#gen-h3-quality-profile")?.value || "h3_production";
  const profile = H3_QUALITY_PROFILES[profileId];
  if (!profile) return;
  const orientation = $("#gen-h3-orientation")?.value || "landscape";

  const vertical = orientation === "portrait";

  const fastH3 = $("#gen-h3-model-variant")?.value === FAST_H3_VARIANT;

  $("#gen-width").value = vertical ? profile.verticalWidth : profile.width;
  $("#gen-height").value = vertical ? profile.verticalHeight : profile.height;
  $("#gen-width").disabled = true;
  $("#gen-height").disabled = true;
  const stepsField = $("#gen-steps");
  stepsField.value = fastH3 ? 8 : profile.steps;
  stepsField.min = fastH3 ? 8 : profileId === "h3_hero" ? 12 : profile.steps;
  stepsField.max = fastH3 ? 8 : profileId === "h3_hero" ? 14 : profile.steps;
  stepsField.disabled = fastH3 || profileId !== "h3_hero";

  $("#gen-fps").value = 24;
  $("#gen-video-duration").value = 10;
  $("#gen-guidance").value = 1;
  $("#gen-guidance").disabled = true;
  syncGenVideoTiming();
  syncGenMinimaxAudio();

  syncH3VariantControls();
}

function syncH3VariantControls() {

  const mode = $("#gen-mode")?.value || "";

  const isH3 = ["video", "text_video"].includes(mode) && state.selectedVideoEngineId === "minimax_h3";

  const cacheOption = $("#gen-h3-quality-profile option[value='h3_master_fbc20']");
  const spectrumOption = $("#gen-h3-quality-profile option[value='h3_master_spectrum20']");
  const cacheSelected = false; // Sage + Spectrum are mandatory in every H3 profile.
  if (cacheOption) cacheOption.disabled = !isH3 || state.genStatus?.h3Workflow?.capabilities?.masterCacheReady !== true;
  if (spectrumOption) spectrumOption.disabled = !isH3 || state.genStatus?.h3Workflow?.capabilities?.masterSpectrumReady !== true;
  $("#gen-h3-cache-help")?.classList.toggle("hidden", !isH3 || !cacheSelected);

  const fastOption = $("#gen-h3-model-variant option[value='fasth3_8step_v2']");

  const fastReady = state.genStatus?.h3Workflow?.capabilities?.fastH3Ready === true;

  const fastFileReady = state.genStatus?.h3Workflow?.capabilities?.fastH3FileReady === true;

  const fastNodeListed = state.genStatus?.h3Workflow?.capabilities?.fastH3NodeListed === true;

  if (fastOption) {

    fastOption.disabled = !fastReady || !isH3;

    fastOption.textContent = fastReady
      ? "FastH3 8-Step V2 — texto ou imagem"
      : fastFileReady && !fastNodeListed
        ? "FastH3 — atualizar ComfyUI"
        : "FastH3 8-Step V2 — instalando";

  }

  $("#gen-h3-variant-field")?.classList.toggle("hidden", !isH3);

  $("#gen-h3-orientation-field")?.classList.toggle("hidden", !isH3);

  $("#gen-h3-sage-status")?.classList.toggle("hidden", !isH3);

  const fastSelected = $("#gen-h3-model-variant")?.value === FAST_H3_VARIANT;

  const help = $("#gen-h3-variant-help");

  if (help) {

    help.classList.toggle("hidden", !isH3 || (!fastSelected && fastReady));

    help.textContent = fastSelected && !fastReady
      ? fastFileReady && !fastNodeListed
        ? "FastH3 está instalado, mas o ComfyUI ainda não atualizou a lista do UNETLoader. Quando não houver geração em andamento, reinicie o ComfyUI para liberar o seletor."
        : "FastH3 está sendo instalado; a opção só será liberada após verificar o arquivo completo no runtime ativo."
      : fastSelected
          ? "FastH3 8-Step V2: texto ou imagem, primeiro/último quadro, 8 passos e áudio opcional. Ref2VA exige H3 Base."
          : fastReady
            ? "FastH3 está pronto para texto ou imagem, com áudio opcional. H3 Base continua disponível."
            : fastFileReady && !fastNodeListed
              ? "FastH3 está instalado, mas aguarda uma atualização segura do ComfyUI antes de liberar o seletor."
              : "FastH3 está sendo instalado; a opção só será liberada após verificar o arquivo completo no runtime ativo.";

  }

}


function syncMovaProfile() {
  $("#gen-end-image-label")?.classList.toggle("hidden", $("#gen-mode").value !== "video");
  $("#gen-video-conditioning-profile").disabled = false;
  $("#gen-base-image-title").textContent = "Imagem de origem";
  $("#gen-base-image-help").textContent = "Escolha a foto que será preservada.";
}

function applyGenModelPreset() {
  const mode = $("#gen-mode").value;
  const isVideoMode = mode === "video" || mode === "text_video";
  const model = ($("#gen-model").value || "").toLowerCase();
  $("#gen-width").disabled = false;
  $("#gen-height").disabled = false;
  $("#gen-steps").disabled = false;
  $("#gen-guidance").disabled = false;
  if (isVideoMode && state.selectedVideoEngineId === "minimax_h3") {
    applyH3QualityProfile();
    $("#gen-lora").value = "";
  } else if (["image", "edit", "marketing_card"].includes(mode) && model.startsWith("qwen_image_2.1")) {
    $("#gen-steps").value = 40;
    $("#gen-guidance").value = 1;
    $("#gen-lora").value = "";
  } else if (mode === "video" && model.includes("hunyuanvideo1.5")) {
    $("#gen-frames").value = 121;
    $("#gen-fps").value = 30;
    $("#gen-video-duration").value = 4;
    $("#gen-steps").value = 20;
    $("#gen-guidance").value = 6;
  }
  syncGenVideoTiming();
  syncGenMinimaxAudio();
  syncMovaProfile();
  $("#gen-h3-workflow")?.classList.toggle(
    "hidden",
    !isVideoMode || state.selectedVideoEngineId !== "minimax_h3",
  );
  $("#gen-h3-profile-field")?.classList.toggle("hidden", !isVideoMode || state.selectedVideoEngineId !== "minimax_h3");

  syncH3VariantControls();
}

function applyGenPreset() {
  const preset = GEN_PRESETS[$("#gen-preset")?.value || ""];
  if (!preset) return;
  $("#gen-mode").value = preset.mode || "video";
  syncGenMode({ resetVideoEngine: true });
  if (String(preset.model || "").toLowerCase().includes("minimax_h3")) {
    selectVideoEngine("minimax_h3");
  }
  const modelOptions = Array.from($("#gen-model").options).map((option) => option.value);
  if (preset.model && modelOptions.includes(preset.model)) $("#gen-model").value = preset.model;
  applyGenModelPreset();
  $("#gen-width").value = preset.width || 1280;
  $("#gen-height").value = preset.height || 720;
  $("#gen-frames").value = preset.frames || 121;
  $("#gen-fps").value = preset.fps || 30;
  $("#gen-video-duration").value = preset.duration || ((preset.frames - 1) / preset.fps) || 6;
  $("#gen-steps").value = preset.steps || 28;
  $("#gen-guidance").value = preset.guidance || 6;
  $("#gen-prompt").value = preset.prompt || "";
  $("#gen-negative").value = preset.negative || "";
  syncGenVideoTiming();
  syncMovaProfile();
  scheduleMovaProducerAnalysis();
}

function videoCameraInstruction(pose) {
  return ({
    "Zoom Out": "cinematic dolly out with real perspective change between foreground, middle ground and background",
    "Zoom In": "cinematic push in with real perspective change and controlled depth",
    "Pan Right": "tracking move to the right with coherent foreground and background separation",
    "Pan Left": "tracking move to the left with coherent foreground and background separation",
    "Pan Up": "camera rises through the scene with visible depth separation",
    "Pan Down": "camera descends through the scene with visible depth separation",
    "Static": "locked cinematic camera while existing scene elements move independently",
    "ClockWise (CW)": "clockwise cinematic orbit with real perspective change",
    "Anti Clockwise (ACW)": "counter-clockwise cinematic orbit with real perspective change",
  })[pose] || "cinematic camera movement with real perspective change";
}

function updateImagePreview(input, image, wrap) {
  const file = input?.files?.[0];
  if (image?._previewUrl) URL.revokeObjectURL(image._previewUrl);
  if (!file) {
    wrap?.classList.add("hidden");
    image?.removeAttribute("src");
    return;
  }
  const url = URL.createObjectURL(file);
  image._previewUrl = url;
  image.src = url;
  wrap?.classList.remove("hidden");
}

let movaProducerTimer = null;
let movaProducerSequence = 0;

function renderMovaProducerPlan(plan) {
  state.movaProducerPlan = plan || null;
  const summary = $("#gen-mova-producer-summary");
  const reason = $("#gen-mova-producer-reason");
  const applyButton = $("#gen-mova-producer-apply");
  if (!plan) {
    if (summary) summary.textContent = "Escreva o prompt para receber a duracao sugerida.";
    if (reason) reason.textContent = "O produtor mede fala, acao, reacao e mudanca final sem usar a GPU.";
    if (applyButton) applyButton.disabled = true;
    return;
  }
  const estimate = plan.estimated_generation_minutes || {};
  if (summary) {
    summary.textContent = `${plan.recommended_duration_seconds}s · ${plan.recommended_frames} quadros · 832x480 · ${plan.steps} passos · estimativa ${estimate.min}-${estimate.max} min`;
  }
  const policyNotes = [];
  if (plan.voice_contract?.human_pt_br_listening_required) {
    policyNotes.push("PT-BR obrigatório: entrega e upscale bloqueados até escuta humana");
  }
  if (plan.motion_contract?.locomotion_overridden) {
    policyNotes.push("caminhada/passos removidos: diálogo usa pés plantados e microações");
  }
  policyNotes.push(`pose final estável por ${plan.motion_contract?.required_final_hold_seconds || 0.75}s`);
  if (reason) reason.textContent = [...(plan.reasons || []), ...policyNotes].join(" · ");
  if (applyButton) applyButton.disabled = false;
}

function applyMovaProducerPlan() {
  const plan = state.movaProducerPlan;
  if (!plan) return;
  $("#gen-width").value = plan.resolution?.width || 832;
  $("#gen-height").value = plan.resolution?.height || 480;
  $("#gen-frames").value = plan.recommended_frames;
  $("#gen-fps").value = plan.fps || 24;
  $("#gen-video-duration").value = plan.recommended_duration_seconds || 6;
  $("#gen-steps").value = plan.steps || 25;
  $("#gen-guidance").value = 5;
  syncGenVideoTiming();
}

async function analyzeMovaPrompt({ apply = false } = {}) {
  const isMova = $("#gen-mode").value === "video" && $("#gen-model").value === "MOVA-720p";
  const prompt = $("#gen-prompt").value.trim();
  if (!isMova || !prompt) {
    renderMovaProducerPlan(null);
    return null;
  }
  const sequence = ++movaProducerSequence;
  const summary = $("#gen-mova-producer-summary");
  if (summary) summary.textContent = "Produtor analisando o contrato do take...";
  const payload = await fetchJson(`${API.studio}/api/generative/mova/producer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, fps: 24 }),
  });
  if (sequence !== movaProducerSequence) return null;
  renderMovaProducerPlan(payload.plan);
  if (apply) applyMovaProducerPlan();
  return payload.plan;
}

function scheduleMovaProducerAnalysis() {
  clearTimeout(movaProducerTimer);
  movaProducerTimer = setTimeout(() => {
    analyzeMovaPrompt().catch((error) => {
      renderMovaProducerPlan(null);
      const reason = $("#gen-mova-producer-reason");
      if (reason) reason.textContent = error.message;
    });
  }, 650);
}

async function runGen(event) {
  event.preventDefault();
  const prompt = $("#gen-prompt").value.trim();
  if (!prompt) return toast("Digite um prompt");
  const mode = $("#gen-mode").value;
  if (["music", "sfx"].includes(mode)) {
    const providerId = $("#gen-provider").value;
    const providerInfo = state.genStatus?.providers?.audio?.[providerId];
    if (!providerInfo?.configured) {
      return toast(providerInfo?.message || "Motor de áudio indisponível");
    }
  }
  const isVideoMode = mode === "video" || mode === "text_video";
  const isTextVideoMode = mode === "text_video";
  const engineId = state.selectedVideoEngineId;
  const selectedEngine = videoEngineById(engineId);
  const isMinimaxH3 = isVideoMode && engineId === "minimax_h3";

  const h3ModelVariant = isMinimaxH3 ? ($("#gen-h3-model-variant")?.value || "base") : "base";
  if (isVideoMode && !selectedEngine) return toast("Escolha MiniMax H3.");
  if (isVideoMode && selectedEngine.readiness?.production_ready !== true) {
    return toast(selectedEngine.readiness?.message || "O motor escolhido ainda não passou todos os gates de produção.");
  }

  if (h3ModelVariant === FAST_H3_VARIANT) {


    if (state.genStatus?.h3Workflow?.capabilities?.fastH3Ready !== true) return toast("FastH3 ainda não está completo no ComfyUI. Nenhum fallback será usado.");

  }
  if (isVideoMode) syncGenVideoTiming();
  const baseImage = isTextVideoMode ? null : ($("#gen-base-image")?.files?.[0] || null);
  const endImage = isTextVideoMode ? null : ($("#gen-end-image")?.files?.[0] || null);
  if (mode === "edit" && !baseImage) return toast("Selecione uma imagem base para editar");
  if (mode === "video" && !baseImage) return toast("Selecione a imagem-âncora para animar.");
  appendMessage("user", prompt);
  const fd = new FormData();
  ["mode", "model", "lora", "lora-strength", "width", "height", "steps", "guidance", "seed", "frames", "fps", "negative"].forEach((name) => {
    const field = $(`#gen-${name}`);
    if (field) fd.append(name.replace("-", "_"), field.value);
  });
  ["provider", "prompt-influence"].forEach((name) => {
    const field = $(`#gen-${name}`);
    if (field) fd.append(name.replace("-", "_"), field.value);
  });
  if (isTextVideoMode) fd.set("mode", "video");
  if (isVideoMode) {
    fd.append("engine_id", engineId);
    fd.append("video_duration", $("#gen-video-duration").value);
    if (isMinimaxH3) {
      fd.append("h3_quality_profile", $("#gen-h3-quality-profile")?.value || "h3_production");

      fd.append("h3_model_variant", h3ModelVariant);

      fd.append("h3_orientation", $("#gen-h3-orientation")?.value || "landscape");
      fd.append("enable_minimax_h3_native_audio", $("#gen-minimax-native-audio")?.checked ? "true" : "false");
      fd.append("enable_minimax_h3_live_preview", $("#gen-minimax-live-preview")?.checked ? "true" : "false");
    }
  } else {
    const modelDecidesDuration = mode === "music" && $("#gen-provider").value === "yue2_local"
      && $("#gen-music-duration-auto")?.checked;
    fd.append("duration", modelDecidesDuration ? "900" : $("#gen-duration").value);
    fd.append("music_duration_auto", String(Boolean(modelDecidesDuration)));
  }
  if (mode === "music" && ["ace_step_local", "yue2_local", "levo2_local"].includes($("#gen-provider").value)) {
    const instrumental = $("#gen-music-instrumental").checked;
    const yue = $("#gen-provider").value === "yue2_local";
    const action = yue ? $("#gen-music-action").value : "auto";
    const lyrics = instrumental ? "" : $("#gen-music-lyrics").value.trim();
    if (!instrumental && !lyrics && action !== "auto") return toast("Informe a letra para o modo manual ou use o modo automático.");
    if (yue && action === "generate" && (!$("#gen-music-abc-reviewed").checked || !$("#gen-music-abc").value.trim())) {
      return toast("Revise a partitura ABC e marque a confirmação antes de gerar áudio.");
    }
    fd.append("music_instrumental", String(instrumental));
    fd.append("music_lyrics", lyrics);
    fd.append("music_model", yue ? "" : $("#gen-music-model").value);
    fd.append("music_bpm", yue ? "0" : $("#gen-music-bpm").value);
    fd.append("music_action", action);
    fd.append("music_abc", yue && action === "generate" ? $("#gen-music-abc").value : "");
    fd.append("music_abc_reviewed", String(yue && action === "generate" && $("#gen-music-abc-reviewed").checked));
  }
  fd.append("loop", $("#gen-loop")?.checked ? "true" : "false");
  if (baseImage) fd.append("base_image", baseImage);
  if (endImage) fd.append("end_image", endImage);
  if (isVideoMode) {
    const pose = $("#gen-camera-pose").value;
    fd.append("camera_pose", pose);
    fd.append("camera_speed", $("#gen-camera-speed").value);
    fd.append("video_conditioning_profile", $("#gen-video-conditioning-profile").value);
    if (isTextVideoMode) {
      const textVideoPrompt = `${prompt}\nCamera direction: ${videoCameraInstruction(pose)}. Build the complete scene directly from this description with coherent subjects, action, composition, lighting and temporal continuity.`;
      fd.append("prompt", textVideoPrompt);
    } else {
      fd.append("prompt", prompt);
    }
  } else {
    fd.append("prompt", prompt);
  }
  try {
    setBusy($("#gen-submit"), true, isVideoMode ? "Gerando take" : "Criando");
    setGenProgress(1, "Iniciando geracao");
    const started = await fetchJson(`${API.studio}/api/generative/job`, { method: "POST", body: fd });
    loadGenJobs();
    let data = null;
    let pollFailureStartedAt = null;
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 1400));
      try {
        data = await fetchJson(`${API.studio}/api/generative/job/${started.job_id}`);
        pollFailureStartedAt = null;
      } catch (error) {
        const now = Date.now();
        if (pollFailureStartedAt === null) pollFailureStartedAt = now;
        if (now - pollFailureStartedAt >= 90000) {
          appendMessage(
            "assistant",
            `Acompanhamento pausado, mas o trabalho ${started.job_id} continua em Trabalhos recentes. Toque em Atualizar para reconectar.`
          );
          break;
        }
        setGenProgress(data?.progress || 0, "Conexao oscilou; reconectando automaticamente");
        continue;
      }
      setGenProgress(data.progress || 0, data.message || "Gerando");
      if (data.status === "done") {
        const result = data.result || {};
        if (result.provider === "yue2_local" && result.approval_status === "PENDING_SCORE_REVIEW" && result.music_abc) {
          $("#gen-music-abc").value = result.music_abc;
          $("#gen-music-abc-reviewed").checked = false;
          $("#gen-music-action").value = "generate";
          syncGenAudioProviderDetails();
        }
        const gate = result.approval_status ? `\nGate: ${result.approval_status}` : "";
        const resultText = result.music_action === "auto" ? result.message || "Música pronta para ouvir."
          : `${result.message || "Pronto."}\nSeed: ${result.seed ?? "--"}${result.lora ? `\nLoRA: ${result.lora}` : ""}${gate}`;
        appendMessage("assistant", resultText, result.outputs || []);
        break;
      }
      if (data.status === "canceled") {
        appendMessage("assistant", "Trabalho cancelado. Os parametros continuam disponiveis no historico para tentar novamente.");
        break;
      }
      if (data.status === "error" || data.status === "interrupted") {
        throw new Error(data.error || data.message || "Geracao interrompida");
      }
    }
  } catch (error) {
    appendMessage("assistant", `ERRO: ${error.message}`);
  } finally {
    setBusy($("#gen-submit"), false);
    setTimeout(hideGenProgress, 1800);
    loadGenJobs();
  }
}

function assetDate(timestamp) {
  const date = new Date(Number(timestamp || 0) * 1000);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function assetSize(bytes) {
  const value = Number(bytes || 0);
  if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  if (value >= 1024) return `${Math.round(value / 1024)} KB`;
  return `${value} B`;
}

function assetKindLabel(kind) {
  return ({ image: "Imagem", video: "Video", audio: "Audio" })[kind] || "Arquivo";
}

function assetReviewLabel(item) {
  if (item?.source !== "music_reinstrument") return "";
  return ({
    PENDING_HUMAN_REVIEW: "Aguardando sua escuta",
    OWNER_APPROVED_FINAL: "Master aprovado",
  })[item.review_status] || "Candidato de reinstrumentação";
}

async function loadAssets() {
  const grid = $("#asset-grid");
  if (!grid) return;
  grid.setAttribute("aria-busy", "true");
  grid.innerHTML = '<div class="asset-empty" role="status">Carregando biblioteca...</div>';
  const query = new URLSearchParams({
    page: String(state.assets.page),
    page_size: String(state.assets.pageSize),
  });
  if (state.assets.kind) query.set("kind", state.assets.kind);
  try {
    const payload = await fetchJson(`${API.studio}/api/generative/assets?${query}`);
    const assets = payload.items || [];
    state.assets.total = Number(payload.total || 0);
    $("#assets-count").textContent = `${payload.total || 0} arquivos recentes`;
    $("#assets-page").textContent = `Pagina ${payload.page || state.assets.page}`;
    $("#assets-prev").disabled = state.assets.page <= 1;
    $("#assets-next").disabled = state.assets.page * state.assets.pageSize >= state.assets.total;
    if (!assets.length) {
      grid.innerHTML = '<div class="asset-empty" role="status">Nenhum arquivo neste filtro.</div>';
      return;
    }
    grid.innerHTML = assets.map((item) => {
      const src = `${API.studio}${item.url}`;
      let preview = `<div class="asset-generic">${html(assetKindLabel(item.kind))}</div>`;
      if (item.kind === "image") {
        preview = `<img src="${html(src)}" alt="${html(item.filename)}" loading="lazy">`;
      } else if (item.kind === "video") {
        preview = `<video src="${html(src)}" controls preload="none" playsinline></video>`;
      } else if (item.kind === "audio") {
        preview = `<div class="asset-audio-mark" aria-hidden="true">AUDIO</div><audio src="${html(src)}" controls preload="none"></audio>`;
      }
      return `<article class="asset-card">
        <div class="asset-preview">${preview}</div>
        <div class="asset-card-body">
          <div class="asset-card-title"><strong title="${html(item.filename)}">${html(item.filename)}</strong><span>${html(assetKindLabel(item.kind))}${assetReviewLabel(item) ? ` · ${html(assetReviewLabel(item))}` : ""}</span></div>
          <small>${html(assetDate(item.modified_at))} · ${html(assetSize(item.size))}</small>
          <a class="output-link" href="${html(src)}" target="_blank" rel="noopener">Abrir arquivo</a>
        </div>
      </article>`;
    }).join("");
  } catch (error) {
    $("#assets-count").textContent = "Falha ao carregar";
    grid.innerHTML = `<div class="asset-empty" role="alert">${html(error.message)}</div>`;
  } finally {
    grid.removeAttribute("aria-busy");
  }
}

function selectAssetKind(button) {
  state.assets.kind = button.dataset.assetKind || "";
  state.assets.page = 1;
  $$('[data-asset-kind]').forEach((item) => {
    const active = item === button;
    item.classList.toggle("active", active);
    item.setAttribute("aria-pressed", active ? "true" : "false");
  });
  loadAssets();
}

function changeAssetPage(delta) {
  const next = Math.max(1, state.assets.page + delta);
  if (delta > 0 && state.assets.page * state.assets.pageSize >= state.assets.total) return;
  state.assets.page = next;
  loadAssets();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

const FILM_TAKE_STATUSES = [
  ["PLANNED", "Aguardando vídeo"],
  ["IN_PRODUCTION", "Preparando produção"],
  ["QUEUED", "Aguardando na fila"],
  ["GENERATING", "Sendo produzido"],
  ["READY", "Pronto para você decidir"],
  ["APPROVED", "Aprovado"],
  ["REJECTED", "Reprovado — precisa correção"],
  ["UPSCALING", "Aplicando acabamento a 60 FPS"],
  ["FINAL", "Arquivo final"],
  ["ERROR", "Erro — veja o motivo"],
];

const FILM_TAKE_REVIEW_STATUSES = new Set(["READY", "APPROVED", "REJECTED", "FINAL"]);
const FILM_DIRECTOR_UNDELIVERED_STATUSES = new Set(["PENDING", "IN_PROGRESS"]);
const FILM_REQUEST_AWAITING_EXECUTOR_COPY = "Pedido registrado, aguardando executor";

function filmDirectorRequestAwaitingExecutor(request) {
  const status = String(request?.status || "").trim().toUpperCase();
  const category = String(request?.category || "").trim().toUpperCase();
  return status === "PENDING" || (category === "ANCHOR" && status === "IN_PROGRESS");
}

function filmDirectorRequestLabel(request) {
  if (filmDirectorRequestAwaitingExecutor(request)) return "Pedido registrado";
  return ({
    IN_PROGRESS: "Em correção",
  })[request?.status] || "Explicar correção (1/2)";
}

function filmDirectorStatusLabel(request) {
  const status = typeof request === "object"
    ? String(request?.status || "").trim().toUpperCase()
    : String(request || "").trim().toUpperCase();
  if (filmDirectorRequestAwaitingExecutor(
    typeof request === "object" ? request : { status },
  )) return "Aguardando executor";
  return ({
    IN_PROGRESS: "Em andamento",
    DELIVERED: "Entregue",
    CANCELLED: "Cancelado",
    SUPERSEDED: "Substituído",
  })[status] || status || "Registrado";
}

function filmDirectorAcknowledgementMarkup(take, { compact = false } = {}) {
  const request = take?.directorRequest;
  const requestId = String(request?.requestId || "").trim();
  if (!requestId) return "";
  const status = String(request?.status || "").trim().toUpperCase();
  const heading = filmDirectorRequestAwaitingExecutor(request)
    ? FILM_REQUEST_AWAITING_EXECUTOR_COPY
    : status === "IN_PROGRESS"
      ? "Correção vinculada à produção"
      : "Pedido ao diretor atualizado";
  return `<div class="film-director-ack${compact ? " compact" : ""}" role="status" data-film-director-ack="${html(requestId)}">
    <strong>${html(heading)}</strong>
    <span>Take ${html(take.takeId)} · ${html(filmDirectorStatusLabel(request))}</span>
    <code title="requestId">${html(requestId)}</code>
  </div>`;
}

function filmDirectorStatusCardMarkup() {
  const undeliveredRequests = state.films.takes
    .filter((take) => take?.directorRequest?.requestId && FILM_DIRECTOR_UNDELIVERED_STATUSES.has(String(take.directorRequest.status || "").toUpperCase()))
    .sort((left, right) => String(right.directorRequest.updatedAt || "").localeCompare(String(left.directorRequest.updatedAt || "")));
  if (!undeliveredRequests.length) return "";
  return `<section class="film-director-status-card" id="film-director-status-card" aria-label="Pedidos registrados sem entrega">
    <div class="film-director-status-head"><strong>Pedidos registrados</strong><span>${undeliveredRequests.length} sem entrega</span></div>
    <div class="film-director-status-list">${undeliveredRequests.slice(0, 3).map((take) => filmDirectorAcknowledgementMarkup(take, { compact: true })).join("")}</div>
    ${undeliveredRequests.length > 3 ? `<span class="film-director-status-more">Mais ${undeliveredRequests.length - 3} pedido${undeliveredRequests.length - 3 === 1 ? "" : "s"} sem entrega nos respectivos takes.</span>` : ""}
  </section>`;
}

function filmTakeStatusOptions(take) {
  const selectable = take.hasPreview
    ? FILM_TAKE_STATUSES.filter(([value]) => FILM_TAKE_REVIEW_STATUSES.has(value))
    : [];
  if (!selectable.some(([value]) => value === take.status)) {
    const current = FILM_TAKE_STATUSES.find(([value]) => value === take.status);
    if (current) selectable.unshift(current);
  }
  return selectable.length ? selectable : [[take.status || "PLANNED", filmTakeStatusLabel(take.status)]];
}

function filmTakeActionLabel(take, engineReady) {
  const engine = String(take?.engine || "motor de vídeo");
  if (take.status === "QUEUED") return "Na fila...";
  if (take.status === "GENERATING") return "Gerando...";
  if (take.status === "UPSCALING") return "Upscale na fila...";
  if (take.hasUpscalePreview) return "Decida o FHD primeiro";
  if (filmTakeAnchorReviewPending(take)) return "Aprove a foto-base";
  if (filmAnchorRequestAwaitingExecutor(take)) return "Aguardando executor";
  if (filmTakeAnchorPending(take)) return "Peça a foto-base";
  if (!filmTakeEngineKey(take)) return "Escolha o motor";
  if (!engineReady) return `${engine} indisponível`;
  if (!take.canGenerate) return "Base pendente";
  if (take.status === "REJECTED") return "Gerar substituto";
  if (["READY", "APPROVED", "FINAL"].includes(take.status)) return `Nova variante ${engine}`;
  return `Gerar no ${engine}`;
}

function filmTakeStatusLabel(status) {
  return FILM_TAKE_STATUSES.find(([value]) => value === status)?.[1] || status || "—";
}

function filmTakeDisplayName(take) {
  const value = String(take?.name || `Take ${take?.takeId || ""}`).replaceAll("_", " ").trim();
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : "Take";
}

function filmTakeEngineKey(take) {
  const profile = String(take?.generationProfile || "").toLowerCase();
  const engine = String(take?.engine || "").toLowerCase();
  if (profile.includes("minimax_h3") || engine.includes("minimax h3")) return "minimax_h3";
  if (profile.includes("ltx25") || engine.includes("ltx 2.5")) return "ltx_2_5";
  return "";
}

function filmTakeEngineReady(take) {
  const videoMethod = state.genStatus?.quality?.video_method || {};
  const readiness = videoMethod.engine_readiness;
  const engineKey = filmTakeEngineKey(take);
  if (engineKey && readiness && Object.prototype.hasOwnProperty.call(readiness, engineKey)) {
    return readiness[engineKey] === true;
  }
  if (readiness && !engineKey) return false;
  return videoMethod.engine_ready === true;
}

function filmTakeProductionEligible(take) {
  if (
    !take?.canGenerate
    || take.hasUpscalePreview
    || ["QUEUED", "GENERATING", "UPSCALING"].includes(take.status)
  ) return false;
  if (!take.hasPreview) return true;
  if (take.status === "ERROR") return true;
  if (take.status === "REJECTED") {
    return ["PENDING", "IN_PROGRESS", "DELIVERED"].includes(take.directorRequest?.status)
      || String(take.qcStatus || "").toLowerCase().includes("rerender_required");
  }
  return false;
}

function filmTakeCorrectionRetry(take) {
  return ["ERROR", "REJECTED"].includes(String(take?.status || "").trim().toUpperCase());
}

function filmProductionBatchPlan() {
  const project = state.films.projects.find((item) => item.projectId === state.films.activeProjectId) || {};
  const policy = project.productionBatch || {};
  const allEligible = state.films.takes.filter(filmTakeProductionEligible);
  if (policy.enabled !== true) {
    return {
      selected: allEligible,
      batchIds: allEligible.map((take) => take.takeId),
      blockedIds: [],
      totalEligible: allEligible.length,
      requiredCount: allEligible.length,
      ready: allEligible.length > 0,
      incomplete: false,
      incompleteCorrectionBatch: false,
    };
  }

  const requestedOrder = Array.isArray(policy.renderOrder) ? policy.renderOrder.map(String) : [];
  const byId = new Map(state.films.takes.map((take) => [String(take.takeId), take]));
  const orderedIds = [...new Set([
    ...requestedOrder.filter((takeId) => byId.has(takeId)),
    ...state.films.takes.map((take) => String(take.takeId)),
  ])];
  const eligibleById = new Map(allEligible.map((take) => [String(take.takeId), take]));
  const rawBatchSize = Number(policy.batchSize || 3);
  const batchSize = Math.max(1, Math.min(20, Number.isFinite(rawBatchSize) ? rawBatchSize : 3));
  const finalize = (selected, batchIds, blockedIds) => {
    const correctionOnly = selected.length > 0 && selected.every(filmTakeCorrectionRetry);
    const incompleteCorrectionBatch = policy.allowIncompleteCorrectionBatch === true
      && correctionOnly
      && selected.length < batchSize;
    const incomplete = policy.requireFullBatch === true
      && selected.length !== batchSize
      && !incompleteCorrectionBatch;
    return {
      selected,
      batchIds,
      blockedIds,
      totalEligible: allEligible.length,
      requiredCount: batchSize,
      ready: selected.length > 0 && blockedIds.length === 0 && !incomplete,
      incomplete,
      incompleteCorrectionBatch,
    };
  };
  const firstIndex = orderedIds.findIndex((takeId) => eligibleById.has(takeId));
  if (firstIndex < 0) {
    return finalize([], [], []);
  }
  if (
    policy.allowIncompleteCorrectionBatch === true
    && filmTakeCorrectionRetry(eligibleById.get(orderedIds[firstIndex]))
  ) {
    const selected = [];
    const batchIds = [];
    for (const takeId of orderedIds.slice(firstIndex)) {
      const take = eligibleById.get(takeId);
      if (!take || !filmTakeCorrectionRetry(take)) break;
      selected.push(take);
      batchIds.push(takeId);
      if (selected.length >= batchSize) break;
    }
    return finalize(selected, batchIds, []);
  }
  if (policy.fillEligibleAcrossBatches === true) {
    const selected = [];
    const batchIds = [];
    const blockedIds = [];
    for (const takeId of orderedIds.slice(firstIndex)) {
      const take = byId.get(takeId);
      if (eligibleById.has(takeId)) {
        selected.push(eligibleById.get(takeId));
        batchIds.push(takeId);
        if (selected.length >= batchSize) break;
        continue;
      }
      if (take && !take.canGenerate && !take.hasPreview) {
        batchIds.push(takeId);
        blockedIds.push(takeId);
        if (policy.strictContiguous !== false && policy.requireAllBaseImagesReady !== false) {
          return finalize(selected, batchIds, blockedIds);
        }
      }
    }
    return finalize(selected, batchIds, blockedIds);
  }
  const batchStart = Math.floor(firstIndex / batchSize) * batchSize;
  const batchIds = orderedIds.slice(batchStart, batchStart + batchSize);
  const blockedIds = batchIds.filter((takeId) => {
    const take = byId.get(takeId);
    return take && !take.canGenerate && !take.hasPreview;
  });
  const selected = batchIds
    .filter((takeId) => eligibleById.has(takeId))
    .map((takeId) => eligibleById.get(takeId));
  return finalize(selected, batchIds, blockedIds);
}

function filmTakeAnchorPending(take) {
  if (
    take?.hasEndKeyframeCandidate
    && String(take?.qcStatus || "") === "anchor_delivered_pending_user_approval"
  ) return false;
  if (typeof take?.canRequestAnchor === "boolean") return take.canRequestAnchor;
  const status = String(take?.status || "").trim().toUpperCase();
  const qcStatus = String(take?.qcStatus || "").trim().toLowerCase();
  return Boolean(
    status === "PLANNED"
    && !take.keyframeApproved
    && !take.hasPreview
    && (
      !take.hasKeyframe
      || qcStatus.startsWith("waiting_derived_anchor")
    ),
  );
}

function filmTakeAnchorReviewPending(take) {
  return Boolean(
    ((take?.hasKeyframe && !take.keyframeApproved) || take?.hasEndKeyframeCandidate)
    && String(take.qcStatus || "") === "anchor_delivered_pending_user_approval",
  );
}

function filmTakeHasRegisteredAnchor(take) {
  return Boolean(
    (take?.hasKeyframe || take?.hasEndKeyframeCandidate)
    && take?.directorRequest?.category === "ANCHOR"
    && take?.directorRequest?.requestId
    && ["anchor_delivered_pending_user_approval", "anchor_approved_for_video"].includes(String(take.qcStatus || "")),
  );
}

function filmAnchorReviewRequestId(take) {
  return String(take?.anchorCandidate?.requestId || take?.directorRequest?.requestId || "").trim();
}

function filmTakeAnchorUnresolved(take) {
  return filmTakeAnchorPending(take) || filmTakeAnchorReviewPending(take);
}

function filmAnchorRequestAwaitingExecutor(take) {
  return Boolean(
    filmTakeAnchorPending(take)
    && String(take?.directorRequest?.category || "").trim().toUpperCase() === "ANCHOR"
    && FILM_DIRECTOR_UNDELIVERED_STATUSES.has(
      String(take?.directorRequest?.status || "").trim().toUpperCase(),
    ),
  );
}

function filmAnchorWorkflowState(take) {
  if (take?.keyframeApproved && take?.canGenerate) {
    return { state: "approved", copy: "Foto aprovada, pronta para vídeo" };
  }
  if (filmTakeAnchorReviewPending(take)) {
    return { state: "review", copy: "Foto entregue, aguardando aprovação" };
  }
  if (filmAnchorRequestAwaitingExecutor(take)) {
    return { state: "awaiting_executor", copy: FILM_REQUEST_AWAITING_EXECUTOR_COPY };
  }
  if (filmTakeAnchorPending(take)) {
    return { state: "needed", copy: "Foto-base necessária" };
  }
  return { state: "none", copy: "" };
}

function filmAnchorRequestReason(take) {
  const objective = String(take?.objective || "").trim();
  const notes = String(take?.notes || "").trim();
  return [
    `Preparar uma imagem-âncora própria e aprovada para o take ${take?.takeId || ""} — ${filmTakeDisplayName(take)}.`,
    objective ? `Objetivo visual: ${objective}` : "",
    notes ? `Observação de produção: ${notes}` : "",
    "Preservar identidade, composição, paleta e iluminação do mundo de referência; criar o novo ponto de vista necessário sem repetir cegamente a foto anterior.",
  ].filter(Boolean).join(" ").slice(0, 2000);
}

function clampFilmProgress(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function filmProgressMarkup(percent, {
  heading = "Andamento",
  detail = "",
  tone = "active",
  className = "",
  ariaLabel = "",
} = {}) {
  const value = clampFilmProgress(percent);
  const classes = ["film-progress", `film-progress-${tone}`, className].filter(Boolean).join(" ");
  return `<div class="${html(classes)}">
    <div class="film-progress-copy"><span>${html(heading)}</span><strong>${value}%</strong></div>
    <div class="film-progress-track" role="progressbar" aria-label="${html(ariaLabel || `${heading}: ${value}%`)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}" data-film-progress-value="${value}"><span></span></div>
    ${detail ? `<span class="film-progress-detail">${html(detail)}</span>` : ""}
  </div>`;
}

function syncFilmProgressWidths(root = document) {
  root.querySelectorAll?.("[data-film-progress-value]").forEach((track) => {
    const fill = track.querySelector("span");
    if (fill) fill.style.width = `${clampFilmProgress(track.dataset.filmProgressValue)}%`;
  });
}

function filmActiveProjectQueueItems() {
  const projectId = String(state.films.activeProjectId || "");
  return (state.films.productionQueueData?.items || []).filter((item) => (
    String(item?.projectId || "") === projectId
  ));
}

function filmTakeQueueItem(take) {
  const projectId = String(state.films.activeProjectId || "");
  const takeId = String(take?.takeId || "");
  const candidates = (state.films.productionQueueData?.items || []).filter((item) => (
    String(item?.projectId || "") === projectId
    && String(item?.takeId || "") === takeId
  ));
  if (!candidates.length) return null;
  const jobId = String(take?.lastJobId || "");
  const exact = jobId && candidates.find((item) => String(item?.jobId || "") === jobId);
  if (exact) return exact;
  const wantedKind = take?.status === "UPSCALING" ? "video_upscale" : "video_take";
  return candidates.find((item) => item?.jobKind === wantedKind) || candidates[0];
}

function filmTakeProgress(take) {
  const status = String(take?.status || "PLANNED");
  const queueItem = filmTakeQueueItem(take);
  const runningNow = queueItem?.state === "RUNNING";
  const jobProgress = runningNow ? clampFilmProgress(queueItem?.progress || 0) : 0;
  const queuePosition = Number(queueItem?.position || 0);

  if (status === "ERROR" && !queueItem) {
    return {
      percent: 0,
      heading: "Produção interrompida",
      label: String(take?.lastError || "O job terminou com erro; nenhum vídeo novo foi entregue."),
      tone: "danger",
    };
  }

  if (queueItem?.jobKind === "video_upscale") {
    return {
      percent: jobProgress,
      heading: "Acabamento 60 FPS",
      label: runningNow
        ? `Processamento em andamento · estimativa do job ${jobProgress}%`
        : `Ainda não iniciado${queuePosition ? ` · posição ${queuePosition} na fila` : ""}`,
      tone: runningNow ? "active" : "warning",
    };
  }
  if (take?.hasUpscalePreview) {
    return {
      percent: 100,
      heading: "Acabamento 60 FPS",
      label: "Candidato FHD pronto · aguardando sua aprovação",
      tone: "warning",
    };
  }
  if (take?.isUpscaled) {
    return { percent: 100, heading: "Acabamento 60 FPS", label: "Acabamento concluído", tone: "success" };
  }
  if (queueItem?.jobKind === "video_take") {
    return {
      percent: jobProgress,
      heading: "Produção do vídeo",
      label: runningNow
        ? `Render em andamento · estimativa do job ${jobProgress}%`
        : `Ainda não iniciado${queuePosition ? ` · posição ${queuePosition} na fila` : ""}`,
      tone: runningNow ? "active" : "warning",
    };
  }
  if (take?.hasPreview) {
    return {
      percent: 100,
      heading: "Produção do vídeo",
      label: status === "REJECTED" ? "Vídeo produzido · correção solicitada" : "Vídeo produzido",
      tone: status === "REJECTED" ? "danger" : "success",
    };
  }
  const anchorWorkflow = filmAnchorWorkflowState(take);
  if (anchorWorkflow.state === "review") {
    return { percent: 0, heading: "Pré-requisito do vídeo", label: anchorWorkflow.copy, tone: "warning" };
  }
  if (anchorWorkflow.state === "awaiting_executor") {
    return { percent: 0, heading: "Pré-requisito do vídeo", label: `${anchorWorkflow.copy} · vídeo ainda não iniciado`, tone: "warning" };
  }
  if (anchorWorkflow.state === "needed") {
    return { percent: 0, heading: "Pré-requisito do vídeo", label: anchorWorkflow.copy, tone: "warning" };
  }
  if (take?.keyframeApproved || take?.canGenerate) {
    return { percent: 0, heading: "Produção do vídeo", label: "Imagem-base aprovada · render ainda não iniciado", tone: "warning" };
  }
  return { percent: 0, heading: "Produção do vídeo", label: "Preparação ainda não concluída", tone: "warning" };
}

function filmTakeIsProjectFinalOutput(take) {
  return String(take?.takeId || "").trim().toUpperCase() === "MASTER";
}

function filmProductionTakes() {
  return state.films.takes.filter((take) => !filmTakeIsProjectFinalOutput(take));
}

function filmProjectProgress() {
  // Rejected takes remain preserved in history, but do not dilute active work.
  const takes = filmProductionTakes().filter((take) => take?.status !== "REJECTED");
  if (!takes.length) return { percent: 0, detail: "Nenhum take cadastrado.", tone: "warning" };
  const completedStatuses = new Set(["READY", "APPROVED", "FINAL"]);
  const readyVideos = takes.filter((take) => (
    take?.hasPreview && completedStatuses.has(String(take?.status || ""))
  )).length;
  const failedTakes = takes.filter((take) => String(take?.status || "") === "ERROR").length;
  const runningFractions = takes.reduce((sum, take) => {
    if (take?.hasPreview) return sum;
    const item = filmTakeQueueItem(take);
    if (item?.jobKind !== "video_take" || item?.state !== "RUNNING") return sum;
    return sum + (clampFilmProgress(item.progress || 0) / 100);
  }, 0);
  const percent = Math.round(((readyVideos + runningFractions) / takes.length) * 100);
  const anchorReview = takes.filter(filmTakeAnchorReviewPending).length;
  const anchorAwaitingExecutor = takes.filter(
    (take) => filmAnchorWorkflowState(take).state === "awaiting_executor",
  ).length;
  const activeJobs = filmActiveProjectQueueItems().length;
  const details = [
    `${readyVideos}/${takes.length} vídeos produzidos`,
    activeJobs ? `${activeJobs} job${activeJobs === 1 ? "" : "s"} na produção` : "",
    failedTakes ? `${failedTakes} ${failedTakes === 1 ? "job falhou" : "jobs falharam"}` : "",
    anchorReview ? `${anchorReview} ${anchorReview === 1 ? "imagem" : "imagens"} para decidir` : "",
    anchorAwaitingExecutor ? `${FILM_REQUEST_AWAITING_EXECUTOR_COPY} · ${anchorAwaitingExecutor} foto${anchorAwaitingExecutor === 1 ? "-base" : "s-base"}` : "",
  ].filter(Boolean);
  return {
    percent,
    detail: details.join(" · "),
    tone: percent === 100 ? "success" : (failedTakes && !activeJobs ? "danger" : "active"),
  };
}

function syncFilmProjectProgress() {
  const container = document.querySelector(".film-project-progress");
  if (!container) return;
  const progress = filmProjectProgress();
  container.outerHTML = filmProgressMarkup(progress.percent, {
    heading: "Produção dos vídeos",
    detail: progress.detail,
    tone: progress.tone,
    className: "film-metric film-project-progress",
    ariaLabel: `Vídeos produzidos no projeto: ${progress.percent}%`,
  });
  syncFilmProgressWidths(document.querySelector("#film-metrics"));
}

function syncFilmTakeProgressBars() {
  state.films.takes.forEach((take) => {
    const card = document.querySelector(`[data-film-take-card="${CSS.escape(String(take.takeId || ""))}"]`);
    const current = card?.querySelector(".film-take-progress");
    if (!current) return;
    const progress = filmTakeProgress(take);
    current.outerHTML = filmProgressMarkup(progress.percent, {
      heading: progress.heading,
      detail: progress.label,
      tone: progress.tone,
      className: "film-take-progress",
      ariaLabel: `Take ${take.takeId}: ${progress.percent}%`,
    });
  });
  syncFilmProgressWidths(document.querySelector("#film-takes-list"));
}

const FILM_WORKFLOW_VIEWS = new Set(["review", "production", "all", "approved", "rejected"]);

function filmTakeNeedsReview(take) {
  // Owner archived the six accepted Thiago shots; only the two replacements remain in review.
  if (state.films.activeProjectId === "thiago_apresentacao_master_review_20260929") {
    if (["APPROVED", "FINAL"].includes(take?.status)) return false;
    if (["T02", "T05"].includes(take?.takeId)) return true;
  }
  return Boolean(take?.hasUpscalePreview)
    || filmTakeAnchorReviewPending(take)
    || Boolean(
      take?.hasPreanalysisGallery
      && String(take?.preanalysisGallery?.humanApproval || "").toUpperCase() === "PENDING"
    )
    || Boolean(take?.audioCandidateNeedsReview)
    || Boolean(
      take?.hasPreview
      // A rejection is already an owner decision. Keep it in history, never
      // send it back to the active review queue.
      && String(take?.status || "").trim().toUpperCase() === "READY"
    );
}

function filmTakeMatchesView(take, view = state.films.view) {
  if (filmTakeIsProjectFinalOutput(take)) return false;
  if (state.films.activeProjectId === "thiago_apresentacao_master_review_20260929"
      && view === "all" && ["APPROVED", "FINAL"].includes(take?.status)) return false;
  if (view === "review") return filmTakeNeedsReview(take);
  if (view === "approved") return ["APPROVED", "FINAL"].includes(take?.status);
  if (view === "rejected") return String(take?.status || "").trim().toUpperCase() === "REJECTED";
  return true;
}

function visibleFilmTakes(view = state.films.view) {
  return state.films.takes.filter((take) => filmTakeMatchesView(take, view));
}

function filmWorkflowViewHasContent(view) {
  const takes = filmProductionTakes();
  if (view === "review") return takes.some(filmTakeNeedsReview);
  if (view === "approved") return takes.some((take) => ["APPROVED", "FINAL"].includes(take?.status));
  if (view === "rejected") return takes.some((take) => String(take?.status || "").trim().toUpperCase() === "REJECTED");
  if (view === "production") {
    return filmActiveProjectQueueItems().length > 0
      || takes.some((take) => (
        filmTakeProductionEligible(take)
        || filmTakeAnchorUnresolved(take)
        || take.canUpscale
      ));
  }
  if (view === "all") return takes.length > 0;
  return false;
}

function defaultFilmWorkflowView() {
  const takes = filmProductionTakes();
  if (takes.some(filmTakeNeedsReview)) return "review";
  if (takes.some((take) => filmTakeProductionEligible(take) || filmTakeAnchorUnresolved(take) || take.canUpscale)) return "production";
  if (takes.some((take) => ["APPROVED", "FINAL"].includes(take.status))) return "approved";
  return "all";
}

function syncFilmWorkflowTabs() {
  const view = FILM_WORKFLOW_VIEWS.has(state.films.view) ? state.films.view : "review";
  const takes = filmProductionTakes();
  const reviewCount = takes.filter(filmTakeNeedsReview).length;
  const approvedCount = takes.filter((take) => ["APPROVED", "FINAL"].includes(take.status)).length;
  const rejectedCount = takes.filter((take) => String(take?.status || "").trim().toUpperCase() === "REJECTED").length;
  const queuedCount = filmActiveProjectQueueItems().length;
  const productionCount = queuedCount
    + takes.filter(filmTakeProductionEligible).length
    + takes.filter(filmTakeAnchorUnresolved).length
    + takes.filter((take) => take.canUpscale).length;
  const counts = { review: reviewCount, production: productionCount, all: visibleFilmTakes("all").length, approved: approvedCount, rejected: rejectedCount };
  Object.entries(counts).forEach(([name, count]) => {
    const target = $(`#film-view-${name}-count`);
    if (target) target.textContent = String(count);
  });
  $$('[data-film-view]').forEach((button) => {
    const active = button.dataset.filmView === view;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  const filmsActive = $("#section-films")?.classList.contains("active") === true;
  const productionShortcut = $("#mobile-production-link");
  const takesShortcut = $('.nav-link[data-section="films"]');
  if (productionShortcut) {
    const active = filmsActive && view === "production";
    productionShortcut.classList.toggle("active", active);
    productionShortcut.setAttribute("aria-pressed", active ? "true" : "false");
    if (active) productionShortcut.setAttribute("aria-current", "page");
    else productionShortcut.removeAttribute("aria-current");
  }
  if (takesShortcut && filmsActive) {
    const active = view !== "production";
    takesShortcut.classList.toggle("active", active);
    if (active) takesShortcut.setAttribute("aria-current", "page");
    else takesShortcut.removeAttribute("aria-current");
  }
  const production = $("#film-production-queue");
  const watch = $("#film-preview-panel");
  if (production) production.classList.toggle("hidden", view !== "production");
  if (watch) watch.classList.toggle("hidden", view === "production");
  const help = $("#film-workflow-help");
  if (help) help.textContent = ({
    review: reviewCount ? "Abra o vídeo ou a nova imagem e escolha aprovar ou pedir outra versão." : "Nada esperando sua decisão. Veja Ações ou Aprovados.",
    production: productionCount ? "Aqui você pede fotos-base, produz pendentes e faz upscaling obrigatório." : "A fila está livre e não há ações pendentes.",
    all: "Veja todos os takes e abra qualquer um para conferir.",
    approved: approvedCount ? "Estes takes já foram aprovados por você." : "Nenhum take aprovado ainda.",
    rejected: rejectedCount ? "Histórico preservado: estes vídeos foram rejeitados e estão bloqueados para a montagem." : "Nenhum take rejeitado neste projeto.",
  })[view];
}

function setFilmWorkflowView(view, { remember = true } = {}) {
  state.films.view = FILM_WORKFLOW_VIEWS.has(view) ? view : defaultFilmWorkflowView();
  if (remember) {
    try { window.localStorage.setItem("maestro-film-view", state.films.view); } catch (_error) { /* armazenamento opcional */ }
  }
  syncFilmWorkflowTabs();
  if (state.films.view === "production") {
    closeFilmTakePreview();
    renderFilmTakes();
    return;
  }
  renderFilmTakes();
  const takes = visibleFilmTakes();
  const selected = takes.find((take) => take.takeId === state.films.activeTakeId) || takes[0];
  if (selected) openFilmTakePreview(selected.takeId, { autoplay: false, scroll: false, refreshList: false });
  else closeFilmTakePreview();
}

function syncFilmBatchActions() {
  const production = $("#film-batch-production");
  const upscale = $("#film-batch-upscale");
  const help = $("#film-batch-help");
  const anchorPanel = $("#film-anchor-batch");
  const anchorButton = $("#film-batch-anchors");
  const anchorCopy = $("#film-anchor-batch-copy");
  if (!production || !upscale || !help) return;
  const hasProject = Boolean(state.films.activeProjectId);
  const activeProject = state.films.projects.find((item) => item.projectId === state.films.activeProjectId) || {};
  const resolution = $("#film-upscale-resolution");
  if (resolution) {
    const final = activeProject.final || {};
    resolution.value = `${final.width || 1920}x${final.height || 1080}`;
    resolution.disabled = !hasProject || filmActiveProjectQueueItems().length > 0;
  }
  const anchorGeneration = activeProject.anchorGeneration || {};
  const codexImagegenOnly = anchorGeneration.localExecutorAllowed === false
    && anchorGeneration.provider === "codex_builtin_imagegen";
  const productionPlan = filmProductionBatchPlan();
  const productionCount = productionPlan.selected.length;
  const productionReady = productionPlan.ready === true;
  const upscaleCount = state.films.takes.filter((take) => take.canUpscale).length;
  const anchorPendingCount = state.films.takes.filter(filmTakeAnchorPending).length;
  const anchorReviewCount = state.films.takes.filter(filmTakeAnchorReviewPending).length;
  const anchorCount = anchorPendingCount + anchorReviewCount;
  const anchorRequestCount = state.films.takes.filter(filmAnchorRequestAwaitingExecutor).length;
  const anchorToRequestCount = anchorPendingCount - anchorRequestCount;
  const engineReady = productionPlan.selected.length > 0
    && productionPlan.selected.every(filmTakeEngineReady);
  const projectEngine = String(state.films.takes[0]?.engine || "motor de vídeo");
  const activeProjectJobs = filmActiveProjectQueueItems().length;
  const projectDataLoading = state.films.projectDataLoading === true;
  const projectDataError = String(state.films.projectDataError || "").trim();
  const productionSubmitting = state.films.batchInFlight.production === true;
  const upscaleSubmitting = state.films.batchInFlight.upscale === true;
  const activeJobsLabel = `${activeProjectJobs} job${activeProjectJobs === 1 ? "" : "s"} ativo${activeProjectJobs === 1 ? "" : "s"} · aguarde`;

  production.disabled = projectDataLoading || Boolean(projectDataError) || !hasProject || !engineReady || !productionReady || activeProjectJobs > 0 || productionSubmitting;
  upscale.disabled = projectDataLoading || Boolean(projectDataError) || !hasProject || upscaleCount === 0 || activeProjectJobs > 0 || upscaleSubmitting;
  production.textContent = projectDataLoading
    ? "Carregando takes..."
    : projectDataError
      ? "Falha ao carregar os takes"
      : productionSubmitting
    ? "Enfileirando produção..."
    : activeProjectJobs
      ? `Produção ativa · ${activeJobsLabel}`
      : productionPlan.blockedIds.length
        ? `Trinca bloqueada · ${productionCount}/${productionPlan.requiredCount} prontos`
        : productionPlan.incomplete
          ? `Trinca incompleta · ${productionCount}/${productionPlan.requiredCount} prontos`
          : productionReady
            ? productionPlan.incompleteCorrectionBatch
              ? `Corrigir take${productionCount === 1 ? "" : "s"} · ${productionPlan.batchIds.join("-")}`
              : `Produzir ${productionCount} take${productionCount === 1 ? "" : "s"} · ${productionPlan.batchIds.join("-")}`
          : anchorCount
            ? `${anchorCount} aguardando foto-base`
            : "Nenhum take pendente";
  upscale.textContent = projectDataLoading
    ? "Carregando aprovados..."
    : projectDataError
      ? "Atualize o projeto"
      : upscaleSubmitting
    ? "Enfileirando upscaling..."
    : activeProjectJobs
      ? `Upscaling bloqueado · ${activeJobsLabel}`
      : upscaleCount
        ? `Upscaling obrigatório · ${upscaleCount} aprovado${upscaleCount === 1 ? "" : "s"}`
        : "Upscaling obrigatório · nada pendente";

  if (anchorPanel && anchorButton && anchorCopy) {
    anchorPanel.classList.remove("hidden");
    anchorButton.classList.remove("primary");
    anchorButton.classList.add("secondary");
    if (!hasProject) {
      anchorPanel.dataset.state = "idle";
      anchorButton.disabled = true;
      anchorButton.dataset.anchorAction = "none";
      anchorButton.textContent = "Fotos-base";
      anchorCopy.textContent = "Selecione um projeto para verificar quais takes precisam de uma foto-base própria.";
    } else if (anchorReviewCount) {
      anchorPanel.dataset.state = "review";
      anchorButton.classList.remove("secondary");
      anchorButton.classList.add("primary");
      anchorButton.disabled = false;
      anchorButton.dataset.anchorAction = "review";
      anchorButton.textContent = `Revisar ${anchorReviewCount} foto${anchorReviewCount === 1 ? "-base" : "s-base"}`;
      anchorCopy.textContent = `${anchorReviewCount} foto${anchorReviewCount === 1 ? " nova foi entregue" : "s novas foram entregues"}. Abra, aprove ou peça outra; somente as aprovadas liberam o vídeo.`;
    } else if (anchorToRequestCount) {
      anchorPanel.dataset.state = "attention";
      anchorButton.classList.remove("secondary");
      anchorButton.classList.add("primary");
      anchorButton.disabled = false;
      anchorButton.dataset.anchorAction = "request";
      anchorButton.textContent = `Pedir ${anchorToRequestCount} foto${anchorToRequestCount === 1 ? "-base" : "s-base"}`;
      anchorCopy.textContent = `${anchorToRequestCount} take${anchorToRequestCount === 1 ? " está" : "s estão"} bloqueado${anchorToRequestCount === 1 ? "" : "s"}. O pedido fica registrado e, após sua confirmação, o executor usa a GPU uma foto por vez.`;
    } else if (anchorRequestCount) {
      anchorPanel.dataset.state = "attention";
      if (codexImagegenOnly) {
        anchorButton.disabled = true;
        anchorButton.dataset.anchorAction = "none";
        anchorButton.textContent = `${anchorRequestCount} foto${anchorRequestCount === 1 ? "-base" : "s-base"} · Codex Imagegen`;
        anchorCopy.textContent = `O motor local está bloqueado neste projeto. As ${anchorRequestCount} bases serão criadas pelo Codex built-in imagegen e entregues aqui para sua aprovação.`;
      } else {
        anchorButton.classList.remove("secondary");
        anchorButton.classList.add("primary");
        anchorButton.disabled = false;
        anchorButton.dataset.anchorAction = "start";
        anchorButton.textContent = `Iniciar ${anchorRequestCount} foto${anchorRequestCount === 1 ? "-base" : "s-base"} (GPU)`;
        anchorCopy.textContent = `${anchorRequestCount} pedido${anchorRequestCount === 1 ? " está registrado" : "s estão registrados"}. Inicie o executor supervisionado; ele retoma a fila se houver uma falha transitória.`;
      }
    } else {
      anchorPanel.dataset.state = "ready";
      anchorButton.disabled = true;
      anchorButton.dataset.anchorAction = "none";
      anchorButton.textContent = "Fotos-base em dia";
      anchorCopy.textContent = "Nenhum take deste projeto precisa pedir ou revisar uma foto-base agora.";
    }
  }

  if (projectDataLoading) help.textContent = "Carregando o estado real dos takes antes de liberar a autorização.";
  else if (projectDataError) help.textContent = `Não foi possível carregar os takes: ${projectDataError}. Use Atualizar e tente novamente.`;
  else if (!hasProject) help.textContent = "Selecione um projeto para ver os trabalhos elegíveis.";
  else if (activeProjectJobs) help.textContent = `${activeProjectJobs} job${activeProjectJobs === 1 ? " ainda está" : "s ainda estão"} ativo${activeProjectJobs === 1 ? "" : "s"}. O botão libera sozinho quando a produção atual terminar; você pode validar os vídeos depois.`;
  else if (!engineReady && productionCount) help.textContent = `${projectEngine} indisponível; o upscaling obrigatório dos aprovados continua disponível.`;
  else if (productionPlan.blockedIds.length) help.textContent = `A trinca ${productionPlan.batchIds.join("-")} tem ${productionCount}/${productionPlan.requiredCount} prontos e espera as fotos-base ${productionPlan.blockedIds.join(", ")}. Nenhum job isolado será iniciado.`;
  else if (productionPlan.incomplete) help.textContent = `Há ${productionCount}/${productionPlan.requiredCount} takes prontos. O Maestro só libera a produção quando puder reservar a trinca completa.`;
  else if (anchorReviewCount) help.textContent = `${anchorReviewCount} foto${anchorReviewCount === 1 ? " está" : "s estão"} esperando sua decisão · ${productionCount} take${productionCount === 1 ? " está" : "s estão"} pronto${productionCount === 1 ? "" : "s"} para vídeo.`;
  else if (anchorPendingCount) help.textContent = `${productionCount} pronto${productionCount === 1 ? "" : "s"} para vídeo · ${anchorPendingCount} aguardando foto-base. As fotos exibidas nesses takes são apenas referências.`;
  else if (productionPlan.incompleteCorrectionBatch) help.textContent = `Correção ${productionPlan.batchIds.join("-")} liberada sem esperar fotos-base de takes futuros. A fila normal continua reservando três takes por vez.`;
  else if (productionReady) help.textContent = `Trinca pronta para reservar. A 5090 executa um render por vez com os três jobs já comprometidos; a validação não bloqueia a próxima trinca.`;
  else help.textContent = `${productionCount} para produzir · ${upscaleCount} para upscaling obrigatório. O Maestro não duplica o que já está na fila.`;
  syncFilmWorkflowTabs();
}

function filmStatusLabel(status) {
  return ({
    PLANNED: "Planejado",
    IN_PROGRESS: "Em produção",
    PAUSED: "Pausado",
    COMPLETED: "Concluído",
    ERROR: "Erro",
  })[status] || status || "—";
}

function renderFilmProjectList() {
  const list = $("#film-project-list");
  const projects = state.films.projects;
  $("#film-project-count").textContent = `${projects.length} projeto${projects.length === 1 ? "" : "s"}`;
  if (!projects.length) {
    list.innerHTML = '<div class="film-empty" role="status">Nenhum projeto encontrado.</div>';
    return;
  }
  list.innerHTML = projects.map((project) => {
    const active = project.projectId === state.films.activeProjectId;
    const counts = project.takeCounts || {};
    const finalFallbackOffset = active && state.films.takes.some(filmTakeIsProjectFinalOutput) ? 1 : 0;
    const planned = Math.max(0, Number(counts.planned || 0) - finalFallbackOffset);
    return `<button class="film-project-button${active ? " active" : ""}" type="button" data-film-project="${html(project.projectId)}" aria-pressed="${active ? "true" : "false"}">
      <strong>${html(project.name)}</strong>
      <span>${html(filmStatusLabel(project.status))} · ${Number(counts.approved || 0)} aprovados · ${Number(counts.inProduction || 0)} em produção · ${planned} takes</span>
    </button>`;
  }).join("");
  window.requestAnimationFrame(() => {
    const activeButton = list.querySelector(".film-project-button.active");
    if (!activeButton || list.scrollWidth <= list.clientWidth + 1) return;
    const listRect = list.getBoundingClientRect();
    const buttonRect = activeButton.getBoundingClientRect();
    const buttonLeft = list.scrollLeft + buttonRect.left - listRect.left;
    const buttonRight = buttonLeft + buttonRect.width;
    const visibleLeft = list.scrollLeft;
    const visibleRight = visibleLeft + list.clientWidth;
    if (buttonLeft < visibleLeft + 4 || buttonRight > visibleRight - 4) {
      list.scrollTo({ left: Math.max(0, buttonLeft - 8), behavior: "auto" });
    }
  });
}

function filmFinalOutputSource(project) {
  if (project?.projectId === "thiago_apresentacao_master_review_20260929" && project?.candidateOutput?.ready) {
    const review = project.candidateOutput;
    return { candidate: true, takeId: "", output: {
      ...review, masterBytes: review.bytes, masterFile: review.file,
      reviewFile: review.file, qcStatus: "REVISÃO DO PROPRIETÁRIO",
      reviewStatus: "CANDIDATE_PENDING_REVIEW", stale: false,
    } };
  }
  if (project?.finalOutput?.ready) return { output: project.finalOutput, takeId: "" };
  const take = state.films.takes.find((item) => filmTakeIsProjectFinalOutput(item) && item.hasPreview);
  if (!project || !take) return null;
  return {
    takeId: take.takeId,
    output: {
      ready: true,
      durationSeconds: Number(take.durationSeconds || take.reviewDurationSeconds || 0),
      width: Number(take.width || 1920),
      height: Number(take.height || 1080),
      fps: Number(take.fps || 60),
      masterBytes: Number(take.masterBytes || 0),
      masterFile: take.previewFile || "clipe_completo.mp4",
      qcStatus: take.qcStatus || "PASS",
      hasReviewProxy: Boolean(take.hasReviewProxy),
    },
  };
}

function filmFinalPreviewUrls(project, source) {
  const output = source?.output;
  if (!project || !output) return null;
  const projectId = encodeURIComponent(project.projectId);
  const version = encodeURIComponent(output.reviewFile || output.sha256 || output.masterFile || "final");
  if (source.candidate) {
    const base = `${API.studio}/api/video-projects/${projectId}/candidate-preview`;
    return { preview: `${base}?v=${encodeURIComponent(output.sha256)}`, download: `${base}?v=${encodeURIComponent(output.sha256)}&download=true` };
  }
  if (source.takeId) {
    const takeId = encodeURIComponent(source.takeId);
    const base = `${API.studio}/api/video-projects/${projectId}/takes/${takeId}/preview`;
    return {
      preview: `${base}?v=${version}`,
      download: `${base}?download=true`,
    };
  }
  const base = `${API.studio}/api/video-projects/${projectId}/final-preview`;
  return {
    preview: `${base}?v=${version}`,
    download: `${base}?download=true`,
  };
}

function markFilmFinalPlaybackVisible(video = $("#film-final-video")) {
  const fingerprint = String(video?.dataset.finalFingerprint || "");
  if (
    !fingerprint
    || video.readyState < 2
    || video.videoWidth < 1
    || video.videoHeight < 1
    || video.offsetParent === null
  ) return;
  if (state.films.finalViewedFingerprint === fingerprint) return;
  state.films.finalViewedFingerprint = fingerprint;
  const project = state.films.projects.find((item) => item.projectId === state.films.activeProjectId);
  renderFilmFinalOutput(project);
}

function renderFilmCandidateOutput(project) {
  const anchor = $("#film-final-output");
  if (!anchor) return;
  let panel = $("#film-candidate-output");
  if (project?.projectId === "thiago_apresentacao_master_review_20260929" && project?.candidateOutput?.ready) {
    if (panel) {
      const priorVideo = panel.querySelector("video");
      priorVideo.pause(); priorVideo.removeAttribute("src"); priorVideo.load();
      delete priorVideo.dataset.previewUrl;
      panel.classList.add("hidden");
    }
    return;
  }
  if (!panel) {
    panel = document.createElement("section");
    panel.id = "film-candidate-output";
    panel.className = "film-final-output hidden";
    panel.setAttribute("aria-labelledby", "film-candidate-title");
    panel.innerHTML = `<div class="film-final-output-copy"><h3 id="film-candidate-title">Capítulo completo para revisão</h3><p id="film-candidate-note">Candidata para assistir; aprovações dos takes e do master permanecem separadas.</p></div><div class="film-final-output-actions"><a class="btn" id="film-candidate-download">Baixar candidata</a></div><video id="film-candidate-video" controls preload="metadata" playsinline aria-label="Capítulo completo para revisão"></video>`;
    anchor.before(panel);
  }
  const video = panel.querySelector("video");
  const primaryOutput = project?.candidateOutput;
  const output = primaryOutput;
  if (!output?.ready) {
    video.pause();
    video.removeAttribute("src");
    delete video.dataset.previewUrl;
    video.load();
    panel.classList.add("hidden");
    return;
  }
  const base = primaryOutput?.ready ? `${API.studio}/api/video-projects/${encodeURIComponent(project.projectId)}/candidate-preview` : `${API.studio}/api/video-projects/${encodeURIComponent(project.projectId)}/takes/CHAPTER_REVIEW/preview`;

  const numeric = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const thiagoNativeComplete = project.projectId === "thiago_apresentacao_master_review_20260929"
    && output.file === "thiago_minimax_native_voice_qhd60_v01.mp4";
  const partialSilentReview = String(output.file || "").includes("PREVIA_PARCIAL") && String(output.file || "").includes("SEM_AUDIO");
  panel.querySelector("#film-candidate-title").textContent = thiagoNativeComplete
    ? "Vídeo completo — QHD 60 FPS / voz original MiniMax"
    : partialSilentReview ? "Prévia parcial para revisão — sem áudio" : "Capítulo completo para revisão";
  video.setAttribute("aria-label", thiagoNativeComplete ? "Vídeo completo Thiago com voz original MiniMax" : partialSilentReview ? "Prévia parcial para revisão sem áudio" : "Capítulo completo para revisão");
  panel.querySelector("#film-candidate-note").textContent = `${numeric(output.durationSeconds).toFixed(2)}s · ${numeric(output.width)}×${numeric(output.height)} · ${numeric(output.fps)} FPS. ${thiagoNativeComplete ? "Oito takes e sete conectores, com voz e ritmo originais MiniMax. Revisão do proprietário pendente." : partialSilentReview ? "Trecho parcial sem áudio; versão completa e Foley ainda em produção. Revisão do proprietário pendente." : "Candidata para assistir; aprovações dos takes e do master permanecem separadas."}`;
  const url = `${base}?v=${encodeURIComponent(output.sha256)}`;
  if (video.dataset.previewUrl !== url) {
    video.pause();
    video.dataset.previewUrl = url;
    video.src = url;
    video.load();
  }
  const link = panel.querySelector("a");
  link.href = `${url}&download=true`;
  link.setAttribute("download", output.file || "capitulo_candidato.mp4");
  setVerifiedDownloadLink(link);
  panel.classList.remove("hidden");
}


function renderFilmFinalOutput(project) {

  renderFilmCandidateOutput(project);
  const panel = $("#film-final-output");
  const video = $("#film-final-video");
  const playerStatus = $("#film-final-player-status");
  const source = filmFinalOutputSource(project);
  const output = source?.output;
  if (!panel || !output) {
    if (video) {
      video.pause();
      video.removeAttribute("src");
      delete video.dataset.previewUrl;
      delete video.dataset.finalFingerprint;
      video.load();
    }
    if (playerStatus) playerStatus.textContent = "Selecione um projeto com master registrado.";
    panel?.classList.add("hidden");
    return;
  }
  const duration = Number(output.durationSeconds || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const currentElevenlabsPackage = source.candidate && /^thiago_elevenlabs_current_20260930_144436_v02_(whatsapp_qhd60|presentation_4k60|presentation_fullhd60)\.mp4$/.test(output.masterFile || "");
  const elevenlabsAudioOnly = currentElevenlabsPackage || (source.candidate && output.masterFile === "thiago_elevenlabs_audio_only_qhd60_v01.mp4");
  const approvedNativeGuide = source.candidate && /^thiago_minimax_native_approved_t02v11_t05v09_qhd60_v01(?:_under50mb)?\.mp4$/.test(output.masterFile || "");
  const nativeCadenceGuide = approvedNativeGuide || (source.candidate && output.masterFile === "thiago_minimax_native_cadence_v09_qhd60.mp4");
  const originalH3Resolution = source.candidate && output.masterFile === "thiago_owner_voice_audio_only_h3res60_v01.mp4";
  const audioOnlyOwner = source.candidate && (elevenlabsAudioOnly || originalH3Resolution || output.masterFile === "thiago_owner_voice_audio_only_qhd60_v01.mp4");
  const ownerVoiceComplete = source.candidate && (audioOnlyOwner || output.masterFile === "thiago_owner_voice_qhd60_v02.mp4");
  $("#film-final-output-title").textContent = currentElevenlabsPackage ? (Number(output.width) === 1920 ? "Clipe completo — ElevenLabs / apresentação Full HD 60 FPS" : Number(output.width) === 3840 ? "Clipe completo — ElevenLabs / apresentação 4K 60 FPS" : "Clipe completo — ElevenLabs / WhatsApp compacto QHD 60 FPS") : approvedNativeGuide ? "Clipe completo — voz-guia MiniMax / QHD 60 FPS / menor que 50 MB" : nativeCadenceGuide ? "Clipe completo — revisão de cadência / voz-guia MiniMax / QHD 60 FPS" : elevenlabsAudioOnly ? "Clipe completo — ElevenLabs / sem lip-sync / QHD 60 FPS" : originalH3Resolution ? "Clipe completo — sua voz / sem lip-sync / H3 1344×768" : audioOnlyOwner ? "Clipe completo — sua voz / sem lip-sync / QHD 60 FPS" : ownerVoiceComplete ? "Clipe completo — sua voz / QHD 60 FPS" : "Clipe completo";
  const sizeMb = currentElevenlabsPackage ? (Number(output.masterBytes || 0) / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) : Math.max(1, Math.round(Number(output.masterBytes || 0) / (1024 * 1024)));
  $("#film-final-output-meta").textContent = `${duration}s · ${Number(output.width || 0)}×${Number(output.height || 0)} · ${Number(output.fps || 0)} FPS · ${sizeMb} MB · QC ${output.qcStatus || "registrado"}`;
  const download = $("#film-final-download");
  const urls = filmFinalPreviewUrls(project, source);
  download.href = urls.download;
  download.setAttribute("download", output.masterFile || "clipe_completo.mp4");
  setVerifiedDownloadLink(download);
  const viewedFingerprint = String(output.sha256 || output.reviewFile || output.masterFile || "final");
  if (video) {
    video.dataset.finalFingerprint = viewedFingerprint;
    video.setAttribute("aria-label", `${source.candidate ? "Vídeo completo para revisão" : "Master final"} de ${project.name}`);
    if (video.dataset.previewUrl !== urls.preview) {
      video.pause();
      video.dataset.previewUrl = urls.preview;
      video.src = urls.preview;
      video.load();
      if (playerStatus) playerStatus.textContent = "Carregando o master no player.";
    }
  }
  panel.classList.remove("hidden");
  const reviewStatus = String(output.reviewStatus || "PENDING_OWNER_REVIEW");
  const viewed = state.films.finalViewedFingerprint === viewedFingerprint;
  const finalReviewStatus = $("#film-final-review-status");
  const approve = $("#film-final-approve");
  const reject = $("#film-final-reject");
  const reason = $("#film-final-rejection-reason");
  const pending = reviewStatus === "PENDING_OWNER_REVIEW" && !output.stale;
  approve.disabled = !pending || !viewed;
  reject.disabled = !pending || !viewed;
  reason.disabled = !pending || !viewed;
  if (source.candidate) finalReviewStatus.textContent = currentElevenlabsPackage ? "Novo áudio ElevenLabs aplicado inteiro, com oito takes aprovados e sete transições. Cadência e movimentos de boca preservados, sem pós-lip-sync. Exportação completa para revisão." : approvedNativeGuide ? "Oito takes aprovados, com T02 v11, T05 corrigido e sete transições originais. Completo com voz-guia MiniMax, pronto para baixar e converter no ElevenLabs. Sem pós-lip-sync ou alteração de cadência; revisão da montagem pendente." : nativeCadenceGuide ? "Takes 2 e 5 refeitos com direção e fala nativa corrigidas. Revisão com voz-guia; nova conversão ElevenLabs ainda pendente. Sem pós-lip-sync." : elevenlabsAudioOnly ? "Voz ElevenLabs fornecida pelo proprietário, preservada inteira e sem ajustes. Imagem e boca originais mantidas; revisão pendente." : audioOnlyOwner ? "Sua voz com a imagem e a boca originais do MiniMax. Ritmo ajustado apenas no áudio; revisão do proprietário pendente." : ownerVoiceComplete ? "Versão com sua voz selecionada para assistir. Aprovação do resultado permanece pendente." : "Vídeo completo selecionado para revisão do proprietário.";
  else if (output.stale) finalReviewStatus.textContent = "Este master ficou desatualizado. Monte novamente a sequência aprovada.";
  else if (reviewStatus === "APPROVED_BY_OWNER") finalReviewStatus.textContent = "Master aprovado pelo proprietário.";
  else if (reviewStatus === "REJECTED_BY_OWNER") finalReviewStatus.textContent = `Master reprovado: ${output.reviewReason || "nova montagem necessária"}`;
  else if (!viewed) finalReviewStatus.textContent = "Assista ao clipe completo antes de liberar a decisão final.";
  else finalReviewStatus.textContent = "Visualização registrada nesta sessão. Aprove ou explique a reprovação.";
}

function renderFilmFinalization(project) {
  const status = $("#film-assembly-status");
  const button = $("#film-assembly-start");
  if (!status || !button) return;
  if (!project) {
    status.textContent = "Selecione um projeto para conferir as aprovações.";
    button.disabled = true;
    return;
  }
  const job = state.films.assemblyJob;
  const jobActive = job?.projectId === project.projectId
    && !["done", "error", "canceled", "interrupted"].includes(job.status);
  if (jobActive) {
    status.textContent = `${Number(job.progress || 0)}% · ${job.message || "Montando sequência aprovada."}`;
    button.disabled = true;
    button.textContent = "Montagem em andamento";
    return;
  }
  const readiness = project.assemblyReadiness || { ready: false, blockers: [] };
  const blockers = Array.isArray(readiness.blockers) ? readiness.blockers : [];
  button.disabled = readiness.ready !== true;
  button.textContent = project.finalOutput?.stale || project.finalOutput?.reviewStatus === "REJECTED_BY_OWNER"
    ? "Remontar sequência aprovada"
    : "Montar sequência aprovada";
  if (readiness.ready) {
    status.textContent = `${Number(readiness.sources?.length || 0)} takes com imagem e áudio aprovados. A montagem usará cortes secos e exigirá revisão final.`;
  } else if (blockers.length) {
    status.textContent = blockers.slice(0, 3).map((item) => item.message).join(" ");
  } else {
    status.textContent = "Aguardando os contratos e as aprovações dos takes.";
  }
}

function renderFilmSummary(project) {
  window.dispatchEvent(new CustomEvent("maestro:film-project", { detail: project || null }));
  $("#film-active-title").textContent = project?.name || "Selecione um projeto";
  $("#film-active-status").textContent = project ? filmStatusLabel(project.status) : "—";
  $("#film-active-objective").textContent = project?.objective || "Os projetos existentes e seus takes aparecerão aqui.";
  if (!project) {
    $("#film-metrics").innerHTML = "";
    renderFilmFinalOutput(null);
    renderFilmFinalization(null);
    syncFilmWorkflowTabs();
    return;
  }
  const counts = project.takeCounts || {};
  const takes = filmProductionTakes();
  const reviewCount = takes.filter(filmTakeNeedsReview).length;
  const approvedCount = takes.filter((take) => ["APPROVED", "FINAL"].includes(take.status)).length;
  const productionCount = takes.filter((take) => ["IN_PRODUCTION", "QUEUED", "GENERATING", "UPSCALING"].includes(take.status)).length;
  const metrics = [
    [takes.length || counts.planned || 0, "Total de takes"],
    [reviewCount, "Para você decidir"],
    [productionCount, "Na produção"],
    [approvedCount, "Aprovados"],
  ];
  const projectProgress = filmProjectProgress();
  $("#film-metrics").innerHTML = metrics.map(([value, label]) => `<div class="film-metric"><strong>${html(value)}</strong><span>${html(label)}</span></div>`).join("")
    + filmProgressMarkup(projectProgress.percent, {
      heading: "Produção dos vídeos",
      detail: projectProgress.detail,
      tone: projectProgress.tone,
      className: "film-metric film-project-progress",
      ariaLabel: `Vídeos produzidos no projeto: ${projectProgress.percent}%`,
    })
    + filmDirectorStatusCardMarkup();
  syncFilmProgressWidths($("#film-metrics"));
  renderFilmFinalization(project);
  renderFilmFinalOutput(project);
  syncFilmWorkflowTabs();
}

function filmProductionItemTitle(item) {
  const project = state.films.projects.find((entry) => entry.projectId === item.projectId);
  const projectName = project?.name || item.projectId || "Studio";
  const takeName = item.takeId ? `Take ${item.takeId}` : (item.mode || "Trabalho");
  const stage = item.jobKind === "video_upscale" ? "Acabamento 60 FPS" : "Criação do vídeo";
  const batch = item.batchId && item.batchSize
    ? ` · Trinca ${Number(item.batchIndex || 0)}/${Number(item.batchSize || 0)}`
    : "";
  return `${projectName} · ${takeName} · ${stage}${batch}`;
}

function renderFilmProductionQueue(queue) {
  const total = $("#film-production-total");
  const items = $("#film-production-items");
  if (!total || !items) return;
  state.films.productionQueueData = queue || null;
  syncFilmBatchActions();
  syncFilmWorkflowTabs();
  syncFilmProjectProgress();
  syncFilmTakeProgressBars();
  const projectNames = state.films.projects.map((project) => [project.projectId, project.name]);
  const signature = JSON.stringify({ queue: queue || {}, projectNames });
  if (signature === state.films.productionQueueSignature) return;
  state.films.productionQueueSignature = signature;

  if (!queue?.ok) {
    total.textContent = "Indisponível";
    total.classList.remove("active");
    items.innerHTML = `<span class="film-production-empty" role="status">${html(queue?.message || "Não foi possível consultar a fila.")}</span>`;
    return;
  }

  const running = Number(queue.running || 0);
  const pending = Number(queue.pending || 0);
  total.textContent = queue.total ? `${running} produzindo · ${pending} aguardando` : "Fila livre";
  total.classList.toggle("active", Number(queue.total || 0) > 0);
  if (!queue.items?.length) {
    items.innerHTML = '<span class="film-production-empty" role="status">A GPU está livre agora.</span>';
    return;
  }
  items.innerHTML = queue.items.map((item) => {
    const runningNow = item.state === "RUNNING";
    const progress = runningNow ? clampFilmProgress(item.progress || 0) : 0;
    const stateLabel = runningNow
      ? `${progress}% estimado`
      : `posição ${Number(item.position || 0)} na fila · ainda não iniciado`;
    const message = item.message ? ` · ${item.message}` : "";
    const title = filmProductionItemTitle(item);
    return `<article class="film-production-item ${runningNow ? "running" : "pending"}" role="listitem">
      <div class="film-production-item-copy"><strong>${html(title)}</strong><span>${html(stateLabel)}${html(message)}</span></div>
      ${filmProgressMarkup(progress, {
        heading: runningNow ? "Progresso estimado do job" : "Aguardando execução",
        tone: runningNow ? "active" : "warning",
        className: "film-job-progress",
        ariaLabel: `${title}: ${progress}%`,
      })}
    </article>`;
  }).join("");
  syncFilmProgressWidths(items);
}

async function loadFilmProductionQueue() {
  try {
    const queue = await fetchFilmMetadata(`${API.studio}/api/generative/queue`);
    renderFilmProductionQueue(queue);
  } catch (error) {
    renderFilmProductionQueue({ ok: false, message: error.message });
  }
}

async function refreshFilmLiveData() {
  const projectId = state.films.activeProjectId;
  if (state.films.liveRefreshInFlight || state.films.projectsLoadPromise) return;
  state.films.liveRefreshInFlight = true;
  try {
    if (!projectId) {
      await loadFilmProjects();
      return;
    }
    await Promise.all([
      refreshFilmProjectData(projectId, { onlyIfChanged: true }),
      loadFilmProductionQueue(),
    ]);
  } catch (_error) {
    // Mantém a última tela válida; o próximo ciclo tenta novamente sem alterar decisões.
  } finally {
    state.films.liveRefreshInFlight = false;
  }
}

function renderFilmTakes() {
  const list = $("#film-takes-list");
  if (!state.films.activeProjectId) {
    $("#film-playlist-count").textContent = "Selecione um projeto";
    list.innerHTML = '<div class="film-empty" role="status">Selecione um projeto.</div>';
    syncFilmBatchActions();
    return;
  }
  if (!state.films.takes.length) {
    $("#film-playlist-count").textContent = "Nenhum take";
    list.innerHTML = '<div class="film-empty" role="status">Este projeto ainda não possui takes.</div>';
    syncFilmBatchActions();
    return;
  }
  const view = FILM_WORKFLOW_VIEWS.has(state.films.view) ? state.films.view : "all";
  const takes = view === "production" ? [] : visibleFilmTakes(view);
  const viewCopy = {
    review: `${takes.length} aguardando sua decisão`,
    approved: `${takes.length} aprovado${takes.length === 1 ? "" : "s"}`,
    rejected: `${takes.length} rejeitado${takes.length === 1 ? "" : "s"}`,
    all: `${takes.length} take${takes.length === 1 ? "" : "s"} no projeto`,
  };
  $("#film-playlist-count").textContent = viewCopy[view] || "Acompanhe pela aba Produção";
  if (!takes.length) {
    const emptyCopy = {
      review: "Nenhum take precisa da sua decisão agora.",
      approved: "Nenhum take aprovado ainda.",
      rejected: "Nenhum take rejeitado neste projeto.",
      all: "Este projeto ainda não possui takes.",
      production: "",
    };
    list.innerHTML = emptyCopy[view] ? `<div class="film-empty film-view-empty" role="status">${html(emptyCopy[view])}</div>` : "";
    syncFilmBatchActions();
    resumeFilmTakeJobs();
    return;
  }
  list.innerHTML = takes.map((take) => {
    const busy = ["QUEUED", "GENERATING", "UPSCALING"].includes(take.status);
    const engineReady = filmTakeEngineReady(take);
    const actionLabel = filmTakeActionLabel(take, engineReady);
    const directorRequest = take.directorRequest || null;
    const directorUndelivered = FILM_DIRECTOR_UNDELIVERED_STATUSES.has(directorRequest?.status);
    const directorAwaitingExecutor = filmDirectorRequestAwaitingExecutor(directorRequest);
    const directorAcknowledgement = directorUndelivered ? filmDirectorAcknowledgementMarkup(take) : "";
    const anchorPending = filmTakeAnchorPending(take);
    const anchorReviewPending = filmTakeAnchorReviewPending(take);
    const anchorWorkflow = filmAnchorWorkflowState(take);
    const anchorAwaitingExecutor = anchorWorkflow.state === "awaiting_executor";
    const needsDirectorReason = take.status === "REJECTED" && !directorUndelivered;
    const actionDisabled = busy || take.hasUpscalePreview || !engineReady || !take.canGenerate || needsDirectorReason;
    const upscaleDisabled = busy || take.hasUpscalePreview || !take.canUpscale || filmActiveProjectQueueItems().length > 0;
    const takeProgress = filmTakeProgress(take);
    const thumbnailVersion = encodeURIComponent(take.directorRequest?.updatedAt || take.qcStatus || "base");
    const thumbnailEndpoint = filmTakeHasRegisteredAnchor(take) ? "anchor-image" : "thumbnail";
    const thumbnailUrl = `${API.studio}/api/video-projects/${encodeURIComponent(state.films.activeProjectId)}/takes/${encodeURIComponent(take.takeId)}/${thumbnailEndpoint}?v=${thumbnailVersion}`;
    const thumbnail = take.hasKeyframe || take.hasEndKeyframeCandidate
      ? `<img src="${html(thumbnailUrl)}" alt="" loading="lazy">`
      : '<span class="film-thumbnail-empty">Sem imagem</span>';
    const active = take.takeId === state.films.activeTakeId;
    const statusClass = String(take.status || "planned").toLowerCase().replaceAll("_", "-");
    const takeModeLabels = { PRECISION: "Precisão", ACTION: "Ação", PAYOFF: "Clímax", UNSPECIFIED: "Modo não definido" };
    const takeModeLabel = takeModeLabels[take.takeMode] || "Modo não definido";
    const continuityContract = take.continuityContract || {};
    const continuitySummary = [
      continuityContract.characterTopology,
      continuityContract.wardrobeLock,
      continuityContract.powerState,
      continuityContract.entryMotion,
      continuityContract.exitMotion,
      continuityContract.impactLanguage,
    ].filter(Boolean).join(" · ");
    const anchorQuickAction = anchorPending
      ? `<div class="film-take-anchor-quick" data-state="${anchorAwaitingExecutor ? "waiting" : "needed"}">
          <div class="film-take-anchor-quick-copy">
            <strong>${anchorAwaitingExecutor ? FILM_REQUEST_AWAITING_EXECUTOR_COPY : "Este take precisa de foto-base"}</strong>
            <span>${anchorAwaitingExecutor ? "O pedido está preservado. Inicie o executor com GPU; a aprovação do take não muda." : "Registre o pedido e confirme a geração com GPU. Isso não reprova o take."}</span>
          </div>
          <button class="btn primary small film-take-anchor" type="button" ${anchorAwaitingExecutor ? `data-film-anchor-start="${html(take.takeId)}"` : `data-film-take-anchor="${html(take.takeId)}"`}>${anchorAwaitingExecutor ? "Iniciar foto-base (GPU)" : "Pedir foto-base"}</button>
        </div>`
      : anchorReviewPending
        ? `<div class="film-take-anchor-quick" data-state="review">
            <div class="film-take-anchor-quick-copy">
              <strong>Nova foto-base para decidir</strong>
              <span>Abra a imagem e aprove ou explique o que deve mudar.</span>
            </div>
            <div class="film-take-anchor-quick-actions" role="group" aria-label="Decidir foto-base do take ${html(take.takeId)}">
              <button class="btn primary small" type="button" data-film-anchor-approve="${html(take.takeId)}">Aprovar imagem</button>
              <button class="btn danger small" type="button" data-film-anchor-reject="${html(take.takeId)}">Pedir outra</button>
            </div>
          </div>`
        : "";
    const preanalysisGalleryUrl = `${API.studio}/api/video-projects/${encodeURIComponent(state.films.activeProjectId)}/takes/${encodeURIComponent(take.takeId)}/preanalysis-gallery?v=${encodeURIComponent(take.preanalysisGallery?.sha256 || "gallery")}`;
    const preanalysisGalleryAction = take.hasPreanalysisGallery
      ? `<section class="film-preanalysis-gallery" aria-label="Pré-análise visual do take ${html(take.takeId)}">
          <button class="film-preanalysis-gallery-preview" type="button" data-film-preanalysis-open="${html(take.takeId)}" aria-label="Abrir as três âncoras do Take ${html(take.takeId)}">
            <img src="${html(preanalysisGalleryUrl)}" alt="START, aterrissagem e quadro final do Take ${html(take.takeId)}" loading="eager">
          </button>
          <div>
            <strong>START + ${Number(take.preanalysisGallery?.candidateCount || 0) === 3 ? "checkpoint + " : ""}END prontos</strong>
            <span>Pré-análise técnica completa · aprovação humana ainda pendente.</span>
          </div>
          <button class="btn secondary small" type="button" data-film-preanalysis-open="${html(take.takeId)}">Abrir sequência de âncoras</button>
        </section>`
      : "";
    const audioCandidateUrl = `${API.studio}/api/video-projects/${encodeURIComponent(state.films.activeProjectId)}/takes/${encodeURIComponent(take.takeId)}/audio-candidate`;
    const audioVariants = Array.isArray(take.audioCandidates) ? take.audioCandidates : [];
    const audioPlayers = audioVariants.length
      ? `<div class="film-take-audio-variants">${audioVariants.map((candidate) => {
          const url = `${API.studio}/api/video-projects/${encodeURIComponent(state.films.activeProjectId)}/takes/${encodeURIComponent(take.takeId)}/audio-candidates/${encodeURIComponent(candidate.candidateId)}`;
          return `<div class="film-take-audio-variant">
            <strong>${html(candidate.label || candidate.candidateId)}</strong>
            <audio controls preload="none" src="${html(url)}" aria-label="Ouvir ${html(candidate.label || candidate.candidateId)} do take ${html(take.takeId)}"></audio>
          </div>`;
        }).join("")}</div>`
      : `<audio controls preload="none" src="${html(audioCandidateUrl)}" aria-label="Ouvir áudio candidato do take ${html(take.takeId)}"></audio>`;
    const audioReviewTitle = take.audioCandidateNeedsReview
      ? audioVariants.length > 1
        ? `${audioVariants.length} opções novas — escuta humana obrigatória`
        : "Áudio candidato — escuta humana obrigatória"
      : take.audioCandidateApproved
        ? "Áudio aprovado por você"
        : "Áudio preservado como referência";
    const audioReviewActions = take.audioCandidateNeedsReview
      ? `<div class="film-audio-review-actions">
          <button class="btn primary small" type="button" data-film-audio-review="APPROVED" data-film-audio-take="${html(take.takeId)}">Aprovar este áudio</button>
          <label for="film-audio-reject-${html(take.takeId)}">Se reprovar, explique o motivo
            <textarea id="film-audio-reject-${html(take.takeId)}" rows="2" maxlength="1000" data-film-audio-reject-reason="${html(take.takeId)}" data-voice-input data-voice-label="motivo da reprovação do áudio"></textarea>
          </label>
          <button class="btn danger small" type="button" data-film-audio-review="REJECTED" data-film-audio-take="${html(take.takeId)}">Reprovar áudio</button>
        </div>`
      : "";
    const audioQuickAction = take.hasAudioCandidate
      ? `<div class="film-take-audio-quick" data-state="${take.audioCandidateNeedsReview ? "review" : "available"}">
          <div class="film-take-audio-copy">
            <strong>${html(audioReviewTitle)}</strong>
            <span>Origem: ${html(take.audioCandidateSource || "referência preservada")} · transcrição automática: ${html(take.audioCandidateTranscription || "não disponível")}</span>
          </div>
          ${audioPlayers}
          ${audioReviewActions}
        </div>`
      : "";
    const audioDeliveryBadge = take.audioRequired
      ? take.audioReady
        ? take.audioHumanReviewRequired
          ? '<span class="film-audio-review">Áudio no vídeo · escutar</span>'
          : '<span class="film-audio-approved">Áudio aprovado</span>'
        : '<span class="film-audio-review">Áudio/voz pendente</span>'
      : "";
    const videoSoundProviders = (state.films.videoSoundProviders || []).filter((provider) => provider.configured);
    const videoSoundProviderId = videoSoundProviders.some((provider) => provider.providerId === state.films.videoSoundProviderId)
      ? state.films.videoSoundProviderId
      : videoSoundProviders[0]?.providerId || "";
    const videoSoundProviderOptions = videoSoundProviders.map((provider) => (
      `<option value="${html(provider.providerId)}"${provider.providerId === videoSoundProviderId ? " selected" : ""}>${html(provider.label)} · ${html(provider.device || "dispositivo do provider")}</option>`
    )).join("");
    const videoSoundDirection = `Som cinematográfico sincronizado exatamente ao movimento visível: ${take.objective || take.animationPrompt || "ação do take"}. Ambiente e efeitos físicos naturais; sem música e sem fala.`;
    const videoSoundJob = state.films.videoSoundJobs[take.takeId];
    const videoSoundBusy = Boolean(videoSoundJob && !["done", "error", "canceled", "interrupted"].includes(videoSoundJob.status));
    const videoSoundAction = ["APPROVED", "FINAL"].includes(take.status) && take.hasPreview
      ? `<section class="film-video-sound" aria-labelledby="film-video-sound-title-${html(take.takeId)}">
          <strong id="film-video-sound-title-${html(take.takeId)}">Gerar som pelo vídeo</strong>
          <p>O modelo lê este take aprovado. O resultado entra como piloto e exige Escuta humana obrigatória; nunca é anexado automaticamente.</p>
          <label for="film-video-sound-provider-${html(take.takeId)}">Modelo
            <select id="film-video-sound-provider-${html(take.takeId)}" data-film-video-sound-provider="${html(take.takeId)}"${videoSoundBusy ? " disabled" : ""}>
              ${videoSoundProviderOptions || '<option value="">Nenhum provider disponível</option>'}
            </select>
          </label>
          <label for="film-video-sound-prompt-${html(take.takeId)}">Direção sonora
            <textarea id="film-video-sound-prompt-${html(take.takeId)}" rows="4" maxlength="4000" data-film-video-sound-prompt="${html(take.takeId)}" data-voice-input data-voice-label="direção do som pelo vídeo"${videoSoundBusy ? " disabled" : ""}>${html(videoSoundDirection)}</textarea>
          </label>
          <div class="film-video-sound-actions">
            <label for="film-video-sound-duration-${html(take.takeId)}">Piloto (s)
              <input id="film-video-sound-duration-${html(take.takeId)}" type="number" min="0.5" max="15" step="0.1" value="${Math.min(15, Math.max(0.5, Number(take.durationSeconds || 5)))}" data-film-video-sound-duration="${html(take.takeId)}"${videoSoundBusy ? " disabled" : ""}>
            </label>
            <button class="btn primary small" type="button" data-film-video-sound-start="${html(take.takeId)}"${videoSoundBusy || !videoSoundProviderId ? " disabled" : ""}>${videoSoundBusy ? `${Number(videoSoundJob.progress || 0)}% · gerando` : "Gerar piloto sincronizado"}</button>
          </div>
        </section>`
      : "";
    return `<article class="film-take-card${active ? " active" : ""}" role="listitem" data-film-take-card="${html(take.takeId)}">
      <button class="film-take-open" type="button" data-film-take-open="${html(take.takeId)}" aria-label="Abrir take ${html(take.takeId)}: ${html(filmTakeDisplayName(take))}"${take.hasKeyframe || take.hasEndKeyframeCandidate || take.hasPreview || take.hasUpscalePreview ? "" : " disabled"}>
        <span class="film-take-thumbnail">${thumbnail}${take.hasPreview || take.hasUpscalePreview ? '<span class="film-thumbnail-play" aria-hidden="true">▶</span>' : ""}<span class="film-thumbnail-duration">${Number(take.durationSeconds || 0)}s</span></span>
        <span class="film-take-copy">
          <span class="film-take-title"><strong>Take ${html(take.takeId)}</strong> ${html(filmTakeDisplayName(take))}</span>
          <span class="film-take-objective">${html(take.objective || "Imagem aprovada aguardando produção do vídeo.")}</span>
          <span class="film-take-badges"><span class="film-take-state ${html(statusClass)}">${html(filmTakeStatusLabel(take.status))}</span><span class="film-take-mode">${html(takeModeLabel)}</span>${take.keyframeApproved ? '<span class="film-base-approved">Imagem aprovada</span>' : ""}${anchorPending ? '<span class="film-anchor-pending">Imagem apenas de referência</span>' : ""}${anchorReviewPending ? '<span class="film-anchor-review">Imagem nova para aprovar</span>' : ""}${take.hasUpscalePreview ? '<span class="film-anchor-review">Acabamento para aprovar</span>' : ""}${take.isUpscaled ? '<span class="film-upscale-ready">Vídeo 60 FPS</span>' : ""}${audioDeliveryBadge}${take.audioCandidateNeedsReview ? `<span class="film-audio-review">${audioVariants.length > 1 ? `${audioVariants.length} áudios para escutar` : "Áudio para escutar"}</span>` : ""}${take.audioCandidateApproved ? '<span class="film-audio-approved">Áudio aprovado</span>' : ""}</span>
          ${continuitySummary ? `<span class="film-take-continuity">Continuidade: ${html(continuitySummary)}</span>` : ""}
        </span>
      </button>
      ${filmProgressMarkup(takeProgress.percent, {
        heading: takeProgress.heading,
        detail: takeProgress.label,
        tone: takeProgress.tone,
        className: "film-take-progress",
        ariaLabel: `Take ${take.takeId}: ${takeProgress.percent}%`,
      })}
      ${directorAcknowledgement}
      ${preanalysisGalleryAction}
      ${anchorQuickAction}
      ${audioQuickAction}
      ${take.lastError ? `<div class="film-command-error" role="alert">
        <strong>O comando não foi executado</strong>
        <span>${html(take.lastError)}</span>
      </div>` : ""}
      <details class="film-take-more">
        <summary>${take.status === "REJECTED" ? "Corrigir este take" : "Outras opções deste take"}</summary>
        <div class="film-take-prompt-editor">
          <label class="film-take-control-label" for="film-engine-${html(take.takeId)}">Motor deste take (escolha obrigatória)</label>
          <select id="film-engine-${html(take.takeId)}" data-film-engine-select="${html(take.takeId)}"${busy ? " disabled" : ""}>
            <option value=""${filmTakeEngineKey(take) ? "" : " selected"} disabled>Escolha MiniMax H3</option>
            <option value="minimax_h3_fl2va_int8_720p24"${take.generationProfile === "minimax_h3_fl2va_int8_720p24" ? " selected" : ""}>MiniMax H3</option>
          </select>
          <div class="film-take-prompt-meta">Sem padrão e sem fallback. Alterar o motor invalida qualquer decisão implícita anterior e mantém as mídias já produzidas preservadas.</div>
        </div>
        <div class="film-take-prompt-editor">
          <label class="film-take-control-label" for="film-prompt-${html(take.takeId)}">Prompt dirigido para ${html(take.engine || "motor de vídeo")}</label>
          <textarea id="film-prompt-${html(take.takeId)}" rows="7" maxlength="6000" data-film-prompt-input="${html(take.takeId)}" data-voice-input data-voice-label="prompt do take ${html(take.takeId)}"${busy ? " disabled" : ""}>${html(take.animationPrompt || "")}</textarea>
          <div class="film-take-prompt-meta">${take.speaker ? `Fala: <strong>${html(take.speaker)}</strong> — ${html(take.dialoguePtBr || "")}` : "Sem fala neste take."} Texto visível, legenda, interface e pt-PT são bloqueados pelo gate.</div>
          <button class="btn secondary small" type="button" data-film-prompt-save="${html(take.takeId)}"${busy ? " disabled" : ""}>Salvar prompt</button>
        </div>
        <div class="film-take-controls">
          <div class="film-take-action">
            <span class="film-take-control-label">${take.hasPreview ? "Gerar outra versão" : "Produzir este vídeo"}</span>
            <button class="btn secondary small film-take-generate" type="button" data-film-take-generate="${html(take.takeId)}"${actionDisabled ? " disabled" : ""}>${actionLabel}</button>
          </div>
          ${take.canUpscale ? `<div class="film-take-action">
            <span class="film-take-control-label">Remasterizar este aprovado</span>
            <button class="btn primary small film-take-upscale" type="button" data-film-take-upscale="${html(take.takeId)}"${upscaleDisabled ? " disabled" : ""}>Upscaling obrigatório</button>
          </div>` : ""}
          ${take.status === "REJECTED" ? `<div class="film-take-action film-take-director-action">
            <span class="film-take-control-label">Pedir correção</span>
            <button class="btn ${directorUndelivered ? "secondary" : "primary"} small film-take-director" type="button" data-film-take-director="${html(take.takeId)}"${directorUndelivered ? " disabled" : ""}>${html(filmDirectorRequestLabel(directorRequest))}</button>
          </div>` : ""}
        </div>
        ${videoSoundAction}
        ${take.status === "REJECTED" ? `<p class="film-regeneration-help">${directorUndelivered ? `${directorAwaitingExecutor ? FILM_REQUEST_AWAITING_EXECUTOR_COPY : "Correção em produção"}: ${html(directorRequest.reason)} O vídeo atual continua guardado.` : "Use <strong>Explicar correção (1/2)</strong>, revise o formulário e então registre o pedido. O vídeo atual continuará guardado."}</p>` : ""}
        ${take.upscaleError ? `<span class="film-job-error">Acabamento 60 FPS: ${html(take.upscaleError)}</span>` : ""}
        ${take.lastError ? `<span class="film-job-error">${html(take.lastError)}</span>` : ""}
      </details>
    </article>`;
  }).join("");
  enhanceVoiceInputs(list);
  syncFilmProgressWidths(list);
  syncFilmBatchActions();
  resumeFilmTakeJobs();
}

function renderFilmPlayerReview(take) {
  const review = $("#film-player-review");
  if (!review) return;
  const anchorReviewPending = filmTakeAnchorReviewPending(take);
  const upscaleReviewPending = Boolean(take?.hasUpscalePreview);
  if (!take?.hasPreview && !anchorReviewPending && !upscaleReviewPending) {
    review.classList.add("hidden");
    return;
  }
  review.classList.remove("hidden");
  const title = $("#film-player-review-title");
  const more = review.querySelector(".film-review-more");
  const approveButton = review.querySelector('[data-film-player-decision="APPROVED"]');
  const rejectButton = review.querySelector('[data-film-player-decision="REJECTED"]');
  if (upscaleReviewPending) {
    title.textContent = "Aprovar este remaster 1080p?";
    $("#film-player-review-state").textContent = "Candidato FHD";
    approveButton.textContent = "Aprovar FHD";
    rejectButton.textContent = "Rejeitar e refazer";
    approveButton.disabled = false;
    rejectButton.disabled = false;
    approveButton.setAttribute("aria-pressed", "false");
    rejectButton.setAttribute("aria-pressed", "false");
    more.classList.add("hidden");
    $("#film-player-review-help").textContent = "O player mostra somente o candidato FHD. Aprovar promove esse arquivo; rejeitar preserva o vídeo ativo anterior e libera uma nova tentativa.";
    return;
  }
  if (anchorReviewPending) {
    title.textContent = "Aprovar esta imagem-âncora?";
    $("#film-player-review-state").textContent = "Imagem nova";
    approveButton.textContent = "Aprovar imagem";
    rejectButton.textContent = "Explicar mudança (1/2)";
    approveButton.disabled = false;
    rejectButton.disabled = false;
    approveButton.setAttribute("aria-pressed", "false");
    rejectButton.setAttribute("aria-pressed", "false");
    more.classList.add("hidden");
    $("#film-player-review-help").textContent = "Aprovar libera este take para o Wan. Pedir outra mantém o vídeo bloqueado e envia sua explicação ao diretor.";
    return;
  }
  title.textContent = "Qual é a sua decisão?";
  approveButton.textContent = "Aprovar este take";
  rejectButton.textContent = "Explicar correção (1/2)";
  more.classList.remove("hidden");
  const busy = ["QUEUED", "GENERATING", "UPSCALING"].includes(take.status);
  const directorUndelivered = FILM_DIRECTOR_UNDELIVERED_STATUSES.has(take.directorRequest?.status);
  if (busy) approveButton.textContent = directorUndelivered ? "Aguardando vídeo corrigido" : "Aguardando vídeo pronto";
  else if (take.status === "APPROVED" && !(take.audioReady && take.audioHumanReviewRequired)) approveButton.textContent = "Take já aprovado";
  $("#film-player-review-state").textContent = filmTakeStatusLabel(take.status);
  review.querySelectorAll("[data-film-player-decision]").forEach((button) => {
    const decision = button.dataset.filmPlayerDecision;
    const selected = decision === take.status && !(
      decision === "APPROVED"
      && take.audioReady
      && take.audioHumanReviewRequired
    );
    const finalBlocked = decision === "FINAL" && !["APPROVED", "FINAL"].includes(take.status);
    const repeatedRejection = decision === "REJECTED" && take.status === "REJECTED" && directorUndelivered;
    button.setAttribute("aria-pressed", selected ? "true" : "false");
    button.disabled = busy || selected || finalBlocked || repeatedRejection;
  });

  let help = "A decisão será aplicada ao vídeo acima.";
  if (busy) help = directorUndelivered && take.hasPreview
    ? "O player mostra a versão anterior, preservada após sua reprovação. Aprovar ficará disponível quando o vídeo corrigido completo for entregue."
    : "O vídeo está em produção. Aprovar ficará disponível quando o candidato completo estiver pronto.";
  else if (take.status === "REJECTED" && directorUndelivered) {
    help = `${filmDirectorRequestAwaitingExecutor(take.directorRequest) ? FILM_REQUEST_AWAITING_EXECUTOR_COPY : "Correção em produção"} · requestId ${take.directorRequest.requestId}. ${take.directorRequest.reason}`;
  }
  else if (take.status === "APPROVED" && take.audioRequired && !take.audioReady) {
    help = "Imagem aprovada. A faixa de ambiente/efeitos e voz continua pendente, sem bloquear sua decisao visual.";
  }
  else if (take.status === "APPROVED" && take.audioReady && take.audioHumanReviewRequired) {
    help = "Imagem aprovada. Escute a faixa anexada e confirme novamente para aprovar o audio.";
  }
  else if (take.status === "APPROVED") help = "Aprovado. Finalize somente quando este for o arquivo escolhido para entrega.";
  else if (take.status === "FINAL") help = "Este take está marcado como entrega final.";
  $("#film-player-review-help").textContent = help;
}

function filmPreviewMeta(take) {
  if (!take) return "";
  if (take.hasUpscalePreview) {
    return `${Number(take.durationSeconds || 0)}s · candidato FHD aguardando aprovação`;
  }
  const lightPlayback = take.hasReviewProxy ? " · reprodução leve (até 720p)" : "";
  const duration = take.hasReviewProxy
    ? Number(take.reviewDurationSeconds || take.durationSeconds || 0)
    : Number(take.durationSeconds || 0);
  return `${duration.toFixed(2)}s · ${filmTakeStatusLabel(take.status)}${lightPlayback}`;
}

function syncFilmTakeAfterUpdate(updated) {
  state.films.takeUpdateSequence += 1;
  const previous = state.films.takes.find((take) => take.takeId === updated.takeId);
  state.films.takes = state.films.takes.map((take) => (take.takeId === updated.takeId ? updated : take));
  renderFilmSummary(state.films.projects.find((project) => project.projectId === state.films.activeProjectId));
  renderFilmTakes();
  if (state.films.activeTakeId === updated.takeId) {
    const mediaChanged = !previous
      || previous.hasPreview !== updated.hasPreview
      || previous.previewFile !== updated.previewFile
      || previous.hasUpscalePreview !== updated.hasUpscalePreview
      || previous.upscalePreviewFile !== updated.upscalePreviewFile
      || previous.upscaleCandidateStatus !== updated.upscaleCandidateStatus
      || previous.isUpscaled !== updated.isUpscaled
      || previous.reviewProxyVersion !== updated.reviewProxyVersion;
    if (mediaChanged) {
      openFilmTakePreview(updated.takeId, { autoplay: false, scroll: false, refreshList: false });
    } else {
      $("#film-preview-meta").textContent = filmPreviewMeta(updated);
      renderFilmPlayerReview(updated);
      syncActiveFilmTakeCard(updated.takeId);
    }
  }
}

function advanceFilmReview(completedTakeId) {
  if (state.films.view !== "review") return;
  const completedIndex = state.films.takes.findIndex((take) => take.takeId === completedTakeId);
  const remaining = visibleFilmTakes("review");
  const next = remaining.find((take) => state.films.takes.indexOf(take) > completedIndex) || remaining[0];
  renderFilmTakes();
  if (next) openFilmTakePreview(next.takeId, { autoplay: false, scroll: false, refreshList: false });
  else closeFilmTakePreview();
}

async function refreshActiveFilmProjectSummary() {
  const projectId = state.films.activeProjectId;
  if (!projectId) return;
  const updateSequence = state.films.takeUpdateSequence;
  try {
    const project = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}`);
    if (state.films.activeProjectId !== projectId || state.films.takeUpdateSequence !== updateSequence) return;
    state.films.projects = state.films.projects.map((entry) => (entry.projectId === projectId ? project : entry));
    renderFilmProjectList();
    renderFilmSummary(project);
  } catch (_error) {
    // A decisão já foi salva; a próxima atualização recompõe somente o resumo.
  }
}

async function refreshFilmProjectData(projectId = state.films.activeProjectId, { onlyIfChanged = false } = {}) {
  if (!projectId || state.films.activeProjectId !== projectId) return;
  const updateSequence = state.films.takeUpdateSequence;
  const previousActive = state.films.takes.find((take) => take.takeId === state.films.activeTakeId);
  const [project, takes] = await Promise.all([
    fetchFilmMetadata(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}`),
    fetchFilmMetadata(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes?page=1&pageSize=100`),
  ]);
  if (state.films.activeProjectId !== projectId || state.films.takeUpdateSequence !== updateSequence) return;
  const currentProject = state.films.projects.find((entry) => entry.projectId === projectId) || null;
  const nextTakes = takes.data || [];
  const changed = state.films.projectDataLoading || Boolean(state.films.projectDataError)
    || JSON.stringify(currentProject) !== JSON.stringify(project)
    || JSON.stringify(state.films.takes) !== JSON.stringify(nextTakes);
  state.films.projectDataLoading = false;
  state.films.projectDataError = "";
  state.films.projects = state.films.projects.map((entry) => (entry.projectId === projectId ? project : entry));
  state.films.takes = nextTakes;
  if (onlyIfChanged && !changed) return;
  renderFilmProjectList();
  renderFilmSummary(project);
  renderFilmTakes();

  const active = state.films.takes.find((take) => take.takeId === state.films.activeTakeId);
  if (!active) return;
  const mediaChanged = previousActive
    && (
      previousActive.hasPreview !== active.hasPreview
      || previousActive.previewFile !== active.previewFile
      || previousActive.hasUpscalePreview !== active.hasUpscalePreview
      || previousActive.upscalePreviewFile !== active.upscalePreviewFile
      || previousActive.upscaleCandidateStatus !== active.upscaleCandidateStatus
      || previousActive.isUpscaled !== active.isUpscaled
      || previousActive.reviewProxyVersion !== active.reviewProxyVersion
    );
  if (mediaChanged) {
    openFilmTakePreview(active.takeId, { autoplay: false, scroll: false, refreshList: false });
  } else {
    $("#film-preview-meta").textContent = filmPreviewMeta(active);
    renderFilmPlayerReview(active);
    syncActiveFilmTakeCard(active.takeId);
  }
}

function closeFilmTakePreview() {
  const video = $("#film-preview-video");
  const image = $("#film-preview-image");
  video.pause();
  delete video.dataset.previewUrl;
  delete video.dataset.autoplay;
  video.removeAttribute("src");
  video.load();
  video.classList.add("hidden");
  image.removeAttribute("src");
  image.alt = "";
  image.classList.add("hidden");
  $("#film-preview-empty").classList.remove("hidden");
  $("#film-preview-open").classList.add("hidden");
  $("#film-preview-open").removeAttribute("href");
  $("#film-preview-download").classList.add("hidden");
  $("#film-preview-download").removeAttribute("href");
  setVerifiedDownloadLink($("#film-preview-download"));
  $("#film-preview-kicker").textContent = "Player do projeto";
  $("#film-preview-title").textContent = "Assista aos takes";
  $("#film-preview-meta").textContent = "Escolha um take na lista abaixo.";
  syncFilmPreviewBuffer(video, "Selecione um take para carregar o vídeo.");
  renderFilmPlayerReview(null);
  state.films.activeTakeId = "";
}

function filmPreviewBufferedPercent(video) {
  if (!video || !Number.isFinite(video.duration) || video.duration <= 0 || !video.buffered?.length) return 0;
  let bufferedEnd = 0;
  for (let index = 0; index < video.buffered.length; index += 1) {
    bufferedEnd = Math.max(bufferedEnd, video.buffered.end(index));
  }
  return Math.max(0, Math.min(100, Math.round((bufferedEnd / video.duration) * 100)));
}

function syncFilmPreviewBuffer(video, message = "") {
  const progress = $("#film-preview-buffer-progress");
  const status = $("#film-preview-playback-status");
  const percent = filmPreviewBufferedPercent(video);
  if (progress) {
    progress.value = percent;
    progress.textContent = `${percent}%`;
  }
  if (status && message) status.textContent = message.replace("{percent}", String(percent));
  return percent;
}

function playFilmPreviewWhenReady(video, previewUrl) {
  if (!video || video.dataset.previewUrl !== previewUrl) return;
  const start = () => {
    if (video.dataset.previewUrl !== previewUrl || video.dataset.autoplay !== "1") return;
    video.play().catch(() => {
      syncFilmPreviewBuffer(video, "Vídeo carregado. Pressione play para assistir.");
    });
  };
  if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) start();
  else video.addEventListener("canplay", start, { once: true });
}

function syncActiveFilmTakeCard(takeId) {
  document.querySelectorAll("[data-film-take-card]").forEach((card) => {
    const active = card.dataset.filmTakeCard === takeId;
    card.classList.toggle("active", active);
    const button = card.querySelector("[data-film-take-open]");
    if (button) button.setAttribute("aria-current", active ? "true" : "false");
  });
}

function openFilmFinalPreview({ autoplay = true, scroll = true } = {}) {
  const project = state.films.projects.find((item) => item.projectId === state.films.activeProjectId);
  const source = filmFinalOutputSource(project);
  const output = source?.output;
  if (!project || !output) return;
  renderFilmFinalOutput(project);
  const video = $("#film-final-video");
  const player = $("#film-final-player");
  if (autoplay) {
    video.play().catch(() => {
      $("#film-final-player-status").textContent = "Pressione play para assistir ao master.";
    });
  }
  if (scroll) {
    const bounds = player.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
      const stickyActions = $("#film-project-actions");
      const stickyStyle = stickyActions ? window.getComputedStyle(stickyActions) : null;
      const stickyHeight = stickyActions && stickyStyle?.position === "sticky"
        ? stickyActions.getBoundingClientRect().height + 24
        : 12;
      const targetTop = window.scrollY + bounds.top - stickyHeight;
      window.scrollTo({ top: Math.max(0, targetTop), behavior: "auto" });
    }
  }
}

async function pollFilmAssemblyJob(projectId, jobId) {
  while (state.films.assemblyJob?.jobId === jobId) {
    try {
      const job = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}`);
      state.films.assemblyJob = { ...job, jobId, projectId };
      const project = state.films.projects.find((item) => item.projectId === projectId);
      renderFilmFinalization(project);
      if (["done", "error", "canceled", "interrupted"].includes(job.status)) {
        await refreshFilmProjectData(projectId);
        if (job.status === "done") toast("Master técnico pronto para sua revisão final");
        else toast(job.error || job.message || "A montagem não foi concluída.");
        return;
      }
    } catch (error) {
      state.films.assemblyJob = { jobId, projectId, status: "error", error: error.message };
      const project = state.films.projects.find((item) => item.projectId === projectId);
      renderFilmFinalization(project);
      toast(error.message);
      return;
    }
    await sleep(1400);
  }
}

async function startFilmAssembly(button = $("#film-assembly-start")) {
  const projectId = state.films.activeProjectId;
  if (!projectId || !button || button.disabled) return;
  if (!window.confirm("Montar agora somente os takes e áudios aprovados, com cortes secos e sem reduzir a qualidade?")) return;
  try {
    setBusy(button, true, "Enfileirando");
    const started = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/assembly-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    state.films.assemblyJob = { ...started, projectId };
    renderFilmFinalization(state.films.projects.find((item) => item.projectId === projectId));
    pollFilmAssemblyJob(projectId, started.jobId);
  } catch (error) {
    toast(error.message);
    setBusy(button, false);
  }
}

async function reviewFilmFinalOutput(decision, button) {
  const projectId = state.films.activeProjectId;
  if (!projectId || !button || button.disabled) return;
  const reject = decision === "reject";
  const reasonField = $("#film-final-rejection-reason");
  const reason = String(reasonField?.value || "").trim();
  if (reject && reason.length < 3) {
    reasonField?.focus();
    toast("Explique em pelo menos 3 caracteres por que o master foi reprovado.");
    return;
  }
  const question = reject
    ? "Reprovar este master e preservar o arquivo como evidência?"
    : "Aprovar este master como entrega final do projeto?";
  if (!window.confirm(question)) return;
  try {
    setBusy(button, true, reject ? "Reprovando" : "Aprovando");
    const project = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/final-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason }),
    });
    state.films.projects = state.films.projects.map((item) => (item.projectId === projectId ? project : item));
    if (reasonField) reasonField.value = "";
    renderFilmProjectList();
    renderFilmSummary(project);
    toast(reject ? "Master reprovado e preservado" : "Master aprovado como entrega final");
  } catch (error) {
    toast(error.message);
  } finally {
    if (document.body.contains(button)) setBusy(button, false);
  }
}

function openFilmTakePreview(takeId, { autoplay = true, scroll = true, refreshList = false } = {}) {
  const projectId = state.films.activeProjectId;
  const take = state.films.takes.find((item) => item.takeId === takeId);
  if (!projectId || !take) return;
  const previewEndpoint = take.hasUpscalePreview ? "upscale-preview" : "preview";
  const previewBaseUrl = `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/${previewEndpoint}`;
  const previewVersion = previewEndpoint === "preview"
    ? take.reviewProxyVersion || take.previewVersion || `${take.previewFile || "master"}-${take.masterBytes || 0}`
    : take.upscalePreviewFile || "upscale";
  const previewUrl = `${previewBaseUrl}?v=${encodeURIComponent(previewVersion)}`;
  const imageVersion = encodeURIComponent(take.directorRequest?.updatedAt || take.qcStatus || "base");
  const thumbnailUrl = `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/thumbnail?v=${imageVersion}`;
  const anchorImageUrl = `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/anchor-image?v=${imageVersion}`;
  const imageUrl = filmTakeHasRegisteredAnchor(take) ? anchorImageUrl : thumbnailUrl;
  const video = $("#film-preview-video");
  const image = $("#film-preview-image");
  const open = $("#film-preview-open");
  const download = $("#film-preview-download");
  state.films.activeTakeId = takeId;
  $("#film-preview-title").textContent = `Take ${takeId} — ${filmTakeDisplayName(take)}`;
  $("#film-preview-meta").textContent = filmPreviewMeta(take);
  renderFilmPlayerReview(take);
  $("#film-preview-empty").classList.add("hidden");
  open.classList.remove("hidden");

  if (take.hasPreview || take.hasUpscalePreview) {
    image.classList.add("hidden");
    image.removeAttribute("src");
    video.classList.remove("hidden");
    video.preload = "auto";
    const sourceChanged = video.dataset.previewUrl !== previewUrl;
    if (sourceChanged) {
      video.pause();
      video.dataset.previewUrl = previewUrl;
      video.src = previewUrl;
      video.load();
      syncFilmPreviewBuffer(video, "Carregando vídeo e preparando o buffer… {percent}%");
    }
    open.href = previewUrl;
    open.textContent = "Abrir vídeo";
    if (take.canDownload) {
      download.href = `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/preview?download=true`;
      download.setAttribute("download", take.previewFile || `take_${takeId}.mp4`);
      download.classList.remove("hidden");
    } else {
      download.classList.add("hidden");
      download.removeAttribute("href");
    }
    setVerifiedDownloadLink(download);
    $("#film-preview-kicker").textContent = "Em exibição";
    video.dataset.autoplay = autoplay ? "1" : "0";
    if (autoplay) playFilmPreviewWhenReady(video, previewUrl);
  } else if (take.hasKeyframe || take.hasEndKeyframeCandidate) {
    video.pause();
    video.removeAttribute("src");
    video.load();
    video.classList.add("hidden");
    image.src = imageUrl;
    image.alt = filmTakeAnchorReviewPending(take)
      ? `Nova imagem-âncora do take ${takeId}, aguardando sua aprovação: ${filmTakeDisplayName(take)}`
      : filmTakeAnchorPending(take)
        ? `Imagem de referência do take ${takeId}, ainda bloqueado para vídeo: ${filmTakeDisplayName(take)}`
        : `Imagem aprovada do take ${takeId}: ${filmTakeDisplayName(take)}`;
    image.classList.remove("hidden");
    open.href = imageUrl;
    open.textContent = "Abrir imagem";
    download.classList.add("hidden");
    download.removeAttribute("href");
    setVerifiedDownloadLink(download);
    $("#film-preview-kicker").textContent = filmTakeAnchorReviewPending(take)
      ? "Imagem nova · aguardando sua aprovação"
      : filmTakeAnchorPending(take)
        ? "Imagem de referência · vídeo bloqueado"
        : "Imagem aprovada · pronta para o vídeo";
  } else {
    closeFilmTakePreview();
    return;
  }
  if (refreshList) renderFilmTakes();
  syncActiveFilmTakeCard(takeId);
  if (scroll) {
    const frame = $("#film-player-frame");
    const bounds = frame.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > window.innerHeight) {
      frame.scrollIntoView({ behavior: "auto", block: "start" });
    }
  }
}

async function loadVideoSoundProviders() {
  const payload = await fetchFilmMetadata(`${API.studio}/api/video-sound/providers`);
  state.films.videoSoundProviders = Array.isArray(payload.providers) ? payload.providers : [];
  const configured = state.films.videoSoundProviders.filter((provider) => provider.configured);
  if (!configured.some((provider) => provider.providerId === state.films.videoSoundProviderId)) {
    state.films.videoSoundProviderId = payload.defaultProviderId || configured[0]?.providerId || "";
  }
  return payload;
}

async function pollFilmVideoSoundJob(projectId, takeId, jobId) {
  while (state.films.videoSoundJobs[takeId]?.jobId === jobId) {
    try {
      const job = await fetchJson(`${API.studio}/api/video-sound/jobs/${encodeURIComponent(jobId)}`);
      state.films.videoSoundJobs[takeId] = job;
      renderFilmTakes();
      if (job.status === "done") {
        toast(`Take ${takeId}: som sincronizado pronto para escuta humana`);
        delete state.films.videoSoundJobs[takeId];
        await refreshFilmProjectData(projectId);
        return;
      }
      if (["error", "interrupted", "canceled"].includes(job.status)) {
        throw new Error(job.error || "Falha na geração do som pelo vídeo.");
      }
      await sleep(2500);
    } catch (error) {
      delete state.films.videoSoundJobs[takeId];
      renderFilmTakes();
      toast(`Take ${takeId}: ${error.message}`);
      return;
    }
  }
}

async function startFilmVideoSound(button) {
  const projectId = state.films.activeProjectId;
  const takeId = button.dataset.filmVideoSoundStart;
  const provider = document.querySelector(`[data-film-video-sound-provider="${CSS.escape(takeId)}"]`);
  const prompt = document.querySelector(`[data-film-video-sound-prompt="${CSS.escape(takeId)}"]`);
  const duration = document.querySelector(`[data-film-video-sound-duration="${CSS.escape(takeId)}"]`);
  if (!projectId || !takeId || !provider || !prompt || !duration) return;
  const direction = String(prompt.value || "").trim();
  if (direction.length < 12) return toast("Descreva o ambiente, movimentos e impactos esperados.");
  state.films.videoSoundProviderId = provider.value;
  try {
    setBusy(button, true, "Enfileirando som");
    const started = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/video-sound-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        providerId: provider.value,
        prompt: direction,
        negativePrompt: "music, soundtrack, speech, dialogue, clipping",
        durationSeconds: Number(duration.value || 0),
        seed: -1,
      }),
    });
    state.films.videoSoundJobs[takeId] = {
      jobId: started.jobId,
      status: "queued",
      progress: 1,
    };
    renderFilmTakes();
    pollFilmVideoSoundJob(projectId, takeId, started.jobId);
  } catch (error) {
    delete state.films.videoSoundJobs[takeId];
    renderFilmTakes();
    toast(error.message);
  }
}

async function reviewFilmAudioCandidate(button) {
  const projectId = state.films.activeProjectId;
  const takeId = button.dataset.filmAudioTake;
  const decision = button.dataset.filmAudioReview;
  const reasonField = document.querySelector(`[data-film-audio-reject-reason="${CSS.escape(takeId)}"]`);
  const reason = String(reasonField?.value || "").trim();
  if (decision === "REJECTED" && reason.length < 3) {
    reasonField?.focus();
    return toast("Explique por que o som foi reprovado.");
  }
  try {
    setBusy(button, true, decision === "APPROVED" ? "Aprovando" : "Reprovando");
    const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/audio-candidate-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, reason }),
    });
    syncFilmTakeAfterUpdate(updated);
    toast(decision === "APPROVED" ? "Áudio aprovado por escuta humana" : "Áudio reprovado e removido do slot ativo");
  } catch (error) {
    toast(error.message);
  } finally {
    if (document.body.contains(button)) setBusy(button, false);
  }
}

async function loadFilmProject(projectId) {
  const loadSequence = state.films.projectLoadSequence + 1;
  state.films.projectLoadSequence = loadSequence;
  const preferredTakeId = projectId === state.films.activeProjectId ? state.films.activeTakeId : "";
  if (projectId !== state.films.activeProjectId) state.films.finalViewedFingerprint = "";
  closeFilmTakePreview();
  state.films.activeProjectId = projectId;
  state.films.projectDataLoading = true;
  state.films.projectDataError = "";
  state.films.takes = [];
  renderFilmProjectList();
  $("#film-playlist-count").textContent = "Carregando";
  $("#film-takes-list").innerHTML = '<div class="film-empty" role="status">Carregando takes...</div>';
  syncFilmBatchActions();
  try {
    const [project, takes] = await Promise.all([
      fetchFilmMetadata(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}`),
      fetchFilmMetadata(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes?page=1&pageSize=100`),
      loadVideoSoundProviders().catch(() => null),
    ]);
    if (state.films.projectLoadSequence !== loadSequence || state.films.activeProjectId !== projectId) return;
    state.films.projectDataLoading = false;
    state.films.projectDataError = "";
    state.films.takes = takes.data || [];
    renderFilmProjectList();
    const defaultView = defaultFilmWorkflowView();
    if (
      !FILM_WORKFLOW_VIEWS.has(state.films.view)
      || (
        !filmWorkflowViewHasContent(state.films.view)
        && filmWorkflowViewHasContent(defaultView)
      )
    ) {
      state.films.view = defaultView;
    }
    const candidates = state.films.view === "production" ? [] : visibleFilmTakes();
    const preferred = candidates.find((take) => take.takeId === preferredTakeId) || candidates[0];
    state.films.activeTakeId = preferred?.takeId || "";
    renderFilmSummary(project);
    renderFilmTakes();
    if (preferred) openFilmTakePreview(preferred.takeId, { autoplay: false, scroll: false, refreshList: false });
    else closeFilmTakePreview();
  } catch (error) {
    if (state.films.projectLoadSequence !== loadSequence || state.films.activeProjectId !== projectId) return;
    state.films.projectDataLoading = false;
    state.films.projectDataError = error.message || "erro desconhecido";
    state.films.takes = [];
    renderFilmSummary(null);
    $("#film-playlist-count").textContent = "Erro";
    $("#film-takes-list").innerHTML = `<div class="film-empty" role="alert">${html(error.message)}</div>`;
    syncFilmBatchActions();
  }
}

async function loadFilmProjects() {
  if (state.films.projectsLoadPromise) return state.films.projectsLoadPromise;

  const pending = (async () => {
    $("#film-project-count").textContent = "Carregando";
    state.films.projectDataLoading = true;
    state.films.projectDataError = "";
    syncFilmBatchActions();
    loadFilmProductionQueue();
    try {
      const payload = await fetchFilmMetadata(`${API.studio}/api/video-projects?page=1&pageSize=100`);
      state.films.projects = payload.data || [];
      if (state.films.productionQueueData) renderFilmProductionQueue(state.films.productionQueueData);
      if (!state.films.projects.some((project) => project.projectId === state.films.activeProjectId)) {
        state.films.activeProjectId = state.films.projects[0]?.projectId || "";
      }
      renderFilmProjectList();
      if (state.films.activeProjectId) {
        await loadFilmProject(state.films.activeProjectId);
      } else {
        state.films.projectDataLoading = false;
        state.films.takes = [];
        renderFilmSummary(null);
        renderFilmTakes();
      }
    } catch (error) {
      state.films.projectDataLoading = false;
      state.films.projectDataError = error.message || "erro desconhecido";
      $("#film-project-count").textContent = "Erro";
      $("#film-project-list").innerHTML = `<div class="film-empty" role="alert">${html(error.message)}</div>`;
      syncFilmBatchActions();
    }
  })();

  state.films.projectsLoadPromise = pending;
  try {
    return await pending;
  } finally {
    if (state.films.projectsLoadPromise === pending) {
      state.films.projectsLoadPromise = null;
    }
  }
}

async function createFilmProject(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $("#film-create-submit");
  const payload = {
    name: $("#film-name").value.trim(),
    objective: $("#film-objective").value.trim(),
    durationSeconds: Number($("#film-duration").value || 60),
    distributionMode: $("#film-distribution-mode")?.value || "auto",
  };
  try {
    setBusy(button, true, "Criando");
    const project = await fetchJson(`${API.studio}/api/video-projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.films.activeProjectId = project.projectId;
    form.reset();
    $("#film-duration").value = "60";
    await loadFilmProjects();
    toast("Projeto criado");
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

async function applyFilmTakeDecision(takeId, status, control = null) {
  const projectId = state.films.activeProjectId;
  if (!projectId || !takeId) return;
  const take = state.films.takes.find((item) => item.takeId === takeId);
  const upscaleReviewPending = Boolean(take?.hasUpscalePreview);
  if (status === "REJECTED" && !upscaleReviewPending) {
    openFilmDirectorDialog(takeId);
    return;
  }
  if (
    status === "REJECTED"
    && upscaleReviewPending
    && !confirm("Rejeitar este candidato FHD? O vídeo aprovado anterior será preservado e uma nova tentativa ficará disponível.")
  ) return;
  const isButton = control?.tagName === "BUTTON";
  if (isButton) setBusy(control, true, "Salvando");
  else if (control) control.disabled = true;
  try {
    const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (state.films.activeProjectId !== projectId) return;
    syncFilmTakeAfterUpdate(updated);
    toast(upscaleReviewPending
      ? `Take ${takeId}: remaster FHD ${status === "APPROVED" ? "aprovado" : "rejeitado; anterior preservado"}`
      : `Take ${takeId}: ${filmTakeStatusLabel(status)}`);
    if (["APPROVED", "REJECTED"].includes(status)) advanceFilmReview(takeId);
    void refreshActiveFilmProjectSummary();
  } catch (error) {
    toast(error.message);
  } finally {
    if (isButton) setBusy(control, false);
    else if (control) control.disabled = false;
  }
}

async function updateFilmTakeStatus(select) {
  const takeId = select.dataset.filmTakeStatus;
  const previous = state.films.takes.find((take) => take.takeId === takeId)?.status || "PLANNED";
  const status = select.value;
  if (status === "REJECTED") select.value = previous;
  await applyFilmTakeDecision(takeId, status, select);
}

function closeFilmDirectorDialog() {
  const dialog = $("#film-director-dialog");
  $("#film-director-form").reset();
  $("#film-director-take-id").value = "";
  $("#film-director-mode").value = "correction";
  $("#film-director-category-field").classList.remove("hidden");
  if (typeof dialog.close === "function" && dialog.open) dialog.close();
  else dialog.removeAttribute("open");
}

function openFilmDirectorDialog(takeId, mode = "correction") {
  const take = state.films.takes.find((item) => item.takeId === takeId);
  if (!take) return;
  const dialog = $("#film-director-dialog");
  $("#film-director-form").reset();
  $("#film-director-take-id").value = takeId;
  $("#film-director-mode").value = mode;
  const anchorRequestMode = mode === "anchor";
  const anchorReviewMode = mode === "anchor_review";
  const anchorMode = anchorRequestMode || anchorReviewMode;
  $("#film-director-kicker").textContent = anchorMode ? "IMAGEM-ÂNCORA" : "CORREÇÃO";
  $("#film-director-title").textContent = anchorReviewMode ? "Explicar nova imagem (1/2)" : anchorRequestMode ? "Pedir foto-base (1/2)" : "Explicar correção (1/2)";
  $("#film-director-copy").textContent = anchorReviewMode
    ? `Take ${takeId} — ${filmTakeDisplayName(take)}. Explique o que precisa mudar; a candidata atual ficará guardada e a nova geração usa a GPU.`
    : anchorRequestMode
      ? `Take ${takeId} — ${filmTakeDisplayName(take)}. Ao enviar, o pedido será registrado e o executor supervisionado usa a GPU para gerar a foto-base.`
      : `Take ${takeId} — ${filmTakeDisplayName(take)}. Ao enviar, o pedido será registrado e a correção será enfileirada no motor autorizado do take; o vídeo atual continuará guardado.`;
  $("#film-director-category-field").classList.toggle("hidden", anchorMode);
  $("#film-director-category").value = anchorMode ? "ANCHOR" : "";
  $("#film-director-reason-label").textContent = anchorReviewMode ? "O que deve mudar na imagem" : anchorRequestMode ? "Orientação para a nova imagem" : "O que deve ser corrigido";
  $("#film-director-reason").value = anchorRequestMode ? filmAnchorRequestReason(take) : "";
  $("#film-director-submit").textContent = anchorReviewMode ? "Registrar e gerar outra imagem com GPU (2/2)" : anchorRequestMode ? "Registrar e gerar foto-base com GPU (2/2)" : "Registrar e enfileirar correção (2/2)";
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  (anchorMode ? $("#film-director-reason") : $("#film-director-category")).focus();
}

async function startFilmAnchorExecutor(takeIds, control = null) {
  const projectId = state.films.activeProjectId;
  const selected = [...new Set((takeIds || []).filter(Boolean))];
  if (!projectId || !selected.length) return null;
  try {
    if (control) setBusy(control, true, "Iniciando GPU");
    const started = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/anchor-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ takeIds: selected }),
    });
    await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
    toast(`${selected.length} foto${selected.length === 1 ? "-base iniciada" : "s-base iniciadas"} no executor supervisionado`);
    return started;
  } catch (error) {
    toast(`Pedidos preservados; o executor de fotos-base não iniciou · ${error.message}`);
    throw error;
  } finally {
    if (control) setBusy(control, false);
  }
}

function closeFilmPreanalysisDialog() {
  const dialog = $("#film-preanalysis-dialog");
  const image = $("#film-preanalysis-image");
  image?.removeAttribute("src");
  if (typeof dialog?.close === "function" && dialog.open) dialog.close();
  else dialog?.removeAttribute("open");
}

function openFilmPreanalysisDialog(takeId) {
  const take = state.films.takes.find((item) => item.takeId === takeId);
  if (!take?.hasPreanalysisGallery) return;
  const projectId = state.films.activeProjectId;
  const dialog = $("#film-preanalysis-dialog");
  const url = `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/preanalysis-gallery?v=${encodeURIComponent(take.preanalysisGallery?.sha256 || "gallery")}`;
  $("#film-preanalysis-title").textContent = `Take ${takeId} — sequência de âncoras`;
  $("#film-preanalysis-copy").textContent = `${Number(take.preanalysisGallery?.candidateCount || 0)} imagens em ordem de movimento. QC técnico concluído; nenhuma aprovação humana é inferida por esta galeria.`;
  const image = $("#film-preanalysis-image");
  image.src = url;
  image.alt = `Pré-análise START, checkpoint e END do take ${takeId}`;
  const full = $("#film-preanalysis-full");
  full.href = url;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  $("#film-preanalysis-close").focus();
}

async function submitFilmDirectorRequest(event) {
  event.preventDefault();
  const projectId = state.films.activeProjectId;
  const takeId = $("#film-director-take-id").value;
  const button = $("#film-director-submit");
  const mode = $("#film-director-mode").value;
  if (!projectId || !takeId) return;
  const directorRequest = {
    category: $("#film-director-category").value,
    reason: $("#film-director-reason").value.trim(),
  };
  const payload = mode === "anchor" ? { directorRequest } : {
    status: "REJECTED",
    directorRequest: {
      ...directorRequest,
    },
  };
  try {
    setBusy(button, true, "Enviando");
    const anchorReviewMode = mode === "anchor_review";
    const take = state.films.takes.find((item) => item.takeId === takeId);
    const requestId = filmAnchorReviewRequestId(take);
    const endpoint = anchorReviewMode
      ? `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/anchor-review`
      : `${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}`;
    const updated = await fetchFilmDirectorRequest(endpoint, {
      method: anchorReviewMode ? "POST" : "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(anchorReviewMode ? {
        decision: "REJECTED",
        reason: directorRequest.reason,
        ...(requestId ? { requestId } : {}),
      } : payload),
    });
    closeFilmDirectorDialog();
    if (state.films.activeProjectId === projectId) {
      syncFilmTakeAfterUpdate(updated);
      if (mode !== "anchor") advanceFilmReview(takeId);
      void refreshActiveFilmProjectSummary();
    }
    toast(`Take ${takeId}: ${mode === "correction" ? "rejeição e correção salvas" : "pedido salvo"}`);
    void continueSavedFilmCorrection(projectId, takeId, mode, updated);
  } catch (error) {
    toast(error.message);
  } finally {
    setBusy(button, false);
  }
}

async function continueSavedFilmCorrection(projectId, takeId, mode, updated) {
  const anchorReviewMode = mode === "anchor_review";
  try {
    let started = null;
    let anchorStarted = null;
    if (mode === "correction" && updated.canGenerate) {
      try {
        started = await fetchFilmDirectorRequest(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
      } catch (queueError) {
        toast(`Take ${takeId}: pedido salvo; não foi possível confirmar a entrada da correção na fila · ${queueError.message}`);
        return;
      }
    } else if (mode === "anchor" || anchorReviewMode) {
      try {
        anchorStarted = await fetchFilmDirectorRequest(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/anchor-jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ takeIds: [takeId] }),
        });
      } catch (queueError) {
        toast(`Take ${takeId}: pedido salvo; não foi possível confirmar o início da foto-base · ${queueError.message}`);
        return;
      }
    }
    if (started) {
      pollFilmTakeJob(projectId, takeId, started.jobId);
      toast(`Take ${takeId}: pedido registrado e correção enfileirada`);
    } else if (anchorStarted) {
      toast(`Take ${takeId}: pedido registrado e foto-base iniciada com GPU`);
    } else {
      toast(`Take ${takeId}: ${FILM_REQUEST_AWAITING_EXECUTOR_COPY}`);
    }
    if ((started || anchorStarted) && state.films.activeProjectId === projectId) {
      await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
    }
  } catch (error) {
    toast(`Take ${takeId}: pedido salvo; atualização da correção pendente · ${error.message}`);
  }
}

async function reviewFilmAnchor(takeId, decision, control = null) {
  const projectId = state.films.activeProjectId;
  if (!projectId || !takeId || decision !== "APPROVED") return;
  const take = state.films.takes.find((item) => item.takeId === takeId);
  const requestId = filmAnchorReviewRequestId(take);
  try {
    if (control) setBusy(control, true, "Aprovando");
    const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/anchor-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision,
        humanConfirmed: true,
        ...(requestId ? { requestId } : {}),
        ...(Array.isArray(take?.anchorExpectedVisibleCharacters)
          ? { actualVisibleCharacters: take.anchorExpectedVisibleCharacters }
          : {}),
      }),
    });
    if (state.films.activeProjectId !== projectId) return;
    syncFilmTakeAfterUpdate(updated);
    toast(`Take ${takeId}: imagem aprovada e vídeo liberado`);
    advanceFilmReview(takeId);
    void refreshActiveFilmProjectSummary();
  } catch (error) {
    toast(error.message);
  } finally {
    if (control) setBusy(control, false);
  }
}

async function requestFilmAnchorBatch(button) {
  const projectId = state.films.activeProjectId;
  const candidates = state.films.takes.filter((take) => filmTakeAnchorPending(take) && !filmAnchorRequestAwaitingExecutor(take));
  if (!projectId || !candidates.length || !button || button.disabled) return;
  if (!confirm(`Registrar e iniciar ${candidates.length} foto${candidates.length === 1 ? "-base" : "s-base"}? O executor usa a GPU e processa uma imagem por vez.`)) return;
  const updatedById = new Map();
  const failures = [];
  try {
    setBusy(button, true, `Enviando 0/${candidates.length}`);
    for (let index = 0; index < candidates.length; index += 1) {
      const take = candidates[index];
      button.textContent = `Enviando ${index + 1}/${candidates.length}`;
      try {
        const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(take.takeId)}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            directorRequest: { category: "ANCHOR", reason: filmAnchorRequestReason(take) },
          }),
        });
        updatedById.set(updated.takeId, updated);
      } catch (error) {
        failures.push(`${take.takeId}: ${error.message}`);
      }
    }
    state.films.takes = state.films.takes.map((take) => updatedById.get(take.takeId) || take);
    renderFilmTakes();
    renderFilmSummary(state.films.projects.find((project) => project.projectId === projectId));
    let executorError = null;
    if (updatedById.size) {
      try {
        await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/anchor-jobs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ takeIds: [...updatedById.keys()] }),
        });
      } catch (error) {
        executorError = error;
      }
    }
    toast(executorError
      ? `${updatedById.size} pedido(s) preservado(s), mas o executor não iniciou · ${executorError.message}`
      : failures.length
        ? `${updatedById.size} foto(s) iniciada(s) com GPU; ${failures.length} pedido(s) falharam.`
        : `${updatedById.size} foto${updatedById.size === 1 ? "-base iniciada" : "s-base iniciadas"} com GPU`);
    await refreshActiveFilmProjectSummary();
  } finally {
    setBusy(button, false);
    syncFilmBatchActions();
  }
}

function handleFilmAnchorBatchAction(button) {
  if (button?.dataset.anchorAction === "review") {
    const candidate = state.films.takes.find(filmTakeAnchorReviewPending);
    if (!candidate) return;
    setFilmWorkflowView("review");
    openFilmTakePreview(candidate.takeId, { autoplay: false, scroll: true, refreshList: false });
    return;
  }
  if (button?.dataset.anchorAction === "start") {
    const waiting = state.films.takes.filter(filmAnchorRequestAwaitingExecutor).map((take) => take.takeId);
    if (!waiting.length) return;
    if (!confirm(`Iniciar ${waiting.length} foto${waiting.length === 1 ? "-base" : "s-base"} agora? O executor usará a GPU uma por vez.`)) return;
    startFilmAnchorExecutor(waiting, button).catch(() => {});
    return;
  }
  requestFilmAnchorBatch(button);
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function formatFilmTakeJobProgress(job) {
  const progress = Math.max(0, Math.min(100, Number(job?.progress || 0)));
  const message = String(job?.message || "Gerando").trim();
  if (job?.status === "queued") return message;
  if (job?.status !== "running") return `${progress}% ${message}`;

  const nowSeconds = Date.now() / 1000;
  const startedAt = Number(job?.started_at || job?.created_at || nowSeconds);
  const updatedAt = Number(job?.updated_at || 0);
  const elapsedSeconds = Math.max(0, Math.floor(nowSeconds - startedAt));
  const elapsed = elapsedSeconds >= 60
    ? `${Math.floor(elapsedSeconds / 60)}m ${String(elapsedSeconds % 60).padStart(2, "0")}s`
    : `${elapsedSeconds}s`;
  const heartbeatAge = updatedAt > 0 ? Math.max(0, nowSeconds - updatedAt) : Infinity;
  const heartbeat = heartbeatAge <= 15 ? "motor ativo" : "sem resposta recente";
  return `${progress}% estimado · ${heartbeat} · ${elapsed}`;
}

async function pollFilmTakeJob(projectId, takeId, jobId) {
  if (!jobId || state.films.pollingJobs[jobId] || state.films.terminalJobs[jobId]) return;
  state.films.pollingJobs[jobId] = true;
  try {
    while (true) {
      const job = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}`);
      const button = document.querySelector(`[data-film-take-generate="${CSS.escape(takeId)}"]`);
      if (button) {
        button.disabled = true;
        button.textContent = formatFilmTakeJobProgress(job);
        button.title = job.message || "";
      }
      if (job.status === "done") {
        delete state.films.terminalJobs[jobId];
        toast(job.job_kind === "video_upscale"
          ? `Take ${takeId}: versão 1080p pronta para revisar`
          : `Take ${takeId} pronto para você decidir`);
        break;
      }
      if (["error", "interrupted", "canceled"].includes(job.status)) {
        state.films.terminalJobs[jobId] = true;
        throw new Error(job.error || "Falha na geração do take.");
      }
      await sleep(3000);
    }
  } catch (error) {
    toast(`Take ${takeId}: ${error.message}`);
  } finally {
    delete state.films.pollingJobs[jobId];
    if (state.films.activeProjectId === projectId) {
      try {
        await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
      } catch (_error) {
        // A fila persistente continua correta; o proximo polling recompõe a interface.
      }
    }
    if (state.films.terminalJobs[jobId]) {
      window.setTimeout(async () => {
        try {
          const recovered = await fetchJson(`${API.studio}/api/generative/job/${encodeURIComponent(jobId)}`);
          if (recovered.status === "queued" || recovered.status === "running") {
            delete state.films.terminalJobs[jobId];
            pollFilmTakeJob(projectId, takeId, jobId);
          }
        } catch (_error) {
          // Mantem a tela estavel; uma atualizacao manual tenta novamente.
        }
      }, 10000);
    }
  }
  const selected = $("#gen-model").selectedOptions?.[0]?.textContent || "Motor indisponível";
  $("#gen-engine-pill").textContent = selected;
}

function resumeFilmTakeJobs() {
  const projectId = state.films.activeProjectId;
  state.films.takes.forEach((take) => {
    if (["QUEUED", "GENERATING", "UPSCALING"].includes(take.status) && take.lastJobId) {
      pollFilmTakeJob(projectId, take.takeId, take.lastJobId);
    }
  });
}

async function saveFilmTakePrompt(button) {
  const projectId = state.films.activeProjectId;
  const takeId = button.dataset.filmPromptSave;
  const input = document.querySelector(`[data-film-prompt-input="${CSS.escape(takeId)}"]`);
  const animationPrompt = String(input?.value || "").trim();
  if (!projectId || !takeId || !input) return;
  if (animationPrompt.length < 20) return toast("O prompt precisa ter pelo menos 20 caracteres.");
  try {
    setBusy(button, true, "Salvando");
    input.disabled = true;
    const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ animationPrompt }),
    });
    syncFilmTakeAfterUpdate(updated);
    toast(`Take ${takeId}: prompt salvo no projeto`);
  } catch (error) {
    toast(error.message);
  } finally {
    if (document.body.contains(button)) setBusy(button, false);
    if (document.body.contains(input)) input.disabled = false;
  }
}

async function selectFilmTakeEngine(select) {
  const projectId = state.films.activeProjectId;
  const takeId = select.dataset.filmEngineSelect;
  const generationProfile = String(select.value || "").trim();
  if (!projectId || !takeId || !generationProfile) return;
  select.disabled = true;
  try {
    const updated = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ generationProfile }),
    });
    syncFilmTakeAfterUpdate(updated);
    toast(`Take ${takeId}: motor definido como ${updated.engine}`);
  } catch (error) {
    toast(error.message);
    await refreshFilmProjectData(projectId);
  } finally {
    if (document.body.contains(select)) select.disabled = false;
  }
}

async function generateFilmTake(button) {
  const projectId = state.films.activeProjectId;
  const takeId = button.dataset.filmTakeGenerate;
  if (!projectId || !takeId) return;
  try {
    setBusy(button, true, "Enfileirando");
    const started = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ seed: -1 }),
    });
    await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
    pollFilmTakeJob(projectId, takeId, started.jobId);
  } catch (error) {
    toast(error.message);
    setBusy(button, false);
  }
}

async function upscaleFilmTake(button) {
  const projectId = state.films.activeProjectId;
  const takeId = button.dataset.filmTakeUpscale;
  if (!projectId || !takeId || button.disabled) return;
  if (!window.confirm(`Enviar o take ${takeId} para upscaling obrigatório? O vídeo aprovado atual será preservado até você revisar o remaster.`)) return;
  try {
    setBusy(button, true, "Enfileirando");
    const started = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/takes/${encodeURIComponent(takeId)}/upscale-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
    pollFilmTakeJob(projectId, takeId, started.jobId);
  } catch (error) {
    toast(error.message);
    setBusy(button, false);
  }
}

async function startFilmBatch(action, button) {
  const projectId = state.films.activeProjectId;
  if (!projectId || !button || button.disabled || state.films.batchInFlight[action]) return;
  if (filmActiveProjectQueueItems().length) {
    syncFilmBatchActions();
    return;
  }
  const productionPlan = filmProductionBatchPlan();
  if (action === "production" && productionPlan.ready !== true) {
    syncFilmBatchActions();
    return;
  }
  const eligible = action === "production"
    ? productionPlan.selected
    : state.films.takes.filter((take) => take.canUpscale);
  if (!eligible.length) return;
  const label = action === "production" ? "produção dos vídeos" : "melhoria para 1080p";
  const takeLabel = action === "production" ? ` (${eligible.map((take) => take.takeId).join(", ")})` : "";
  const confirmation = action === "production"
    ? productionPlan.incompleteCorrectionBatch
      ? `Gerar a correção${takeLabel} agora? A fila normal de três permanece igual para takes novos.`
      : `Reservar a trinca${takeLabel}? Os três jobs entram agora; a 5090 renderiza um por vez e você pode validar depois.`
    : `Enviar ${eligible.length} take(s) para ${label}? A fila evita duplicar itens ocupados ou concluídos.`;
  if (!window.confirm(confirmation)) return;

  state.films.batchInFlight[action] = true;
  try {
    setBusy(button, true, "Enfileirando");
    const result = await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}/batch-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    await Promise.all([refreshFilmProjectData(projectId), loadFilmProductionQueue()]);
    (result.started || []).forEach((item) => pollFilmTakeJob(projectId, item.takeId, item.jobId));
    const failures = Number(result.errors?.length || 0);
    const failureSummary = failures
      ? [...new Set((result.errors || []).map((item) => `${item.takeId || "take"}: ${item.message || "erro desconhecido"}`))]
        .slice(0, 2)
        .join(" | ")
      : "";
    const successLabel = action === "production"
      ? result.incompleteCorrectionBatch
        ? `Correção iniciada: ${Number(result.startedCount || 0)} take(s)`
        : `Trinca reservada: ${Number(result.startedCount || 0)} takes`
      : `${Number(result.startedCount || 0)} take(s) enviados para ${label}`;
    toast(
      successLabel
      + (failures ? ` · ${failures} não entraram` : "")
      + (failureSummary ? ` — ${failureSummary}` : ""),
    );
  } catch (error) {
    toast(error.message);
  } finally {
    state.films.batchInFlight[action] = false;
    setBusy(button, false);
    syncFilmBatchActions();
  }
}

function bindEvents() {
  $$(".nav-link[data-section]").forEach((button) => button.addEventListener("click", () => {
    switchSection(button.dataset.section, { focusHeading: true });
    if (button.dataset.section === "films") setFilmWorkflowView("review");
  }));
  $("#mobile-production-link")?.addEventListener("click", () => {
    switchSection("films", { focusHeading: true });
    setFilmWorkflowView("production");
  });
  $$("[data-section-jump]").forEach((button) => button.addEventListener("click", () => {
    switchSection(button.dataset.sectionJump, { focusHeading: true });
  }));
  $$("[data-tool]").forEach((button) => button.addEventListener("click", () => openTool(button.dataset.tool, button.dataset.port)));
  $$("[data-asset-kind]").forEach((button) => button.addEventListener("click", () => selectAssetKind(button)));
  $$("[data-pick-target]").forEach((button) => button.addEventListener("click", () => pickFolder(button.dataset.pickTarget)));

  $("#refresh-btn").addEventListener("click", refreshAll);
  $("#hyperframes-embed")?.addEventListener("click", embedHyperFrames);
  $("#hyperframes-open")?.addEventListener("click", () => openTool("hyperframes", 8032));
  $("#hyperframes-refresh")?.addEventListener("click", () => loadHyperFramesStatus({ autoStart: true }));
  $("#hyperframes-close")?.addEventListener("click", closeHyperFrames);
  $("#hyperframes-render")?.addEventListener("click", startHyperFramesRender);
  $("#hyperframes-download")?.addEventListener("click", downloadHyperFramesPilot);
  $("#qwen-release-button")?.addEventListener("click", releaseQwenForComfyUi);
  $("#qwen-auto-release-enabled")?.addEventListener("change", saveQwenAutoRelease);
  $("#qwen-auto-release-delay")?.addEventListener("change", saveQwenAutoRelease);
  $("#assets-refresh")?.addEventListener("click", loadAssets);
  $("#assets-prev")?.addEventListener("click", () => changeAssetPage(-1));
  $("#assets-next")?.addEventListener("click", () => changeAssetPage(1));
  $("#gen-mode").addEventListener("change", () => syncGenMode({ resetVideoEngine: true }));
  $("#gen-provider")?.addEventListener("change", () => {
    $("#gen-music-abc-reviewed").checked = false;
    syncGenAudioProviderDetails({ resetDuration: true });
  });
  $("#gen-music-action")?.addEventListener("change", () => syncGenAudioProviderDetails());
  $("#gen-music-duration-auto")?.addEventListener("change", () => {
    $("#gen-music-abc-reviewed").checked = false;
    syncGenAudioProviderDetails();
  });
  $("#gen-music-instrumental")?.addEventListener("change", () => {
    $("#gen-music-lyrics").disabled = $("#gen-music-instrumental").checked;
    $("#gen-music-abc-reviewed").checked = false;
  });
  ["#gen-prompt", "#gen-duration", "#gen-music-lyrics", "#gen-music-abc"].forEach((id) => {
    $(id)?.addEventListener("input", () => { $("#gen-music-abc-reviewed").checked = false; });
  });
  $$('[data-gen-mode]').forEach((button) => button.addEventListener("click", () => {
    $("#gen-mode").value = button.dataset.genMode;
    syncGenMode({ resetVideoEngine: true });
  }));
  $("#gen-video-engines")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-video-engine-id]");
    if (button) selectVideoEngine(button.dataset.videoEngineId);
  });
  $("#gen-model").addEventListener("change", () => {
    applyGenModelPreset();
    scheduleMovaProducerAnalysis();
  });
  $("#gen-h3-quality-profile")?.addEventListener("change", applyH3QualityProfile);

  $("#gen-h3-model-variant")?.addEventListener("change", applyH3QualityProfile);

  $("#gen-h3-orientation")?.addEventListener("change", applyH3QualityProfile);
  $("#gen-preset").addEventListener("change", applyGenPreset);
  $("#gen-fps").addEventListener("change", () => {
    syncGenVideoTiming();
  });
  $("#gen-video-duration").addEventListener("change", () => {
    syncGenVideoTiming();
  });
  $$('[data-gen-duration]').forEach((button) => button.addEventListener("click", () => {
    $("#gen-video-duration").value = button.dataset.genDuration;
    syncGenVideoTiming();
  }));
  $("#gen-prompt").addEventListener("input", () => {
    scheduleMovaProducerAnalysis();
  });
  $("#gen-mova-producer-apply")?.addEventListener("click", applyMovaProducerPlan);
  $("#gen-base-image").addEventListener("change", () => {
    updateImagePreview($("#gen-base-image"), $("#gen-base-preview"), $("#gen-base-preview-wrap"));
  });
  $("#gen-end-image").addEventListener("change", () => updateImagePreview(
    $("#gen-end-image"), $("#gen-end-preview"), $("#gen-end-preview-wrap"),
  ));
  $("#gen-camera-speed").addEventListener("input", () => {
    $("#gen-camera-speed-value").textContent = Number($("#gen-camera-speed").value).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  });
  $("#gen-form").addEventListener("submit", runGen);
  $("#gen-history-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-gen-job-action]");
    if (button) handleGenJobAction(button);
  });
  $("#film-refresh").addEventListener("click", loadFilmProjects);
  $("#film-final-watch")?.addEventListener("click", () => openFilmFinalPreview());
  $("#film-final-video")?.addEventListener("loadeddata", (event) => {
    $("#film-final-player-status").textContent = "Master carregado. Pressione play para revisar.";
    if (!event.currentTarget.paused) markFilmFinalPlaybackVisible(event.currentTarget);
  });
  $("#film-final-video")?.addEventListener("playing", (event) => {
    $("#film-final-player-status").textContent = "Master em reprodução no Maestro.";
    markFilmFinalPlaybackVisible(event.currentTarget);
  });
  $("#film-final-video")?.addEventListener("timeupdate", (event) => {
    if (event.currentTarget.currentTime > 0) markFilmFinalPlaybackVisible(event.currentTarget);
  });
  $("#film-final-video")?.addEventListener("error", (event) => {
    if (!event.currentTarget.dataset.previewUrl) return;
    $("#film-final-player-status").textContent = "O player não conseguiu abrir o proxy. Use Baixar master FHD e tente atualizar a página.";
  });
  $("#film-preview-video")?.addEventListener("loadstart", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Carregando vídeo e preparando o buffer… {percent}%");
  });
  $("#film-preview-video")?.addEventListener("progress", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Buffer disponível: {percent}%");
  });
  $("#film-preview-video")?.addEventListener("loadedmetadata", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Metadados carregados. Preparando reprodução… {percent}%");
  });
  $("#film-preview-video")?.addEventListener("canplay", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Pronto para reproduzir · buffer {percent}%");
  });
  $("#film-preview-video")?.addEventListener("waiting", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Bufferizando… {percent}% disponível");
  });
  $("#film-preview-video")?.addEventListener("stalled", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Conexão lenta; mantendo o trecho já carregado ({percent}%).");
  });
  $("#film-preview-video")?.addEventListener("playing", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Reproduzindo · buffer {percent}%");
  });
  $("#film-preview-video")?.addEventListener("ended", (event) => {
    syncFilmPreviewBuffer(event.currentTarget, "Reprodução concluída · buffer {percent}%");
  });
  $("#film-preview-video")?.addEventListener("error", (event) => {
    if (!event.currentTarget.dataset.previewUrl) return;
    syncFilmPreviewBuffer(event.currentTarget, "Falha ao carregar o vídeo. Tente novamente ou use Abrir vídeo.");
  });
  $("#film-assembly-start")?.addEventListener("click", (event) => startFilmAssembly(event.currentTarget));
  $("#film-final-approve")?.addEventListener("click", (event) => reviewFilmFinalOutput("approve", event.currentTarget));
  $("#film-final-reject")?.addEventListener("click", (event) => reviewFilmFinalOutput("reject", event.currentTarget));
  $$("[data-film-view]").forEach((button) => button.addEventListener("click", () => setFilmWorkflowView(button.dataset.filmView)));
  $("#film-batch-production").addEventListener("click", (event) => startFilmBatch("production", event.currentTarget));
  $("#film-batch-upscale").addEventListener("click", (event) => startFilmBatch("upscale", event.currentTarget));
  $("#film-upscale-resolution")?.addEventListener("change", async (event) => {
    const projectId = state.films.activeProjectId;
    if (!projectId) return;
    event.target.disabled = true;
    try {
      await fetchJson(`${API.studio}/api/video-projects/${encodeURIComponent(projectId)}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ finalResolution: event.target.value }),
      });
      await refreshFilmProjectData(projectId);
      toast("Resolução salva; os próximos upscales usarão esse tamanho a 60 FPS");
    } catch (error) {
      toast(`Resolução não alterada · ${error.message}`);
      syncFilmBatchActions();
    } finally {
      syncFilmBatchActions();
    }
  });
  $("#film-batch-anchors").addEventListener("click", (event) => handleFilmAnchorBatchAction(event.currentTarget));
  $("#film-create-form").addEventListener("submit", createFilmProject);
  $("#film-project-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-film-project]");
    if (button) loadFilmProject(button.dataset.filmProject);
  });
  $("#film-takes-list").addEventListener("change", (event) => {
    if (event.target.matches("[data-film-take-status]")) updateFilmTakeStatus(event.target);
    if (event.target.matches("[data-film-engine-select]")) selectFilmTakeEngine(event.target);
    if (event.target.matches("[data-film-video-sound-provider]")) {
      state.films.videoSoundProviderId = event.target.value;
    }
  });
  $("#film-takes-list").addEventListener("click", (event) => {
    const preanalysisButton = event.target.closest("[data-film-preanalysis-open]");
    if (preanalysisButton) {
      openFilmPreanalysisDialog(preanalysisButton.dataset.filmPreanalysisOpen);
      return;
    }
    const openButton = event.target.closest("[data-film-take-open]");
    if (openButton) {
      openFilmTakePreview(openButton.dataset.filmTakeOpen);
      return;
    }
    const directorButton = event.target.closest("[data-film-take-director]");
    if (directorButton) {
      openFilmDirectorDialog(directorButton.dataset.filmTakeDirector);
      return;
    }
    const anchorButton = event.target.closest("[data-film-take-anchor]");
    if (anchorButton) {
      openFilmDirectorDialog(anchorButton.dataset.filmTakeAnchor, "anchor");
      return;
    }
    const anchorStartButton = event.target.closest("[data-film-anchor-start]");
    if (anchorStartButton) {
      startFilmAnchorExecutor([anchorStartButton.dataset.filmAnchorStart], anchorStartButton).catch(() => {});
      return;
    }
    const anchorApproveButton = event.target.closest("[data-film-anchor-approve]");
    if (anchorApproveButton) {
      reviewFilmAnchor(anchorApproveButton.dataset.filmAnchorApprove, "APPROVED", anchorApproveButton);
      return;
    }
    const anchorRejectButton = event.target.closest("[data-film-anchor-reject]");
    if (anchorRejectButton) {
      openFilmDirectorDialog(anchorRejectButton.dataset.filmAnchorReject, "anchor_review");
      return;
    }
    const promptSaveButton = event.target.closest("[data-film-prompt-save]");
    if (promptSaveButton) {
      saveFilmTakePrompt(promptSaveButton);
      return;
    }
    const videoSoundButton = event.target.closest("[data-film-video-sound-start]");
    if (videoSoundButton) {
      startFilmVideoSound(videoSoundButton);
      return;
    }
    const audioReviewButton = event.target.closest("[data-film-audio-review]");
    if (audioReviewButton) {
      reviewFilmAudioCandidate(audioReviewButton);
      return;
    }
    const upscaleButton = event.target.closest("[data-film-take-upscale]");
    if (upscaleButton) {
      upscaleFilmTake(upscaleButton);
      return;
    }
    const generateButton = event.target.closest("[data-film-take-generate]");
    if (generateButton) generateFilmTake(generateButton);
  });
  $("#film-player-review").addEventListener("click", (event) => {
    const button = event.target.closest("[data-film-player-decision]");
    if (!button || button.disabled || !state.films.activeTakeId) return;
    const activeTake = state.films.takes.find((take) => take.takeId === state.films.activeTakeId);
    if (filmTakeAnchorReviewPending(activeTake)) {
      if (button.dataset.filmPlayerDecision === "APPROVED") reviewFilmAnchor(activeTake.takeId, "APPROVED", button);
      else openFilmDirectorDialog(activeTake.takeId, "anchor_review");
      return;
    }
    applyFilmTakeDecision(state.films.activeTakeId, button.dataset.filmPlayerDecision, button);
  });
  $("#film-director-form").addEventListener("submit", submitFilmDirectorRequest);
  $("#film-director-cancel").addEventListener("click", closeFilmDirectorDialog);
  $("#film-director-close").addEventListener("click", closeFilmDirectorDialog);
  $("#film-preanalysis-close")?.addEventListener("click", closeFilmPreanalysisDialog);
  $("#film-preanalysis-dialog")?.addEventListener("close", () => {
    $("#film-preanalysis-image")?.removeAttribute("src");
  });
  $("#film-director-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeFilmDirectorDialog();
  });
  $("#video-form").addEventListener("submit", runVideo);
  $("#audio-form").addEventListener("submit", runAudio);
  $("#audio-action").addEventListener("change", syncAudioAction);
  $("#image-form").addEventListener("submit", runImage);
  $("#studio-log-refresh").addEventListener("click", loadStudioLog);
  $("#org-form").addEventListener("submit", runOrg);
  $("#doc-form").addEventListener("submit", runDoc);
  $("#cad-form").addEventListener("submit", addCad);
  $("#cad-refresh").addEventListener("click", loadCad);
  $("#hist-refresh").addEventListener("click", loadHist);
  $("#org-hist-refresh").addEventListener("click", loadHist);

  $("#cad-body").addEventListener("change", async (event) => {
    if (event.target.matches("[data-cad-id]")) {
      await saveCad(event.target.dataset.cadId, event.target.value);
      toast("Campo salvo");
    }
  });

  $("#cad-body").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-del-cad]");
    if (!button) return;
    if (!confirm("Apagar campo?")) return;
    await fetchJson(`${API.cadastro}/campos/${button.dataset.delCad}`, { method: "DELETE" });
    loadCad();
  });
}

function refreshAll() {
  loadTelemetry();
  loadQwenStatus();
  loadHealth();
  if ($("#section-gen")?.classList.contains("active")) loadGenJobs();
  if ($("#section-hyperframes")?.classList.contains("active")) {
    void loadHyperFramesStatus({ autoStart: true });
  }
  loadGenStatus();
  if ($("#section-films")?.classList.contains("active")) loadFilmProjects();
}

function tickClock() {
  $("#clock").textContent = new Date().toLocaleString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

async function reloadIfFrontendIsOutdated() {
  try {
    const response = await fetch(`${MAESTRO_BUILD_MANIFEST}?t=${Date.now()}`, {
      cache: "no-store",
      credentials: "same-origin",
    });
    if (!response.ok) return;
    const manifest = await response.json();
    const publishedBuild = String(manifest?.build || "").trim();
    if (!publishedBuild || publishedBuild === MAESTRO_FRONTEND_BUILD) return;

    const reloadMarker = `maestro-build-reload:${publishedBuild}`;
    if (window.sessionStorage.getItem(reloadMarker) === "1") return;
    window.sessionStorage.setItem(reloadMarker, "1");
    window.location.reload();
  } catch (_error) {
    // Uma falha transitória de rede não deve interromper o uso do Maestro.
  }
}

function init() {
  window.MaestroEditorSuite?.init({
    apiBase: `${API.studio}/api/editor`,
    notify: toast,
  });
  bindEvents();
  enhanceVoiceInputs(document);
  try {
    const savedFilmView = window.localStorage.getItem("maestro-film-view");
    if (FILM_WORKFLOW_VIEWS.has(savedFilmView)) state.films.view = savedFilmView;
  } catch (_error) {
    // O app continua funcionando mesmo se o WebView bloquear armazenamento local.
  }
  syncAudioAction();
  appendMessage("assistant", "Escolha criar uma imagem, editar uma foto, animar uma imagem ou criar um vídeo diretamente de texto. O resultado aparecerá aqui.");
  tickClock();
  refreshAll();
  void reloadIfFrontendIsOutdated();
  loadOrgModels();
  setInterval(tickClock, 1000);
  setInterval(loadTelemetry, 2500);
  setInterval(loadQwenStatus, 3000);
  setInterval(loadHealth, 15000);
  setInterval(reloadIfFrontendIsOutdated, 30000);
  setInterval(() => {
    if ($("#section-gen")?.classList.contains("active")) loadGenJobs();
  }, 5000);
  setInterval(() => {
    if ($("#section-films")?.classList.contains("active")) refreshFilmLiveData();
  }, 5000);
}

document.addEventListener("DOMContentLoaded", init);
window.addEventListener("beforeunload", () => releaseVoiceStream(voiceInputState.active));
