"""Reuse the installed Maestro neural finishing pipeline inside its backend worker."""
import json
import subprocess
import os
from contextlib import contextmanager
from pathlib import Path
from .assets import file_hash
from .finishing import Finishing


def install_finishing(service, ns):
    profiles = {}
    for profile_id,w,h,path in (("neural_fhd",1920,1080,ns["_VIDEO_UPSCALE_PROFILE"]),
                                ("neural_vertical",1080,1920,ns["_VIDEO_UPSCALE_VERTICAL_PROFILE"])):
        available=Path(path).is_file() and ns["_VIDEO_UPSCALE_TOOL"].is_file()
        profiles[profile_id]={"id":profile_id,"enabled":available,"width":w,"height":h,
            "method":"existing_realesrgan_pixel_finishing","latent_refinement":False,
            "profile_sha256":file_hash(path) if available else None,"requires_human_review":True}
    profiles["h3_latent_2stage_v1"]={"id":"h3_latent_2stage_v1","enabled":False,
        "method":"learned_latent_refinement","reason":"H3_UPSCALER_ADAPTER_AND_ROUNDTRIP_BENCHMARK_MISSING",
        "target_megapixels":1.5,"refine_steps":4,"experimental":True}
    from .h3_latent_finishing import profile as latent_profile
    qualified_latent=latent_profile(service.root)
    if qualified_latent: profiles['h3_latent_2stage_v1']=qualified_latent

    @contextmanager
    def admission(job):
        # Generation work has priority over deferred finishing.
        for status in ("queued", "running", "canceling"):
            if ns["_GEN_JOB_STORE"].list(status=status,page_size=1)["total"]:
                raise BlockingIOError("Geração do Maestro tem prioridade.")
        lease=ns["_GPU_LEASE_REGISTRY"]
        try:
            lease.acquire(owner="creative_os",operation="deferred_hq",job_id=job["id"])
        except ns["GpuLeaseBusy"] as exc: raise BlockingIOError(str(exc)) from exc
        locked=False
        try:
            locked=ns["_VIDEO_UPSCALE_LOCK"].acquire(blocking=False)
            if not locked: raise BlockingIOError("Acabamento existente está ativo.")
            ns["_VIDEO_UPSCALE_GATE"].set()
            queue=ns["_comfy_request"]("/queue",timeout=10)
            if queue.get("queue_running") or queue.get("queue_pending"): raise BlockingIOError("ComfyUI ocupado.")
            yield
        finally:
            if locked:
                ns["_VIDEO_UPSCALE_GATE"].clear()
                ns["_VIDEO_UPSCALE_LOCK"].release()
            lease.release(job["id"])

    def execute(job,source,target):
        if job['profile_id']=='h3_latent_2stage_v1':
            from .h3_latent_finishing import execute as execute_latent
            return execute_latent(service,ns,job,target)
        spec={"source":str(source),"outputDir":str(target),"workDir":str(target/"work"),"name":"candidate",
              "targetWidth":job["profile"]["width"],"targetHeight":job["profile"]["height"]}
        _,profile_path,_,_=ns["_upscale_profile_for_spec"](spec)
        if file_hash(profile_path) != job["profile"]["profile_sha256"]:
            raise ValueError("Perfil de acabamento mudou desde o enqueue.")
        command=ns["_build_upscale_command"](spec,source_sha256=job["source_sha256"],dry_run=True)
        fingerprint,required=ns["_run_upscale_plan"](command)
        ns["_upscale_disk_preflight"](spec,required_work_bytes=required)
        command=ns["_build_upscale_command"](spec,source_sha256=job["source_sha256"],dry_run=False)
        command=[command[0],str(Path(__file__).with_name("hq_process.py")),"--lease",str(ns["_GPU_LEASE_REGISTRY"].path),
                 "--job",job["id"],"--parent",str(os.getpid()),"--",*command[1:]]
        with (target/"worker.log").open("wb") as log:
            result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode: raise RuntimeError("Pipeline de acabamento falhou; consulte worker.log.")
        for sidecar_path in target.glob("*.json"):
            sidecar=json.loads(sidecar_path.read_text(encoding="utf-8"))
            candidate=Path(str(sidecar.get("candidate", "")))
            if candidate.is_file() and candidate.resolve().parent == target.resolve() and file_hash(candidate).upper() == str(sidecar.get("candidate_sha256","")).upper():
                return candidate
        raise RuntimeError("Pipeline não entregou candidato com checksum válido.")

    def cleanup():
        queue=ns["_comfy_request"]("/queue",timeout=10)
        if queue.get("queue_running") or queue.get("queue_pending"): return
        ns["_comfy_request"]("/free",{"unload_models":True,"free_memory":True},timeout=30)

    finishing=Finishing(service,profiles,execute,lambda:ns["_comfy_request"]("/system_stats",timeout=15),admission,cleanup)
    service.finishing=finishing
    ns["_STARTUP_HANDLERS"].append(finishing.recover)
    ns["_SHUTDOWN_HANDLERS"].append(finishing.stop.set)
    return finishing
