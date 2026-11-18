"""Original local music: prompt-only creation and optional manual score controls."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from music_ending import arrangement_style, ending_budget, score_seconds, generation_ending, compact_score

ACE_ID = "ace_step_local"
YUE_ID = "yue2_local"
ACE_COMMIT = "ca1e85fe9430179831e6bc6be790c332190a3866"
PROJECT = Path(__file__).resolve().parents[2]
RUNTIME = PROJECT / "ferramentas/audio_neural/music_ai_runtime"
ACE_SOURCE = RUNTIME / "sources/ACE-Step-1.5-20261005"
ACE_PYTHON = ACE_SOURCE / ".venv/Scripts/python.exe"
ACE_MODELS = RUNTIME / "models/ace_step"
ACE_CLI = RUNTIME / "ace_create_cli.py"
YUE_CHECKPOINT = "yue2_3b_int8_convrot.safetensors"
YUE_MODEL_PATH = Path(r"D:\PemaraModels\workflows_20260920\checkpoints") / YUE_CHECKPOINT
ACE_CHOICES = {"acestep-v15-turbo": "Turbo · 8 passos", "acestep-v15-xl-base": "XL Base · 50 passos"}


def provider_status():
    models = {name: label for name, label in ACE_CHOICES.items()
              if (ACE_MODELS / name / "config.json").is_file()}
    ace_ready = ACE_PYTHON.is_file() and ACE_CLI.is_file() and bool(models)
    return {
        ACE_ID: {"label": "ACE-Step 1.5 local", "configured": ace_ready,
                 "modes": ["music"], "min_duration_seconds": 10, "max_duration_seconds": 600,
                 "default_duration_seconds": 30, "models": models, "requires_human_listening": True,
                 "message": "Criação original com estilo e letra. Turbo ou XL Base, sem serviço pago." if ace_ready else "Runtime ACE-Step de criação ainda indisponível.",
                 "runtime_commit": ACE_COMMIT},
        YUE_ID: {"label": "YuE2 local · partitura e áudio", "configured": YUE_MODEL_PATH.is_file(),
                 "modes": ["music"], "min_duration_seconds": 6, "max_duration_seconds": 900,
                 "engine_max_duration_seconds": 900,
                 "default_duration_seconds": 30, "requires_human_listening": True,
                 "message": "Descreva a música: letra, composição e áudio são gerados em sequência, com encerramento dentro do tempo. Ajustes e partitura são opcionais."},
    }


def validate(provider, prompt, duration, lyrics="", instrumental=True, music_model="", music_bpm=0,
             music_action="generate", music_abc="", music_abc_reviewed=False):
    if provider not in {ACE_ID, YUE_ID}:
        raise ValueError("Motor de música local desconhecido.")
    if not isinstance(prompt, str) or not 8 <= len(prompt.strip()) <= 1500:
        raise ValueError("Descreva o estilo musical em 8 a 1500 caracteres.")
    if not isinstance(lyrics, str) or len(lyrics) > 4096:
        raise ValueError("Letra limitada a 4096 caracteres.")
    if type(instrumental) is not bool or type(music_abc_reviewed) is not bool:
        raise ValueError("Instrumental e revisão de partitura devem ser booleanos.")
    if instrumental and lyrics.strip():
        raise ValueError("Para usar a letra, desmarque Instrumental.")
    if not instrumental and not lyrics.strip() and music_action != "auto":
        raise ValueError("Informe a letra ou selecione Instrumental.")
    info = provider_status()[provider]
    if not math.isfinite(float(duration)) or not info["min_duration_seconds"] <= float(duration) <= info["max_duration_seconds"]:
        raise ValueError(f"Duração deve ficar entre {info['min_duration_seconds']} e {info['max_duration_seconds']} segundos.")
    if music_action not in {"generate", "plan", "auto"}:
        raise ValueError("Etapa de música inválida.")
    if provider == ACE_ID:
        if music_action not in {"generate", "auto"}:
            raise ValueError("Planejamento ABC pertence ao YuE2.")
        if (music_model or "acestep-v15-turbo") not in ACE_CHOICES:
            raise ValueError("Modelo ACE-Step não permitido.")
        if int(music_bpm) != 0 and not 30 <= int(music_bpm) <= 300:
            raise ValueError("BPM: 0 para automático ou entre 30 e 300.")
    elif music_action == "generate":
        if not music_abc_reviewed:
            raise ValueError("Revise a partitura ABC e confirme a revisão antes de gerar áudio YuE2.")
        if not isinstance(music_abc, str) or not 10 <= len(music_abc.strip()) <= 100000 or not re.search(r"(?m)^K:\s*\S+", music_abc):
            raise ValueError("Informe a partitura ABC revisada, incluindo o campo K: de tonalidade.")


def prepare_vocal_score(abc, duration):
    """Keep short vocal previews from being consumed by the model's long intro."""
    if not isinstance(abc, str) or not re.search(r"(?m)^K:\s*\S+", abc):
        raise ValueError("YuE2 não retornou uma composição ABC válida.")
    if float(duration) > 60:
        return abc
    intro = re.search(r"(?mi)^%\s*intro\b[^\n]*\n", abc)
    if not intro:
        return abc
    vocal = re.search(r"(?mi)^%\s*(?:verse|chorus)\b", abc[intro.end():])
    if not vocal:
        return abc
    return abc[:intro.start()] + abc[intro.end() + vocal.start():]


