"""Model-independent video-to-sound providers for Maestro Studio.

This module only orchestrates trained audio engines and measures their output.
It never synthesizes waveforms or creative DSP in Python.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


ProgressCallback = Callable[[int, str], None]
_PROVIDER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_HUNYUAN_PROCESS_LOCK = threading.Lock()


class VideoSoundError(RuntimeError):
    """A provider or its resource gate refused a video-to-sound job."""


class VideoSoundCancelled(VideoSoundError):
    """The owner cancelled an active video-to-sound job."""


@dataclass(frozen=True)
class VideoSoundRequest:
    job_id: str
    source_video: Path
    output_dir: Path
    prompt: str
    negative_prompt: str = ""
    duration_seconds: float = 0.0
    seed: int = -1


@dataclass(frozen=True)
class VideoSoundResult:
    provider_id: str
    model: str
    audio_path: Path
    source_video_sha256: str
    qc: dict[str, Any]
    generation: dict[str, Any]


def _safe_output_path(output_dir: Path, extension: str) -> Path:
    output_dir = Path(output_dir).resolve()
    extension = str(extension or ".wav").strip().lower()
    if not re.fullmatch(r"\.[a-z0-9]{2,8}", extension):
        raise ValueError("outputExtension invalida para provider video-to-sound.")
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate = (output_dir / f"candidate{extension}").resolve()
    if candidate.parent != output_dir:
        raise ValueError("Saida do provider escapou da pasta do job.")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_checked(argv: list[str], *, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "falha sem detalhes").strip()[-1600:]
        raise VideoSoundError(f"Executor video-to-sound falhou ({result.returncode}): {detail}")
    return result


def probe_audio(path: Path) -> dict[str, Any]:
    result = _run_checked([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,sample_rate,channels,bits_per_sample:format=duration",
        "-of", "json", str(path),
    ])
    payload = json.loads(result.stdout)
    stream = next(
        (item for item in payload.get("streams", []) if item.get("sample_rate")),
        {},
    )
    if not stream:
        raise VideoSoundError("O provider nao entregou uma faixa de audio valida.")
    duration = float((payload.get("format") or {}).get("duration") or 0)
    if duration <= 0:
        raise VideoSoundError("A faixa gerada tem duracao invalida.")
    return {
        "durationSeconds": round(duration, 6),
        "sampleRate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "codec": str(stream.get("codec_name") or ""),
        "bitsPerSample": int(stream.get("bits_per_sample") or 0),
        "sha256": _sha256(path),
    }


def probe_video_duration(path: Path) -> float:
    result = _run_checked([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise VideoSoundError("Nao foi possivel medir a duracao do video.") from exc
    if duration <= 0:
        raise VideoSoundError("O video tem duracao invalida.")
    return duration


class VideoSoundProvider:
    provider_id = ""
    label = ""
    model = ""
    min_duration_seconds = 0.5
    max_duration_seconds = 15.0
    output_extension = ".wav"

    def status(self) -> dict[str, Any]:
        raise NotImplementedError

    def generate(
        self,
        request: VideoSoundRequest,
        progress_cb: ProgressCallback,
        cancel_event: threading.Event,
    ) -> VideoSoundResult:
        raise NotImplementedError

    def validate_request(self, request: VideoSoundRequest) -> None:
        if not request.source_video.resolve().is_file():
            raise FileNotFoundError(request.source_video)
        if request.source_video.suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv"}:
            raise ValueError("Video-to-sound aceita MP4, MOV, WebM ou MKV.")
        prompt = str(request.prompt or "").strip()
        if len(prompt) < 12 or len(prompt) > 4000:
            raise ValueError("A direcao sonora deve ter entre 12 e 4000 caracteres.")
        duration = float(request.duration_seconds or 0)
        if duration and not self.min_duration_seconds <= duration <= self.max_duration_seconds:
            raise ValueError(
                f"Duracao deve ficar entre {self.min_duration_seconds:g} e "
                f"{self.max_duration_seconds:g} segundos para {self.label}."
            )


class VideoSoundProviderRegistry:
    def __init__(self):
        self._providers: dict[str, VideoSoundProvider] = {}

    def register(self, provider: VideoSoundProvider) -> None:
        provider_id = str(provider.provider_id or "").strip().lower()
        if not _PROVIDER_ID_RE.fullmatch(provider_id):
            raise ValueError("providerId video-to-sound invalido.")
        if provider_id in self._providers:
            raise ValueError(f"Provider video-to-sound duplicado: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> VideoSoundProvider:
        provider_id = str(provider_id or "").strip().lower()
        provider = self._providers.get(provider_id)
        if provider is None:
            raise ValueError("Provider video-to-sound desconhecido.")
        return provider

    def status(self) -> dict[str, Any]:
        providers = [provider.status() for provider in self._providers.values()]
        configured = [item for item in providers if item.get("configured")]
        default = (configured or providers or [{}])[0].get("providerId", "")
        return {
            "ok": True,
            "contractVersion": "1.0",
            "defaultProviderId": default,
            "providers": providers,
            "humanReviewRequired": True,
            "autoAttach": False,
        }


class ExternalCommandVideoSoundProvider(VideoSoundProvider):
    """Trusted server-side argv adapter for a local trained model runtime."""

    _PLACEHOLDERS = {
        "input_video", "output_audio", "prompt", "negative_prompt",
        "duration_seconds", "seed", "job_id",
    }

    def __init__(self, spec: dict[str, Any]):
        self.provider_id = str(spec.get("id") or "").strip().lower()
        self.label = str(spec.get("label") or self.provider_id).strip()
        self.model = str(spec.get("model") or "external-model").strip()
        self.enabled = bool(spec.get("enabled", False))
        self.output_extension = str(spec.get("outputExtension") or ".wav").lower()
        self.min_duration_seconds = float(spec.get("minDurationSeconds") or 0.5)
        self.max_duration_seconds = float(spec.get("maxDurationSeconds") or 15.0)
        argv_template = spec.get("argvTemplate")
        if not isinstance(argv_template, list) or not argv_template or not all(
            isinstance(item, str) and item for item in argv_template
        ):
            raise ValueError("argvTemplate deve ser uma lista de argumentos, nunca uma string shell.")
        self.argv_template = tuple(argv_template)
        required_paths = spec.get("requiredPaths", [])
        if not isinstance(required_paths, list) or not all(isinstance(p, str) and Path(p).is_absolute() for p in required_paths):
            raise ValueError("requiredPaths exige caminhos absolutos locais.")
        self.required_paths = tuple(Path(p) for p in required_paths)
        if not re.fullmatch(r"\.[a-z0-9]{2,8}", self.output_extension):
            raise ValueError("outputExtension invalida para provider video-to-sound.")

    def status(self) -> dict[str, Any]:
        executable = self.argv_template[0]
        installed = Path(executable).is_file() if Path(executable).is_absolute() else bool(shutil.which(executable))
        missing_paths = [str(p) for p in self.required_paths if not p.is_file()]
        configured = bool(self.enabled and installed and not missing_paths)
        return {
            "providerId": self.provider_id,
            "label": self.label,
            "model": self.model,
            "configured": configured,
            "message": "Pronto." if configured else ("Arquivos do modelo incompletos." if missing_paths else "Provider desativado ou executor nao encontrado."),
            "missingPaths": missing_paths,
            "minDurationSeconds": self.min_duration_seconds,
            "maxDurationSeconds": self.max_duration_seconds,
            "formats": [self.output_extension.lstrip(".")],
            "device": "provider-defined",
        }

    def generate(
        self,
        request: VideoSoundRequest,
        progress_cb: ProgressCallback,
        cancel_event: threading.Event,
    ) -> VideoSoundResult:
        self.validate_request(request)
        if not self.status()["configured"]:
            raise VideoSoundError(self.status()["message"])
        if cancel_event.is_set():
            raise VideoSoundCancelled("Geracao cancelada antes de iniciar.")
        output = _safe_output_path(request.output_dir, self.output_extension)
        values = {
            "input_video": str(request.source_video.resolve()),
            "output_audio": str(output),
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "duration_seconds": f"{float(request.duration_seconds or 0):g}",
            "seed": str(int(request.seed)),
            "job_id": request.job_id,
        }
        argv = [item.format_map(values) for item in self.argv_template]
        progress_cb(15, f"Iniciando {self.label}.")
        result = subprocess.run(argv, capture_output=True, text=True, shell=False)
        if cancel_event.is_set():
            raise VideoSoundCancelled("Geracao cancelada pelo proprietario.")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "falha sem detalhes").strip()[-1600:]
            raise VideoSoundError(f"{self.label} falhou ({result.returncode}): {detail}")
        if not output.is_file() or output.stat().st_size <= 0:
            raise VideoSoundError(f"{self.label} terminou sem criar o audio esperado.")
        progress_cb(90, "Medindo candidato de audio.")
        qc = probe_audio(output) if output.stat().st_size > 44 else {"sha256": _sha256(output)}
        return VideoSoundResult(
            provider_id=self.provider_id,
            model=self.model,
            audio_path=output,
            source_video_sha256=_sha256(request.source_video),
            qc=qc,
            generation={"seed": request.seed, "durationSeconds": request.duration_seconds},
        )


class HunyuanVideoFoleyProvider(VideoSoundProvider):
    provider_id = "hunyuan_video_foley_xxl"
    label = "HunyuanVideo-Foley XXL"
    model = "Tencent HunyuanVideo-Foley XXL"
    min_duration_seconds = 0.5
    max_duration_seconds = 15.0
    output_extension = ".wav"

    DEFAULT_NEGATIVE = (
        "music, soundtrack, melody, rhythm, drums, vocals, speech, dialogue, announcer, "
        "synthesizer, chiptune, retro game sound, cartoon, clipping"
    )

    def __init__(
        self,
        *,
        model_root: Path,
        image: str = "pemara/hunyuanvideo-foley:cuda128",
        gpu_id: int = 0,
        min_free_vram_mb: int = 24000,
        comfy_queue_url: str = "http://127.0.0.1:8188/queue",
    ):
        self.model_root = Path(model_root)
        self.image = str(image)
        self.gpu_id = int(gpu_id)
        self.min_free_vram_mb = int(min_free_vram_mb)
        self.comfy_queue_url = str(comfy_queue_url)

    def _docker_image_ready(self) -> bool:
        if not shutil.which("docker"):
            return False
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", self.image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                shell=False,
            )
            return result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def status(self) -> dict[str, Any]:
        needs = []
        if not self.model_root.is_dir():
            needs.append(f"pesos em {self.model_root}")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            needs.append("ffmpeg/ffprobe")
        if not self._docker_image_ready():
            needs.append(f"imagem Docker {self.image}")
        configured = not needs
        return {
            "providerId": self.provider_id,
            "label": self.label,
            "model": self.model,
            "configured": configured,
            "message": "Pronto para piloto." if configured else "Falta: " + ", ".join(needs),
            "minDurationSeconds": self.min_duration_seconds,
            "maxDurationSeconds": self.max_duration_seconds,
            "formats": ["wav"],
            "device": f"cuda:{self.gpu_id}",
            "requiresExclusiveGpu": True,
            "minimumFreeVramMb": self.min_free_vram_mb,
        }

    def _assert_resources(self) -> None:
        status = self.status()
        if not status["configured"]:
            raise VideoSoundError(status["message"])
        try:
            with urllib.request.urlopen(self.comfy_queue_url, timeout=3) as response:
                queue = json.loads(response.read().decode("utf-8"))
            if queue.get("queue_running") or queue.get("queue_pending"):
                raise VideoSoundError("A fila principal de video esta ocupada; o som nao tomou a GPU.")
        except VideoSoundError:
            raise
        except (OSError, ValueError, urllib.error.URLError):
            raise VideoSoundError("Nao foi possivel confirmar a fila principal da GPU.")
        result = _run_checked([
            "nvidia-smi", f"--id={self.gpu_id}", "--query-gpu=memory.free",
            "--format=csv,noheader,nounits",
        ], timeout=10)
        match = re.search(r"\d+", result.stdout)
        free_mb = int(match.group(0)) if match else 0
        if free_mb < self.min_free_vram_mb:
            raise VideoSoundError(
                f"RTX sem VRAM livre suficiente: {free_mb} MB; minimo {self.min_free_vram_mb} MB."
            )

    def generate(
        self,
        request: VideoSoundRequest,
        progress_cb: ProgressCallback,
        cancel_event: threading.Event,
    ) -> VideoSoundResult:
        self.validate_request(request)
        if not _HUNYUAN_PROCESS_LOCK.acquire(blocking=False):
            raise VideoSoundError("Outro job video-to-sound ja esta usando o motor Hunyuan.")
        container_name = f"maestro-videosound-{re.sub(r'[^a-z0-9]', '', request.job_id.lower())[:32]}"
        try:
            self._assert_resources()
            output_dir = request.output_dir.resolve()
            input_dir = output_dir / "input"
            raw_dir = output_dir / "raw"
            input_dir.mkdir(parents=True, exist_ok=True)
            raw_dir.mkdir(parents=True, exist_ok=True)
            proxy = input_dir / "source_512x288_24fps.mp4"
            duration = float(request.duration_seconds or self.max_duration_seconds)
            progress_cb(8, "Preparando proxy visual na GPU.")
            _run_checked([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-hwaccel", "cuda",
                "-i", str(request.source_video), "-an", "-vf", "scale=512:288:flags=lanczos,fps=24",
                "-t", f"{duration:g}", "-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq",
                "-cq", "18", "-b:v", "0", "-pix_fmt", "yuv420p", str(proxy),
            ], timeout=180)
            csv_path = input_dir / "job.csv"
            with csv_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["video", "prompt"])
                writer.writerow(["/input/source_512x288_24fps.mp4", request.prompt.strip()])
            negative = request.negative_prompt.strip() or self.DEFAULT_NEGATIVE
            argv = [
                "docker", "run", "--rm", "--name", container_name, "--gpus", "all",
                "--env", "HF_HUB_OFFLINE=1", "--env", "TRANSFORMERS_OFFLINE=1",
                "--mount", f"type=bind,source={self.model_root.resolve()},target=/models,readonly",
                "--mount", f"type=bind,source={input_dir},target=/input,readonly",
                "--mount", f"type=bind,source={raw_dir},target=/output",
                self.image,
                "--model_path", "/models", "--model_size", "xxl", "--device", "cuda",
                "--gpu_id", str(self.gpu_id), "--csv_path", "/input/job.csv",
                "--neg_prompt", negative, "--output_dir", "/output",
                "--audio_length", f"{duration:g}", "--num_inference_steps", "50",
            ]
            log_path = output_dir / "generation.log"
            progress_cb(15, f"{self.label} lendo movimento e eventos do video.")
            with log_path.open("w", encoding="utf-8", errors="replace") as log:
                process = subprocess.Popen(
                    argv, stdout=log, stderr=subprocess.STDOUT, text=True, shell=False,
                )
                started = time.monotonic()
                while process.poll() is None:
                    if cancel_event.wait(1.0):
                        subprocess.run(
                            ["docker", "stop", "--time", "5", container_name],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=15,
                            shell=False,
                        )
                        raise VideoSoundCancelled("Geracao video-to-sound cancelada pelo proprietario.")
                    elapsed = max(1.0, time.monotonic() - started)
                    progress = min(82, 15 + int(elapsed / 4))
                    progress_cb(progress, f"{self.label} ativo na RTX 5090.")
                if process.returncode != 0:
                    tail = log_path.read_text(encoding="utf-8", errors="replace")[-1800:]
                    raise VideoSoundError(f"{self.label} falhou ({process.returncode}): {tail}")
            raw = raw_dir / "0000.wav"
            if not raw.is_file():
                raise VideoSoundError("Hunyuan terminou sem entregar 0000.wav.")
            candidate = _safe_output_path(output_dir, ".wav")
            progress_cb(88, "Conformando candidato em WAV 48 kHz estereo, sem sintese procedural.")
            _run_checked([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
                "-af", f"apad=pad_dur={duration:g},atrim=duration={duration:g}",
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(candidate),
            ], timeout=120)
            qc = probe_audio(candidate)
            progress_cb(96, "Candidato medido; aguardando registro para escuta humana.")
            return VideoSoundResult(
                provider_id=self.provider_id,
                model=self.model,
                audio_path=candidate,
                source_video_sha256=_sha256(request.source_video),
                qc=qc,
                generation={
                    "seed": request.seed,
                    "durationSeconds": duration,
                    "steps": 50,
                    "device": f"cuda:{self.gpu_id}",
                    "containerImage": self.image,
                    "log": str(log_path),
                },
            )
        finally:
            _HUNYUAN_PROCESS_LOCK.release()


def load_external_provider_specs(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or int(payload.get("version") or 0) != 1:
        raise ValueError("Arquivo de providers video-to-sound deve usar version 1.")
    providers = payload.get("providers")
    if not isinstance(providers, list):
        raise ValueError("providers deve ser uma lista.")
    return [item for item in providers if isinstance(item, dict)]


def build_default_registry(base_dir: Path) -> VideoSoundProviderRegistry:
    base_dir = Path(base_dir).resolve()
    registry = VideoSoundProviderRegistry()
    registry.register(HunyuanVideoFoleyProvider(
        model_root=Path(os.environ.get(
            "VIDEO_SOUND_HUNYUAN_MODEL_ROOT",
            r"G:\Pemara_AI_Models\HunyuanVideo-Foley",
        )),
        image=os.environ.get(
            "VIDEO_SOUND_HUNYUAN_DOCKER_IMAGE",
            "pemara/hunyuanvideo-foley:cuda128",
        ),
        gpu_id=int(os.environ.get("VIDEO_SOUND_GPU_ID", "0")),
        min_free_vram_mb=int(os.environ.get("VIDEO_SOUND_MIN_FREE_VRAM_MB", "24000")),
        comfy_queue_url=os.environ.get(
            "VIDEO_SOUND_COMFY_QUEUE_URL",
            "http://127.0.0.1:8188/queue",
        ),
    ))
    config = base_dir / "ferramentas" / "audio_neural" / "video_sound" / "providers.json"
    for spec in load_external_provider_specs(config):
        registry.register(ExternalCommandVideoSoundProvider(spec))
    return registry
