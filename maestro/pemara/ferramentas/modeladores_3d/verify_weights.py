"""Compare local model files with official Hugging Face LFS hashes."""
import hashlib
import json
from pathlib import Path
from huggingface_hub import HfApi

root = Path('D:/PemaraRuntimes/maestro-game-ai/models')
reports = []
for name in ('TripoSG', 'Hunyuan3D-2.1'):
    download = json.loads((root / (name + '-download.json')).read_text())
    info = HfApi().model_info(download['repo'], revision=download['revision'], files_metadata=True)
    for entry in info.siblings:
        path = root / name / entry.rfilename
        if not path.is_file() or not entry.lfs:
            continue
        with path.open('rb') as handle:
            actual = hashlib.file_digest(handle, 'sha256').hexdigest()
        expected = entry.lfs.sha256
        assert actual == expected, f'Hash mismatch: {path}'
        reports.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': actual,
                        'officialHashMatched': True, 'revision': download['revision']})
target = Path(__file__).with_name('weights-verified.json')
target.write_text(json.dumps(reports, indent=2), encoding='utf-8')
print(f'Official hashes matched: {len(reports)} files')