def yue_workflow(*, prompt, lyrics, instrumental, duration, seed, music_action, music_abc, prefix, music_duration_auto=False, production_plan=None):
    """Auto composes and renders; manual planning/review remains an explicit mode."""
    lyric_input = "[Instrumental]" if instrumental else lyrics
    loader = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": YUE_CHECKPOINT}}
    if music_duration_auto:
        duration = 900
    score_style = arrangement_style(prompt, None if music_duration_auto else duration, instrumental) if music_action == "auto" or music_duration_auto else prompt
    if production_plan:
        sections = "; ".join(f"{s['name']} {s['start']:g}-{s['end']:g}s energy {s['energy']:g} lead {s['lead']}"
                             for s in production_plan['sections'])
        score_style += f". Qwen producer tempo {production_plan['bpm']} BPM. Planned form: {sections}. Finish all singing before the final decay."
    if music_action == "plan":
        return {
            "1": loader,
            "2": {"class_type": "YuE2GenerateABC", "inputs": {
                "clip": ["1", 1], "style": score_style, "lyrics": lyric_input, "seed": seed,
                "mode": "full", "max_abc_tokens": 8192, "temperature": 0.7,
                "top_p": 0.9, "top_k": 30, "repetition_penalty": 1.005, "penalty_window": 100}},
            "3": {"class_type": "PreviewAny", "inputs": {"source": ["2", 0]}},
        }
    workflow = {
        "1": loader,
        "2": {"class_type": "YuE2GenerateMusic", "inputs": {
            "clip": ["1", 1], "style": score_style, "lyrics": lyric_input, "abc": music_abc,
            "seed": seed, "mode": "full", "max_duration": duration, "temperature": 1.0,
            "top_p": 0.95, "top_k": 100, "repetition_penalty": 1.2}},
        "3": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["2", 0]}},
        "4": {"class_type": "EmptyYuE2LatentAudio", "inputs": {"seconds": ["2", 1], "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["2", 0],
              "negative": ["3", 0], "latent_image": ["4", 0], "seed": seed, "steps": 32,
              "cfg": 1.0, "sampler_name": "dpm_2", "scheduler": "sgm_uniform", "denoise": 1.0}},
        "6": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "12": {"class_type": "AudioAdjustVolume", "inputs": {"audio": ["6", 0], "volume": -6.0}},
        "7": {"class_type": "SaveAudioAdvanced", "inputs": {"audio": ["12", 0], "filename_prefix": prefix, "format": "flac"}},
    }
    if music_action == "auto":
        workflow["10"] = {"class_type": "PreviewAny", "inputs": {"source": ["2", 0]}}
        workflow["11"] = {"class_type": "PreviewAny", "inputs": {"source": ["2", 1]}}
    if music_action == "auto" and not music_abc.strip():
        workflow["8"] = {"class_type": "YuE2GenerateABC", "inputs": {
            "clip": ["1", 1], "style": score_style, "lyrics": lyric_input, "seed": seed,
            "mode": "full", "max_abc_tokens": 8192, "temperature": 0.7,
            "top_p": 0.9, "top_k": 30, "repetition_penalty": 1.005, "penalty_window": 100}}
        workflow["2"]["inputs"]["abc"] = ["8", 0]
        workflow["9"] = {"class_type": "PreviewAny", "inputs": {"source": ["8", 0]}}
    return workflow


