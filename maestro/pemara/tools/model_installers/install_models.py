"""Instalador reexecutavel dos modelos de producao H3 e dependencias compartilhadas do Maestro.

Os artefatos sao fixados por revisao, tamanho e SHA-256 em models.lock.json.
Downloads interrompidos usam a retomada do Hugging Face/Xet ou HTTP Range.
Nenhum token e lido ou escrito pelo instalador; o huggingface_hub pode usar a
autenticacao ja configurada pelo proprietario sem expo-la no log.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
LOCK_PATH = SCRIPT_DIR / "models.lock.json"
COMPONENTS = ("all", "h3", "shared", "qwen", "rife", "foley", "wan_animate")
FOLEY_IMAGE = "pemara/hunyuanvideo-foley:cuda128"
HASH_CHUNK = 16 * 1024 * 1024
DOWNLOAD_CHUNK = 8 * 1024 * 1024
RESERVE_BYTES = 20 * 1024**3
PINNED_HF_DEPENDENCY = "huggingface_hub[hf_xet]==1.24.0"
ALLOWED_HF_REPOSITORIES = frozenset(
    {
        "Comfy-Org/MiniMax-H3",
        "tencent/HunyuanVideo-Foley",
        "google/siglip2-base-patch16-512",
        "laion/larger_clap_general",
        "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "Comfy-Org/Wan_2.1_ComfyUI_repackaged",
        "yzd-v/DWPose",
        "hr16/DWPose-TorchScript-BatchSize5",
        "Comfy-Org/gemma-4",
    }
)
ALLOWED_HTTP_URLS = frozenset(
    {
        "https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-windows.zip",
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
    }
)
ALLOWED_REDIRECT_HOSTS = frozenset(
    {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
)


@dataclass(frozen=True)
class Layout:
    target_root: Path
    repo_root: Path
    comfy_models: Path
    comfy_offloaded_models: Path
    video_tools_bin: Path
    foley_models: Path
    foley_hf_cache: Path
    dwpose_ckpts: Path
    logs: Path
    quarantine: Path
    state_file: Path

    def roots(self) -> dict[str, Path]:
        return {
            "comfy_models": self.comfy_models,
            "comfy_offloaded_models": self.comfy_offloaded_models,
            "video_tools_bin": self.video_tools_bin,
            "foley_models": self.foley_models,
            "foley_hf_cache": self.foley_hf_cache,
            "dwpose_ckpts": self.dwpose_ckpts,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instala e verifica H3, LTX 2.5, Qwen, RIFE/RealESRGAN, Foley XXL e Wan Animate do Maestro."
    )
    parser.add_argument("--action", choices=("preflight", "install", "verify"), default="install")
    parser.add_argument("--component", choices=COMPONENTS, default="all")
    parser.add_argument("--target-root", type=Path, default=None)
    parser.add_argument("--foley-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--accept-licenses", action="store_true")
    parser.add_argument("--skip-foley-image", action="store_true")
    parser.add_argument("--rebuild-foley-image", action="store_true")
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--log", type=Path, default=None)
    return parser.parse_args(argv)


def infer_target_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PEMARA_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    installed_repo = SCRIPT_DIR.parents[1]
    if installed_repo.name.casefold() == "pemara" and installed_repo.parent.name.casefold() == "maestro":
        return installed_repo.parent.parent.resolve()
    return Path(r"E:\Pemara").resolve()


def infer_foley_root(target_root: Path, repo_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_override = os.environ.get("PEMARA_FOLEY_ROOT", "").strip()
    if env_override:
        return Path(env_override).resolve()
    env_file = repo_root / ".env"
    if env_file.is_file():
        try:
            lines = env_file.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            lines = []
        for line in lines:
            if line.startswith("VIDEO_SOUND_HUNYUAN_MODEL_ROOT="):
                configured = line.split("=", 1)[1].strip().strip('"')
                if configured:
                    return Path(configured).resolve()
    active_legacy = Path(r"G:\Pemara_AI_Models\HunyuanVideo-Foley")
    if target_root == Path(r"E:\Pemara").resolve() and active_legacy.is_dir():
        return active_legacy.resolve()
    return (target_root / "AI_Models" / "HunyuanVideo-Foley").resolve()


def build_layout(target_root: Path, foley_root: Path | None = None) -> Layout:
    target = target_root.resolve()
    anchor = Path(target.anchor).resolve()
    if target == anchor or len(str(target)) < 6:
        raise ValueError(f"TargetRoot inseguro: {target}")
    repo = target / "maestro" / "pemara"
    logs = target / "logs" / "model_installers"
    foley = infer_foley_root(target, repo, foley_root)
    offloaded_override = os.environ.get("PEMARA_OFFLOADED_COMFY_ROOT", "").strip()
    if offloaded_override:
        offloaded = Path(offloaded_override).resolve()
    elif target == Path(r"E:\Pemara").resolve() and Path("D:\\").exists():
        offloaded = Path(r"D:\PemaraModels\offloaded\ComfyUI").resolve()
    else:
        offloaded = repo / "ferramentas" / "ComfyUI" / "models"
    if foley == Path(foley.anchor).resolve() or len(str(foley)) < 6:
        raise ValueError(f"FoleyRoot inseguro: {foley}")
    return Layout(
        target_root=target,
        repo_root=repo,
        comfy_models=repo / "ferramentas" / "ComfyUI" / "models",
        comfy_offloaded_models=offloaded,
        video_tools_bin=repo / "ferramentas" / "video_global_engine" / "tools" / "bin",
        foley_models=foley,
        foley_hf_cache=foley / ".cache" / "huggingface" / "hub",
        dwpose_ckpts=(
            repo
            / "ferramentas"
            / "ComfyUI"
            / "custom_nodes"
            / "comfyui_controlnet_aux"
            / "ckpts"
        ),
        logs=logs,
        quarantine=logs / "quarantine",
        state_file=logs / "verified_state.json",
    )


def configure_logging(path: Path) -> logging.Logger:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=(logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler()),
        force=True,
    )
    return logging.getLogger("maestro-model-installer")


def load_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("schema_version de models.lock.json nao suportado")
    validate_lock(data)
    return data


def _safe_relative(value: str) -> Path:
    relative = Path(value.replace("/", os.sep))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Caminho relativo inseguro no manifesto: {value}")
    return relative


def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("python_dependency") != PINNED_HF_DEPENDENCY:
        raise ValueError("Dependencia Python divergiu do valor permitido pelo codigo")
    if set(lock.get("allowed_hf_repositories", ())) != set(ALLOWED_HF_REPOSITORIES):
        raise ValueError("Allowlist HF do manifesto divergiu do codigo")
    if set(lock.get("allowed_http_hosts", ())) != set(ALLOWED_REDIRECT_HOSTS):
        raise ValueError("Allowlist HTTPS do manifesto divergiu do codigo")
    roots = {
        "comfy_models",
        "comfy_offloaded_models",
        "video_tools_bin",
        "foley_models",
        "foley_hf_cache",
        "dwpose_ckpts",
    }
    seen: set[str] = set()
    for item in lock.get("artifacts", ()):
        artifact_id = str(item.get("id", ""))
        if not artifact_id or artifact_id in seen:
            raise ValueError(f"ID ausente ou duplicado: {artifact_id!r}")
        seen.add(artifact_id)
        if item.get("component") not in COMPONENTS[1:]:
            raise ValueError(f"Componente invalido: {artifact_id}")
        if item.get("destination_root") not in roots:
            raise ValueError(f"Raiz de destino invalida: {artifact_id}")
        kind = item.get("kind")
        if kind in {"hf_file", "hf_snapshot"}:
            if item.get("repo_id") not in ALLOWED_HF_REPOSITORIES:
                raise ValueError(f"Repositorio HF fora da allowlist: {artifact_id}")
            revision = str(item.get("revision", ""))
            if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
                raise ValueError(f"Revisao HF nao fixada por commit: {artifact_id}")
        if kind in {"http_file", "http_archive"}:
            url = str(item.get("url", ""))
            parsed = urllib.parse.urlparse(url)
            if url not in ALLOWED_HTTP_URLS or parsed.scheme != "https":
                raise ValueError(f"URL fora da allowlist HTTPS: {artifact_id}")
        if kind != "hf_snapshot":
            _safe_relative(str(item.get("filename", "")))
            if item.get("destination_filename"):
                _safe_relative(str(item["destination_filename"]))
            expected = int(item.get("expected_bytes", 0))
            digest = str(item.get("sha256", ""))
            dynamic_integrity = item.get("integrity_source") == "hf_lfs_oid" and kind == "hf_file"
            if expected <= 0 or (len(digest) != 64 and not dynamic_integrity):
                raise ValueError(f"Tamanho/hash invalido: {artifact_id}")
        filename = str(item.get("filename") or "").casefold()
        if "ltx-2.3" in filename:
            consumers = item.get("ltx25_consumers")
            if (
                item.get("classification") != "LTX25_COMPATIBILITY_ASSET"
                or not isinstance(consumers, list)
                or not consumers
                or "ic-lora" not in filename
            ):
                raise ValueError(f"Artefato LTX 2.3 fora da excecao IC-LoRA 2.5: {artifact_id}")


def selected_items(lock: dict[str, Any], component: str) -> list[dict[str, Any]]:
    if component == "all":
        return list(lock["artifacts"])
    return [item for item in lock["artifacts"] if item["component"] == component]


def destination_for(item: dict[str, Any], layout: Layout) -> Path:
    root = layout.roots()[item["destination_root"]].resolve()
    filename = item.get("destination_filename") or item.get("filename")
    if not filename:
        return root
    destination = (root / _safe_relative(filename)).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"Destino escapou da raiz permitida: {item['id']}")
    return destination


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema_version": 1, "artifacts": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "artifacts": {}}
    if state.get("schema_version") != 1 or not isinstance(state.get("artifacts"), dict):
        return {"schema_version": 1, "artifacts": {}}
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity_receipt_path(layout: Layout) -> Path:
    return layout.logs / "resolved_integrity.json"


def _load_integrity_receipt(layout: Layout) -> dict[str, Any]:
    path = _integrity_receipt_path(layout)
    if not path.is_file():
        return {"schema_version": 1, "artifacts": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 1, "artifacts": {}}
    if payload.get("schema_version") != 1 or not isinstance(payload.get("artifacts"), dict):
        return {"schema_version": 1, "artifacts": {}}
    return payload


def _save_integrity_receipt(layout: Layout, receipt: dict[str, Any]) -> None:
    path = _integrity_receipt_path(layout)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def resolve_runtime_integrity(
    items: list[dict[str, Any]],
    layout: Layout,
    *,
    log: logging.Logger,
) -> list[dict[str, Any]]:
    """Resolve gated HF LFS hashes at the pinned revision and persist a safe receipt."""

    from huggingface_hub import get_hf_file_metadata, hf_hub_url
    from huggingface_hub.errors import GatedRepoError

    receipt = _load_integrity_receipt(layout)
    resolved_items: list[dict[str, Any]] = []
    for source_item in items:
        item = dict(source_item)
        digest = str(item.get("sha256") or "").casefold()
        probe_optional_access = (
            item.get("required", True) is False
            and item.get("classification") == "LTX25_COMPATIBILITY_ASSET"
        )
        if len(digest) == 64 and not probe_optional_access:
            resolved_items.append(item)
            continue
        if (
            item.get("integrity_source") != "hf_lfs_oid"
            and not probe_optional_access
        ) or item.get("kind") != "hf_file":
            raise ValueError(f"Integridade nao resolvida: {item.get('id')}")
        cached = receipt["artifacts"].get(item["id"], {})
        cache_matches = (
            cached.get("repo_id") == item.get("repo_id")
            and cached.get("revision") == item.get("revision")
            and cached.get("filename") == item.get("filename")
            and int(cached.get("expected_bytes") or 0) == int(item.get("expected_bytes") or 0)
            and len(str(cached.get("sha256") or "")) == 64
        )
        if cache_matches:
            item["sha256"] = str(cached["sha256"]).casefold()
            resolved_items.append(item)
            continue
        try:
            metadata = get_hf_file_metadata(
                hf_hub_url(
                    repo_id=item["repo_id"],
                    filename=item["filename"],
                    revision=item["revision"],
                )
            )
        except GatedRepoError:
            if item.get("required", True) is not False:
                raise
            item["_access_required"] = True
            receipt["artifacts"][item["id"]] = {
                "repo_id": item["repo_id"],
                "revision": item["revision"],
                "filename": item["filename"],
                "expected_bytes": int(item["expected_bytes"]),
                "status": "ACCESS_REQUIRED",
                "resolved_at_epoch": time.time(),
            }
            log.warning(
                "Acesso HF pendente para compatibilidade opcional %s; o nucleo LTX 2.5 continuara.",
                item["id"],
            )
            resolved_items.append(item)
            continue
        etag = str(metadata.etag or "").strip('"').casefold()
        if len(etag) != 64 or any(char not in "0123456789abcdef" for char in etag):
            raise RuntimeError(f"HF nao forneceu SHA-256 LFS valido para {item['id']}")
        remote_size = int(metadata.size or 0)
        if remote_size != int(item["expected_bytes"]):
            raise RuntimeError(
                f"Tamanho remoto divergiu para {item['id']}: {remote_size} != {item['expected_bytes']}"
            )
        item["sha256"] = etag
        receipt["artifacts"][item["id"]] = {
            "repo_id": item["repo_id"],
            "revision": item["revision"],
            "filename": item["filename"],
            "expected_bytes": int(item["expected_bytes"]),
            "sha256": etag,
            "resolved_at_epoch": time.time(),
        }
        log.info("Integridade HF resolvida em revisao fixada: %s", item["id"])
        resolved_items.append(item)
    _save_integrity_receipt(layout, receipt)
    return resolved_items


def verify_file(
    item: dict[str, Any],
    path: Path,
    state: dict[str, Any],
    *,
    use_cache: bool,
) -> tuple[bool, str]:
    if not path.is_file():
        return False, "ausente"
    stat = path.stat()
    expected_size = int(item["expected_bytes"])
    if stat.st_size != expected_size:
        return False, f"tamanho {stat.st_size}, esperado {expected_size}"
    expected_hash = str(item["sha256"]).casefold()
    cached = state["artifacts"].get(item["id"], {})
    if (
        use_cache
        and cached.get("path") == str(path)
        and cached.get("bytes") == stat.st_size
        and cached.get("mtime_ns") == stat.st_mtime_ns
        and cached.get("sha256") == expected_hash
    ):
        return True, "hash verificado (cache local imutavel)"
    actual_hash = sha256_file(path)
    if actual_hash.casefold() != expected_hash:
        return False, f"SHA-256 divergente: {actual_hash}"
    state["artifacts"][item["id"]] = {
        "path": str(path),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": expected_hash,
    }
    return True, "SHA-256 verificado"


def quarantine_file(path: Path, layout: Layout, log: logging.Logger) -> Path:
    layout.quarantine.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = layout.quarantine / f"{path.name}.{stamp}.invalid"
    counter = 1
    while target.exists():
        target = layout.quarantine / f"{path.name}.{stamp}.{counter}.invalid"
        counter += 1
    shutil.move(str(path), str(target))
    log.warning("Arquivo invalido preservado em quarentena: %s", target)
    return target


def ensure_huggingface_dependency(lock: dict[str, Any], *, dry_run: bool, log: logging.Logger) -> None:
    required = str(lock["python_dependency"])
    expected_version = required.rsplit("==", 1)[-1]
    try:
        installed_version = importlib.metadata.version("huggingface_hub")
        if installed_version == expected_version:
            importlib.import_module("huggingface_hub")
            log.info("huggingface_hub disponivel: %s", installed_version)
            return
        if dry_run:
            log.info(
                "DRY-RUN ajustaria huggingface_hub de %s para %s",
                installed_version,
                expected_version,
            )
            return
    except ImportError:
        if dry_run:
            log.info("DRY-RUN instalaria dependencia Python fixada: %s", required)
            return
    except importlib.metadata.PackageNotFoundError:
        if dry_run:
            log.info("DRY-RUN instalaria dependencia Python fixada: %s", required)
            return
    log.info("Instalando dependencia Python fixada: %s", required)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            required,
        ],
        check=True,
    )
    importlib.invalidate_caches()
    importlib.import_module("huggingface_hub")


def preflight(
    items: list[dict[str, Any]],
    layout: Layout,
    lock: dict[str, Any],
    *,
    dry_run: bool,
    build_foley_image: bool,
    log: logging.Logger,
) -> None:
    required_system = (
        layout.repo_root / "services" / "studio" / "h3_workflow.py",
        layout.repo_root / "ferramentas" / "ComfyUI",
    )
    missing_system = [str(path) for path in required_system if not path.exists()]
    if missing_system:
        raise RuntimeError("Restaure primeiro o sistema Maestro; ausente: " + ", ".join(missing_system))
    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python 3.11+ exigido; encontrado {sys.version.split()[0]}")

    missing_by_volume: dict[str, int] = {}
    for item in items:
        if item["kind"] == "hf_snapshot":
            destination = layout.roots()[item["destination_root"]]
            volume = destination.anchor or str(layout.target_root.anchor)
            missing_by_volume[volume] = missing_by_volume.get(volume, 0) + int(item.get("estimated_bytes", 0))
            continue
        destination = destination_for(item, layout)
        if not destination.is_file() or destination.stat().st_size != int(item["expected_bytes"]):
            volume = destination.anchor or str(layout.target_root.anchor)
            missing_by_volume[volume] = missing_by_volume.get(volume, 0) + int(item["expected_bytes"])
    if build_foley_image:
        volume = layout.target_root.anchor or str(layout.target_root)
        missing_by_volume[volume] = missing_by_volume.get(volume, 0) + 12 * 1024**3
    for volume, missing_bytes in missing_by_volume.items():
        usage = shutil.disk_usage(volume)
        log.info(
            "Disco %s - %.1f GiB livres; plano restante estimado %.1f GiB + reserva 20 GiB",
            volume,
            usage.free / 1024**3,
            missing_bytes / 1024**3,
        )
        if usage.free < missing_bytes + RESERVE_BYTES:
            raise RuntimeError(
                f"Espaco insuficiente em {volume}: livres {usage.free / 1024**3:.1f} GiB; "
                f"necessarios {(missing_bytes + RESERVE_BYTES) / 1024**3:.1f} GiB."
            )
    ensure_huggingface_dependency(lock, dry_run=dry_run, log=log)
    if any(item["component"] in {"h3", "shared", "qwen", "foley", "wan_animate"} for item in items):
        if shutil.which("nvidia-smi") is None:
            raise RuntimeError("Driver NVIDIA ausente: nvidia-smi nao encontrado.")
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            check=True,
            capture_output=True,
            text=True,
        )
        log.info("GPU: %s", result.stdout.strip())
    if build_foley_image and shutil.which("docker") is None:
        raise RuntimeError("Docker Desktop/CLI e exigido para construir o runtime Foley XXL.")


def download_hf_file(
    item: dict[str, Any],
    layout: Layout,
    *,
    retries: int,
    log: logging.Logger,
) -> Path:
    from huggingface_hub import hf_hub_download

    root = layout.roots()[item["destination_root"]]
    destination = destination_for(item, layout)
    root.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            log.info(
                "Baixando HF %s/%s @ %s (%d/%d)",
                item["repo_id"],
                item["filename"],
                item["revision"][:12],
                attempt,
                retries,
            )
            resolved = Path(
                hf_hub_download(
                    repo_id=item["repo_id"],
                    filename=item["filename"],
                    revision=item["revision"],
                    local_dir=root,
                )
            ).resolve()
            if resolved != destination:
                if not resolved.is_relative_to(root.resolve()):
                    raise RuntimeError(f"Hugging Face resolveu destino inseguro: {resolved}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(resolved, destination)
            return destination
        except Exception as exc:  # erro registrado e devolvido ao fim
            last_error = exc
            log.exception("Falha no download HF de %s", item["id"])
            if attempt < retries:
                time.sleep(min(30, 2**attempt))
    raise RuntimeError(f"Download HF falhou: {item['id']}") from last_error


def download_http_file(
    item: dict[str, Any],
    layout: Layout,
    *,
    retries: int,
    log: logging.Logger,
) -> Path:
    destination = destination_for(item, layout)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        existing = partial.stat().st_size if partial.is_file() else 0
        headers = {"User-Agent": "Pemara-Maestro-Model-Installer/1.0"}
        if existing:
            headers["Range"] = f"bytes={existing}-"
        request = urllib.request.Request(item["url"], headers=headers)
        try:
            log.info("Baixando HTTPS %s (%d/%d, retomada=%d bytes)", item["id"], attempt, retries, existing)
            with urllib.request.urlopen(request, timeout=60) as response:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or final.hostname not in ALLOWED_REDIRECT_HOSTS:
                    raise RuntimeError(f"Redirect fora da allowlist: {response.geturl()}")
                append = existing > 0 and getattr(response, "status", 200) == 206
                mode = "ab" if append else "wb"
                with partial.open(mode) as stream:
                    while chunk := response.read(DOWNLOAD_CHUNK):
                        stream.write(chunk)
            os.replace(partial, destination)
            return destination
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            last_error = exc
            log.exception("Falha no download HTTPS de %s", item["id"])
            if attempt < retries:
                time.sleep(min(30, 2**attempt))
    raise RuntimeError(f"Download HTTPS falhou: {item['id']}") from last_error


def safe_extract_zip(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    resolved_root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            candidate = (resolved_root / Path(member.filename.replace("/", os.sep))).resolve()
            if candidate != resolved_root and resolved_root not in candidate.parents:
                raise RuntimeError(f"ZIP traversal bloqueado: {member.filename}")
        bundle.extractall(resolved_root)


def ensure_archive_extracted(item: dict[str, Any], layout: Layout, *, log: logging.Logger) -> None:
    root = layout.roots()[item["destination_root"]]
    extract_root = (root / _safe_relative(item["extract_relative"])).resolve()
    required = (extract_root / _safe_relative(item["required_after_extract"])).resolve()
    if required.is_file():
        log.info("RIFE ja extraido: %s", required)
        return
    log.info("Extraindo %s em %s", item["id"], extract_root)
    safe_extract_zip(destination_for(item, layout), extract_root)
    if not required.is_file():
        raise RuntimeError(f"Extracao incompleta; ausente: {required}")


def install_snapshot(item: dict[str, Any], layout: Layout, *, log: logging.Logger) -> None:
    from huggingface_hub import snapshot_download

    cache_dir = layout.roots()[item["destination_root"]]
    cache_dir.mkdir(parents=True, exist_ok=True)
    log.info("Baixando snapshot HF %s @ %s", item["repo_id"], item["revision"][:12])
    snapshot = Path(
        snapshot_download(
            repo_id=item["repo_id"],
            revision=item["revision"],
            cache_dir=cache_dir,
            allow_patterns=item.get("allow_patterns"),
        )
    )
    required = snapshot / item["required_snapshot_file"]
    if not required.exists():
        raise RuntimeError(f"Snapshot incompleto; ausente: {required}")


def snapshot_ready(item: dict[str, Any], layout: Layout) -> bool:
    repo_cache = "models--" + item["repo_id"].replace("/", "--")
    required = (
        layout.roots()[item["destination_root"]]
        / repo_cache
        / "snapshots"
        / item["revision"]
        / item["required_snapshot_file"]
    )
    return required.exists()


def install_files(
    items: list[dict[str, Any]],
    layout: Layout,
    state: dict[str, Any],
    *,
    dry_run: bool,
    retries: int,
    log: logging.Logger,
) -> None:
    for item in items:
        if item.get("_access_required"):
            state["artifacts"][item["id"]] = {
                "status": "ACCESS_REQUIRED",
                "repo_id": item.get("repo_id"),
                "revision": item.get("revision"),
            }
            save_state(layout.state_file, state)
            log.warning("SKIP opcional sem acesso HF: %s", item["id"])
            continue
        if item["kind"] == "hf_snapshot":
            ready = snapshot_ready(item, layout)
            if dry_run:
                log.info("DRY-RUN snapshot %s: %s", item["id"], "presente" if ready else "baixar")
            elif ready:
                log.info("Snapshot presente: %s", item["id"])
            else:
                install_snapshot(item, layout, log=log)
            continue

        destination = destination_for(item, layout)
        if dry_run:
            if destination.is_file() and destination.stat().st_size == int(item["expected_bytes"]):
                log.info("DRY-RUN %s: presente com tamanho correto", item["id"])
            else:
                log.info("DRY-RUN %s: baixar para %s", item["id"], destination)
            if item["kind"] == "http_archive":
                root = layout.roots()[item["destination_root"]]
                required = (
                    root
                    / _safe_relative(item["extract_relative"])
                    / _safe_relative(item["required_after_extract"])
                )
                log.info("DRY-RUN extracao %s: %s", item["id"], "presente" if required.is_file() else "necessaria")
            continue

        valid, reason = verify_file(item, destination, state, use_cache=True)
        if valid:
            log.info("OK existente %s: %s", item["id"], reason)
        else:
            if destination.exists():
                quarantine_file(destination, layout, log)
            try:
                if item["kind"] == "hf_file":
                    download_hf_file(item, layout, retries=retries, log=log)
                else:
                    download_http_file(item, layout, retries=retries, log=log)
            except Exception:
                if item.get("required", True) is not False:
                    raise
                state["artifacts"][item["id"]] = {
                    "status": "OPTIONAL_UNAVAILABLE",
                    "repo_id": item.get("repo_id"),
                    "revision": item.get("revision"),
                }
                save_state(layout.state_file, state)
                log.warning("Compatibilidade opcional indisponivel; continuando: %s", item["id"])
                continue
            valid, reason = verify_file(item, destination, state, use_cache=False)
            if not valid:
                quarantine_file(destination, layout, log)
                raise RuntimeError(f"Verificacao falhou apos download de {item['id']}: {reason}")
            log.info("INSTALADO %s: %s", item["id"], reason)
            save_state(layout.state_file, state)
        if item["kind"] == "http_archive":
            ensure_archive_extracted(item, layout, log=log)
    save_state(layout.state_file, state)


def docker_image_exists() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", FOLEY_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def build_foley_image(layout: Layout, *, rebuild: bool, dry_run: bool, log: logging.Logger) -> None:
    source = layout.repo_root / "ferramentas" / "audio_neural" / "HunyuanVideo-Foley"
    dockerfile = layout.repo_root / "ferramentas" / "audio_neural" / "hunyuan_gpu" / "Dockerfile"
    if not source.is_dir() or not dockerfile.is_file():
        raise RuntimeError("Codigo/Dockerfile oficial do Foley ausente no sistema restaurado.")
    exists = docker_image_exists()
    if dry_run:
        log.info("DRY-RUN Docker Foley: %s", "imagem presente" if exists else "construir imagem")
        return
    if exists and not rebuild:
        log.info("Imagem Docker Foley ja presente: %s", FOLEY_IMAGE)
        return
    subprocess.run(
        ["docker", "build", "--pull", "-f", str(dockerfile), "-t", FOLEY_IMAGE, str(source)],
        check=True,
    )
    if not docker_image_exists():
        raise RuntimeError("Docker build terminou sem registrar a imagem Foley esperada.")
    log.info("Imagem Docker Foley pronta: %s", FOLEY_IMAGE)


def verify_installation(
    items: list[dict[str, Any]],
    layout: Layout,
    state: dict[str, Any],
    *,
    require_foley_image: bool,
    log: logging.Logger,
) -> None:
    failures: list[str] = []
    for item in items:
        if item.get("_access_required"):
            log.warning("NAO VERIFICADO opcional sem acesso HF: %s", item["id"])
            continue
        if item["kind"] == "hf_snapshot":
            if not snapshot_ready(item, layout):
                failures.append(f"snapshot ausente: {item['id']}")
            else:
                log.info("VERIFICADO snapshot: %s", item["id"])
            continue
        path = destination_for(item, layout)
        valid, reason = verify_file(item, path, state, use_cache=True)
        if not valid:
            if item.get("required", True) is False:
                log.warning("OPCIONAL ausente %s: %s", item["id"], reason)
            else:
                failures.append(f"{item['id']}: {reason}")
        else:
            log.info("VERIFICADO %s: %s", item["id"], reason)
        if item["kind"] == "http_archive":
            root = layout.roots()[item["destination_root"]]
            required = (
                root
                / _safe_relative(item["extract_relative"])
                / _safe_relative(item["required_after_extract"])
            )
            if not required.is_file():
                failures.append(f"RIFE extraido ausente: {required}")
    if require_foley_image and not docker_image_exists():
        failures.append(f"imagem Docker ausente: {FOLEY_IMAGE}")
    save_state(layout.state_file, state)
    if failures:
        raise RuntimeError("Verificacao final falhou:\n- " + "\n- ".join(failures))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = infer_target_root(args.target_root)
    layout = build_layout(target, args.foley_root)
    default_log = layout.logs / f"install_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log = configure_logging(args.log or default_log)
    try:
        if args.retries < 1:
            raise ValueError("--retries deve ser pelo menos 1")
        lock = load_lock()
        items = selected_items(lock, args.component)
        if not items:
            raise RuntimeError(f"Nenhum artefato para {args.component}")
        installing = args.action == "install" and not args.dry_run
        if installing and not args.accept_licenses:
            raise RuntimeError(
                "Confirme as licencas dos modelos selecionados com --accept-licenses."
            )
        build_image = args.component in {"all", "foley"} and not args.skip_foley_image
        preflight(
            items,
            layout,
            lock,
            dry_run=args.dry_run or args.action != "install",
            build_foley_image=build_image,
            log=log,
        )
        state = load_state(layout.state_file)
        if args.action == "preflight":
            log.info("PREFLIGHT OK: %s", args.component)
            return 0
        if not (args.action == "install" and args.dry_run):
            items = resolve_runtime_integrity(items, layout, log=log)
        if args.action == "install":
            install_files(
                items,
                layout,
                state,
                dry_run=args.dry_run,
                retries=args.retries,
                log=log,
            )
            if build_image:
                build_foley_image(layout, rebuild=args.rebuild_foley_image, dry_run=args.dry_run, log=log)
            if args.dry_run:
                log.info("DRY-RUN OK: nenhuma alteracao foi feita.")
                return 0
        verify_installation(
            items,
            layout,
            state,
            require_foley_image=build_image,
            log=log,
        )
        if args.action == "verify":
            log.info("PASS componentes %s verificados.", args.component)
        else:
            log.info("PASS modelos %s instalados e verificados.", args.component)
        return 0
    except Exception:
        log.exception("FALHOU instalador de modelos")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
