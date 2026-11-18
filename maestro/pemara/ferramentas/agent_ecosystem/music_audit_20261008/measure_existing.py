from pathlib import Path
import json
import subprocess
import sys
import shutil
import math

PROJECT = Path('E:/Pemara/maestro/pemara')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT/'services/studio'))
from music_ai_audio import sample_metrics, loudness_metrics, sha256_file

installation = json.loads((HERE/'installation_and_artifacts.json').read_text(encoding='utf-8'))
targets = [Path(item['path']) for item in installation['recent_generated_audio'][:3]]
album_track = PROJECT/'outputs/steel_legacy_20_yue2_20261007/01_signal_beyond_the_storm'
targets.extend(sorted(album_track.glob('*.flac'))[:1])
targets.extend(sorted(album_track.glob('*.mp3'))[:1])
ffmpeg = shutil.which('ffmpeg')
reports = []
for path in targets:
    metrics = sample_metrics(path)
    metrics.update(loudness_metrics(path, ffmpeg))
    decode = subprocess.run([ffmpeg,'-v','error','-xerror','-i',str(path),'-f','null','NUL'],
                            capture_output=True, text=True, timeout=300)
    metrics['full_decode_passed'] = decode.returncode == 0
    if decode.returncode:
        metrics['decode_error'] = decode.stderr[-500:]
    row = {'path': str(path), 'sha256': sha256_file(path), 'metrics': metrics,
           'listened_by_agent': False, 'musical_quality_verdict': 'NOT_ASSESSED_BY_LISTENING'}
    reports.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
(HERE/'existing_audio_measurements.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
