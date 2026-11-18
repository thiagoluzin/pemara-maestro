"""Ordered execution and assembly of reviewed shots over the existing assembler."""
import shutil
import threading
import os
from pathlib import Path
from .assets import file_hash,safe_path
from .ir import CreativeError,digest,identifier


def status(service,direction_id):
    plan=service.store.get("directions",direction_id)
    steps=[]
    previous_approved=True
    for step in plan["steps"]:
        shot=service.store.get("shots",step["shot_id"])
        matching=service.store.where("generations","shot_id",step["shot_id"])
        latest=max(matching,key=lambda g:g["created_at"]) if matching else None
        if latest: latest=service.sync(latest["id"])
        changed=shot["ir_hash"] != step["ir_hash"]
        approved=bool(latest and latest.get("human_verdict")=="approved" and digest(latest["ir"])==step["ir_hash"] and not changed)
        state="SHOT_CHANGED" if changed else "APPROVED" if approved else latest["status"] if latest else "PLANNED"
        steps.append({**step,"state":state,"generation_id":latest["id"] if latest else None,
            "can_generate":previous_approved and not latest and not changed,"human_approved":approved})
        previous_approved=previous_approved and approved
    return {**plan,"steps":steps,"all_sources_approved":previous_approved}


def advance(service,direction_id,bindings,key):
    identifier(key)
    plan=status(service,direction_id)
    claim=plan.get("submission_claim") or {}
    if claim.get("key")==key:
        return service.store.get("generations",claim["generation_id"])
    step=next((s for s in plan["steps"] if not s["human_approved"]),None)
    if step is None: return {"status":"READY_FOR_CONTINUITY_AND_ASSEMBLY","direction_id":direction_id}
    if not step["can_generate"]:
        raise CreativeError("DIRECTION_GATE", "Aguarde ou revise o plano atual antes de avançar.",409)
    with service.store.transaction() as con:
        current=service.store.read(con,"directions",direction_id)
        if (current.get("submission_claim") or {}).get("shot_id")==step["shot_id"]:
            raise CreativeError("DIRECTION_SUBMISSION_RESERVED", "Envio deste plano já reservado; consulte a geração antes de repetir.",409)
        service.store.write(con,"directions",direction_id,{**current,"submission_claim":{"shot_id":step["shot_id"],"key":key,
            "generation_id":digest([step["shot_id"],key])}},expected=plan["revision"])
    return service.generate(step["shot_id"],bindings,key,expected_ir_hash=step["ir_hash"])


def assembly_sources(service,direction_id):
    plan=status(service,direction_id)
    if not plan["all_sources_approved"]: raise CreativeError("UNAPPROVED_SEQUENCE", "Todos os planos precisam de aprovação humana vigente.",409)
    sources=[]
    for step in plan["steps"]:
        master,path=service.finishing.master(step["generation_id"])
        sources.append({"generation_id":step["generation_id"],"master":master,"path":str(path)})
    reviews=service.store.list("continuity",500)
    for left,right in zip(sources,sources[1:]):
        review=next((r for r in reviews if r["left"]==left["generation_id"] and r["right"]==right["generation_id"]),None)
        if not review or any(v["state"] != "match" for v in review["dimensions"].values()):
            raise CreativeError("CONTINUITY_REVIEW_REQUIRED", "Revise cada fronteira antes da montagem.",409)
        if left["master"]["artifact"]["sha256"] not in review["left_hashes"] or right["master"]["artifact"]["sha256"] not in review["right_hashes"]:
            raise CreativeError("CONTINUITY_CHANGED", "A revisão não corresponde aos masters atuais.",409)
    return plan,sources


def assemble(service,direction_id,key):
    identifier(key)
    plan,sources=assembly_sources(service,direction_id)
    job_id=digest([direction_id,key])
    fingerprint=digest([s["master"]["artifact"]["sha256"] for s in sources])
    with service.store.transaction() as con:
        previous=service.store.read(con,"assemblies",job_id)
        if previous:
            if previous["source_fingerprint"]!=fingerprint: raise CreativeError("IDEMPOTENCY_CONFLICT", "Montagem já vinculada a outras fontes.",409)
            return previous
        record=service.store.write(con,"assemblies",job_id,{"direction_id":direction_id,"source_fingerprint":fingerprint,
            "status":"queued","worker_pid":os.getpid(),"source_generations":[s["generation_id"] for s in sources],"artifacts":[],"human_verdict":None},create=True)

    def worker():
        current=record
        try:
            with service.finishing.admission({"id":job_id}):
                assembly_sources(service,direction_id)
                current=service.store.put("assemblies",{**current,"status":"running"},entity_id=job_id,expected=current["revision"],create=False)
                target=service.root/"assemblies"/job_id
                target.mkdir(parents=True,exist_ok=True)
                inputs=[]
                from .evaluation import inspect_video
                for i,source in enumerate(sources):
                    original=Path(source["path"])
                    path=target/(f"source_{i:03d}"+original.suffix)
                    shutil.copyfile(original,path)
                    if file_hash(path)!=source["master"]["artifact"]["sha256"]: raise CreativeError("SOURCE_CHANGED", "Fonte mudou durante a cópia.",409)
                    inputs.append({"takeId":source["generation_id"],"videoFile":path.name,
                        "audioEmbedded":inspect_video(path).get("audio_present",False)})
                result=service.assembler(target,sources=inputs,source_fingerprint=fingerprint,job_id=job_id[:32])
                assembly_sources(service,direction_id)
                artifacts=[]
                for field in ("file","review_file"):
                    path=safe_path(target,result[field])
                    artifacts.append({"relative_path":path.relative_to(service.root).as_posix(),"kind":"video","sha256":file_hash(path),"role":field})
                service.store.put("assemblies",{**current,"status":"PENDING_HUMAN_REVIEW","artifacts":artifacts,"technical":result},entity_id=job_id,expected=current["revision"],create=False)
        except Exception as exc:
            service.store.put("assemblies",{**current,"status":"error","error":str(exc),"automatic_retry":False},entity_id=job_id,expected=current["revision"],create=False)
    threading.Thread(target=worker,name="creative-assembly",daemon=True).start()
    return record


def review_assembly(service,assembly_id,decision,sha):
    if decision not in {"approved","rejected"}: raise CreativeError("INVALID_VERDICT", "Decisão inválida.")
    record=service.store.get("assemblies",assembly_id)
    if record["status"] not in {"PENDING_HUMAN_REVIEW","APPROVED","REJECTED"}: raise CreativeError("ASSEMBLY_NOT_READY", "Montagem não concluída.",409)
    assembly_sources(service,record["direction_id"])
    artifact=next((a for a in record["artifacts"] if a.get("role")=="file" and a["sha256"]==sha),None)
    if not artifact or file_hash(safe_path(service.root,artifact["relative_path"]))!=sha:
        raise CreativeError("ARTIFACT_CHANGED", "Escolha o master exato da montagem.",409)
    return service.store.put("assemblies",{**record,"status":decision.upper(),"human_verdict":decision},entity_id=assembly_id,expected=record["revision"],create=False)
