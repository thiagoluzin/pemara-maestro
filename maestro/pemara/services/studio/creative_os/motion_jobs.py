"""Durable multi-shot plans over Maestro's existing autonomous generation queue."""
from .adapters import H3Adapter
from .ir import CreativeError, digest, identifier
from .motion_director import compile_motion


def qualification(root, nodes, runtime):
    import json
    from pathlib import Path
    from .assets import file_hash
    try:
        record=json.loads((Path(root)/"motion_qualification_20260907.json").read_text(encoding="utf-8"))
        if record.get("technical_status") != "PASS": return None
        if (runtime.get("system") or {}).get("comfyui_version") != record["comfyui_version"]: return None
        if "MiniMaxH3MotionDirector" not in nodes: return None
        if not record.get("files") or any(file_hash(p) != sha for p,sha in record["files"].items()): return None
        return {"integrated":True,"enabled":True,"experimental":True,"auto_route":False,
            "scope":"H3 Production T2V, audio off; segment outputs and selective rerun without saved predecessor",
            "technical_evidence":record["prompt_ids"],"requires_human_review":True}
    except (OSError,ValueError,KeyError): return None


def prepare(service, shot_ids, *, seed, profile="h3_production", selected=None, motion_context=True):
    if not isinstance(shot_ids,list) or not 2 <= len(shot_ids) <= 12:
        raise CreativeError("MOTION_SHOT_COUNT", "Informe 2–12 planos salvos.")
    records = [service.store.get("shots",identifier(key)) for key in shot_ids]
    compiled = compile_motion([r["ir"] for r in records],seed=seed,profile=profile,
        selected=selected,motion_context=motion_context)
    data = {"shot_ids":shot_ids,"source_ir_hashes":[r["ir_hash"] for r in records],
        "shots":[r["ir"] for r in records],"seed":seed,"profile":profile,
        "selected":selected,"motion_context":motion_context,"compiled":compiled,
        "state":"PREPARED","generation_submitted":False}
    key=digest(data)
    with service.store.transaction() as con:
        old=service.store.read(con,"motion_plans",key)
        return old or service.store.write(con,"motion_plans",key,data,create=True)


def generate(service, plan_id, key):
    identifier(key)
    plan=service.store.get("motion_plans",plan_id)
    batch_id=digest([plan_id,key])
    with service.store.transaction() as con:
        old=service.store.read(con,"motion_batches",batch_id)
        if old: return old  # Includes uncertain/failed submissions; never replay.
    caps=service.bridge.capabilities()
    if not caps.get("optional",{}).get("h3_motion_director",{}).get("enabled"):
        raise CreativeError("MOTION_UNAVAILABLE", "Adapter Motion Director ainda não qualificado neste runtime.",409)
    if plan["profile"] != "h3_production" or plan["compiled"]["timeline"]["output"]["creativeOsNativeAudio"]:
        raise CreativeError("MOTION_SCOPE", "Qualificação atual: H3 Production T2V sem áudio.",409)
    for shot_id, expected in zip(plan["shot_ids"],plan["source_ir_hashes"]):
        if service.store.get("shots",shot_id)["ir_hash"] != expected:
            raise CreativeError("SHOT_CHANGED", "Plano foi editado; prepare novamente antes de gerar.",409)
    spec=H3Adapter().build_job(plan["shots"][0],{"seed":plan["seed"],"h3_quality_profile":plan["profile"]})
    spec["creative_motion_request"]={"shots":plan["shots"],"selected":plan["selected"],"motion_context":plan["motion_context"]}
    if service.bridge.prepare: spec=service.bridge.prepare(spec,{}, {})
    with service.store.transaction() as con:
        old=service.store.read(con,"motion_batches",batch_id)
        if old: return old
        batch=service.store.write(con,"motion_batches",batch_id,{"plan_id":plan_id,
            "state":"SUBMITTING","job_id":None,"generation_ids":[],"request_spec":spec,
            "transport":service.bridge.transport,"restart_policy":"NO_BLIND_REPLAY",
            "cancel_scope":"ALL_SEGMENTS_IN_THIS_BATCH"},create=True)
    try:
        job_id=service.bridge.submit(spec)
    except Exception as exc:
        service.store.put("motion_batches",{**batch,"state":"SUBMISSION_FAILED","error":str(exc)},
            entity_id=batch_id,expected=batch["revision"],create=False)
        raise
    return service.store.put("motion_batches",{**batch,"job_id":job_id,"state":"QUEUED"},
        entity_id=batch_id,expected=batch["revision"],create=False)


def sync(service,batch_id):
    batch=service.store.get("motion_batches",batch_id)
    if not batch.get("job_id") or batch["state"] in {"DONE","ERROR","CANCELED"}: return batch
    job=service.bridge.status(batch["job_id"])
    if not job: raise CreativeError("JOB_UNKNOWN","Job ausente; nenhum reenvio automático.",409)
    state=str(job.get("status", "queued")).upper()
    if state != "DONE":
        return service.store.put("motion_batches",{**batch,"state":state,"error":job.get("error")},
            entity_id=batch_id,expected=batch["revision"],create=False)
    plan=service.store.get("motion_plans",batch["plan_id"])
    observed=(job.get("result") or {}).get("creative_motion") or {}
    if any(observed.get(k) != plan["compiled"][k] for k in ("source_ir_hashes","selected_shots","workflow_hash")):
        raise CreativeError("MOTION_PROVENANCE", "Job não corresponde ao plano compilado; saídas não vinculadas.",409)
    outputs=(job.get("result") or {}).get("outputs",[])
    videos=[i for i,o in enumerate(outputs) if o.get("kind")=="video"]
    selected=plan["selected"] if plan["selected"] is not None else list(range(len(plan["shots"])))
    selected=sorted(set(selected))
    if len(videos) != len(selected):
        raise CreativeError("MOTION_OUTPUT_COUNT","Número de vídeos diverge dos planos selecionados; nenhum vínculo adivinhado.",409)
    ids=[]
    with service.store.transaction() as con:
        current=service.store.read(con,"motion_batches",batch_id)
        if current["state"] == "DONE": return current
        for shot_index, output_index in zip(selected,videos):
            ir=plan["shots"][shot_index]
            generation_id=digest([batch_id,ir["shot_id"]])
            service.store.write(con,"generations",generation_id,{"shot_id":plan["shot_ids"][shot_index],
                "project_id":ir["project_id"],"ir":ir,"engine_id":"minimax_h3","job_id":batch["job_id"],
                "request_spec":batch["request_spec"],"request_hash":digest(batch["request_spec"]),
                "parent_generation_id":None,"status":"queued","human_verdict":None,"artifacts":[],
                "transport":batch["transport"],"source":"motion_director","motion_batch_id":batch_id,
                "output_indices":[output_index],"actual_seed_override":None,
                "seed_policy":"BASE_SEED_IN_WORKFLOW; SEGMENT_ACTUAL_SEED_NOT_EXPORTED",
                "cancel_scope":"ALL_SEGMENTS_IN_THIS_BATCH"},create=True)
            ids.append(generation_id)
        return service.store.write(con,"motion_batches",batch_id,{**current,"state":"DONE","generation_ids":ids},expected=current["revision"])
