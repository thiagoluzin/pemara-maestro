(() => {
  'use strict';
  const $ = (id) => document.getElementById(id), section = $('section-voices');
  if (!section) return;
  const base = '/api/studio/api/voice-studio';
  const state = { voices: [], jobs: [], active: '', ready: false, busy: false, submitting: false, page: 1, total: 0, timer: null, loaded: false, uploadUrl: '', detailKey: '' };
  const activeStatuses = ['QUEUED', 'SUBMITTING', 'RUNNING', 'CANCELLING', 'SUBMISSION_UNCERTAIN'];
  const statuses = { QUEUED: 'Na fila', SUBMITTING: 'Enviando ao motor', RUNNING: 'Gerando narração', CANCELLING: 'Cancelando', COMPLETED: 'Pronta para ouvir', FAILED: 'Não concluída', CANCELLED: 'Cancelada', INTERRUPTED: 'Interrompida', SUBMISSION_UNCERTAIN: 'Envio a conferir', INTEGRITY_ERROR: 'Integridade alterada' };
  const phases = { verifying: 'Verificando o modelo', loading: 'Carregando Drama 3', encoding_reference: 'Preparando a referência vocal', prefill: 'Preparando a leitura', generating: 'Narrando seu roteiro', decoding: 'Convertendo a fala em áudio', exporting: 'Preparando o arquivo', complete: 'Finalizando' };
  const fields = { title: 'voice-title', text: 'voice-text', voiceId: 'voice-select', mode: 'voice-mode', maxFrames: 'voice-budget', temperature: 'voice-temperature', topP: 'voice-top-p', topK: 'voice-top-k', seed: 'voice-seed', chunkLength: 'voice-chunk-length' };
  function node(tag, text, className) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (className) n.className = className; return n; }
  function button(text, handler, style = 'btn secondary') { const n = node('button', text, style); n.type = 'button'; n.addEventListener('click', handler); return n; }
  function message(text, error = false) { $('voice-message').textContent = text; $('voice-message').dataset.error = String(error); }
  async function api(path, options = {}) {
    const response = await fetch(base + path, { credentials: 'same-origin', cache: 'no-store', ...options,
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    let result; try { result = await response.json(); } catch { throw new Error('O estúdio não respondeu. Confira a conexão com o Maestro.'); }
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Não foi possível concluir. Confira os campos.');
    return result;
  }
  function tab(name, focus = false) {
    for (const item of section.querySelectorAll('[data-voice-tab]')) {
      const selected = item.dataset.voiceTab === name;
      item.setAttribute('aria-selected', String(selected)); item.tabIndex = selected ? 0 : -1;
      $('voice-pane-' + item.dataset.voiceTab).hidden = !selected;
      if (selected && focus) item.focus();
    }
  }
  section.querySelectorAll('[data-voice-tab]').forEach((item, index, list) => {
    item.addEventListener('click', () => tab(item.dataset.voiceTab));
    item.addEventListener('keydown', (event) => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % list.length;
      if (event.key === 'ArrowLeft') target = (index + list.length - 1) % list.length;
      if (event.key === 'Home') target = 0;
      if (event.key === 'End') target = list.length - 1;
      if (target !== undefined) { event.preventDefault(); tab(list[target].dataset.voiceTab, true); }
    });
  });
  function settings() {
    const values = {};
    for (const [key, id] of Object.entries(fields)) values[key] = ['title', 'text', 'voiceId', 'mode'].includes(key) ? $(id).value : Number($(id).value);
    values.voiceId ||= null; return values;
  }
  function controls() {
    const chunked = $('voice-mode').value === 'chunked';
    $('voice-chunk-label').hidden = !chunked;
    section.querySelectorAll('[data-long-only]').forEach((option) => { option.hidden = option.disabled = !chunked; });
    if (!chunked && Number($('voice-budget').value) > 8192) $('voice-budget').value = '8192';
    $('voice-temperature-value').textContent = Number($('voice-temperature').value).toLocaleString('pt-BR');
    const text = $('voice-text').value;
    $('voice-text-count').textContent = `${text.length.toLocaleString('pt-BR')} / 20.000 caracteres`;
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    $('voice-duration-estimate').textContent = words ? `Leitura estimada: ${Math.max(1, Math.round(words / 160 * 60))} s · pode variar` : 'A duração depende da leitura.';
    $('voice-generate').disabled = !state.ready || state.busy || state.submitting;
    $('voice-generate').firstChild.textContent = state.submitting ? 'Enviando… ' : state.busy ? 'Narração em andamento ' : 'Gerar narração ';
  }
  function saveDraft() {
    controls();
    try { localStorage.setItem('maestro-voice-draft-v1', JSON.stringify(settings())); $('voice-draft-status').textContent = 'Rascunho salvo neste navegador'; }
    catch { $('voice-draft-status').textContent = 'O navegador não permitiu salvar o rascunho'; }
  }
  function fill(values) {
    for (const [key, id] of Object.entries(fields)) if (key in values && key !== 'voiceId') $(id).value = values[key];
    if ('voiceId' in values) $('voice-select').value = state.voices.some((v) => v.id === values.voiceId) ? values.voiceId : '';
    selectedVoice(); controls();
  }
  let draft;
  try { draft = JSON.parse(localStorage.getItem('maestro-voice-draft-v1')); if (draft) fill(draft); } catch { /* Storage is optional. */ }
  $('voice-narration-form').addEventListener('input', saveDraft);
  $('voice-mode').addEventListener('change', saveDraft);
  function selectedVoice() {
    const voice = state.voices.find((v) => v.id === $('voice-select').value), player = $('voice-reference-player');
    $('voice-selected-description').textContent = voice ? (voice.description || 'A referência salva orientará esta narração.') : 'Sem referência: a identidade vocal pode variar entre gerações.';
    player.pause(); player.hidden = !voice;
    if (voice) player.src = voice.previewUrl; else player.removeAttribute('src');
  }
  $('voice-select').addEventListener('change', () => { selectedVoice(); saveDraft(); });
  function renderVoices() {
    const query = $('voice-search').value.toLocaleLowerCase('pt-BR'), list = $('voice-library-list'); list.replaceChildren();
    const voices = state.voices.filter((v) => `${v.name} ${v.description}`.toLocaleLowerCase('pt-BR').includes(query));
    if (!voices.length) list.append(node('p', query ? 'Nenhuma voz encontrada.' : 'Sua biblioteca está vazia. Adicione um áudio de referência para começar.', 'voice-empty'));
    for (const voice of voices) {
      const card = node('article', undefined, 'voice-library-card');
      card.append(node('span', voice.name.charAt(0).toLocaleUpperCase(), 'voice-avatar'), node('h4', voice.name), node('p', voice.description || 'Voz por referência', 'voice-help'));
      const player = node('audio'); player.controls = true; player.preload = 'none'; player.src = voice.previewUrl; player.setAttribute('aria-label', 'Ouvir referência de ' + voice.name);
      card.append(player, node('p', `${voice.duration.toFixed(1)} s de referência · transcrição salva`, 'voice-help'), button('Usar esta voz', () => { $('voice-select').value = voice.id; selectedVoice(); saveDraft(); tab('narration'); $('voice-text').focus(); }));
      list.append(card);
    }
    $('voice-library-count').textContent = String(state.voices.length);
  }
  async function loadVoices() {
    const previous = $('voice-select').value || draft?.voiceId;
    state.voices = (await api('/voices')).voices;
    $('voice-select').replaceChildren(new Option('Voz livre do modelo', ''));
    for (const voice of state.voices) $('voice-select').append(new Option(voice.name, voice.id));
    $('voice-select').value = state.voices.some((v) => v.id === previous) ? previous : '';
    selectedVoice(); renderVoices();
  }
  $('voice-search').addEventListener('input', renderVoices);
  function renderHistory() {
    const list = $('voice-history-list'); list.replaceChildren();
    if (!state.jobs.length) list.append(node('p', 'Nenhuma narração criada ainda.', 'voice-empty'));
    for (const job of state.jobs) {
      const row = button('', () => void select(job.id, true), 'voice-history-row'), info = node('span');
      info.append(node('strong', job.title), node('small', `${job.voiceName} · ${new Date(job.createdAt * 1000).toLocaleString('pt-BR')}`));
      row.append(info, node('span', statuses[job.status] || job.status)); list.append(row);
    }
    $('voice-history-more').hidden = state.jobs.length >= state.total;
    state.busy = state.jobs.some((job) => activeStatuses.includes(job.status)); controls();
  }
  async function loadJobs(reset = true) {
    const page = reset ? 1 : state.page + 1;
    const result = await api(`/jobs?page=${page}&pageSize=20`);
    state.page = page; state.total = result.total;
    state.jobs = reset ? result.jobs : [...state.jobs, ...result.jobs]; renderHistory();
  }
  function download(text, href) { const link = node('a', text, 'btn secondary'); link.href = href; link.setAttribute('download', ''); return link; }
  function renderJob(job) {
    $('voice-current').hidden = false; $('voice-current-title').textContent = job.title;
    $('voice-current-status').textContent = statuses[job.status] || job.status;
    const key = JSON.stringify([job.id, job.status, job.review, job.result, job.error]);
    if (key !== state.detailKey) {
      state.detailKey = key;
      const body = $('voice-current-body'); body.replaceChildren();
      if (activeStatuses.includes(job.status)) {
        body.append(node('div', '', 'voice-progress'));
        const actions = node('div', undefined, 'voice-result-actions');
        actions.append(button('Cancelar esta narração', async (event) => {
          const target = event.currentTarget; target.disabled = true;
          try { renderJob(await api(`/jobs/${job.id}/cancel`, { method: 'POST' })); await loadJobs(); }
          catch (error) { message(error.message, true); target.disabled = false; }
        })); body.append(actions);
      } else if (job.status === 'COMPLETED') {
        const audio = node('audio'); audio.controls = true; audio.preload = 'metadata'; audio.src = job.audioUrl; audio.setAttribute('aria-label', 'Ouvir narração ' + job.title); body.append(audio);
        body.append(node('p', `${job.result.duration.toFixed(1)} segundos · ${job.result.sampleRate.toLocaleString('pt-BR')} Hz · ${job.voiceName}`, 'voice-help'));
        const actions = node('div', undefined, 'voice-result-actions'); actions.append(download('Baixar WAV', job.audioUrl + '?download=1'));
        if (job.mp3Url) actions.append(download('Baixar MP3', job.mp3Url + '?download=1'));
        actions.append(download('Salvar receita', base + `/jobs/${job.id}/recipe`)); body.append(actions);
        body.append(node('p', `Avaliação: ${{ pending: 'aguardando sua escuta', approved: 'aprovada por você', rejected: 'reprovada por você' }[job.review.decision]}.`, 'voice-help'));
        const review = node('div', undefined, 'voice-result-actions');
        for (const [value, label] of [['approved', 'Aprovar esta versão'], ['rejected', 'Reprovar esta versão']]) {
          review.append(button(label, async (event) => {
            const target = event.currentTarget; target.disabled = true;
            try { renderJob(await api(`/jobs/${job.id}/review`, { method: 'POST', body: JSON.stringify({ decision: value, note: '' }) })); message('Avaliação salva para esta versão. O áudio foi preservado.'); }
            catch (error) { target.disabled = false; message(error.message, true); }
          }));
        }
        body.append(review, node('p', 'Confira palavras, final da leitura, sotaque e identidade da voz. O término normal do motor não substitui sua escuta.', 'voice-help'));
      }
      if (job.error) body.append(node('p', job.error, 'voice-notice'));
      const recipeActions = node('div', undefined, 'voice-result-actions');
      recipeActions.append(button('Editar como nova versão', () => { fill(job.settings); saveDraft(); tab('narration'); $('voice-text').focus(); message('Roteiro e parâmetros carregados. Gere quando estiver pronto para criar outra versão.'); })); body.append(recipeActions);
      const details = node('details'), summary = node('summary', 'Ver roteiro desta versão'); details.append(summary, node('pre', job.text)); body.append(details);
    }
    const progress = $('voice-current-body').querySelector('.voice-progress');
    if (progress) {
      const p = job.progress, frames = p?.progress?.frames;
      progress.textContent = job.status === 'SUBMISSION_UNCERTAIN' ? 'O envio não foi confirmado. Confira esta tentativa antes de repetir; não há reenvio automático.' : job.status === 'CANCELLING' ? 'Aguardando o encerramento desta tentativa. Outros trabalhos não são interrompidos.' : `${phases[p?.phase] || statuses[job.status] || 'Aguardando o motor'}${Number.isFinite(frames) ? ` · ${frames} quadros de áudio gerados` : ''}. Você pode continuar usando o Maestro.`;
    }
  }
  async function select(jobId, focus = false) {
    state.active = jobId;
    try { const job = await api('/jobs/' + jobId); if (state.active !== jobId) return; renderJob(job); if (focus) { tab('narration'); $('voice-current').scrollIntoView({ behavior: 'smooth', block: 'start' }); } }
    catch (error) { message(error.message, true); }
  }
  async function refresh() {
    if (!section.classList.contains('active')) return;
    try { await loadJobs(); if (state.active) await select(state.active); }
    catch (error) { message(error.message, true); }
    clearTimeout(state.timer); state.timer = setTimeout(refresh, state.busy ? 2500 : 12000);
  }
  $('voice-narration-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (state.submitting || state.busy || !state.ready || !event.currentTarget.reportValidity()) return;
    state.submitting = true; controls(); message('Preparando sua narração…');
    const payload = settings(), signature = JSON.stringify(payload);
    let pending;
    try { pending = JSON.parse(sessionStorage.getItem('maestro-voice-pending-v1')); } catch { /* optional storage */ }
    if (pending?.signature !== signature) pending = { signature, id: crypto.randomUUID().replaceAll('-', '') };
    try { sessionStorage.setItem('maestro-voice-pending-v1', JSON.stringify(pending)); } catch { /* optional storage */ }
    try {
      const job = await api('/jobs', { method: 'POST', body: JSON.stringify({ ...payload, requestId: pending.id }) });
      try { sessionStorage.removeItem('maestro-voice-pending-v1'); } catch { /* optional storage */ }
      state.active = job.id; renderJob(job); await loadJobs(); message('Narração registrada. Acompanhe a geração abaixo.'); void refresh();
    } catch (error) { message(error.message, true); }
    finally { state.submitting = false; controls(); }
  });
  $('voice-new-draft').addEventListener('click', () => {
    // Keep the previous draft for recovery instead of silently discarding it.
    try { localStorage.setItem('maestro-voice-previous-draft-v1', JSON.stringify(settings())); } catch { /* optional storage */ }
    $('voice-title').value = 'Nova narração'; $('voice-text').value = ''; saveDraft(); $('voice-text').focus(); message('Novo roteiro. O histórico de áudios continua preservado.');
  });
  section.querySelectorAll('[data-voice-cue]').forEach((item) => item.addEventListener('click', () => {
    const text = $('voice-text'); text.setRangeText(item.dataset.voiceCue, text.selectionStart, text.selectionEnd, 'end'); text.focus(); saveDraft();
  }));
  function cloneDialog() { $('voice-clone-dialog').showModal(); $('voice-clone-name').focus(); }
  $('voice-add').addEventListener('click', cloneDialog); $('voice-add-shortcut').addEventListener('click', cloneDialog);
  $('voice-clone-close').addEventListener('click', () => $('voice-clone-dialog').close());
  $('voice-clone-audio').addEventListener('change', () => {
    if (state.uploadUrl) URL.revokeObjectURL(state.uploadUrl);
    const file = $('voice-clone-audio').files[0], player = $('voice-upload-player'); player.hidden = !file;
    if (file) { state.uploadUrl = URL.createObjectURL(file); player.src = state.uploadUrl; }
  });
  $('voice-clone-dialog').addEventListener('close', () => $('voice-upload-player').pause());
  $('voice-clone-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (!event.currentTarget.reportValidity()) return;
    const file = $('voice-clone-audio').files[0], output = $('voice-clone-message'); output.dataset.error = 'false';
    if (!file || file.size > 32 * 1024 * 1024) { output.textContent = 'Escolha uma referência de até 32 MB.'; output.dataset.error = 'true'; return; }
    $('voice-clone-save').disabled = true; output.textContent = 'Preparando e salvando a referência local…';
    const form = new FormData(); form.append('audio', file); form.append('metadata', JSON.stringify({ name: $('voice-clone-name').value, description: $('voice-clone-description').value, transcript: $('voice-clone-transcript').value, authorized: $('voice-clone-authorized').checked }));
    try {
      const voice = await api('/voices', { method: 'POST', body: form }); await loadVoices(); $('voice-select').value = voice.id; selectedVoice(); saveDraft();
      $('voice-clone-dialog').close(); $('voice-clone-form').reset(); $('voice-upload-player').hidden = true;
      if (state.uploadUrl) URL.revokeObjectURL(state.uploadUrl); state.uploadUrl = ''; output.textContent = '';
      message(`Voz “${voice.name}” salva e selecionada. Digite o texto para criar sua primeira narração com ela.`); tab('narration');
    } catch (error) { output.textContent = error.message; output.dataset.error = 'true'; }
    finally { $('voice-clone-save').disabled = false; }
  });
  $('voice-history-refresh').addEventListener('click', () => void refresh());
  $('voice-history-more').addEventListener('click', () => void loadJobs(false).catch((error) => message(error.message, true)));
  async function activate() {
    try {
      const result = await api('/status'); state.ready = result.ready;
      $('voice-engine-status').textContent = result.ready ? '● Drama 3 · local' : result.message;
      $('voice-engine-status').dataset.ready = String(result.ready); controls();
      if (!state.loaded) {
        await loadVoices(); await loadJobs(); state.loaded = true;
        const job = state.jobs.find((j) => activeStatuses.includes(j.status)) || state.jobs[0];
        if (job) await select(job.id);
      }
      void refresh();
    } catch (error) { message(error.message, true); }
  }
  new MutationObserver(() => {
    if (section.classList.contains('active')) void activate(); else clearTimeout(state.timer);
  }).observe(section, { attributes: true, attributeFilter: ['class'] });
  if (section.classList.contains('active')) void activate(); controls();
})();
