"""Local MP3 delivery; source recordings are never changed."""
import hashlib
import os
from pathlib import Path
import subprocess
import threading
from urllib.parse import parse_qs, quote, urlsplit
import uuid

_LOCKS = [threading.Lock() for _ in range(8)]
_AUDIO_SUFFIXES = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".aiff", ".aif"}


def mp3_filename(name: str) -> str:
    stem = str(name).replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    stem = "".join(c if c.isalnum() or c in " -_()" else "_" for c in stem)
    return (stem.strip(" ._")[:120] or "Musica") + ".mp3"


def mp3_disposition(name: str, download: bool) -> str:
    filename = mp3_filename(name)
    ascii_name = filename.encode("ascii", errors="replace").decode().replace("?", "_")
    mode = "attachment" if download else "inline"
    return f'{mode}; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


def resolve_audio_source(source: str, studio_root: Path, comfy_resolver) -> Path:
    """Accept existing output URLs only, never fetch a service or remote URL."""
    url = urlsplit(source)
    if url.scheme or url.netloc or url.fragment:
        raise ValueError("Origem de audio invalida")
    query = parse_qs(url.query, keep_blank_values=True)
    if any(len(values) != 1 for values in query.values()):
        raise ValueError("Origem de audio invalida")
    if url.path == "/api/generative/output":
        relative = query.get("path", [""])[0].replace("\\", "/")
        if not relative or Path(relative).is_absolute() or Path(relative).drive or ".." in Path(relative).parts:
            raise ValueError("Caminho de audio invalido")
        root = studio_root.resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Caminho de audio invalido")
    elif url.path == "/api/generative/comfy-view":
        resolved = comfy_resolver(query.get("filename", [""])[0],
                                  query.get("subfolder", [""])[0],
                                  query.get("type", ["output"])[0])
        if not resolved:
            raise FileNotFoundError("Audio nao encontrado no armazenamento local")
        path = Path(resolved)
    else:
        raise ValueError("Origem de audio invalida")
    if not path.is_file():
        raise FileNotFoundError("Audio nao encontrado")
    if path.suffix.lower() not in _AUDIO_SUFFIXES:
        raise ValueError("Este arquivo nao e um audio compativel")
    return path


def prepare_mp3(source: Path, cache_root: Path, ffmpeg: str) -> Path:
    source = source.resolve(strict=True)
    if source.suffix.lower() == ".mp3":
        return source
    stat = source.stat()
    key = hashlib.sha256(f"{source}|{stat.st_mtime_ns}|{stat.st_size}|lame320-v1".encode()).hexdigest()
    target = cache_root / f"{key}.mp3"
    with _LOCKS[int(key[:8], 16) % len(_LOCKS)]:
        if target.is_file() and target.stat().st_size > 0:
            return target
        cache_root.mkdir(parents=True, exist_ok=True)
        temporary = cache_root / f"{key}.{uuid.uuid4().hex}.tmp.mp3"
        try:
            result = subprocess.run([
                ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(source), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame",
                "-b:a", "320k", "-id3v2_version", "3", str(temporary),
            ], capture_output=True, timeout=300, creationflags=0x08000000 if os.name == "nt" else 0)
            if result.returncode or not temporary.is_file() or temporary.stat().st_size == 0:
                raise RuntimeError("Nao foi possivel converter este audio para MP3")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return target
