"""MMAudio installation test with a synthetic CPU fixture; no Comfy HTTP calls."""
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import uuid

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'ferramentas/audio_neural/zico_audio_studio'
REPO = ROOT / 'engines/mmaudio/repo'
OUT = Path('D:/PemaraRuntimes/maestro-game-ai/logs') / ('smoke-mmaudio-' + uuid.uuid4().hex[:8])
OUT.mkdir()
fixture = OUT / 'fixture.mp4'
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:size=320x240:rate=24',
                '-t', '2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(fixture)], check=True)
sys.path.insert(0, str(PROJECT / 'services/studio'))
from gpu_lease import GpuLeaseRegistry
lease = GpuLeaseRegistry(PROJECT / 'dados/studio/gpu_lease.json')
job_id = 'mmaudio-install-' + uuid.uuid4().hex
lease.acquire(owner='maestro-install', operation='mmaudio_runtime_smoke', job_id=job_id)
try:
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['MMAUDIO_CLIP_MODEL'] = 'local-dir:' + str(ROOT/'engines/mmaudio/clip')
    os.chdir(REPO); sys.path.insert(0, str(REPO))
    sys.argv = ['mmaudio-smoke', '--variant', 'large_44k_v2', '--video', str(fixture), '--output', str(OUT),
                '--prompt', 'A soft click in a quiet room.', '--duration', '2', '--seed', '42', '--skip_video_composite']
    runpy.run_path(str(REPO/'demo.py'), run_name='__main__')
    import soundfile as sf
    import numpy as np
    audio, rate = sf.read(OUT/'fixture.flac')
    assert audio.size and np.isfinite(audio).all() and abs(audio).max() > 0
    result = {'engine': 'mmaudio', 'output': str(OUT/'fixture.flac'), 'sampleRate': rate,
              'duration': len(audio)/rate, 'technicalInferencePassed': True, 'artisticApproval': False}
    (OUT/'receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
finally:
    lease.release(job_id)