def run_yue_auto(*, prompt, lyrics, instrumental, duration, seed, queue, music_abc="", progress_cb=None, music_duration_auto=False, production_plan=None):
    """One Maestro job; bounded internal composition/retry, no human score step.

    Rendered failures stay on disk and in the attempt receipts; no source audio
    is cut, faded, sped up or overwritten to pass the duration check.
    """
    attempts = []
    if music_duration_auto:
        duration = 900
    original_abc = music_abc
    target = ending_budget(duration)["score_target_seconds"]
    planned_seconds = None
    for render_attempt in range(2):
        planning_prompt = prompt
        for plan_attempt in range(3):
            if not music_abc:
                graph = yue_workflow(prompt=planning_prompt, lyrics=lyrics, instrumental=instrumental,
                    duration=target, seed=(seed + render_attempt * 10 + plan_attempt) % (2**64),
                    music_action="auto", music_abc="", prefix="unused",
                    music_duration_auto=music_duration_auto and render_attempt == 0 and plan_attempt == 0,
                    production_plan=production_plan)
                graph = {key: graph[key] for key in ("1", "8", "9")}
                score_prompt_id, outputs = queue(graph)
                abc = "\n".join(item["text"] for item in outputs if item.get("kind") == "text").strip()
                if not original_abc: original_abc = abc
                music_abc = abc if instrumental or music_duration_auto else prepare_vocal_score(abc, duration)
            else:
                score_prompt_id = None
            try:
                planned_seconds = None
                planned_seconds = score_seconds(music_abc)
                if planned_seconds > target:
                    music_abc = compact_score(music_abc, target)
                    planned_seconds = score_seconds(music_abc)
                fits = planned_seconds <= target
                reason = f"Previous ABC lasts {planned_seconds:g} seconds, exceeding the budget."
            except ValueError as exc:
                fits = False
                reason = f"Previous ABC duration could not be measured: {exc}"
            attempts.append({"stage": "score", "prompt_id": score_prompt_id, "abc": music_abc,
                             "planned_seconds": planned_seconds, "fits_duration": fits})
            if fits: break
            music_abc = ""
            planning_prompt = (f"{prompt}\n{reason} Rewrite a much more compact COMPLETE arrangement "
                               f"lasting at most {target:g} seconds at the same musical tempo. "
                               "Reduce intro, instrumental interludes and unnecessary repetitions. "
                               "Keep the sung lyrics and include the final cadence. Use explicit measures, "
                               "constant meter and one constant Q tempo, no repeat signs or inline tempo changes.")
            if progress_cb: progress_cb(35, "Ajustando a composição para caber no tempo e terminar.")
        else:
            raise RuntimeError("YuE2 não compôs um encerramento dentro do tempo após três tentativas. "
                               "Nenhum áudio foi cortado. Tente uma duração maior ou uma letra mais curta.")
        if progress_cb: progress_cb(55, "Composição dentro do tempo; gerando a música e seu encerramento.")
        graph = yue_workflow(prompt=prompt, lyrics=lyrics, instrumental=instrumental,
            duration=duration, seed=(seed + render_attempt) % (2**64), music_action="auto", music_abc=music_abc,
            prefix=f"audio/Maestro_YuE2_{uuid.uuid4().hex[:12]}", music_duration_auto=music_duration_auto,
            production_plan=production_plan)
        prompt_id, outputs = queue(graph)
        check = generation_ending(outputs, duration)
        attempts.append({"stage": "audio", "prompt_id": prompt_id, "ending_check": check,
                         "outputs": [item for item in outputs if item.get("kind") == "audio"]})
        if check["end_token_reached"] and check["within_duration"]:
            return prompt_id, outputs, {"music_abc": music_abc, "music_abc_original": original_abc,
                "music_attempts": attempts, "ending_check": check, "planned_seconds": planned_seconds,
                "requested_duration_seconds": None if music_duration_auto else float(duration),
                "music_duration_auto": music_duration_auto, "duration_ceiling_seconds": float(duration)}
        if progress_cb: progress_cb(40, "O motor parou antes de encerrar; recompondo automaticamente.")
        music_abc = ""
        target *= .75
    raise RuntimeError("YuE2 atingiu o limite antes do encerramento em duas tentativas. "
                       "Os arquivos foram preservados, mas não foram marcados como música concluída.")


