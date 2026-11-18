"""Package existing media without changing its bytes; ZIP CRC detects truncation."""
import hashlib
import json
import os
from pathlib import Path
import threading
import uuid
import zipfile

_LOCKS = [threading.Lock() for _ in range(8)]
_VERIFIED = {}


def _token(path: Path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def prepare_verified_zip(source: Path, cache_root: Path, filename: str = "") -> Path:
    source = source.resolve(strict=True)
    name = Path(str(filename or source.name).replace("\\", "/")).name
    if not name or name in {".", "..", "VERIFICAR.json", "LEIA-ME.txt"} or any(ord(c) < 32 for c in name):
        raise ValueError("Nome de download invalido")
    before = _token(source)
    key = hashlib.sha256(f"{source}|{before}|{name}|zip-stored-v1".encode()).hexdigest()
    target = cache_root / f"{key}.zip"
    with _LOCKS[int(key[:8], 16) % len(_LOCKS)]:
        if target.is_file() and target.stat().st_size > 0:
            cached_token = _token(target)
            if _VERIFIED.get(str(target)) == cached_token:
                return target
            try:
                with zipfile.ZipFile(target) as archive:
                    receipt = json.loads(archive.read("VERIFICAR.json"))
                    valid = (set(archive.namelist()) == {name, "VERIFICAR.json", "LEIA-ME.txt"}
                             and receipt.get("file") == name and receipt.get("bytes") == before[0]
                             and archive.getinfo(name).file_size == before[0] and archive.testzip() is None)
                if valid:
                    if len(_VERIFIED) >= 256:
                        _VERIFIED.clear()
                    _VERIFIED[str(target)] = cached_token
                    return target
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                pass
        cache_root.mkdir(parents=True, exist_ok=True)
        temporary = cache_root / f"{key}.{uuid.uuid4().hex}.tmp.zip"
        try:
            digest = hashlib.sha256()
            count = 0
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                with source.open("rb") as original, archive.open(name, "w", force_zip64=before[0] >= 2**31) as output:
                    for chunk in iter(lambda: original.read(1024 * 1024), b""):
                        output.write(chunk)
                        digest.update(chunk)
                        count += len(chunk)
                if count != before[0] or _token(source) != before:
                    raise OSError("Arquivo de origem mudou durante o preparo; tente novamente")
                archive.writestr("VERIFICAR.json", json.dumps({"file": name, "bytes": count,
                    "sha256": digest.hexdigest(), "media_bytes_unchanged": True}, ensure_ascii=False, indent=2))
                archive.writestr("LEIA-ME.txt", "Baixe este ZIP por completo e extraia pelo app Arquivos.\n"
                    "Se o app informar erro na extracao, o download esta incompleto ou danificado: baixe novamente.\n"
                    "O arquivo de midia e identico ao original, sem reducao de qualidade.\n"
                    "VERIFICAR.json informa seu tamanho exato e SHA-256.\n")
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise OSError("Falha na verificacao do pacote")
            os.replace(temporary, target)
            if len(_VERIFIED) >= 256:
                _VERIFIED.clear()
            _VERIFIED[str(target)] = _token(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target
