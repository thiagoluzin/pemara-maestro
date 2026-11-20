(() => {
  const id = key => document.getElementById(key);
  const desk = id("scene-desk");
  let project, take, tab = "chat", direction, epoch = 0, timer, signature, pendingId, pendingSignature;
  let latest = [], older = [], more = false, busy = false, dirty = false;
  let pollingEpoch, refreshPending = false;
  const api = () => API.studio + "/api/video-projects/" + encodeURIComponent(project.projectId) + "/cinema";
  const say = text => {id("cinema-notice").textContent = text;};
  const post = (url, data) => fetchJson(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  function node(tag,text,cls) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  }
  function button(text,fn) {
    const b = node("button",text,"btn secondary small");
    b.type = "button";
    b.onclick = async () => {
      b.disabled = true;
      try { await fn(); } catch (error) { say(error.message); } finally { b.disabled = false; }
    };
    return b;
  }
  const current = ticket => desk.open && epoch===ticket;
  function message(row) {
    const article = node("article");
    const meta = [row.selection.takeId,row.selection.versionId && Number(row.selection.seconds).toFixed(2)+" s"].filter(Boolean).join(" · ");
    if (meta) article.append(button(meta,() => window.MaestroSceneContext.restore(row.selection)));
    article.append(node("p",row.request,"cinema-request"));
    const r = row.result;
    if (r.answer) article.append(node("p",r.answer,"cinema-answer"));
    if (r.correction) article.append(node("p",r.correction,"cinema-proposal"));
    function photoText(values) {
      return Object.entries(values || {}).filter(([,v])=>v).map(([k,v])=>(fields[k]?.[0] || k)+" · "+v).join(" / ");
    }
    if (r.photography) article.append(node("p",photoText(r.photography.values),"cinema-proposal"));
    if (r.shots?.length) {
      const ol = node("ol");
      for (const s of r.shots) {
        const li=node("li");
        li.append(node("strong",s.name+" · "+s.durationSeconds+" s"),node("p",s.direction));
        if (s.photography) li.append(node("small",photoText(s.photography)));
        ol.append(li);
      }
      article.append(ol);
    }
    for (const kind of ["correction","produce","shots","photography"]) {
      if (!(kind==="produce" ? r.produce : kind==="photography" ? r[kind]?.values : r[kind]?.length)) continue;
      const action = row.actions[kind];
      if (action) {
        if (["correction","produce"].includes(kind) && action.state==="submitted") {
          article.append(button("Acompanhar render",async () => {
            const ticket=epoch;
            const job = await fetchFilmMetadata(API.studio + "/api/generative/job/" + encodeURIComponent(action.detail));
            if (!current(ticket)) return;
            if (job.status==="done") await window.MaestroSceneContext.restore({takeId:row.selection.takeId});
            say((job.message || job.status) + (Number.isFinite(job.progress) ? " · "+job.progress+"%" : ""));
          }));
        } else article.append(node("small",action.detail || "Pedido registrado. Consulte o estado antes de reenviar."));
      } else if (r.triage?.choice==="aligned" && (kind!=="correction" || row.selection.versionId) && (kind!=="produce" || row.selection.takeId)) {
        const labels={correction:"Autorizar correção do take",produce:"Produzir este take",shots:"Salvar roteiro como modelo",photography:"Aplicar fotografia"};
        article.append(button(labels[kind], async () => {
          const ticket=epoch;
          const name = kind==="shots" ? prompt("Nome do modelo de episódio") : "";
          if (kind==="shots" && !name) return;
          if (kind==="correction" && !confirm("Registrar a correção no take "+row.selection.takeId+" e iniciar a produção se ele estiver disponível?")) return;
          await post(api()+"/chat/"+row.id+"/apply/"+kind,{name});
          if (current(ticket)) await poll(ticket);
        }));
      } else article.append(node("small",r.triage?.choice==="unavailable" ? "Gemini Decision indisponível. Proposta guardada para leitura." : "Confira o escopo e a versão selecionada antes de uma nova proposta."));
    }
    if (["queued","running"].includes(row.status)) article.append(button("Cancelar pedido",async () => {
      const ticket=epoch;
      await post(api()+"/chat/"+row.id+"/cancel",{});
      if (current(ticket)) await poll(ticket);
    }));
    if (row.status!=="done") article.append(node("small",row.progress));
    return article;
  }
  function drawMessages() {
    const log=id("cinema-messages");
    const bottom=log.scrollTop+log.clientHeight>=log.scrollHeight-24;
    const rows=[...new Map([...older,...latest].map(r=>[r.id,r])).values()].sort((a,b)=>a.seq-b.seq);
    log.replaceChildren(...rows.map(message));
    if (!rows.length) log.append(node("p","Comece a conversa sobre este episódio."));
    if (bottom) log.scrollTop=log.scrollHeight;
    id("cinema-older").hidden=!more;
  }
  async function poll(ticket) {
    clearTimeout(timer);
    if (!current(ticket) || tab!=="chat" || document.hidden) return;
    if (pollingEpoch===ticket) { refreshPending=true; return; }
    pollingEpoch=ticket;
    refreshPending=false;
    let delay=12000;
    try {
      const query=signature==null ? "" : "?since="+encodeURIComponent(signature);
      const data = await fetchFilmMetadata(api()+"/chat"+query);
      if (!current(ticket) || tab!=="chat") return;
      if (!data.unchanged) {
        if (older.length) {
          const nextIds=new Set(data.items.map(row=>row.id));
          older.push(...latest.filter(row=>!nextIds.has(row.id)));
        }
        latest=data.items;
        if (!older.length) more=data.older;
        signature=data.revision;
        drawMessages();
      }
      const active=latest.some(r=>["running","queued"].includes(r.status));
      if (active) delay=3000;
      id("cinema-send").querySelector("button").disabled=busy || active;
      if (!data.workerOnline) say("Operador local desconectado. Pedidos na fila ficam guardados.");
      else if (active) say(latest.find(r=>["running","queued"].includes(r.status)).progress);
      else if (!busy && /Operador local|Na fila|Abrindo|Codex preparando|Conferindo/.test(id("cinema-notice").textContent)) say("");
    } catch(error) { if (current(ticket)) say(error.message); }
    finally {
      if (pollingEpoch===ticket) {
        pollingEpoch=undefined;
        if (current(ticket) && tab==="chat" && !document.hidden)
          timer=setTimeout(()=>poll(ticket),refreshPending ? 0 : delay);
      }
    }
  }
  id("cinema-older").onclick=async () => {
    const ticket=epoch;
    try {
      const before=(older[0] || latest[0]).seq;
      const data=await fetchFilmMetadata(api()+"/chat?before="+before);
      if (!current(ticket)) return;
      older=[...data.items,...older];more=data.older;drawMessages();
    } catch(e) {say(e.message);}
  };
  id("cinema-send").onsubmit=async e=>{
    e.preventDefault();
    if (busy) return;
    const form=e.currentTarget, ticket=epoch;
    const data={message:form.elements.message.value.trim(),...window.MaestroSceneContext.selection()};
    const key=JSON.stringify([project.projectId,data]);
    if (pendingSignature!==key) {pendingSignature=key;pendingId=crypto.randomUUID();}
    busy=true;
    form.querySelector("button").disabled=true;
    try {
      await post(api()+"/chat",{...data,id:pendingId});
      if (current(ticket)) {form.reset();pendingId=null;pendingSignature=null;say("Na fila");}
    } catch(error) {if(current(ticket)) say(error.message);}
    finally {busy=false;if(current(ticket)) await poll(ticket);}
  };
  const fields={lighting:["Iluminação","Luz lateral difusa"],palette:["Paleta","Azul e âmbar"],
    framing:["Enquadramento","Plano médio"],lens:["Lente","50 mm"],movement:["Movimento","Aproximação lenta"]};
  const presets={lighting:["Luz natural difusa","Contraluz","Luz lateral dura","Luz de janela"],
    palette:["Quente e terrosa","Azul e âmbar","Fria e dessaturada","Preto e branco"],
    framing:["Plano geral","Plano médio","Primeiro plano","Plano detalhe","Sobre o ombro"],
    lens:["24 mm","35 mm","50 mm","85 mm","100 mm macro"],
    movement:["Câmera fixa","Aproximação lenta","Afastamento lento","Travelling lateral","Panorâmica","Câmera na mão"]};
  const form=id("cinema-look-form");
  function displayDirection() {
    const shot=form.elements.scope.value==="take";
    const values=shot ? direction.shots[take?.takeId]?.values || {} : direction.look;
    id("cinema-fields").replaceChildren(...Object.entries(fields).filter(([k])=>shot || ["lighting","palette"].includes(k)).map(([k,[title,hint]])=>{
      const label=node("label",title);
      const input=node("input");input.name=k;input.maxLength=["framing","lens"].includes(k)?80:100;
      input.placeholder=shot && direction.look[k] ? "Herdado · "+direction.look[k] : hint;
      const choices=node("datalist");choices.id="cinema-presets-"+k;
      for (const option of presets[k]) choices.append(new Option(option,option));
      input.setAttribute("list",choices.id);
      input.value=values[k] || "";label.append(input,choices);return label;
    }));
    const pick=id("cinema-pick");
    pick.hidden=!shot || !direction.elements.length;
    pick.replaceChildren(node("legend","Referências do take"));
    const selected=direction.shots[take?.takeId]?.elements || [];
    for (const asset of direction.elements) {
      const label=node("label");const check=node("input");
      check.type="checkbox";check.name="element";check.value=asset.id;check.checked=selected.includes(asset.id);
      const img=node("img");img.src=api()+"/elements/"+encodeURIComponent(asset.id);img.alt="";img.loading="lazy";img.width=48;img.height=40;
      label.append(check,img,document.createTextNode(asset.name+" · "+asset.role));pick.append(label);
    }
    id("cinema-gallery").replaceChildren(...direction.elements.map(asset=>{
      const card=node("figure"),img=node("img");img.src=api()+"/elements/"+encodeURIComponent(asset.id);img.alt=asset.name;img.loading="lazy";
      card.append(img,node("figcaption",asset.name+" · "+asset.role));return card;
    }));
    if (!direction.elements.length) id("cinema-gallery").append(node("p","Cadastre um personagem, cenário ou objeto para reutilizar nas cenas."));
  }
  async function loadLook(ticket) {
    direction=null;
    form.querySelector("button").disabled=true;
    try {
      const data=await fetchFilmMetadata(api()+"/direction");
      if (!current(ticket)) return;
      direction=data;
      form.elements.scope.options[1].disabled=!take;
      if (!take) form.elements.scope.value="episode";
      displayDirection();
      dirty=false;
      form.querySelector("button").disabled=false;
    } catch(error) {if(current(ticket)) say(error.message);}
  }
  form.elements.scope.onchange=()=>{if(direction){displayDirection();dirty=false;}};
  form.oninput=e=>{if(e.target!==form.elements.scope)dirty=true;};
  form.onsubmit=async e=>{
    e.preventDefault();if(!direction)return;
    const ticket=epoch,shot=form.elements.scope.value==="take";
    const values=Object.fromEntries([...id("cinema-fields").querySelectorAll("input")].map(i=>[i.name,i.value]));
    const elements=[...id("cinema-pick").querySelectorAll(":checked")].map(i=>i.value);
    form.querySelector("button").disabled=true;
    try {
      const data=await post(api()+"/direction",{takeId:shot?take.takeId:"",values,elements,revision:direction.revision});
      if(current(ticket)){direction=data;dirty=false;say("Direção salva no projeto.");}
    } catch(error) {if(current(ticket))say(error.message);}
    finally {if(current(ticket))form.querySelector("button").disabled=false;}
  };
  id("cinema-add").onsubmit=async e=>{
    e.preventDefault();const form=e.currentTarget,ticket=epoch;
    if(form.elements.file.files[0]?.size>8*1024*1024)return say("Escolha uma imagem de até 8 MB.");
    form.querySelector("button").disabled=true;
    try {
      const data=await fetchJson(api()+"/elements",{method:"POST",body:new FormData(form)});
      if(current(ticket)){direction=data;form.reset();displayDirection();say("Referência cadastrada no projeto.");}
    }catch(error){if(current(ticket))say(error.message);}
    finally {form.querySelector("button").disabled=false;}
  };
  function show() {
    clearTimeout(timer);
    for(const b of document.querySelectorAll("[data-cinema-tab]")){
      const active=b.dataset.cinemaTab===tab;
      id("cinema-"+b.dataset.cinemaTab).hidden=!active;
      b.setAttribute("aria-pressed",String(active));
    }
    if(tab==="chat") poll(epoch);else loadLook(epoch);
  }
  document.querySelectorAll("[data-cinema-tab]").forEach(b=>b.onclick=()=>{
    if(tab===b.dataset.cinemaTab)return;
    if(dirty && !confirm("Sair sem salvar a direção?"))return;
    tab=b.dataset.cinemaTab;dirty=false;say("");++epoch;show();
  });
  window.MaestroCinema={activate(p,t){
    const changed=project?.projectId!==p.projectId;
    project=p;take=t;++epoch;signature=null;dirty=false;
    if(changed){latest=[];older=[];more=false;id("cinema-send").reset();id("cinema-add").reset();drawMessages();}
    say("");show();
  }};
  desk.addEventListener("close",()=>{++epoch;clearTimeout(timer);});
  document.addEventListener("visibilitychange",()=>{
    clearTimeout(timer);
    if (!document.hidden && desk.open && tab==="chat") poll(epoch);
  });
})();

