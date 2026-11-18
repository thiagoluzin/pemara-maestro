"""CPU-only inventory. Never contact ComfyUI or submit jobs."""
import importlib.metadata
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
MODELS = Path('D:/PemaraModels/workflows_20260920')
EXPECTED = [
    'checkpoints/hidream_o1_image_bf16.safetensors',
    'checkpoints/yue2_3b_int8_convrot.safetensors',
    'checkpoints/LLaDA-Image-Base-BF16-AIO.safetensors',
    'checkpoints/LLaDA-Image-Turbo-BF16-AIO.safetensors',
    'text_encoders/gemma4_e4b_it_fp8_scaled.safetensors',
    'text_encoders/qwen_3_4b.safetensors',
    'diffusion_models/flux-2-klein-4b.safetensors',
    'vae/flux2-vae.safetensors',
    'audio_encoders/sheetsage2_bf16.safetensors',
    'auk/AuK/auk_base.safetensors', 'auk/AuK/vae.safetensors',
    'auk/AuK-Flash/auk_flash.safetensors', 'auk/AuK-Flash/vae.safetensors',
]


def inspect_safetensors(path):
    if not path.is_file():
        return {'path': str(path), 'status': 'missing_or_downloading'}
    try:
        with path.open('rb') as f:
            size = struct.unpack('<Q', f.read(8))[0]
            if not 0 < size < 100_000_000:
                raise ValueError('invalid header size')
            header = json.loads(f.read(size))
        tensors = [v for k, v in header.items() if k != '__metadata__']
        expected = 8 + size + max(t['data_offsets'][1] for t in tensors)
        actual = path.stat().st_size
        return {'path': str(path), 'status': 'structurally_complete' if expected == actual else 'incomplete',
                'bytes': actual, 'expected_bytes': expected, 'tensor_count': len(tensors)}
    except (OSError, ValueError, KeyError, struct.error) as e:
        return {'path': str(path), 'status': 'invalid_or_downloading', 'error': str(e)}


models = [inspect_safetensors(MODELS / item) for item in EXPECTED]
qwen = MODELS / 'auk/Qwen2.5-Omni-3B'
index = qwen / 'model.safetensors.index.json'
if index.exists():
    shards = sorted(set(json.loads(index.read_text())['weight_map'].values()))
    models += [inspect_safetensors(qwen / shard) for shard in shards]
else:
    models.append({'path': str(index), 'status': 'missing_or_downloading'})
sources = {}
for source in (ROOT / 'sources').iterdir():
    if source.is_dir() and (source / '.git').exists():
        p = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
        sources[source.name] = p.stdout.strip()
installed = Path('D:/PemaraRuntimes/state/ComfyUI-v0.36.0-pemara/user/default/workflows/PEMARA_IMAGE_AUDIO')
workflows = []
for source in sorted((ROOT / 'workflows').glob('*.json')):
    if source.name.endswith('.api.json'):
        continue
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    target = installed / source.name
    workflows.append({'name': source.name, 'sha256': digest,
                      'installed_path': str(target),
                      'installed_matches': target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == digest})
result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'models': models,
          'workflows': workflows,
          'source_commits': sources, 'artistic_approval': False,
          'note': 'Headers and byte counts only; does not prove model execution or quality.'}
(ROOT / 'receipts/install_inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'complete': sum(m['status'] == 'structurally_complete' for m in models),
                  'total': len(models), 'pending': [m['path'] for m in models if m['status'] != 'structurally_complete']}, indent=2))
