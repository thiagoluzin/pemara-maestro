"""Automatic tracked face crops, T8 low-denoise H3 pass, audited recomposition.

T8 core/sampling/face_refine_advanced are pinned, unmodified GPL-3.0-or-later
sources. This adapter invokes them; it does not register the full T8 pack.
"""
import hashlib
import json
import logging
from pathlib import Path
from types import FunctionType

import torch
import folder_paths

BASE_MODEL = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"


def _call(kind, **kwargs):
    import nodes
    cls = nodes.NODE_CLASS_MAPPINGS[kind]
    function = getattr(cls, "FUNCTION", "execute")
    target = cls if hasattr(cls, "define_schema") else cls()
    result = getattr(target, function)(**kwargs)
    return result["result"] if isinstance(result, dict) else result


def _track_detections(detections, width, height, fr):
    """Consume each observed face once, with the upstream conservative tracker."""
    remaining = [[dict(item) for item in items] for items in detections]
    while any(remaining):
        boxes, states, weights, _ = fr._select_track(remaining, [(0, len(remaining)-1)], width, height, .18, 4)
        selected, consumed = [], 0
        for index, items in enumerate(remaining):
            box = boxes[index]
            matches = [] if box is None else [item for item in items if fr._box_iou(box, item["box"]) > .2]
            if matches:
                best = max(matches, key=lambda item: fr._box_iou(box, item["box"]))
                selected.append([best])
                remaining[index].remove(best)
                consumed += 1
            else:
                selected.append([])
        if not consumed:
            raise RuntimeError("Face tracker made no progress; original preserved")
        yield selected


def _plan(images, detections, report, fr, canvas_size, detector_mode, confidence):
    # Same pattern as T8 plan_from_observation: local function globals, never a
    # module-global monkeypatch. Detector observations are reused, not rescanned.
    def observed(*args, **kwargs):
        return detections, dict(report)
    namespace = dict(fr.build_face_refine_plan.__globals__)
    namespace["_detect_" + detector_mode] = observed
    planner = FunctionType(fr.build_face_refine_plan.__code__, namespace,
                           fr.build_face_refine_plan.__name__, fr.build_face_refine_plan.__defaults__)
    return planner(images, 24., detector_mode, report["model"], "cpu", confidence,
                   .3, .1, .4, .55, 1., .18, 4, 2, 3., str(canvas_size), True, 8)


