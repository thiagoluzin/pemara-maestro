"""Install official game model snapshots; retain verified files for resumption."""
import importlib.util
import json
from pathlib import Path
import urllib.request
import sys

HERE = Path(__file__).resolve().parent
source = HERE.parent / 'audio_neural/zico_audio_studio/scripts/download_weights.py'
spec = importlib.util.spec_from_file_location('verified_download', source)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
RUNTIME = Path('D:/PemaraRuntimes/maestro-game-ai')

def tree(repo, revision):
    url = f'https://huggingface.co/api/models/{repo}/tree/{revision}?recursive=true&expand=false'
    result = []
    while url:
        with urllib.request.urlopen(url, timeout=30) as response:
            result.extend(json.load(response))
            import re
            match = re.search(r'<([^>]+)>; rel="next"', response.headers.get('Link', ''))
            url = match.group(1) if match else None
    return [item for item in result if item['type'] == 'file']

def main():
    plans = [
        ('VAST-AI/SkinTokens', RUNTIME / 'apps/SkinTokens'),
        ('microsoft/TRELLIS.2-4B', RUNTIME / 'apps/ComfyUI/models/microsoft/TRELLIS.2-4B'),
        ('TencentARC/Pixal3D', RUNTIME / 'apps/ComfyUI/models/TencentARC/Pixal3D'),
    ]
    if '--images' in sys.argv:
        plans = [(repo, RUNTIME / 'models' / repo.replace('/', '--')) for repo in (
            'black-forest-labs/FLUX.2-klein-4B', 'Tongyi-MAI/Z-Image-Turbo', 'Tongyi-MAI/Z-Image')]
    for repo, destination in plans:
        revision = helper.api(repo)['sha']
        # Preserve cloned source documentation; only model/config artifacts here.
        files = [item for item in tree(repo, revision) if item['path'].endswith(('.safetensors', '.ckpt', '.json', '.txt', '.model', '.jinja'))]
        if '--images' in sys.argv:
            files = [item for item in files if '/' in item['path'] or item['path'] == 'model_index.json']
        receipt = {'repo': repo, 'revision': revision, 'files': []}
        for item in files:
            target = destination / item['path']
            helper.fetch(repo, revision, item, target)
            receipt['files'].append({'path': str(target), 'size': item['size'], 'sha256': helper.digest(target)})
        (destination / 'maestro-weights-verified.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print('SNAPSHOT VERIFIED ' + repo, flush=True)

if __name__ == '__main__':
    main()