def run_ace(*, prompt, lyrics, instrumental, duration, seed, music_model, music_bpm,
            progress_cb=None, cancel_event=None, process_cb=None, gpu_job_id=""):
    model = music_model or "acestep-v15-turbo"
    if not provider_status()[ACE_ID]["configured"] or model not in provider_status()[ACE_ID]["models"]:
        raise RuntimeError("Modelo/runtime ACE-Step selecionado indisponível; sem fallback.")
    folder = PROJECT / "outputs/music_create" / uuid.uuid4().hex
    folder.mkdir(parents=True)
    request_file = folder / "request.json"
    request_file.write_text(json.dumps({"prompt": prompt, "lyrics": lyrics, "instrumental": instrumental,
                           "duration": duration, "seed": seed, "model": model, "bpm": music_bpm}), encoding="utf-8")
    environment = os.environ.copy()
    environment.update({"ACESTEP_CHECKPOINTS_DIR": str(ACE_MODELS), "PYTHONPATH": str(ACE_SOURCE),
                        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"})
    if progress_cb:
        progress_cb(5, f"Carregando ACE-Step {model}; pesos locais, sem downloads.")
    process = None
    try:
        with (folder / "worker.log").open("w", encoding="utf-8") as log:
            command = [str(ACE_PYTHON), str(ACE_CLI), "--request", str(request_file),
                       "--output-dir", str(folder), "--project-root", str(ACE_SOURCE)]
            if gpu_job_id:
                command += ["--gpu-job-id", gpu_job_id, "--parent-pid", str(os.getpid())]
            process = subprocess.Popen(command,
                                       cwd=str(ACE_SOURCE), env=environment, stdout=log, stderr=log,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if process_cb:
                process_cb(process)
            started = time.monotonic()
            while process.poll() is None:
                if cancel_event is not None and cancel_event.wait(0.5):
                    raise RuntimeError("Criação musical cancelada pelo proprietário.")
                if cancel_event is None:
                    time.sleep(0.5)
                if time.monotonic() - started > 3600:
                    raise TimeoutError("ACE-Step excedeu o limite de uma hora.")
            if process.returncode:
                tail = (folder / "worker.log").read_text(encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(f"ACE-Step falhou; instalação antiga preservada. {tail}")
        report = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        audio = Path(report["path"]).resolve()
        if folder.resolve() not in audio.parents or not audio.is_file():
            raise RuntimeError("Saída ACE-Step fora do diretório deste trabalho.")
        return {"data": audio.read_bytes(), "extension": ".flac", "media_type": "audio/flac",
                "model": model, "seed": seed, "duration_seconds": report["duration_seconds"],
                "runtime_commit": ACE_COMMIT}
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if process_cb:
            process_cb(None)
