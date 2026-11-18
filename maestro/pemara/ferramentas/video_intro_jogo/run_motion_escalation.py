from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent / "video_global_engine" / "projetos" / "intro_ritmos_revolta"
TAKES_DIR = PROJECT / "takes"
QC_ROOT = PROJECT / "qc"
RUNNER = ROOT / "run_intro_take_queue.py"

STYLE_LORA = "intro_ritmos_60s_v1_000089250.safetensors"
PUSH_IN_LORA = "_ready_wan-camera-push-in/motionpushin-v5-wan-i2v-14b-720p-400.safetensors"

VARIANTS = {
    "wan5b_no_lora": {
        "model": "wan2.2_ti2v_5B_fp16.safetensors",
        "lora": "",
        "lora_strength": 0.0,
        "steps": 24,
        "guidance": 7.0,
        "motion_profile": "controlled",
        "note": "Controle: 5B sem LoRA para medir se o LoRA esta congelando movimento.",
    },
    "wan5b_style_low": {
        "model": "wan2.2_ti2v_5B_fp16.safetensors",
        "lora": STYLE_LORA,
        "lora_strength": 0.03,
        "steps": 24,
        "guidance": 7.0,
        "motion_profile": "controlled",
        "note": "5B com estilo minimo; so vale se mover mais que o 0.08 anterior.",
    },
    "wan_a14b_q4_no_lora": {
        "model": "Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "lora": "",
        "lora_strength": 0.0,
        "steps": 22,
        "guidance": 6.5,
        "motion_profile": "controlled",
        "note": "Escalada real: A14B Q4 High/Low sem LoRA, priorizando movimento e composicao.",
    },
    "wan_a14b_q4_smoke_512": {
        "model": "Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "lora": "",
        "lora_strength": 0.0,
        "steps": 16,
        "guidance": 5.5,
        "width": 512,
        "height": 288,
        "seconds": 2,
        "motion_profile": "controlled",
        "note": "Smoke test A14B Q4 pequeno. So valida se o workflow move e finaliza antes de subir resolucao.",
    },
    "wan_a14b_q4_smoke_768": {
        "model": "Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "lora": "",
        "lora_strength": 0.0,
        "steps": 18,
        "guidance": 5.8,
        "width": 768,
        "height": 432,
        "seconds": 3,
        "motion_profile": "controlled",
        "note": "Segundo degrau A14B Q4: ainda curto, mais proximo de 720p, antes de render final.",
    },
    "wan_a14b_q4_pushin_lora": {
        "model": "Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "lora": PUSH_IN_LORA,
        "lora_strength": 0.35,
        "steps": 22,
        "guidance": 6.5,
        "prompt_prefix": "Push-in camera.",
        "motion_profile": "controlled",
        "note": "A14B Q4 com Motion LoRA de camera push-in. Experimental; reprovar se destruir identidade.",
    },
    "wan_a14b_q4_pushin_smoke_512": {
        "model": "Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "lora": PUSH_IN_LORA,
        "lora_strength": 0.25,
        "steps": 16,
        "guidance": 5.5,
        "width": 512,
        "height": 288,
        "seconds": 2,
        "prompt_prefix": "Push-in camera.",
        "motion_profile": "controlled",
        "note": "Smoke test da Motion LoRA push-in; usar so se o A14B sem LoRA finalizou e ficou parado.",
    },
}


def safe_label(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")[:80]


def run(cmd: list[str], *, cwd: Path, env: dict[str, str], stdout: Path, stderr: Path) -> subprocess.CompletedProcess[str]:
    with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        return subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=out, stderr=err)


def parse_ok_path(log: Path) -> Path | None:
    if not log.exists():
        return None
    for line in reversed(log.read_text(encoding="utf-8", errors="replace").splitlines()):
        if line.startswith("OK="):
            return Path(line.split("=", 1)[1].strip())
    return None


def ffprobe_json(video: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames,codec_name",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        str(video),
    ]
    data = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace")
    return json.loads(data)


