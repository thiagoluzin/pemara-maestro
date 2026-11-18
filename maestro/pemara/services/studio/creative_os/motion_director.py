"""Pure IR compiler for the pinned H3 Motion Director; never submits work."""
import json
import re
from .adapters import H3Adapter
from .ir import CreativeError, digest, identifier, validate_ir

TASK = "t2v — 文生视频(Text to Video)"
PATCH_CONTRACT = "creative_os_native_audio_opt_out_v1"


def compile_motion(shots, *, seed, profile="h3_production", selected=None,
                   motion_context=True, filename_prefix="creative_os/motion"):
    if type(motion_context) is not bool:
        raise CreativeError("MOTION_CONTEXT", "Contexto deve ser booleano.")
    if not isinstance(filename_prefix,str) or not re.fullmatch(r"[A-Za-z0-9_/-]{1,180}",filename_prefix) or filename_prefix.startswith('/'):
        raise CreativeError("MOTION_PREFIX", "Prefixo de saída inválido.")
    if not isinstance(shots, list) or not 2 <= len(shots) <= 12:
        raise CreativeError("MOTION_SHOT_COUNT", "Motion Director exige 2–12 planos; use H3 nativo para um plano.")
    shots = [validate_ir(shot) for shot in shots]
    if len({s["project_id"] for s in shots}) != 1 or len({s["shot_id"] for s in shots}) != len(shots):
        raise CreativeError("MOTION_PROJECT", "Planos devem ser distintos e pertencer ao mesmo projeto.")
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise CreativeError("INVALID_SEED", "Motion Director exige seed explícita.")
    specs = [H3Adapter().build_job(s, {"seed":seed, "h3_quality_profile":profile}) for s in shots]
    audio = {s["enable_minimax_h3_native_audio"] for s in specs}
    if len(audio) != 1:
        raise CreativeError("MOTION_AUDIO", "Use a mesma escolha de áudio em todos os planos desta timeline.")
    audio = audio.pop()
    if selected is not None:
        if not isinstance(selected, list) or not selected or any(type(i) is not int or not 0 <= i < len(shots) for i in selected):
            raise CreativeError("MOTION_SELECTION", "Selecione índices válidos para o rerun.")
        selected = sorted(set(selected))
        # Until persisted source-context binding is qualified, never silently
        # substitute empty context or regenerate a predecessor.
        if motion_context and any(i > 0 and i-1 not in selected for i in selected):
            raise CreativeError("MOTION_CONTEXT_SOURCE", "Rerun com contexto exige o predecessor selecionado; contexto salvo ainda não integrado.")
    first = specs[0]
    segments = []
    start = 0
    for index, (shot, spec) in enumerate(zip(shots, specs)):
        # H3 uses 17k+5 frames and the installed Production path starts at 124.
        target=shot["duration_seconds"]*24
        frames=min(range(124,363,17),key=lambda count:abs(count-target))
        segments.append({"id":identifier(shot["shot_id"]), "start":start, "length":frames,
            "frameCount":frames, "prompt":spec["prompt"], "taskType":TASK, "refs":[],
            "referenceVideo":{}, "contextLink":{"enabled":bool(index and motion_context),
                "visual":bool(index and motion_context), "audio":bool(index and motion_context and audio)}})
        start += frames
    timeline = {"version":4, "timelineMode":"prompt_batch", "editMode":"segment",
        "totalFrames":start, "frameRate":24, "width":first["width"], "height":first["height"],
        "refMaxSize":first["width"], "global":{"taskType":TASK,"prompt":"","refs":[]},
        "videoClips":[], "video":{"frames":[]}, "segments":segments,
        "output":{"mode":"fixed", "width":first["width"], "height":first["height"],
            "longEdge":first["width"], "maxExportFrames":0, "exportMode":"segments",
            "creativeOsNativeAudio":audio, "audioMode":"generate" if audio else "mute"},
        "runSelectEnabled":selected is not None, "runSelection":selected or []}
    graph = {
        "1":{"class_type":"UNETLoader","inputs":{"unet_name":"minimax_h3_fl2va_pruned_int8_convrot.safetensors","weight_dtype":"default"}},
        "3":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors","type":"minimax","device":"default"}},
        "4":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_video_vae_fp16.safetensors"}},
        "5":{"class_type":"VAELoader","inputs":{"vae_name":"minimax_h3_audio_vae_fp32.safetensors"}},
        "20":{"class_type":"MiniMaxH3MotionDirector","inputs":{"model":["1",0],"clip":["3",0],
            "video_vae":["4",0],"audio_vae":["5",0],"task_type":TASK,"global_prompt":"",
            "bd_grp_sample":"采样设置","cfg":1.0,"seed":seed,"frame_rate":24.0,
            "width":first["width"],"height":first["height"],"ref_max_size":first["width"],
            "total_frames":start,"timeline_data":json.dumps(timeline,ensure_ascii=False),
            "steps":first["steps"],"sampler_name":"res_multistep","scheduler":"simple",
            "shift_video":12.0,"shift_audio":3.0,"motion_context_enabled":bool(motion_context),
            "audio_context_enabled":bool(motion_context and audio),"clear_vram_between_segments":True}},
        "21":{"class_type":"CreateVideo","inputs":{"images":["20",0],"fps":24.0,"bit_depth":8}},
        "22":{"class_type":"SaveVideo","inputs":{"video":["21",0],"filename_prefix":filename_prefix,"format":"mp4","format.codec":"h264"}}}
    if audio: graph["21"]["inputs"]["audio"] = ["20",1]
    from h3_workflow import ensure_h3_sage_attention
    graph = ensure_h3_sage_attention(graph)
    return {"graph":graph,"timeline":timeline,"workflow_hash":digest(graph),
        "source_ir_hashes":[digest(s) for s in shots],"required_patch":PATCH_CONTRACT,
        "selected_shots":[shots[i]["shot_id"] for i in (selected if selected is not None else range(len(shots)))],
        "segment_frames":[segments[i]["frameCount"] for i in (selected if selected is not None else range(len(shots)))],
        "human_verdict":None,"generation_submitted":False}


def compile_request(request, *, engine_id, seed, profile, native_audio):
    if engine_id != "minimax_h3" or not isinstance(request,dict):
        raise CreativeError("ENGINE_MISMATCH", "Motion Director exige H3 explícito.")
    if set(request) - {"shots","selected","motion_context"}:
        raise CreativeError("MOTION_REQUEST", "Campos de runtime externos não são aceitos.")
    result = compile_motion(request.get("shots"),seed=seed,profile=profile,
        selected=request.get("selected"),motion_context=request.get("motion_context",True))
    if result["timeline"]["output"]["creativeOsNativeAudio"] != bool(native_audio):
        raise CreativeError("MOTION_AUDIO", "A opção de áudio do job diverge dos planos.")
    return result
