"""Authenticated by the Studio application's existing API boundary."""
from fastapi import APIRouter, Body, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from starlette.concurrency import run_in_threadpool
from . import VERSION
from .ir import CreativeError
from .evaluation import evaluate, verdict
from .assets import safe_path, file_hash
from .planning import save_bible, repair_plan, execute_repair, continuity, director
from .benchmark import register as register_benchmark, matrix as benchmark_matrix
from .direction import status as direction_status, advance, assemble, review_assembly


def invoke(action, *args, **kwargs):
    try: return action(*args, **kwargs)
    except CreativeError as exc:
        return JSONResponse(status_code=exc.status, content={"ok":False,"error":{"code":exc.code,"message":str(exc)}})
    except (ValueError, TypeError, KeyError) as exc:
        return JSONResponse(status_code=422, content={"ok":False,"error":{"code":"INVALID_REQUEST","message":str(exc)}})


def create_router(service):
    router = APIRouter(prefix="/api/creative", tags=["Creative OS"])

    @router.post('/generations/{generation_id}/semantic-review', status_code=202)
    def semantic_review(generation_id: str, payload: dict = Body(...)):
        from .semantic_jobs import start
        return invoke(start, service, generation_id, payload.get('artifact_sha256'), payload.get('idempotency_key'))

    @router.get('/semantic-jobs')
    def semantic_jobs(): return service.store.list('semantic_jobs')

    @router.get('/semantic-jobs/{job_id}')
    def semantic_job(job_id: str):
        from .semantic_jobs import sync
        return invoke(sync, service, job_id)

    @router.post('/semantic-jobs/{job_id}/cancel')
    def semantic_cancel(job_id: str):
        return invoke(lambda: service.bridge.cancel(service.store.get('semantic_jobs', job_id)['job_id']))

    @router.get("/health")
    def health():
        return {"ok": True, "version":VERSION,"build_hash":getattr(service,"build_hash",None),
                "existing_engine_selection_preserved":True,"workflow_sampling_preserved":True,
                "maestro_transport":service.bridge.transport,"codex_transport":"mcp_only"}

    @router.get("/capabilities")
    def capabilities(): return invoke(service.bridge.capabilities)

    @router.post('/control-assets')
    async def control_asset(file: UploadFile = File(...)):
        from .fun_control_jobs import import_control
        data=await file.read(512*1024*1024+1)
        return await run_in_threadpool(invoke,import_control,service,data,file.filename)

    @router.post('/shots/{shot_id}/control-generate',status_code=202)
    def control_generate(shot_id: str,payload: dict = Body(...)):
        from .fun_control_jobs import generate
        return invoke(generate,service,shot_id,payload.get('idempotency_key'),asset_id=payload.get('asset_id'),
            control_kind=payload.get('control_kind'),strength=payload.get('strength',1.0),seed=payload.get('seed'))

    @router.post('/shots/{shot_id}/timeline-plan')
    def timeline_plan(shot_id: str,payload: dict = Body(...)):
        from .timeline_jobs import prepare
        return invoke(prepare,service,shot_id,seed=payload.get('seed'),segment_count=payload.get('segment_count',2))

    @router.post('/shots/{shot_id}/timeline-generate',status_code=202)
    def timeline_generate(shot_id: str,payload: dict = Body(...)):
        from .timeline_jobs import generate
        return invoke(generate,service,shot_id,payload.get('idempotency_key'),seed=payload.get('seed'),
            segment_count=payload.get('segment_count',2))

    @router.post("/motion-plans")
    def motion_plan(payload: dict = Body(...)):
        from .motion_jobs import prepare
        return invoke(prepare,service,payload.get("shot_ids"),seed=payload.get("seed"),
            profile=payload.get("profile","h3_production"),selected=payload.get("selected"),
            motion_context=payload.get("motion_context",True))

    @router.post("/motion-plans/{plan_id}/generate",status_code=202)
    def motion_generate(plan_id: str,payload: dict = Body(...)):
        from .motion_jobs import generate
        return invoke(generate,service,plan_id,payload.get("idempotency_key"))

    @router.get("/motion-batches/{batch_id}")
    def motion_batch(batch_id: str):
        from .motion_jobs import sync
        return invoke(sync,service,batch_id)

    @router.post("/motion-batches/{batch_id}/cancel")
    def motion_cancel(batch_id: str):
        return invoke(lambda: service.bridge.cancel(service.store.get("motion_batches",batch_id)["job_id"]))

    @router.post("/shots/{shot_id}/prompt-proposals")
    def prompt_proposal(shot_id: str, payload: dict = Body(...)):
        from .prompt_proposals import propose
        return invoke(propose, service, shot_id, payload.get("text"), payload.get("provenance"))

    @router.post('/shots/{shot_id}/rewrite',status_code=202)
    def rewrite(shot_id: str,payload: dict = Body(...)):
        from .rewriter_jobs import start
        return invoke(start,service,shot_id,payload.get('idempotency_key'),payload.get('seed'))

    @router.get('/rewriter-jobs/{job_id}')
    def rewriter_job(job_id: str):
        from .rewriter_jobs import sync
        return invoke(sync,service,job_id)

    @router.post('/rewriter-jobs/{job_id}/cancel')
    def cancel_rewriter(job_id: str):
        return invoke(lambda: service.bridge.cancel(service.store.get('rewriter_jobs',job_id)['job_id']))

    @router.get('/prompt-proposals/{proposal_id}')
    def get_proposal(proposal_id: str): return invoke(service.store.get,'prompt_proposals',proposal_id)

    @router.post("/prompt-proposals/{proposal_id}/verdict")
    def prompt_verdict(proposal_id: str, payload: dict = Body(...)):
        from .prompt_proposals import review
        return invoke(review, service, proposal_id, payload.get("decision"), payload.get("suggestion_hash"))

    @router.post("/prompt-proposals/{proposal_id}/apply")
    def apply_prompt_proposal(proposal_id: str):
        from .prompt_proposals import apply
        return invoke(apply, service, proposal_id)

    @router.post("/shots")
    def save_shot(payload: dict = Body(...)):
        return invoke(service.save_shot, payload.get("ir",payload), payload.get("expected_revision"))

    @router.get("/shots")
    def shots(): return service.store.list("shots")

    @router.get("/shots/{shot_id}")
    def shot(shot_id: str): return invoke(service.store.get,"shots",shot_id)

    @router.post("/shots/{shot_id}/analyze")
    @router.post("/shots/{shot_id}/route")
    def analyze(shot_id: str): return invoke(service.analyze,shot_id)

    @router.post("/shots/{shot_id}/generate",status_code=202)
    def generate(shot_id: str,payload: dict = Body(...)):
        return invoke(service.generate,shot_id,payload.get("bindings",{}),payload.get("idempotency_key"))

    @router.get("/generations")
    def generations(): return service.store.list("generations")

    @router.post("/jobs/{job_id}/attach")
    def attach(job_id: str,payload: dict = Body(default={})):
        return invoke(service.attach_job,job_id,payload.get("project_id","maestro_manual"))

    @router.get("/generations/{generation_id}")
    def generation(generation_id: str): return invoke(service.sync,generation_id)

    @router.get("/generations/{generation_id}/lineage")
    def lineage(generation_id: str): return invoke(service.store.history,"generations",generation_id)

    @router.post("/generations/{generation_id}/cancel")
    def cancel(generation_id: str):
        return invoke(lambda: service.bridge.cancel(service.store.get("generations",generation_id)["job_id"]))

    @router.get("/generations/{generation_id}/artifacts/{index}")
    def artifact(generation_id: str,index: int):
        return invoke(media,"generations",generation_id,index)

    def media(kind,record_id,index):
        record = service.store.get(kind,record_id)
        if index < 0 or index >= len(record["artifacts"]): raise CreativeError("NOT_FOUND","Artefato ausente.",404)
        entry=record["artifacts"][index]
        path=safe_path(service.root,entry["relative_path"])
        if file_hash(path) != entry["sha256"]: raise CreativeError("ARTIFACT_CHANGED","Artefato alterado.",409)
        return FileResponse(path,headers={"Cache-Control":"private, no-store"})

    @router.post("/generations/{generation_id}/evaluate")
    def evaluation(generation_id: str,payload: dict = Body(default={})):
        return invoke(evaluate,service,generation_id,payload.get("observations"))

    @router.post("/generations/{generation_id}/verdict")
    def human_verdict(generation_id: str,payload: dict = Body(...)):
        return invoke(verdict,service,generation_id,payload.get("decision"),payload.get("artifact_sha256"),payload.get("notes",""))

    @router.post("/assets")
    def asset(payload: dict = Body(...)):
        return invoke(service.assets.register,payload.get("project_id"),payload.get("relative_path"),payload.get("role"))

    @router.get("/projects/{project_id}/reference-sheet")
    def reference_sheet(project_id: str): return invoke(service.assets.reference_sheet,project_id)

    @router.get("/projects/{project_id}/bibles")
    def bibles(project_id: str):
        return [r for r in service.store.list("bibles",500) if r["project_id"]==project_id]

    @router.post("/projects/{project_id}/bibles/{kind}/{item_id}")
    def bible(project_id: str,kind: str,item_id: str,payload: dict = Body(...)):
        return invoke(save_bible,service,project_id,kind,item_id,payload.get("content",{}),payload.get("expected_revision"))

    @router.post("/generations/{generation_id}/repairs")
    def repair(generation_id: str,payload: dict = Body(...)):
        return invoke(repair_plan,service,generation_id,payload)

    @router.get("/repairs")
    def repairs(): return service.store.list("repairs")

    @router.post("/repairs/{repair_id}/execute",status_code=202)
    def repair_execute(repair_id: str): return invoke(execute_repair,service,repair_id)

    @router.post("/continuity")
    def continuity_review(payload: dict = Body(...)):
        return invoke(continuity,service,payload.get("left"),payload.get("right"),payload.get("observations"))

    @router.post("/projects/{project_id}/direction")
    def direction(project_id: str,payload: dict = Body(...)):
        return invoke(director,service,project_id,payload.get("shot_ids"))

    @router.get("/directions/{direction_id}")
    def direction_read(direction_id: str): return invoke(direction_status,service,direction_id)

    @router.post("/directions/{direction_id}/advance",status_code=202)
    def direction_advance(direction_id: str,payload: dict = Body(...)):
        return invoke(advance,service,direction_id,payload.get("bindings",{}),payload.get("idempotency_key"))

    @router.post("/directions/{direction_id}/assemble",status_code=202)
    def direction_assemble(direction_id: str,payload: dict = Body(...)):
        return invoke(assemble,service,direction_id,payload.get("idempotency_key"))

    @router.get("/assemblies/{assembly_id}")
    def assembly_read(assembly_id: str): return invoke(service.store.get,"assemblies",assembly_id)

    @router.get("/assemblies/{assembly_id}/artifacts/{index}")
    def assembly_media(assembly_id: str,index: int): return invoke(media,"assemblies",assembly_id,index)

    @router.post("/assemblies/{assembly_id}/verdict")
    def assembly_review(assembly_id: str,payload: dict = Body(...)):
        return invoke(review_assembly,service,assembly_id,payload.get("decision"),payload.get("artifact_sha256"))

    @router.get("/benchmarks")
    def benchmarks(): return invoke(benchmark_matrix,service)

    @router.post("/generations/{generation_id}/benchmark")
    def benchmark(generation_id: str,payload: dict = Body(...)):
        return invoke(register_benchmark,service,generation_id,payload.get("class"))

    @router.get("/masters")
    def masters(): return service.store.list("masters")

    @router.post("/generations/{generation_id}/latents")
    def latent(generation_id: str,payload: dict = Body(...)):
        return invoke(service.finishing.latent,generation_id,payload)

    @router.get("/hq")
    def hq_status(): return invoke(service.finishing.status)

    @router.post("/hq",status_code=202)
    def hq_enqueue(payload: dict = Body(...)):
        return invoke(service.finishing.enqueue,payload.get("master_id"),payload.get("profile_id"),payload.get("idempotency_key"))

    @router.post("/hq/resume")
    def hq_resume():
        service.finishing.start(resume=True)
        return {"ok":True,"replays_interrupted_jobs":False}

    @router.post("/hq/{job_id}/cancel")
    def hq_cancel(job_id: str): return invoke(service.finishing.cancel,job_id)

    @router.post("/hq/{job_id}/verdict")
    def hq_verdict(job_id: str,payload: dict = Body(...)):
        return invoke(service.finishing.review,job_id,payload.get("decision"),payload.get("artifact_sha256"))

    @router.get("/hq/{job_id}/artifacts/{index}")
    def hq_artifact(job_id: str,index: int): return invoke(media,"hq_jobs",job_id,index)

    return router
