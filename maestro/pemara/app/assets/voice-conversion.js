(() => {
  'use strict';
  const $ = (id) => document.getElementById(id), pane = $('voice-pane-conversion');
  if (!pane) return;
  const base = '/api/studio/api/voice-conversion';
  const active = ['QUEUED', 'SUBMITTING', 'RUNNING', 'CANCELLING', 'SUBMISSION_UNCERTAIN'];
  const labels = { QUEUED: 'Na fila', SUBMITTING: 'Enviando', RUNNING: 'Convertendo', CANCELLING: 'Cancelando', COMPLETED: 'Pronto para ouvir e baixar', FAILED: 'Não concluída', CANCELLED: 'Cancelada', INTERRUPTED: 'Interrompida', INTEGRITY_ERROR: 'Integridade alterada', SUBMISSION_UNCERTAIN: 'Envio a conferir' };
  const phases = { verifying: 'Conferindo a fonte e os modelos', extracting: 'Extraindo o áudio do vídeo', separating: 'Separando voz, música e ambiente', converting: 'Trocando a voz', assembling: 'Mantendo os trechos na linha do tempo original', validating: 'Conferindo a duração do áudio', exporting: 'Preparando os arquivos' };
  const state = { media: null, ready: false, busy: false, sending: false, jobs: [], page: 1, total: 0, selected: '', timer: null, detailKey: '', output: null, synced: false };
  const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  function button(text, handler) { const n = node('button', text, 'btn secondary'); n.type = 'button'; n.addEventListener('click', handler); return n; }
  function message(text, error = false) { $('conversion-message').textContent = text; $('conversion-message').dataset.error = String(error); }
  async function api(path, options = {}) {
    const response = await fetch(base + path, { credentials: 'same-origin', cache: 'no-store', ...options,
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest', ...(typeof options.body === 'string' ? { 'Content-Type': 'application/json' } : {}), ...options.headers } });
    let value; try { value = await response.json(); } catch { throw new Error('O Maestro não respondeu. Confira a conexão.'); }
    if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Não foi possível concluir. Confira os campos.');
    return value;
  }
  function controls() { $('conversion-generate').disabled = !state.ready || !state.media || state.busy || state.sending; }
  async function showMedia(media) {
    state.media = media; state.synced = false;
    $('conversion-file').value = '';
    const video = $('conversion-source-video'), audio = $('conversion-upload-audio'); video.pause(); audio.pause();
    video.hidden = !media.hasVideo; audio.hidden = media.hasVideo;
    (media.hasVideo ? video : audio).src = `${base}/media/${media.id}/preview`;
    $('conversion-source-info').textContent = `${media.name} · ${media.duration.toFixed(2)} s · ${media.tracks.length} faixa(s) de áudio`;
    $('conversion-preview-note').hidden = false;
    $('conversion-track').replaceChildren();
    for (const track of media.tracks) $('conversion-track').append(new Option(`Faixa ${track.index} ${track.language || ''} ${track.title || ''}`.trim(), String(track.index)));
    controls();
  }
  $('conversion-upload-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (!event.currentTarget.reportValidity()) return;
    const file = $('conversion-file').files[0];
    if (!file || file.size > 1024 ** 3) { message('Selecione um vídeo ou áudio de até 1 GB.', true); return; }
    $('conversion-import').disabled = true; message('Importando e conferindo a gravação…');
    try {
      const media = await api('/media?filename=' + encodeURIComponent(file.name), { method: 'POST', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream' } });
      stopSync(); state.selected = ''; state.detailKey = ''; state.output = null; $('conversion-result').hidden = true;
      await showMedia(media);
      $('conversion-title').value = file.name.replace(/\.[^.]+$/, '').slice(0, 120) || 'Troca de voz';
      message('Arquivo importado. Escolha a voz e inicie a conversão.');
    } catch (error) { message(error.message, true); }
    finally { $('conversion-import').disabled = false; }
  });
  function renderHistory() {
    const list = $('conversion-history'); list.replaceChildren();
    if (!state.jobs.length) list.append(node('p', 'Nenhuma conversão ainda. Importe seu primeiro vídeo acima.', 'voice-help'));
    for (const job of state.jobs) {
      const row = button('', () => void select(job.id)); row.className = 'voice-history-row';
      const info = node('span'); info.append(node('strong', job.title), node('small', `${job.voiceName} · ${new Date(job.createdAt * 1000).toLocaleString('pt-BR')}`));
      row.append(info, node('span', labels[job.status] || job.status)); list.append(row);
    }
    $('conversion-more').hidden = state.jobs.length >= state.total;
    state.busy = state.jobs.some((job) => active.includes(job.status)); controls();
  }
  async function jobs(more = false) {
    const page = more ? state.page + 1 : 1, data = await api('/jobs?page=' + page);
    state.page = page; state.total = data.total; state.jobs = more ? [...state.jobs, ...data.jobs] : data.jobs; renderHistory();
  }
  function download(text, url) { const link = node('a', text, 'btn secondary'); link.href = url; link.setAttribute('download', ''); return link; }
  function stopSync() { state.synced = false; if (state.output) state.output.pause(); $('conversion-source-video').pause(); $('conversion-source-video').muted = false; }
  async function synchronizedPreview() {
    const video = $('conversion-source-video');
    if (!state.output || !state.media?.hasVideo) return;
    stopSync(); state.synced = true; video.muted = true; video.currentTime = 0; state.output.currentTime = 0;
    try { await Promise.all([video.play(), state.output.play()]); }
    catch { stopSync(); message('Use os controles de reprodução para liberar a prévia no navegador.', true); }
  }
  $('conversion-source-video').addEventListener('seeking', () => { if (state.synced && state.output && Math.abs(state.output.currentTime - $('conversion-source-video').currentTime) > .08) state.output.currentTime = $('conversion-source-video').currentTime; });
  $('conversion-source-video').addEventListener('timeupdate', () => { if (state.synced && state.output && Math.abs(state.output.currentTime - $('conversion-source-video').currentTime) > .15) state.output.currentTime = $('conversion-source-video').currentTime; });
  $('conversion-source-video').addEventListener('pause', () => { if (state.synced && state.output) state.output.pause(); });
  $('conversion-source-video').addEventListener('play', () => { if (state.synced && state.output) void state.output.play().catch(() => stopSync()); });
  function render(job) {
    $('conversion-result').hidden = false; $('conversion-result-title').textContent = job.title;
    $('conversion-result-status').textContent = labels[job.status] || job.status;
    const key = JSON.stringify([job.id, job.status, job.result, job.error]);
    if (key !== state.detailKey) {
      state.detailKey = key; stopSync(); const body = $('conversion-result-body'); body.replaceChildren(); state.output = null;
      if (active.includes(job.status)) {
        body.append(node('p', '', 'voice-progress'));
        body.append(button('Cancelar esta conversão', async (event) => {
          const target = event.currentTarget; target.disabled = true;
          try { render(await api(`/jobs/${job.id}/cancel`, { method: 'POST' })); await jobs(); }
          catch (error) { target.disabled = false; message(error.message, true); }
        }));
      } else if (job.status === 'COMPLETED') {
        body.append(node('h4', 'Nova voz · áudio sincronizado'));
        const output = node('audio'); output.controls = true; output.preload = 'metadata'; output.src = job.audioUrl; output.setAttribute('aria-label', 'Ouvir áudio com a voz trocada');
        output.addEventListener('seeking', () => { if (state.synced && Math.abs($('conversion-source-video').currentTime - output.currentTime) > .08) $('conversion-source-video').currentTime = output.currentTime; });
        output.addEventListener('pause', () => { if (state.synced) $('conversion-source-video').pause(); });
        output.addEventListener('play', () => { if (state.synced && $('conversion-source-video').paused) void $('conversion-source-video').play().catch(() => stopSync()); });
        state.output = output; body.append(output);
        body.append(node('p', `${job.result.duration.toFixed(3)} s · ${job.voiceName} · ${job.result.preservedBackground ? 'música e ambiente preservados na mixagem' : 'voz convertida'}`, 'voice-help'));
        const actions = node('div', undefined, 'voice-result-actions');
        actions.append(download('Baixar WAV sincronizado', job.audioUrl + '?download=1'));
        if (job.mp3Url) actions.append(download('Baixar MP3', job.mp3Url + '?download=1'));
        actions.append(download('Salvar recibo', `${base}/jobs/${job.id}/receipt`));
        if (state.media?.hasVideo) actions.append(button('Ver vídeo com a nova voz', () => void synchronizedPreview()));
        body.append(actions, node('h4', 'Comparar com o áudio original'));
        const original = node('audio'); original.controls = true; original.preload = 'none'; original.src = `${base}/jobs/${job.id}/source-audio`; original.setAttribute('aria-label', 'Ouvir áudio original para comparação'); body.append(original);
        original.addEventListener('play', stopSync);
        body.append(node('p', 'O WAV mantém a linha do tempo da fonte e está pronto para substituir a faixa no editor. Confira a voz, as pausas e a sincronização antes de usar.', 'voice-help'));
      }
      if (job.error) body.append(node('p', job.error, 'voice-notice'));
    }
    const progress = $('conversion-result-body').querySelector('.voice-progress');
    if (progress) {
      const phase = job.progress?.phase, details = job.progress?.progress;
      progress.textContent = (phases[phase] || labels[job.status] || 'Aguardando o motor') + (details?.segment_count ? ` · trecho ${details.segment_index} de ${details.segment_count}` : '') + '.';
    }
  }
  async function select(id) {
    state.selected = id;
    try {
      const job = await api('/jobs/' + id);
      if (state.selected !== id) return;
      if (state.media?.id !== job.mediaId) {
        const media = await api('/media/' + job.mediaId);
        if (state.selected !== id) return;
        await showMedia(media);
      }
      render(job);
    } catch (error) { message(error.message, true); }
  }
  async function refresh() {
    if (pane.hidden || !$('section-voices').classList.contains('active')) return;
    try { await jobs(); if (state.selected) await select(state.selected); }
    catch (error) { message(error.message, true); }
    clearTimeout(state.timer); state.timer = setTimeout(refresh, state.busy ? 2500 : 12000);
  }
  $('conversion-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (!event.currentTarget.reportValidity() || !state.media || state.sending || state.busy) return;
    state.sending = true; controls(); message('Enviando a conversão…');
    const body = { mediaId: state.media.id, voiceId: $('conversion-voice').value, title: $('conversion-title').value,
                   audioTrack: Number($('conversion-track').value), preserveBackground: $('conversion-background').checked, seed: 123 };
    const signature = JSON.stringify(body); let pending;
    try { pending = JSON.parse(sessionStorage.getItem('maestro-conversion-pending')); } catch { /* optional storage */ }
    if (pending?.signature !== signature) pending = { signature, id: crypto.randomUUID().replaceAll('-', '') };
    try { sessionStorage.setItem('maestro-conversion-pending', JSON.stringify(pending)); } catch { /* optional storage */ }
    try {
      const job = await api('/jobs', { method: 'POST', body: JSON.stringify({ ...body, requestId: pending.id }) });
      try { sessionStorage.removeItem('maestro-conversion-pending'); } catch { /* optional storage */ }
      state.selected = job.id; render(job); await jobs(); message('Conversão registrada. O original está preservado.'); void refresh();
    } catch (error) { message(error.message, true); }
    finally { state.sending = false; controls(); }
  });
  async function activate() {
    if (pane.hidden || !$('section-voices').classList.contains('active')) return;
    try {
      const capability = await api('/status'); state.ready = capability.ready;
      $('conversion-engine-status').textContent = capability.ready ? '● Seed-VC · local' : capability.message;
      $('conversion-engine-status').dataset.ready = String(capability.ready);
      const response = await fetch('/api/studio/api/voice-studio/voices', { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error('Não foi possível carregar sua biblioteca de vozes.');
      const previous = $('conversion-voice').value, voices = (await response.json()).voices;
      $('conversion-voice').replaceChildren(new Option('Selecione uma voz da sua biblioteca', ''));
      for (const voice of voices.filter((v) => v.duration <= 30)) $('conversion-voice').append(new Option(voice.name, voice.id));
      $('conversion-voice').value = previous; controls(); await jobs();
      if (!state.selected && !state.media && state.jobs.length) state.selected = state.jobs[0].id;
      if (state.selected) await select(state.selected);
      void refresh();
    } catch (error) { message(error.message, true); }
  }
  $('conversion-refresh').addEventListener('click', () => void activate());
  $('conversion-more').addEventListener('click', () => void jobs(true).catch((error) => message(error.message, true)));
  new MutationObserver(() => { if (!pane.hidden) void activate(); else { clearTimeout(state.timer); stopSync(); } }).observe(pane, { attributes: true, attributeFilter: ['hidden'] });
  new MutationObserver(() => { if ($('section-voices').classList.contains('active')) void activate(); else { clearTimeout(state.timer); stopSync(); } }).observe($('section-voices'), { attributes: true, attributeFilter: ['class'] });
})();
