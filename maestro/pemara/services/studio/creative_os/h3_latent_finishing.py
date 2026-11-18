"""Pinned video-only H3 latent finishing; no model import or submission on import."""
import copy
import json
from pathlib import Path
from .assets import file_hash, safe_path
from .ir import CreativeError, digest

MODELS={"UNETLoader":("unet_name","diffusion_models","minimax_h3_fl2va_pruned_int8_convrot.safetensors"),
        "CLIPLoader":("clip_name","text_encoders","qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
        "VAELoader":("vae_name","vae","minimax_h3_video_vae_fp16.safetensors")}
ALLOWED={*MODELS,"MiniMaxH3SigmaShift","MiniMaxH3ImageToVideo","BasicGuider","BasicScheduler",
         "RandomNoise","KSamplerSelect","SamplerCustomAdvanced","LTXVSeparateAVLatent","VAEDecodeTiled",
         "ImageScale","CreateVideo","SaveVideo","SaveLatent"}
_HASH_CACHE={}


def one(graph, kind):
    matches=[k for k,n in graph.items() if n.get("class_type")==kind]
    if len(matches)!=1: raise CreativeError("LATENT_GRAPH_SCOPE",f"Exige um nó {kind} no grafo original.",409)
    return matches[0]


def source_contract(graph):
    if not isinstance(graph,dict) or any(n.get("class_type") not in ALLOWED for n in graph.values()):
        raise CreativeError("LATENT_GRAPH_SCOPE","Perfil qualificado somente para H3 T2V nativo sem áudio.",409)
    cond=graph[one(graph,"MiniMaxH3ImageToVideo")]["inputs"]
    schedule=graph[one(graph,"BasicScheduler")]["inputs"]
    video=graph[one(graph,"CreateVideo")]["inputs"]
    if any(k in cond for k in ("first_frame","last_frame")) or "audio" in video:
        raise CreativeError("LATENT_GRAPH_SCOPE","Referências/áudio exigem qualificação adicional.",409)
    if (cond.get("width"),cond.get("height"),cond.get("length")) != (1088,608,124):
        raise CreativeError("LATENT_GEOMETRY","Escopo qualificado: Production 1088×608, 124 frames.",409)
    if schedule.get("steps")!=10 or schedule.get("denoise")!=1.0 or video.get("fps")!=24.0:
        raise CreativeError("LATENT_PROFILE","Perfil original fora da qualificação.",409)
    names={}
    for kind,(field,folder,expected) in MODELS.items():
        name=graph[one(graph,kind)]["inputs"].get(field)
        if name!=expected: raise CreativeError("LATENT_MODEL","Modelo original fora da qualificação.",409)
        names[kind]={"name":name,"folder":folder}
    return {"width":1088,"height":608,"frames":cond["length"],"fps":24,
        "seed":graph[one(graph,"RandomNoise")]["inputs"]["noise_seed"],
        "conditioning_hash":digest(cond),"models":names}


def fingerprint_source(graph, model_root, runtime_version):
    """Record before submission; cache hashes only for unchanged local file stats."""
    contract=source_contract(graph)
    if runtime_version != "0.34.2":
        raise CreativeError("LATENT_RUNTIME", "Runtime fora da qualificação de latent.",409)
    fingerprints={}
    for kind,model in contract["models"].items():
        path=(Path(model_root)/model["folder"]/model["name"]).resolve(strict=True)
        stat=path.stat(); key=(str(path),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)
        sha=_HASH_CACHE.get(key)
        if sha is None:
            sha=file_hash(path); _HASH_CACHE[key]=sha
        fingerprints[kind]={"path":str(path),"sha256":sha,"bytes":stat.st_size}
    return {"contract":contract,"models":fingerprints,"engine_version":"ComfyUI-"+runtime_version,
        "capture":"BEFORE_PROMPT_SUBMISSION"}


def refinement_graph(source, latent_name, *, prefix="creative_os/hq", width=1536, height=864):
    source_contract(source)
    if Path(latent_name).name!=latent_name or not latent_name.endswith('.latent') or any(c in latent_name for c in ('/', '\\', ':')):
        raise CreativeError("LATENT_PATH","Entrada latent deve ser um basename gerenciado.")
    if (width,height)!=(1536,864): raise CreativeError("LATENT_TARGET","Alvo qualificado: 1536×864.")
    graph=copy.deepcopy(source)
    cond=one(graph,"MiniMaxH3ImageToVideo"); sampler=one(graph,"SamplerCustomAdvanced")
    split=one(graph,"LTXVSeparateAVLatent"); scheduler=one(graph,"BasicScheduler")
    graph[cond]["inputs"].update(width=width,height=height)
    graph[one(graph,"ImageScale")]["inputs"].update(width=width,height=height)
    graph[scheduler]["inputs"].update(steps=4,denoise=0.25)
    for k in list(graph):
        if graph[k]["class_type"] == "SaveLatent": del graph[k]
    names={}
    for suffix in ("load","upscale","empty_av","concat","save"):
        key="creative_hq_"+suffix
        while key in graph or key in names.values(): key+="_"
        names[suffix]=key
    graph[names["load"]]={"class_type":"LoadLatent","inputs":{"latent":latent_name}}
    graph[names["upscale"]]={"class_type":"MinimaxH3LatentUpscaler3D","inputs":{
        "latent":[names["load"],0],"model_name":"minimax_h3_latent_upscaler_3d_bf16.safetensors",
        "mode":"target dimensions","mode.width":width,"mode.height":height,"align":32,
        "enable_temporal_chunking":True,"force_unload":True,"device":"cuda","precision":"bf16"}}
    graph[names["empty_av"]]={"class_type":"LTXVSeparateAVLatent","inputs":{"av_latent":[cond,1]}}
    graph[names["concat"]]={"class_type":"LTXVConcatAVLatent","inputs":{
        "video_latent":[names["upscale"],0],"audio_latent":[names["empty_av"],1]}}
    graph[sampler]["inputs"]["latent_image"]=[names["concat"],0]
    graph[one(graph,"SaveVideo")]["inputs"]["filename_prefix"]=prefix
    graph[names["save"]]={"class_type":"SaveLatent","inputs":{"samples":[split,0],"filename_prefix":prefix+"_refined_latent"}}
    return graph


def package(service, generation_id, qualified_models):
    generation=service.sync(generation_id)
    if generation.get("engine_id")!="minimax_h3" or generation.get("status")!="done":
        raise CreativeError("LATENT_ENGINE","Exige geração H3 concluída.",409)
    artifacts=[a for a in generation["artifacts"] if a.get("kind")=="latent"]
    if len(artifacts)!=1: raise CreativeError("LATENT_NOT_CAPTURED","Exige exatamente um latent vinculado à geração.",409)
    artifact=artifacts[0]; path=safe_path(service.root,artifact["relative_path"])
    if file_hash(path)!=artifact["sha256"]: raise CreativeError("LATENT_CHANGED","Checksum do latent divergiu.",409)
    prompt=generation.get("prompt_id")
    from .ir import identifier
    identifier(prompt)
    archive=json.loads((service.root/'workflows'/(prompt+'.json')).read_text(encoding='utf-8'))
    if archive["workflow_hash"] != digest(archive["graph"]) or archive["workflow_hash"] != (generation.get("provenance") or {}).get("workflow_hash"):
        raise CreativeError("LATENT_PROVENANCE","Workflow original divergiu.",409)
    contract=source_contract(archive["graph"])
    captured=archive.get("model_fingerprints") or {}
    if captured.get("capture")!="BEFORE_PROMPT_SUBMISSION" or captured.get("contract")!=contract:
        raise CreativeError("LATENT_LEGACY","Sem fingerprints dos modelos capturados antes da geração; não qualificar retroativamente.",409)
    if captured.get("engine_version")!="ComfyUI-0.34.2" or any(
        captured.get("models",{}).get(kind,{}).get("sha256") != qualified_models.get(kind) for kind in MODELS):
        raise CreativeError("LATENT_QUALIFICATION","Pesos originais não correspondem à qualificação local.",409)
    from safetensors import safe_open
    with safe_open(str(path),framework='numpy') as handle:
        shape=list(handle.get_slice('latent_tensor').get_shape())
    if shape != [1,24,37,38,68]:
        raise CreativeError("LATENT_SHAPE","Tensor não corresponde ao perfil H3 capturado.",409)
    for model in captured["models"].values():
        if file_hash(model["path"])!=model["sha256"]:
            raise CreativeError("LATENT_MODELS_CHANGED","Modelo mudou desde a geração; finishing bloqueado.",409)
    record={"version":1,"generation_id":generation_id,"engine":"minimax_h3","artifact":artifact,
        "metadata":{**contract,"engine_version":captured["engine_version"],"workflow_hash":archive["workflow_hash"],
            "checkpoint_hash":captured["models"]["UNETLoader"]["sha256"],"vae_hash":captured["models"]["VAELoader"]["sha256"]},
        "state":"AVAILABLE","roundtrip_qualified":True,"roundtrip_scope":"H3 T2V VIDEO_ONLY",
        "compatible_finishing_profiles":["h3_latent_2stage_v1"]}
    key=digest([generation_id,artifact["sha256"],archive["workflow_hash"]])
    with service.store.transaction() as con:
        existing=service.store.read(con,'latents',key)
        if not existing: service.store.write(con,'latents',key,record,create=True)
    return path,archive,record


def profile(root):
    try:
        record=json.loads((Path(root)/'h3_latent_qualification_20260907.json').read_text(encoding='utf-8'))
        if record.get('technical_status')!='PASS' or not record.get('code_files'): return None
        if any(file_hash(p)!=sha for p,sha in record['code_files'].items()): return None
        return {'id':'h3_latent_2stage_v1','enabled':True,'default':False,'experimental':True,
            'width':1536,'height':864,'target_megapixels':1536*864/1e6,'refine_steps':4,'denoise':0.25,
            'method':'learned_latent_upscale_then_diffusion_refinement','latent_refinement':True,
            'requires_human_review':True,'requires_captured_latent':True,
            'scope':'H3 Production T2V, audio off, 124 frames; exact captured weights',
            'qualification':record}
    except (OSError,ValueError,KeyError): return None


def execute(service, ns, job, target):
    """Runs only inside Maestro's admitted HQ worker; Codex uses MCP instead."""
    import shutil
    import uuid
    if (target/'prompt.json').exists() or (target/'candidate.mp4').exists():
        raise CreativeError('HQ_ALREADY_SUBMITTED','Esta tentativa já possui prompt/saída; nenhum reenvio automático.',409)
    qualification=job['profile']['qualification']
    if any(file_hash(p)!=sha for p,sha in qualification['code_files'].items()):
        raise CreativeError('LATENT_CODE_CHANGED','Adapter/plugin mudou desde a qualificação.',409)
    version=(ns['_comfy_request']('/system_stats',timeout=15).get('system') or {}).get('comfyui_version')
    if version!='0.34.2': raise CreativeError('LATENT_RUNTIME','Runtime divergiu da qualificação.',409)
    if file_hash(qualification['upscaler']['path'])!=qualification['upscaler']['sha256']:
        raise CreativeError('LATENT_UPSCALER_CHANGED','Peso do upscaler mudou.',409)
    master=service.store.get('masters',job['master_id'])
    latent,archive,package_record=package(service,master['generation_id'],qualification['models'])
    name='creative_hq_'+job['id']+'.latent'
    input_path=Path(ns['COMFY_INPUT_DIR'])/name
    if input_path.exists() and file_hash(input_path)!=package_record['artifact']['sha256']:
        raise CreativeError('LATENT_INPUT_CONFLICT','Entrada HQ existente divergiu.',409)
    if not input_path.exists():
        temp=input_path.with_name('.'+uuid.uuid4().hex+'.tmp')
        shutil.copyfile(latent,temp)
        if file_hash(temp)!=package_record['artifact']['sha256']: raise CreativeError('LATENT_COPY','Cópia do latent divergiu.')
        temp.replace(input_path)
    graph=refinement_graph(archive['graph'],name,prefix='creative_os/hq/'+job['id'])
    (target/'workflow.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2),encoding='utf-8')
    def capture(prompt_id):
        # Persist identity before polling; interrupted jobs are never replayed.
        (target/'prompt.json').write_text(json.dumps({'prompt_id':prompt_id,'workflow_hash':digest(graph),
            'parent_generation_id':master['generation_id'],'latent_sha256':package_record['artifact']['sha256']}),encoding='utf-8')
    prompt_id,outputs=ns['_queue_comfy_workflow'](graph,timeout=7200,prompt_id_cb=capture,
        cancel_event=service.finishing.stop)
    videos=[o for o in outputs if o.get('kind')=='video']
    if len(videos)!=1: raise CreativeError('HQ_OUTPUT_COUNT','Refinamento deve entregar exatamente um vídeo.')
    candidate=target/'candidate.mp4'
    for output in outputs:
        if output.get('kind') not in {'video','latent'}: continue
        source=ns['_safe_comfy_output_path'](output.get('filename',''),output.get('subfolder',''),output.get('type','output'))
        if not source: raise CreativeError('HQ_OUTPUT_PATH','Saída Comfy não resolvida.')
        destination=candidate if output['kind']=='video' else target/'refined.latent'
        if destination.exists(): raise CreativeError('HQ_OUTPUT_EXISTS','Candidato anterior preservado; use outra tentativa.')
        shutil.copyfile(source,destination)
        if file_hash(source)!=file_hash(destination): raise CreativeError('HQ_COPY','Checksum da saída divergiu.')
    (target/'latent_package.json').write_text(json.dumps(package_record,indent=2),encoding='utf-8')
    from fractions import Fraction
    from .evaluation import inspect_video
    inspected=inspect_video(candidate)
    stream=inspected.get('video') or {}
    if (not inspected['pass'] or inspected.get('audio_present')
        or (stream.get('width'),stream.get('height'))!=(1536,864)
        or int(stream.get('nb_read_frames',0))!=package_record['metadata']['frames']
        or float(Fraction(stream.get('r_frame_rate','0')))!=24.0):
        raise CreativeError('HQ_MEDIA_CONTRACT','Candidato não preservou resolução, frames, FPS ou política de áudio.')
    return candidate