def _save_original(images, audio, prefix):
    from comfy_extras.nodes_video import CreateVideo
    from comfy_api.latest import Types
    video = CreateVideo.execute(images=images, fps=24., audio=audio, bit_depth=8)[0]
    root, name, counter, subfolder, _ = folder_paths.get_save_image_path(
        prefix + "_face_original", folder_paths.get_output_directory(), images.shape[2], images.shape[1])
    path = Path(root) / f"{name}_{counter:05}_.mp4"
    video.save_to(str(path), format=Types.VideoContainer("mp4"), codec=Types.VideoCodec("h264"))
    return {"filename": path.name, "subfolder": subfolder, "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _refine_window(images, detections, detector_report, clip, vae, model, steps, denoise, canvas, seed, confidence, mode, fr):
    original_count = len(images)
    count = max(5, original_count + ((5-original_count) % 17))
    pad = count - original_count
    if pad:
        padded = torch.cat([images, images[-1:].expand(pad, -1, -1, -1)], dim=0)
        observed = detections + [detections[-1]] * pad
    else:
        padded, observed = images, detections
    reports, candidate = [], images.clone()
    for track, selected in enumerate(_track_detections(observed, images.shape[2], images.shape[1], fr)):
        import comfy.model_management as mm
        mm.throw_exception_if_processing_interrupted()
        plan, crops, _, _, _, _, _ = _plan(padded, selected, detector_report, fr, canvas, mode, confidence)
        positive, latent = _call("MiniMaxH3ImageToVideo", clip=clip, vae=vae,
            prompt="How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns "
                   "with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns "
                   f"with the {count/24:.2f}-second mark of the target video.\n\n"
                   "integrated_multimodal_description: [Shot 1] A faithful close view of the same face in "
                   "the source images. Preserve the exact face, expression, hairstyle, skin texture, "
                   "lighting and motion of the source. Improve only fine facial detail.\n\n"
                   "overall_soundscape: N/A\n\nnon_diegetic_music: N/A",
            width=canvas, height=canvas, length=count, first_frame=crops[:1], last_frame=crops[-1:])
        video_latent, audio_latent = fr.nested_av_parts(latent)
        import comfy.nested_tensor
        latent["noise_mask"] = comfy.nested_tensor.NestedTensor((torch.ones_like(video_latent), torch.zeros_like(audio_latent)))
        positive, latent, injection = fr.inject_face_refine_video_latent(positive, latent, crops, vae, plan, "require_locked", False)
        patched, sampler, sigmas, schedule = fr.setup_face_refine_sampling(model, latent, steps, denoise, 12., 3., "dual_clock_euler", "native_flow")
        guider = _call("BasicGuider", model=patched, conditioning=positive)[0]
        noise = _call("RandomNoise", noise_seed=(seed + track) % (2**64))[0]
        sampled = _call("SamplerCustomAdvanced", noise=noise, guider=guider, sampler=sampler, sigmas=sigmas, latent_image=latent)[0]
        decoded = _call("VAEDecodeTiled", samples={"samples": sampled["samples"].unbind()[0]}, vae=vae,
            tile_size=512, overlap=64, temporal_size=64, temporal_overlap=8)[0]
        if len(decoded) != count:
            raise RuntimeError(f"Face Refine temporal mismatch: decoded {len(decoded)}, expected {count}")
        repaired, mask, _, _, stitch = fr.stitch_face_refine_candidate(padded, decoded, plan,
            "ellipse", 12., 1., .65, .4, 1, "cpu_memory_safe")
        # Each track uses the original source. Composite only its audited mask;
        # subsequent tracks cannot erase faces already repaired.
        mask = mask[:original_count, ..., None]
        candidate = torch.where(mask > 0, repaired[:original_count], candidate)
        reports.append({"track": track, "plan": plan, "injection": json.loads(injection),
                        "sampling": json.loads(schedule), "stitch": json.loads(stitch),
                        "internal_tail_padding": pad, "valid_source_frames": original_count})
        del crops, positive, latent, sampled, decoded, repaired, mask, patched, guider, noise
    return candidate, reports


class PemaraH3FaceRefine:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "images": ("IMAGE",), "clip": ("CLIP",), "vae": ("VAE",),
            "source_prompt": ("STRING", {"default": "", "multiline": True}),
            "fps": ("FLOAT", {"default": 24., "min": 24., "max": 24.}),
            "seed": ("INT", {"default": 0, "min": 0, "max": 2**64-1}),
            "filename_prefix": ("STRING", {"default": "PEMARA_H3/face_refine"}),
            "enabled": ("BOOLEAN", {"default": True}),
            "steps": ("INT", {"default": 12, "min": 1, "max": 50}),
            "denoise": ("FLOAT", {"default": .45, "min": .01, "max": .6, "step": .01}),
            "canvas_size": ("INT", {"default": 512, "min": 384, "max": 768, "step": 32}),
            "detector": (["auto", "human", "anime"], {"default": "auto"}),
            "confidence": ("FLOAT", {"default": .5, "min": .05, "max": .99, "step": .05}),
        }, "optional": {"audio": ("AUDIO",)}}

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("refined_images", "report")
    FUNCTION = "refine"
    CATEGORY = "PEMARA/H3"
    DESCRIPTION = "Face Refine automático em todos os rostos detectados. Salva original; áudio e pixels fora das máscaras preservados. H3 Base + Sage, 12 steps/0,45; candidato sujeito à revisão."

    def refine(self, images, clip, vae, source_prompt, fps, seed, filename_prefix, enabled=True,
               steps=12, denoise=.45, canvas_size=512, detector="auto", confidence=.5, audio=None):
        if not enabled:
            return images, json.dumps({"status": "explicitly_disabled", "identity_verified": False})
        if abs(float(fps)-24) > .01 or images.ndim != 4 or images.shape[-1] != 3 or len(images) < 1:
            raise ValueError("Face Refine requires unchanged RGB source at 24 FPS")
        if canvas_size not in {384, 512, 640, 768}:
            raise ValueError("Face Refine canvas: 384, 512, 640 or 768")
        from .upstream import face_refine_advanced as fr
        original_ui = _save_original(images, audio, filename_prefix)
        report = {"schema": "pemara.h3.face-refine.v1", "status": "candidate_requires_review",
                  "enabled": True, "frames": len(images), "fps": 24., "steps": steps, "denoise": denoise,
                  "canvas": canvas_size, "original": original_ui, "audio_modified": False,
                  "identity_verified": False, "automatic_accept": False, "source_prompt_sha256": hashlib.sha256(source_prompt.encode()).hexdigest(),
                  "tracks": [], "detector": detector, "windows": []}
        detections, model_report = fr._detect_local_opencv_yunet(images, fr.YUNET_2023MAR_RELATIVE, confidence, "cpu") if detector != "anime" else ([], {})
        mode = "local_opencv_yunet"
        model_name = fr.YUNET_2023MAR_RELATIVE
        if detector == "anime" or (detector == "auto" and not any(detections)):
            detections, model_report = fr._detect_local_anime_onnx_exp(images, fr.ANIME_FACE_V14_N_RELATIVE, confidence, "cpu")
            mode, model_name = "local_anime_onnx_exp", fr.ANIME_FACE_V14_N_RELATIVE
        model_report["model"] = model_name
        report["detector_report"] = model_report
        if len(detections) != len(images):
            raise RuntimeError("Incomplete face scan; cannot report no-face")
        if not any(detections):
            report.update(status="no_face_detected_original_preserved", detected_faces=0)
            result = images
        else:
            # The refine branch always loads clean Base FL2VA; no PDD, FastH3,
            # ControlNet, Turbo or parent-model patch is inherited.
            model = _call("UNETLoader", unet_name=BASE_MODEL, weight_dtype="default")[0]
            model = _call("MiniMaxH3MemoryEfficientSageAttentionPatch", model=model)[0]
            if not any("attn.forward" in str(key) for key in model.object_patches):
                raise RuntimeError("SageAttention is not connected to Face Refine")
            shots, _ = fr._scene_ranges(images, .28)
            result = images.clone()
            for shot_start, shot_end in shots:
                # 124 source frames/window bounds RAM and H3 cost on long clips.
                for start in range(shot_start, shot_end+1, 124):
                    end = min(start+124, shot_end+1)
                    observed = detections[start:end]
                    if not any(observed):
                        report["windows"].append({"start": start, "end": end, "status": "no_face_detected"})
                        continue
                    candidate, tracks = _refine_window(images[start:end], observed, model_report, clip, vae,
                        model, steps, denoise, canvas_size, seed+start, confidence, mode, fr)
                    result[start:end] = candidate
                    report["windows"].append({"start": start, "end": end, "tracks": len(tracks)})
                    report["tracks"].extend({"source_start": start, **track} for track in tracks)
            report["detected_faces"] = sum(len(items) for items in detections)
            report["sage_attention"] = "connected_base_fl2va"
            if result.shape != images.shape:
                raise RuntimeError("Face Refine changed source geometry/frame count")
        path_root = Path(folder_paths.get_output_directory())
        # Prefix path validation is delegated to ComfyUI's own save-path policy.
        root, basename, counter, subfolder, _ = folder_paths.get_save_image_path(filename_prefix + "_face_report", str(path_root))
        report_path = Path(root) / f"{basename}_{counter:05}_.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        logging.info("[PEMARA Face Refine] %s: %s", report["status"], report_path)
        return {"ui": {"text": [json.dumps({"status": report["status"], "report": str(report_path),
                  "tracks": len(report["tracks"]), "identity_verified": False}, ensure_ascii=False)]},
                "result": (result, json.dumps(report, ensure_ascii=False, default=str))}