def make_qc_images(video: Path, out_dir: Path, label: str) -> dict[str, str]:
    contact = out_dir / f"{label}_contact_2fps.jpg"
    strip = out_dir / f"{label}_first_mid_last.jpg"
    probe = ffprobe_json(video)
    stream = (probe.get("streams") or [{}])[0]
    try:
        frames = max(1, int(stream.get("nb_frames") or 1))
    except ValueError:
        frames = 1
    mid = max(0, frames // 2)
    last = max(0, frames - 1)
    select_filter = f"select='eq(n,0)+eq(n,{mid})+eq(n,{last})',scale=426:-1,tile=3x1"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            "fps=2,scale=320:-1,tile=4x3",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(contact),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            select_filter,
            "-frames:v",
            "1",
            "-update",
            "1",
            str(strip),
        ],
        check=True,
    )
    return {"contact": contact.as_posix(), "first_mid_last": strip.as_posix()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Escada de movimento para takes fracos da intro.")
    parser.add_argument("--take", default="06", help="ID ou slug do take.")
    parser.add_argument("--seconds", type=int, default=4, help="Duracao curta para teste honesto.")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument(
        "--variants",
        nargs="*",
        default=["wan5b_no_lora", "wan_a14b_q4_smoke_512", "wan_a14b_q4_smoke_768"],
        choices=sorted(VARIANTS),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    qc_dir = QC_ROOT / f"motion_escalation_{args.take}_{run_tag}"
    qc_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["MAESTRO_STUDIO_URL"] = env.get("MAESTRO_STUDIO_URL", "http://127.0.0.1:8029")

    report: dict = {
        "schema_version": "1.0",
        "type": "motion_escalation_run",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "take": args.take,
        "seconds": args.seconds,
        "variants": [],
        "rule": "Nao voltar a treinar/gerar em massa antes de comparar movimento real.",
    }

    for variant_name in args.variants:
        variant = VARIANTS[variant_name]
        label = safe_label(f"{args.take}_{variant_name}_{run_tag}")
        out_log = qc_dir / f"{label}.out.log"
        err_log = qc_dir / f"{label}.err.log"
        width = int(variant.get("width", args.width))
        height = int(variant.get("height", args.height))
        seconds = int(variant.get("seconds", args.seconds))
        prompt_prefix = str(variant.get("prompt_prefix", ""))
        motion_profile = str(variant.get("motion_profile", "controlled"))
        cmd = [
            sys.executable,
            str(RUNNER),
            "--takes",
            args.take,
            "--max-take-seconds",
            str(seconds),
            "--width",
            str(width),
            "--height",
            str(height),
            "--fps",
            str(args.fps),
            "--steps",
            str(variant["steps"]),
            "--guidance",
            str(variant["guidance"]),
            "--model",
            str(variant["model"]),
            "--lora",
            str(variant["lora"]),
            "--lora-strength",
            str(variant["lora_strength"]),
            "--seed",
            str(args.seed),
            "--motion-profile",
            motion_profile,
            "--prompt-prefix",
            prompt_prefix,
            "--run-label",
            label,
        ]
        item = {
            "id": variant_name,
            "label": label,
            "model": variant["model"],
            "lora": variant["lora"],
            "lora_strength": variant["lora_strength"],
            "steps": variant["steps"],
            "guidance": variant["guidance"],
            "width": width,
            "height": height,
            "seconds": seconds,
            "motion_profile": motion_profile,
            "prompt_prefix": prompt_prefix,
            "note": variant["note"],
            "command": cmd,
            "stdout": out_log.as_posix(),
            "stderr": err_log.as_posix(),
        }
        if args.dry_run:
            item["status"] = "dry_run"
            report["variants"].append(item)
            continue

        started = time.time()
        completed = run(cmd, cwd=ROOT, env=env, stdout=out_log, stderr=err_log)
        item["returncode"] = completed.returncode
        item["elapsed_seconds"] = round(time.time() - started, 1)
        video = parse_ok_path(out_log)
        if completed.returncode == 0 and video and video.exists():
            item["status"] = "generated"
            item["video"] = video.as_posix()
            item["metadata"] = video.with_suffix(".json").as_posix()
            item["ffprobe"] = ffprobe_json(video)
            item["qc_images"] = make_qc_images(video, qc_dir, label)
        else:
            item["status"] = "error"
            item["error_hint"] = (err_log.read_text(encoding="utf-8", errors="replace")[-2000:] if err_log.exists() else "")
        report["variants"].append(item)
        (qc_dir / "motion_escalation_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    md_lines = [
        f"# Motion Escalation - take {args.take} - {run_tag}",
        "",
        "Regra: quando o 5B vira foto viva, comparar variantes antes de treinar ou gerar em massa.",
        "",
    ]
    for item in report["variants"]:
        md_lines.extend(
            [
                f"## {item['id']}",
                "",
                f"- Status: `{item.get('status')}`",
                f"- Modelo: `{item['model']}`",
                f"- LoRA: `{item['lora'] or 'sem LoRA'}`",
                f"- Forca LoRA: `{item['lora_strength']}`",
                f"- Perfil: `{item.get('motion_profile', '-')}`",
                f"- Tamanho/duracao: `{item.get('width')}x{item.get('height')}` por `{item.get('seconds')}` s",
                f"- Tempo: `{item.get('elapsed_seconds', '-')}` s",
                f"- Video: `{item.get('video', '-')}`",
                f"- Contact sheet: `{(item.get('qc_images') or {}).get('contact', '-')}`",
                f"- Nota: {item['note']}",
                "",
            ]
        )
    (qc_dir / "MOTION_ESCALATION_REPORT.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"REPORT={qc_dir / 'MOTION_ESCALATION_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
