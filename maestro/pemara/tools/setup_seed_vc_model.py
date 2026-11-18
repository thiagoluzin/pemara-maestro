"""Install owner-authorized pinned local conversion and separation weights."""
import hashlib
import json
from pathlib import Path
import shutil
import time

REVISION = 'fd2fe4c3195bc410f8b817bf7c7519fd822686fb'
ROOT = Path('G:/Pemara_AI_Models/SeedVC')
ASSETS = (
    ('SeedVC-MLX-GGUF/seed-vc-mlx-f16.gguf', 3629186752,
     '39b79042fd5560a1c642ac96cef451dbc81c08880f85e9c4b92b685add60f500'),
    ('HTDemucs-GGUF/htdemucs-f16.gguf', 84059168,
     'f8c54ba35df95aafea7881eac214b58ec18a73cbcb6ff5a90f4b762631a286b6'),
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def install():
    ROOT.mkdir(parents=True, exist_ok=True)
    for filename, size, checksum in ASSETS:
        target = ROOT / Path(filename).name
        if target.exists():
            if target.stat().st_size != size or digest(target) != checksum:
                raise RuntimeError('Existing model differs; preserved without overwrite.')
            print(f'{target.name}: installed and SHA-256 verified.', flush=True)
            continue
        from huggingface_hub import hf_hub_download
        cached = Path(hf_hub_download('audio-cpp/audio.cpp-gguf', filename,
                                     revision=REVISION, token=False))
        if cached.stat().st_size != size or digest(cached) != checksum:
            raise RuntimeError('Downloaded model failed integrity; cache preserved.')
        with cached.open('rb') as source, target.open('xb') as destination:
            shutil.copyfileobj(source, destination, 8 * 1024 * 1024)
        if digest(target) != checksum:
            raise RuntimeError('Copied model failed integrity; preserved for diagnosis.')
        target.with_suffix('.installation.json').write_text(json.dumps({
            'repository': 'audio-cpp/audio.cpp-gguf', 'filename': filename,
            'revision': REVISION, 'sha256': checksum, 'size': size,
            'installedAt': time.time(),
            'ownerAuthorization': '2026-11-06 current chat: Sim, adicionar Seed-VC local',
        }, indent=2), encoding='utf-8')
        print(f'{target.name}: installed and SHA-256 verified.', flush=True)


if __name__ == '__main__':
    install()
