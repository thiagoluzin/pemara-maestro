/* Additive review surface; the normal engine picker and submission stay authoritative. */
(() => {
  const base = '/api/studio/api/creative';
  const host = document.querySelector('.gen-workspace');
  if (!host) return;
  const panel = document.createElement('section');
  panel.className = 'panel';
  panel.style.cssText = 'grid-column:1/-1;padding:20px;min-width:0';
  panel.innerHTML = `<details><summary><strong>Creative OS · Revisão e acabamento</strong></summary>
    <p>Gere com o motor que você escolher no Maestro. Aqui você pode revisar o vídeo, preservar uma versão aprovada e pedir um acabamento separado.</p>
    <div style="display:flex;gap:12px;flex-wrap:wrap"><button type="button" class="btn secondary" data-action="refresh">Atualizar vídeos</button>
    <label>Trabalho do Maestro <select aria-label="Trabalho para revisar" id="creative-job"></select></label>
    <button type="button" class="btn secondary" data-action="attach">Adicionar à revisão</button></div>
    <p role="status" aria-live="polite" id="creative-status"></p><div id="creative-list"></div>
    <h3>Acabamentos</h3><div id="creative-hq"></div>
    <h3>Sugestão de prompt H3</h3><p>Use o modo Texto para vídeo com H3 selecionado. A sugestão é opcional e precisa da sua revisão.</p>
    <div id="creative-rewriter-actions"></div><p role="status" id="creative-rewriter-status"></p><div id="creative-rewriter-result"></div>
    <h3>Plano contínuo H3 (experimental)</h3><p>Dois segmentos com continuação entre eles, sem áudio. Prepare para conferir a duração efetiva antes de gerar.</p>
    <div id="creative-timeline-actions"></div><p role="status" id="creative-timeline-status"></p>
    <h3>Vídeo de controle H3 (experimental)</h3><p>Escolha um controle já preparado: 1088×608, 124 frames, 24 fps. A saída é um novo vídeo sem áudio.</p>
    <label>Vídeo de controle <input type="file" accept="video/*" id="creative-control-file"></label>
    <label>Tipo do controle <select id="creative-control-kind"><option value="depth">Profundidade</option><option value="canny">Contornos Canny</option><option value="pose">Pose</option><option value="hed">Contornos HED</option><option value="mlsd">Linhas MLSD</option></select></label>
    <div id="creative-control-actions"></div><p role="status" id="creative-control-status"></p>
    <h3>H3 All-In-One (experimental)</h3><p>Texto para vídeo pelo template All-In-One, em Production horizontal e sem áudio. O motor continua sendo H3.</p>
    <div id="creative-all-in-one-actions"></div><p role="status" id="creative-all-in-one-status"></p></details>`;
  host.append(panel);
  const status = panel.querySelector('#creative-status');
  const element = (tag,text) => { const node=document.createElement(tag); node.textContent=text; return node; };
  async function request(path, body) {
    const response=await fetch(base+path,{cache:'no-store',...(body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})});
    const data=await response.json();
    if (!response.ok) throw new Error(data.error?.message || data.erro || 'Falha ao executar a ação.');
    return data;
  }
  function button(label,action) {
    const b=element('button',label); b.type='button'; b.className='btn secondary';
    b.addEventListener('click',async()=>{b.disabled=true;try{await action();}catch(e){status.textContent=e.message;}finally{b.disabled=false;}});
    return b;
  }
  function media(parent,path) {
    const video=document.createElement('video'); video.controls=true; video.preload='metadata';
    video.style.cssText='display:block;max-width:100%;max-height:420px;margin:12px 0';
    video.src=base+path; parent.append(video);
  }
  async function refresh() {
    status.textContent='Carregando revisões…';
    const jobsResponse=await fetch('/api/studio/api/generative/jobs?page=1&page_size=50',{cache:'no-store'});
    if (!jobsResponse.ok) throw new Error('Não foi possível consultar os trabalhos do Maestro.');
    const jobs=await jobsResponse.json();
    const selector=panel.querySelector('#creative-job'); selector.replaceChildren();
    const rows=Array.isArray(jobs) ? jobs : (jobs.items || jobs.jobs || jobs.data || []);
    for(const job of rows.filter(j=>j.mode==='video')) {
      const option=element('option',`${job.engine_id || 'Vídeo'} · ${job.status} · ${(job.prompt || job.job_id).slice(0,70)}`);
      option.value=job.job_id; selector.append(option);
    }
    const list=panel.querySelector('#creative-list'); list.replaceChildren();
    const hq=await request('/hq');
    const generations=await request('/generations');
    const semanticJobs=await request('/semantic-jobs');
    for(const item of generations) {
      const record=await request(`/generations/${item.id}`);
      const card=element('article','');card.style.cssText='padding:16px 0;border-bottom:1px solid #7775';
      card.append(element('h3',`${record.engine_id === 'minimax_h3' ? 'MiniMax H3' : 'LTX 2.5'} · ${record.human_verdict || record.status}`));
      card.append(element('p',(record.ir?.content?.description || record.request_spec?.prompt || '').slice(0,350)));
      const index=record.artifacts.findIndex(a=>a.kind==='video');
      if(index>=0) {
        const artifact=record.artifacts[index]; media(card,`/generations/${record.id}/artifacts/${index}`);
        card.append(button('Verificar vídeo',async()=>{const e=await request(`/generations/${record.id}/evaluate`,{});status.textContent=e.technical_pass ? 'Arquivo verificado. A aprovação visual continua sendo sua.' : 'O arquivo falhou na verificação técnica.';}));
        card.append(button('Avaliação visual local (GPU)',async()=>{
          await request(`/generations/${record.id}/semantic-review`,{artifact_sha256:artifact.sha256,idempotency_key:'sample6-v1-'+artifact.sha256});await refresh();
        }));
        for(const item of semanticJobs.filter(j=>j.generation_id===record.id && j.artifact_sha256===artifact.sha256)) {
          const review=await request(`/semantic-jobs/${item.id}`);
          card.append(element('p',`Avaliação visual consultiva · ${review.state}. Seis quadros amostrados; aprovação humana separada.`));
          if(review.review) {
            card.append(element('p',review.review.summary));
            const details=document.createElement('details');details.append(element('summary','Observações do modelo'));
            for(const [dimension,observation] of Object.entries(review.review.observations))
              details.append(element('p',`${dimension} · ${observation.status}: ${observation.evidence}`));
            card.append(details);
          }
          if(review.error) card.append(element('p',review.error));
          if(['QUEUED','RUNNING'].includes(review.state)) card.append(button('Cancelar avaliação visual',async()=>{await request(`/semantic-jobs/${review.id}/cancel`,{});await refresh();}));
        }
        card.append(button('Aprovar este vídeo',async()=>{await request(`/generations/${record.id}/verdict`,{decision:'approved',artifact_sha256:artifact.sha256});await refresh();}));
        card.append(button('Reprovar este vídeo',async()=>{await request(`/generations/${record.id}/verdict`,{decision:'rejected',artifact_sha256:artifact.sha256});await refresh();}));
        if(record.human_verdict==='approved') {
          const profile=document.createElement('select');profile.setAttribute('aria-label','Formato do acabamento');
          for(const [value,label] of [['neural_fhd','FHD horizontal'],['neural_vertical','FHD vertical']]) {const o=element('option',label);o.value=value;profile.append(o);}
          if(record.engine_id==='minimax_h3' && record.provenance?.latent_capture && record.artifacts.some(a=>a.kind==='latent') && hq.profiles?.h3_latent_2stage_v1?.enabled) {
            const o=element('option','Refinamento H3 1536×864 (experimental)');o.value='h3_latent_2stage_v1';profile.append(o);
          }
          card.append(profile,button('Criar candidato de acabamento',async()=>{
            await request('/hq',{master_id:record.id,profile_id:profile.value,idempotency_key:crypto.randomUUID()});await refresh();
          }));
        }
      } else {
        card.append(element('p',record.error || 'Aguardando o resultado. O trabalho continua no Maestro.'));
        if(record.job_id && ['queued','running','submitting'].includes(record.status))
          card.append(button('Cancelar geração',async()=>{await request(`/generations/${record.id}/cancel`,{});await refresh();}));
      }
      list.append(card);
    }
    const box=panel.querySelector('#creative-hq');box.replaceChildren();
    for(const job of hq.jobs) {
      const card=element('article','');card.append(element('p',`${job.profile_id} · ${job.state}`));
      if(job.error) card.append(element('p',job.error));
      if(job.state==='QUEUED') card.append(button('Cancelar acabamento',async()=>{await request(`/hq/${job.id}/cancel`,{});await refresh();}));
      job.artifacts.forEach((a,i)=>{
        if(a.kind!=='video') return;
        media(card,`/hq/${job.id}/artifacts/${i}`);
        for(const [decision,label] of [['approved','Aprovar acabamento'],['rejected','Reprovar acabamento']])
          card.append(button(label,async()=>{await request(`/hq/${job.id}/verdict`,{decision,artifact_sha256:a.sha256});await refresh();}));
      });box.append(card);
    }
    status.textContent=`${generations.length} vídeo(s) em revisão. Nenhuma aprovação é automática.`;
  }
  const rewriteStatus=panel.querySelector('#creative-rewriter-status');
  const rewriteResult=panel.querySelector('#creative-rewriter-result');
  const rewriteKey='creative_os_rewriter_pending_v1';
  let rewritePending=null, rewriteTimer=null;
  try {rewritePending=JSON.parse(localStorage.getItem(rewriteKey)||'null');} catch(_) {}
  function rememberRewrite(value) {
    rewritePending=value;
    try {if(value)localStorage.setItem(rewriteKey,JSON.stringify(value));else localStorage.removeItem(rewriteKey);} catch(_) {}
  }
  function unchangedBrief(pending) {
    return document.querySelector('#gen-prompt')?.value.trim()===pending.original &&
      document.querySelector('#gen-engine-id')?.value==='minimax_h3' &&
      document.querySelector('#gen-mode')?.value==='text_video' &&
      Number(document.querySelector('#gen-video-duration')?.value)===pending.duration;
  }
  const timelineStatus=panel.querySelector('#creative-timeline-status');
  const timelineActions=panel.querySelector('#creative-timeline-actions');
  let preparedTimeline=null;
  timelineActions.append(button('Preparar plano contínuo',async()=>{
    const original=document.querySelector('#gen-prompt')?.value.trim();
    const duration=Number(document.querySelector('#gen-video-duration')?.value);
    if(!original || !unchangedBrief({original,duration}))throw new Error('Selecione Texto para vídeo e o motor H3, com um prompt preenchido.');
    const seed=Date.now()%2147483647;
    const ir={version:'0.2',project_id:'maestro_timeline',shot_id:'timeline_'+crypto.randomUUID(),duration_seconds:duration,
      content:{description:original},generation:{preferred_engine:'minimax_h3',quality_mode:'balanced',native_audio:false}};
    const shot=await request('/shots',ir);
    const plan=await request(`/shots/${shot.id}/timeline-plan`,{seed,segment_count:2});
    preparedTimeline={original,duration,seed,shotId:shot.id,key:crypto.randomUUID()};
    timelineStatus.textContent=`${plan.segment_count} segmentos; ${plan.output_frames} frames; ${(plan.output_frames/24).toFixed(2)} segundos efetivos. O prompt atual será preservado.`;
  }),button('Gerar plano contínuo',async()=>{
    const pending=preparedTimeline;
    if(!pending || !unchangedBrief(pending))throw new Error('Prepare novamente: o plano ainda não existe ou o prompt, motor ou duração mudou.');
    const result=await request(`/shots/${pending.shotId}/timeline-generate`,{seed:pending.seed,segment_count:2,idempotency_key:pending.key});
    timelineStatus.textContent=`Plano enviado ao Maestro (${result.status}). Acompanhe em Trabalhos e revise o vídeo abaixo.`;
    await refresh();
  }));
  let controlPending=null;
  let allInOnePending=null;
  panel.querySelector('#creative-all-in-one-actions').append(button('Gerar com H3 All-In-One',async()=>{
    const original=document.querySelector('#gen-prompt')?.value.trim();
    const duration=Number(document.querySelector('#gen-video-duration')?.value);
    if(!original || !unchangedBrief({original,duration}))throw new Error('Selecione Texto para vídeo e H3, com um prompt preenchido.');
    if(duration<4 || duration>15)throw new Error('H3 All-In-One exige duração entre 4 e 15 segundos.');
    if(!allInOnePending || allInOnePending.original!==original || allInOnePending.duration!==duration) {
      const shot=await request('/shots',{version:'0.2',project_id:'maestro_all_in_one',shot_id:'aio_'+crypto.randomUUID(),duration_seconds:duration,
        content:{description:original},generation:{preferred_engine:'minimax_h3',quality_mode:'balanced',native_audio:false}});
      allInOnePending={original,duration,shotId:shot.id,key:crypto.randomUUID(),seed:Date.now()%2147483647};
    }
    const p=allInOnePending;if(!unchangedBrief(p))throw new Error('O pedido mudou. Nenhuma geração enviada.');
    const result=await request(`/shots/${p.shotId}/generate`,{idempotency_key:p.key,bindings:{seed:p.seed,h3_adapter:'all_in_one'}});
    panel.querySelector('#creative-all-in-one-status').textContent=`All-In-One enviado ao Maestro (${result.status}). Acompanhe e revise o vídeo abaixo.`;
    await refresh();
  }));
  panel.querySelector('#creative-control-actions').append(button('Gerar com vídeo de controle',async()=>{
    const original=document.querySelector('#gen-prompt')?.value.trim();
    const duration=Number(document.querySelector('#gen-video-duration')?.value);
    const file=panel.querySelector('#creative-control-file').files[0];
    const kind=panel.querySelector('#creative-control-kind').value;
    if(!original || !unchangedBrief({original,duration}))throw new Error('Selecione Texto para vídeo e H3, com um prompt preenchido.');
    if(!file || file.size>512*1024*1024)throw new Error('Escolha um vídeo de controle de até 512 MB.');
    if(duration<4 || duration>5.5)throw new Error('Este controle exige uma duração entre 4 e 5,5 segundos.');
    const same=controlPending && controlPending.file===file && controlPending.original===original && controlPending.duration===duration && controlPending.kind===kind;
    if(!same) {
      const form=new FormData();form.append('file',file);
      const response=await fetch(base+'/control-assets',{method:'POST',body:form});
      const asset=await response.json();if(!response.ok)throw new Error(asset.error?.message || 'Não foi possível importar o controle.');
      const shot=await request('/shots',{version:'0.2',project_id:asset.project_id,shot_id:'control_'+crypto.randomUUID(),duration_seconds:duration,
        content:{description:original},generation:{preferred_engine:'minimax_h3',quality_mode:'balanced',native_audio:false}});
      controlPending={file,original,duration,kind,shotId:shot.id,assetId:asset.id,seed:Date.now()%2147483647,key:crypto.randomUUID()};
    }
    const p=controlPending;
    if(!unchangedBrief(p) || panel.querySelector('#creative-control-file').files[0]!==p.file || panel.querySelector('#creative-control-kind').value!==p.kind)
      throw new Error('O pedido mudou durante a importação. Nenhuma geração foi enviada.');
    const result=await request(`/shots/${p.shotId}/control-generate`,{asset_id:p.assetId,control_kind:p.kind,strength:1,seed:p.seed,idempotency_key:p.key});
    panel.querySelector('#creative-control-status').textContent=`Controle enviado ao Maestro (${result.status}). Acompanhe em Trabalhos e revise o resultado abaixo.`;
    await refresh();
  }));
  async function pollRewrite() {
    clearTimeout(rewriteTimer);
    const pending=rewritePending;if(!pending)return;
    try {
      const job=await request(`/rewriter-jobs/${pending.id}`);
      if(job.state==='DONE') {
        const proposal=await request(`/prompt-proposals/${job.proposal_id}`);
        rewriteResult.replaceChildren();
        rewriteResult.append(element('h4','Original'),element('p',proposal.original_description),element('h4','Sugestão'));
        const text=element('pre',proposal.suggestion);text.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere';rewriteResult.append(text);
        rewriteStatus.textContent='Confira ações, identidade e restrições. O texto ainda não foi aplicado.';
        if(proposal.status==='APPLIED') {rememberRewrite(null);rewriteStatus.textContent='Proposta já aplicada ao plano salvo.';return;}
        rewriteResult.append(button('Aprovar e usar este prompt',async()=>{
          if(!unchangedBrief(pending))throw new Error('O brief, motor ou duração mudou. O campo atual foi preservado.');
          await request(`/prompt-proposals/${proposal.id}/verdict`,{decision:'approved',suggestion_hash:proposal.suggestion_hash});
          await request(`/prompt-proposals/${proposal.id}/apply`,{});
          if(unchangedBrief(pending)) {
            const field=document.querySelector('#gen-prompt');field.value=proposal.suggestion;field.dispatchEvent(new Event('input',{bubbles:true}));
            rewriteStatus.textContent='Prompt revisado aplicado. A geração do vídeo continua sob seu comando.';
          } else rewriteStatus.textContent='Proposta aprovada no histórico. O campo mudou durante a aplicação e foi preservado.';
          rememberRewrite(null);rewriteResult.querySelectorAll('button').forEach(b=>b.remove());
        }),button('Rejeitar sugestão',async()=>{
          await request(`/prompt-proposals/${proposal.id}/verdict`,{decision:'rejected',suggestion_hash:proposal.suggestion_hash});
          rememberRewrite(null);rewriteStatus.textContent='Sugestão rejeitada. Seu prompt foi preservado.';rewriteResult.querySelectorAll('button').forEach(b=>b.remove());
        }));
      } else if(['QUEUED','RUNNING','SUBMITTING','CANCELING'].includes(job.state)) {
        rewriteStatus.textContent=job.state==='CANCELING' ? 'Cancelamento da sugestão solicitado.' : 'Gerando sugestão no Maestro. O prompt original está preservado.';
        if(panel.querySelector('details').open)rewriteTimer=setTimeout(pollRewrite,5000);
      } else {rewriteStatus.textContent=job.error || `Reescrita: ${job.state}`;rememberRewrite(null);}
    } catch(e) {rewriteStatus.textContent=e.message;}
  }
  panel.querySelector('#creative-rewriter-actions').append(button('Sugerir versão do prompt (H3)',async()=>{
    if(rewritePending) {await pollRewrite();return;}
    const original=document.querySelector('#gen-prompt')?.value.trim();
    if(document.querySelector('#gen-mode')?.value!=='text_video' || document.querySelector('#gen-engine-id')?.value!=='minimax_h3')
      throw new Error('Selecione Texto para vídeo e o motor H3 para esta sugestão.');
    if(!original)throw new Error('Escreva o brief primeiro.');
    const duration=Number(document.querySelector('#gen-video-duration')?.value);
    if(!(duration>=4 && duration<=15))throw new Error('Use duração H3 entre 4 e 15 segundos.');
    const shot=await request('/shots',{version:'0.2',project_id:'maestro_prompt_assist',shot_id:'rewrite_'+crypto.randomUUID(),
      duration_seconds:duration,content:{description:original},generation:{preferred_engine:'minimax_h3',quality_mode:'balanced'}});
    const job=await request(`/shots/${shot.id}/rewrite`,{idempotency_key:crypto.randomUUID(),seed:Date.now()%2147483647});
    rememberRewrite({id:job.id,original,duration});rewriteResult.replaceChildren();await pollRewrite();
  }));
  panel.querySelector('#creative-rewriter-actions').append(button('Cancelar sugestão',async()=>{
    if(!rewritePending)return;
    await request(`/rewriter-jobs/${rewritePending.id}/cancel`,{});await pollRewrite();
  }));
  panel.querySelector('[data-action="refresh"]').addEventListener('click',()=>{refresh().catch(e=>status.textContent=e.message);pollRewrite();});
  panel.querySelector('[data-action="attach"]').addEventListener('click',async()=>{
    const id=panel.querySelector('#creative-job').value;if(!id)return;
    try { await request(`/jobs/${encodeURIComponent(id)}/attach`,{}); await refresh(); } catch(e){status.textContent=e.message;}
  });
  panel.querySelector('details').addEventListener('toggle',e=>{if(e.target.open){refresh().catch(err=>status.textContent=err.message);pollRewrite();}else clearTimeout(rewriteTimer);});
})();
