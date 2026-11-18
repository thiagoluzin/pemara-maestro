from pathlib import Path
import importlib
import json
import sys
import time

PROJECT = Path('E:/Pemara/maestro/pemara')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT/'services/studio'))
report = {'scope': 'Read-only installation and existing-artifact audit',
          'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'audit_python': sys.executable, 'new_generation': False, 'runtime': {}, 'errors': []}
for name, fn in [('music_creation', 'provider_status'), ('music_ai_production', 'runtime_status'),
                 ('music_reinstrument', 'runtime_status'), ('music_score_first', 'runtime_status')]:
    try:
        mod = importlib.import_module(name)
        report['runtime'][name] = getattr(mod, fn)()
        if hasattr(mod, 'runtime_paths'):
            paths = mod.runtime_paths()
            report['runtime'][name]['paths'] = {
                key: {'path': str(path), 'exists': path.exists(),
                      'bytes': path.stat().st_size if path.is_file() else None}
                for key, path in paths.items() if isinstance(path, Path)}
    except Exception as exc:
        report['errors'].append({'module': name, 'type': type(exc).__name__, 'message': str(exc)[:250]})

job_root = PROJECT/'dados/studio/music_reinstrument'
job_rows = []
if job_root.is_dir():
    for folder in job_root.iterdir():
        if not folder.is_dir():
            continue
        reports = [path for path in folder.glob('*.json') if path.name not in {'request.json'}]
        job_rows.append({'folder': str(folder), 'mtime': folder.stat().st_mtime,
                         'reports': [path.name for path in reports]})
report['reinstrument_existing_folders'] = sorted(job_rows, key=lambda row: row['mtime'], reverse=True)
album = PROJECT/'outputs/steel_legacy_20_yue2_20261007'
report['album_root_exists'] = album.is_dir()
report['album_files'] = [{'name': path.name, 'bytes': path.stat().st_size}
                         for path in album.glob('*') if path.is_file()] if album.is_dir() else []
report['recent_generated_audio'] = []
for root in [PROJECT/'outputs/audio', PROJECT/'ferramentas/ComfyUI/output/audio']:
    if root.is_dir():
        paths = sorted([path for path in root.glob('*') if path.is_file() and path.suffix.lower() in {'.flac','.wav','.mp3'}],
                       key=lambda path: path.stat().st_mtime, reverse=True)[:8]
        report['recent_generated_audio'].extend({'path':str(path),'bytes':path.stat().st_size,'mtime':path.stat().st_mtime}
                                              for path in paths)
out = HERE/'installation_and_artifacts.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
for module, value in report['runtime'].items():
    if module == 'music_creation':
        print(json.dumps({module: {key: {'configured':item['configured'],'label':item['label']} for key,item in value.items()}}, ensure_ascii=False))
    else:
        print(json.dumps({module: {key:value.get(key) for key in ['configured','scoreImportConfigured','orchestrationConfigured','checks','needs','message']}}, ensure_ascii=False))
print(json.dumps({'errors':report['errors'],'reinstrument_folders':len(job_rows),
                  'album_exists':report['album_root_exists'],'recent_audio':len(report['recent_generated_audio'])}, ensure_ascii=False))
