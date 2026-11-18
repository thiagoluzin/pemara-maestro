/* Native Maestro sections. All requests use the authenticated Maestro proxy. */
(() => {
  const base = '/api/studio/api/zico';
  const el = id => document.getElementById(`native-${id}`);
  const pending = new Set();
  const request = (path, body) => fetchJson(base + path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  const failure = error => /Not Found|404/.test(error.message)
    ? 'A integração está preparada, mas o serviço do Maestro ainda precisa ser reiniciado para ativá-la.'
    : error.message;
  function engines(target, items) {
    target.replaceChildren();
    for (const item of items) {
      const term = document.createElement('dt'); term.textContent = item.label || item.name;
      const description = document.createElement('dd'); description.textContent = item.status;
      target.append(term, description);
    }
  }
  async function audioStatus() {
    el('audio-status').textContent = 'Consultando motores…';
    try {
      const data = await request('/capabilities');
      engines(el('audio-engines'), data.engines);
      el('audio-status').textContent = 'Instalação dos motores abaixo. Disponibilidade para geração depende da memória livre e da fila.';
      el('mix-form').querySelector('[type=submit]').disabled = data.nativeIntegrationRevision !== 2;
      if (data.nativeIntegrationRevision !== 2) {
        el('mix-status').textContent = 'O envio de faixas aguarda a ativação das novas rotas do Maestro.';
        return;
      }
      const history = await request('/jobs');
      el('audio-history').replaceChildren();
      for (const job of history.jobs) {
        const item = document.createElement('li');
        item.textContent = `${job.engine} · ${job.status} `;
        if (job.status === 'done' && /^\/api\/zico\/outputs\/[a-f0-9]{32}$/.test(job.url || '')) {
          const player = document.createElement('audio'); player.controls = true; player.preload = 'none';
          player.src = '/api/studio' + job.url; item.append(player);
          const link = document.createElement('a'); link.href = player.src; link.download = ''; link.textContent = 'Baixar áudio'; item.append(link);
        }
        el('audio-history').append(item);
      }
      if (!history.jobs.length) el('audio-history').textContent = 'Nenhum áudio produzido nesta área.';
    } catch (error) { el('audio-status').textContent = failure(error); }
  }
  async function gamesStatus() {
    el('games-status').textContent = 'Consultando componentes…';
    try {
      const [catalog, data] = await Promise.all([request('/games/catalog'), request('/games/projects')]);
      const activated = catalog.nativeIntegrationRevision === 2;
      const [imageData, history] = activated ? await Promise.all([request('/games/images/engines'), request('/games/jobs')]) : [{engines: []}, {jobs: []}];
      el('game-image-form').querySelector('[type=submit]').disabled = !activated;
      el('game-asset-form').querySelector('[type=submit]').disabled = !activated;
      engines(el('games-engines'), catalog.components);
      el('games-status').textContent = 'Consulte abaixo o estado de cada componente. Motores com pesos pendentes permanecem desabilitados.';
      if (!activated) el('games-status').textContent = 'Projetos podem ser salvos. O processamento de assets aguarda o reinício administrativo para ativar as novas rotas.';
      el('game-projects').replaceChildren();
      const selectedProject = el('game-asset-project').value;
      el('game-asset-project').replaceChildren(new Option('Selecione um projeto', ''));
      const selectedImageProject = el('game-image-project').value;
      el('game-image-project').replaceChildren(new Option('Selecione um projeto', ''));
      for (const project of data.projects) {
        const item = document.createElement('li');
        item.textContent = `${project.name} — briefing salvo`;
        el('game-projects').append(item);
        el('game-asset-project').append(new Option(project.name, project.id));
        el('game-image-project').append(new Option(project.name, project.id));
      }
      el('game-asset-project').value = selectedProject;
      el('game-image-project').value = selectedImageProject;
      const selected3dProject = el('game-3d-project').value;
      el('game-3d-project').replaceChildren(new Option('Selecione um projeto', ''));
      for (const project of data.projects) el('game-3d-project').append(new Option(project.name, project.id));
      el('game-3d-project').value = selected3dProject;
      el('game-3d-form').querySelector('[type=submit]').disabled = true;
      try {
        const models3d = await request('/games/3d/engines');
        const selected3d = el('game-3d-engine').value;
        el('game-3d-engine').replaceChildren(new Option('Escolha o motor', ''));
        for (const model of models3d.engines) {
          const option = new Option(model.id + (model.available ? ' — disponível' : ' — validação pendente'), model.id);
          option.disabled = !model.available;
          el('game-3d-engine').append(option);
        }
        el('game-3d-engine').value = selected3d;
        el('game-3d-form').querySelector('[type=submit]').disabled = !models3d.engines.some(model => model.available);
      } catch (error) { el('game-3d-status').textContent = failure(error); }
      const selectedEngine = el('game-image-engine').value;
      el('game-image-engine').replaceChildren(new Option('Escolha o motor', ''));
      for (const engine of imageData.engines) {
        const option = new Option(engine.id + (engine.available ? ' — preparado' : ' — instalação pendente'), engine.id);
        option.disabled = !engine.available;
        el('game-image-engine').append(option);
      }
      el('game-image-engine').value = selectedEngine;
      if (!data.projects.length) el('game-projects').textContent = 'Nenhum projeto cadastrado.';
      el('game-history').replaceChildren();
      for (const job of history.jobs) {
        const item = document.createElement('li');
        const project = data.projects.find(p => p.id === job.projectId);
        const labels = {done: 'concluído', running: 'em andamento', queued: 'aguardando', error: 'falhou'};
        item.textContent = `${project?.name || 'Projeto'} · ${job.engine || 'Objeto 3D'} · ${labels[job.status] || job.status} `;
        if (job.status === 'done' && /^\/api\/zico\/games\/(images\/[a-f0-9]{32}|assets\/[a-f0-9]{32})\/output$/.test(job.url || '')) {
          const link = document.createElement('a'); link.textContent = 'Baixar resultado';
          link.href = '/api/studio' + job.url; link.download = ''; item.append(link);
          const exportButton = document.createElement('button');
          exportButton.type = 'button'; exportButton.className = 'btn secondary'; exportButton.textContent = 'Exportar para Unity';
          exportButton.addEventListener('click', async () => {
            exportButton.disabled = true;
            try {
              const result = await request('/games/export', {jobId: job.jobId, kind: job.kind});
              el('games-status').textContent = result.message;
            } catch (error) { el('games-status').textContent = failure(error); exportButton.disabled = false; }
          });
          item.append(exportButton);
        }
        el('game-history').append(item);
      }
      if (!history.jobs.length) el('game-history').textContent = 'Nenhuma produção registrada.';
    } catch (error) { el('games-status').textContent = failure(error); }
  }
  function play(kind, url) {
    // Only accept outputs belonging to this integration, never arbitrary URLs.
    if (!/^\/api\/zico\/outputs\/[a-f0-9]{32}$/.test(url)) throw new Error('Endereço de áudio inválido.');
    const source = '/api/studio' + url;
    el(`${kind}-player`).src = source; el(`${kind}-player`).hidden = false;
    el(`${kind}-download`).href = source; el(`${kind}-download`).hidden = false;
  }
  async function submit(kind, form, action) {
    if (pending.has(kind)) return;
    pending.add(kind);
    const button = form.querySelector('[type=submit]'); button.disabled = true;
    el(`${kind}-status`).textContent = 'Processando…';
    try { await action(); }
    catch (error) { el(`${kind}-status`).textContent = failure(error); }
    finally { pending.delete(kind); button.disabled = false; }
  }
  el('fish-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('fish', event.currentTarget, async () => {
      let job = await request('/fish/jobs', {text: el('fish-text').value});
      el('fish-status').textContent = 'Geração em andamento. Você pode navegar por outras áreas.';
      while (['queued', 'running'].includes(job.status)) {
        await new Promise(resolve => setTimeout(resolve, 2500));
        job = await request(`/jobs/${job.jobId}`);
      }
      if (job.status !== 'done') throw new Error(job.message || 'A geração não foi concluída.');
      play('fish', job.url);
      el('fish-status').textContent = 'Voz gerada. Ouça e avalie antes de usar no projeto.';
    });
  });
  el('mix-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('mix', event.currentTarget, async () => {
      async function upload(file) {
        if (!file) return null;
        if (file.size > 128 * 1024 * 1024) throw new Error('O limite por faixa é 128 MB.');
        const form = new FormData(); form.append('audio', file);
        return (await fetchJson(base + '/uploads', {method: 'POST', body: form})).path;
      }
      const effects = Array.from(el('mix-sfx').files);
      if (effects.length > 16) throw new Error('Selecione no máximo 16 faixas de efeitos.');
      const voice = el('mix-dialogue').files[0], music = el('mix-music').files[0];
      if (!voice && !music && !effects.length) throw new Error('Selecione pelo menos uma faixa.');
      el('mix-status').textContent = 'Enviando as faixas…';
      const dialoguePath = await upload(voice), musicPath = await upload(music);
      const effectPaths = [];
      for (const effect of effects) effectPaths.push(await upload(effect));
      el('mix-status').textContent = 'Criando a mixagem…';
      const result = await request('/mix', {
        dialogue: dialoguePath, music: musicPath, sfx: effectPaths,
        target_lufs: Number(el('mix-lufs').value)
      });
      play('mix', result.url);
      el('mix-status').textContent = 'Mixagem criada em WAV. Os arquivos originais foram preservados.';
    });
  });
  el('game-project-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('game-project', event.currentTarget, async () => {
      await request('/games/projects', {name: el('game-name').value, brief: el('game-brief').value});
      el('game-project-status').textContent = 'Projeto salvo no Maestro.';
      await gamesStatus();
    });
  });
  el('audio-refresh').addEventListener('click', audioStatus);
  el('game-image-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('game-image', event.currentTarget, async () => {
      let job = await request('/games/images', {projectId: el('game-image-project').value,
        engine: el('game-image-engine').value, prompt: el('game-image-prompt').value});
      while (['queued', 'running'].includes(job.status)) {
        el('game-image-status').textContent = 'Gerando imagem. Você pode navegar por outras áreas.';
        await new Promise(resolve => setTimeout(resolve, 2500));
        job = await request(`/games/images/${job.jobId}`);
      }
      if (job.status !== 'done') throw new Error(job.message || 'A imagem não foi gerada.');
      if (!/^\/api\/zico\/games\/images\/[a-f0-9]{32}\/output$/.test(job.url)) throw new Error('Endereço de imagem inválido.');
      el('game-image-preview').src = '/api/studio' + job.url;
      el('game-image-preview').hidden = false;
      el('game-image-download').href = '/api/studio' + job.url;
      el('game-image-download').hidden = false;
      el('game-image-status').textContent = 'Imagem gerada. Confira o resultado antes de usar no jogo.';
    });
  });
  el('game-asset-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('game-asset', event.currentTarget, async () => {
      const file = el('game-asset-file').files[0];
      if (!file || file.size > 256 * 1024 * 1024) throw new Error('Selecione um GLB de até 256 MB.');
      const data = new FormData();
      data.append('asset', file); data.append('project_id', el('game-asset-project').value);
      data.append('operation', el('game-asset-operation').value);
      let job = await fetchJson(base + '/games/assets', {method: 'POST', body: data});
      while (['queued', 'running'].includes(job.status)) {
        el('game-asset-status').textContent = job.engine === 'skintokens' ? 'Criando esqueleto e pesos do personagem…' : 'Preparando malha, LODs e collider…';
        await new Promise(resolve => setTimeout(resolve, 2000));
        job = await request(`/games/assets/${job.jobId}`);
      }
      if (job.status !== 'done') throw new Error(job.message || 'O objeto não foi preparado.');
      if (!/^\/api\/zico\/games\/assets\/[a-f0-9]{32}\/output$/.test(job.url)) throw new Error('Endereço de saída inválido.');
      el('game-asset-download').href = '/api/studio' + job.url;
      el('game-asset-download').hidden = false;
      el('game-asset-status').textContent = 'Objeto preparado. Confira a geometria antes de incorporar ao jogo.';
    });
  });
  el('games-refresh').addEventListener('click', gamesStatus);
  el('game-3d-form').addEventListener('submit', event => {
    event.preventDefault();
    void submit('game-3d', event.currentTarget, async () => {
      const file = el('game-3d-file').files[0];
      if (!file || file.size > 20 * 1024 * 1024) throw new Error('Selecione uma imagem de até 20 MB.');
      const data = new FormData();
      data.append('image', file); data.append('project_id', el('game-3d-project').value);
      data.append('engine', el('game-3d-engine').value);
      let job = await fetchJson(base + '/games/3d', {method: 'POST', body: data});
      while (['queued', 'running'].includes(job.status)) {
        el('game-3d-status').textContent = 'Objeto na fila de geração. Você pode navegar por outras áreas.';
        await new Promise(resolve => setTimeout(resolve, 3000));
        job = await request(`/games/assets/${job.jobId}`);
      }
      if (job.status !== 'done') throw new Error(job.message || 'A geração 3D não foi concluída.');
      if (!/^\/api\/zico\/games\/assets\/[a-f0-9]{32}\/output$/.test(job.url)) throw new Error('Saída 3D inválida.');
      el('game-3d-download').href = '/api/studio' + job.url;
      el('game-3d-download').hidden = false;
      el('game-3d-status').textContent = 'Malha 3D gerada. Confira no Blender antes de usar no jogo.';
      await gamesStatus();
    });
  });
  document.querySelector('[data-section="audio-studio"]').addEventListener('click', audioStatus);
  document.querySelector('[data-section="game-studio"]').addEventListener('click', gamesStatus);
})();

