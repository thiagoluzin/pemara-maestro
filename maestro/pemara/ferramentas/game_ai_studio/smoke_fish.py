"""Fish installation test; Comfy preflight is performed by Codex via MCP."""
from pathlib import Path
import json
import os
import runpy
import sys
import uuid

PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT / 'ferramentas/audio_neural/zico_audio_studio/engines/fish/repo'
OUT = Path('D:/PemaraRuntimes/maestro-game-ai/logs') / ('smoke-fish-' + uuid.uuid4().hex[:8])
OUT.mkdir()
sys.path.insert(0, str(PROJECT / 'services/studio'))
from gpu_lease import GpuLeaseRegistry
lease = GpuLeaseRegistry(PROJECT / 'dados/studio/gpu_lease.json')
job_id = 'fish-install-' + uuid.uuid4().hex
lease.acquire(owner='maestro-install', operation='fish_runtime_smoke', job_id=job_id)
try:
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.chdir(REPO); sys.path.insert(0, str(REPO))
    sys.argv = ['fish-smoke', '--text', 'Olá. Este é um teste de áudio do Maestro Pemara.',
                '--checkpoint-path', str(REPO/'checkpoints/s2-pro'), '--device', 'cuda', '--no-compile',
                '--seed', '42', '--max-new-tokens', '256', '--output-dir', str(OUT), '--output', str(OUT/'sample.wav')]
    try:
        runpy.run_module('fish_speech.models.text2semantic.inference', run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (None, 0): raise
    import soundfile as sf
    audio, rate = sf.read(OUT/'sample.wav')
    assert audio.size > 0 and abs(audio).max() > 0
    result = {'engine': 'fish_speech', 'output': str(OUT/'sample.wav'), 'sampleRate': rate,
              'duration': len(audio)/rate, 'peak': float(abs(audio).max()), 'technicalInferencePassed': True,
              'voiceQualityApproved': False}
    (OUT/'receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
finally:
    lease.release(job_id)
