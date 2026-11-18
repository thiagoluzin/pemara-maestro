"""One original ACE-Step song, with no cover parameters or external critic."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--gpu-job-id", default="")
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()
    registry = None
    if args.gpu_job_id:
        project = Path(__file__).resolve().parents[3]
        sys.path.insert(0, str(project / "services/studio"))
        from gpu_lease import GpuLeaseRegistry
        registry = GpuLeaseRegistry(project / "dados/studio/gpu_lease.json")
        registry.adopt_child_process(args.gpu_job_id, expected_parent_pid=args.parent_pid)
    try:
        generate(args)
    finally:
        if registry:
            registry.release(args.gpu_job_id)


def generate(args):
    spec = json.loads(Path(args.request).read_text(encoding="utf-8"))
    model = spec["model"]
    if model not in {"acestep-v15-turbo", "acestep-v15-xl-base"}:
        raise ValueError("Modelo de criação não permitido.")
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationParams, GenerationConfig, generate_music
    import soundfile as sf
    handler = AceStepHandler()
    status, ready = handler.initialize_service(project_root=args.project_root, config_path=model,
        device="cuda", use_flash_attention=False, compile_model=False, offload_to_cpu=False,
        offload_dit_to_cpu=False, quantization=None, prefer_source="huggingface")
    if not ready:
        raise RuntimeError(status)
    turbo = model.endswith("turbo")
    params = GenerationParams(task_type="text2music", caption=spec["prompt"],
        lyrics="[Instrumental]" if spec["instrumental"] else spec["lyrics"],
        instrumental=spec["instrumental"], duration=spec["duration"], bpm=spec.get("bpm") or None,
        seed=spec["seed"], inference_steps=8 if turbo else 50, guidance_scale=1.0 if turbo else 7.0,
        shift=3.0 if turbo else 1.0, thinking=False, use_cot_caption=False,
        use_cot_language=False, use_cot_metas=False, enable_normalization=False)
    config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[spec["seed"]], audio_format="flac")
    result = generate_music(handler, None, params, config, save_dir=args.output_dir)
    if not result.success or len(result.audios) != 1:
        raise RuntimeError(result.error or result.status_message or "Nenhum áudio ACE-Step.")
    audio = Path(result.audios[0]["path"]).resolve()
    if Path(args.output_dir).resolve() not in audio.parents:
        raise RuntimeError("Artefato fora da pasta do trabalho.")
    info = sf.info(str(audio))
    Path(args.output_dir, "result.json").write_text(json.dumps({"path": str(audio),
        "duration_seconds": info.duration, "model": model, "seed": spec["seed"],
        "task_type": "text2music", "approval_status": "PENDING_HUMAN_REVIEW"}), encoding="utf-8")


if __name__ == "__main__":
    main()
