"""Studio integration. These callbacks run in Maestro, never as a Codex MCP bypass."""
import json
import uuid
from pathlib import Path
from .bridge import Bridge, normalize_save_video
from .ir import CreativeError, identifier, digest
from .routing import capabilities
from .service import CreativeService
from .api import create_router


def archive_workflow(root, prompt_id, graph, model_fingerprints=None):
    identifier(prompt_id)
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    record = {"prompt_id": prompt_id, "workflow_hash": digest(graph), "graph": graph}
    if model_fingerprints is not None: record["model_fingerprints"] = model_fingerprints
    path = root / (prompt_id + ".json")
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8"))["workflow_hash"] != record["workflow_hash"]:
            raise CreativeError("WORKFLOW_CONFLICT", "Prompt já possui outro workflow.", 409)
    else:
        temp = root / (uuid.uuid4().hex + ".tmp")
        temp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        temp.replace(path)
    return record


def export_graph(graph, schema):
    required = schema.get("SaveVideo", {}).get("input", {}).get("required", {})
    fmt = required.get("format", [])
    result = normalize_save_video(graph, bool(fmt and fmt[0] == "COMFY_DYNAMICCOMBO_V3"))
    # Retain the sampled video latent for deferred finishing. Do not serialize
    # the nested AV tensor: SaveLatent supports the separated video tensor.
    if any(n.get("class_type") in {"MiniMaxH3ImageToVideo", "MiniMaxH3ReferenceToVideo"} for n in result.values()):
        exporters = [n for n in result.values() if n.get("class_type") == "SaveVideo"]
        if exporters:
            prefix = exporters[0]["inputs"].get("filename_prefix", "creative_os/h3")
            for split_id, node in list(result.items()):
                if node.get("class_type") != "LTXVSeparateAVLatent": continue
                samples = [split_id, 0]
                if any(n.get("class_type") == "SaveLatent" and n.get("inputs",{}).get("samples") == samples for n in result.values()): continue
                key = "creative_os_video_latent_" + str(split_id)
                while key in result: key += "_"
                result[key] = {"class_type":"SaveLatent", "inputs":{"samples":samples,
                    "filename_prefix":str(prefix) + "_video_latent"}}
    return result


def install(ns):
    root = Path(ns["BASE_DIR"]) / "dados" / "creative_os"

    def caps():
        try:
            stats = ns["_comfy_request"]("/system_stats", timeout=10)
            nodes = ns["_comfy_request"]("/object_info", timeout=30)
            registry = ns["_video_engine_registry_live"](comfy_online=True).describe()
            result = capabilities(registry["engines"], nodes, runtime=stats)
            from .motion_jobs import qualification
            motion = qualification(root,nodes,stats)
            if motion: result["optional"]["h3_motion_director"].update(motion,reason="PINNED_LOCAL_TECHNICAL_BENCHMARK_PASS")
            from .h3_rewriter import qualification as rewriter_qualification
            rewriter = rewriter_qualification(root,nodes,stats)
            if rewriter: result['optional']['h3_prompt_rewriter'].update(rewriter)
            from .timeline_jobs import qualification as timeline_qualification
            timeline = timeline_qualification(root,nodes,stats)
            if timeline: result['optional']['h3_timeline_director'].update(timeline)
            from .fun_control import qualification as control_qualification
            control = control_qualification(root,nodes,stats)
            if control: result['optional']['h3_fun_control'].update(control)
            from .all_in_one import qualification as all_in_one_qualification
            all_in_one = all_in_one_qualification(root,nodes,stats)
            if all_in_one: result['optional']['h3_all_in_one'].update(all_in_one)
            from .h3_latent_finishing import profile as latent_profile
            latent = latent_profile(root)
            if latent and (stats.get('system') or {}).get('comfyui_version')=='0.34.2' and 'MinimaxH3LatentUpscaler3D' in nodes:
                result['optional']['h3_latent_upscale'].update(integrated=True,enabled=True,experimental=True,
                    auto_route=False,scope=latent['scope'],reason='APPROVED_MASTER_DEFERRED_HQ_ONLY')
                result['h3_video_latent_roundtrip_qualified']=True
            return result
        except Exception as exc:
            registry = ns["_video_engine_registry_live"](comfy_online=False).describe()
            return capabilities(registry["engines"], {}, error=str(exc))

    def output_path(output):
        return ns["_safe_comfy_output_path"](output.get("filename", ""), output.get("subfolder", ""), output.get("type", "output"))

    def prepare(spec, bindings, inputs):
        # Local prompt compilation is optional; approved images need no external receipt.
        compiled = bindings.get("compiled_prompt")
        if compiled:
            spec = {**spec, "prompt": str(compiled), "negative": str(bindings.get("compiled_negative", ""))}
        return ns["_normalize_generative_job_spec"](spec)

    def provenance(prompt_id):
        identifier(prompt_id)
        path = root / "workflows" / (prompt_id + ".json")
        if not path.is_file(): return {"workflow_hash": None, "reason": "LEGACY_WORKFLOW_NOT_ARCHIVED"}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"workflow_hash": data["workflow_hash"], "relative_path": "workflows/" + path.name,
            "latent_capture": (data.get("model_fingerprints") or {}).get("capture") == "BEFORE_PROMPT_SUBMISSION"}

    def cancel(job_id):
        job = ns["_get_gen_job"](job_id)
        if not job: raise CreativeError("JOB_UNKNOWN", "Job ausente.", 404)
        with ns["_ACTIVE_GEN_JOBS_LOCK"]:
            active = ns["_ACTIVE_GEN_JOBS"].get(job_id)
            if not active: raise CreativeError("JOB_NOT_ACTIVE", "Job não está ativo neste worker.", 409)
            event = active.get("cancel_event")
            if event is None: raise CreativeError("CANCEL_NOT_AVAILABLE", "Cancelamento indisponível.", 409)
            event.set()
        return {"job_id": job_id, "status": "cancel_requested"}

    service = CreativeService(root, ns["VIDEO_PROJECTS_ROOT"], Bridge(
        lambda spec, **inputs: ns["_start_generative_job"](spec, **inputs),
        lambda job_id: ns["_get_gen_job"](job_id), caps, output_path, cancel,
        prepare=prepare, provenance=provenance))
    from .studio_finishing import install_finishing
    install_finishing(service, ns)
    def assemble(project_dir, **kwargs):
        import shutil
        return ns["_assemble_project"](project_dir,ffmpeg=ns["get_ffmpeg"](),ffprobe=shutil.which("ffprobe"),**kwargs)
    service.assembler=assemble
    from .assets import file_hash
    service.build_hash=digest({str(path.relative_to(Path(ns["__file__"]).parent)):file_hash(path)
        for path in [*Path(__file__).parent.glob("*.py"),Path(ns["__file__"]),Path(ns["__file__"]).with_name("gpu_lease.py")]})
    ns["app"].include_router(create_router(service))
    return service
