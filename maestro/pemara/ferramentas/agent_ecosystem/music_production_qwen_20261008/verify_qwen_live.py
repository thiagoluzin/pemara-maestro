"""Text-only planning verification after MCP queue/VRAM admission."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/studio'))
from gpu_lease import GpuLeaseRegistry
from music_qwen import plan_reinstrumentation
from music_ai_audio import sha256_file
from music_writer import write_song

HERE = Path(__file__).resolve().parent
registry = GpuLeaseRegistry(ROOT / 'dados/studio/gpu_lease.json')
job_id = 'qwen_music_production_validation_20261008'
registry.acquire(owner='codex', operation='qwen_music_plan_validation', job_id=job_id,
                 project_id='music_studio', take_id='technical_text_fixture')
try:
    if sys.argv[-1] == 'reinstrument':
        plan = plan_reinstrumentation(prompt='Traditional heavy metal. Bass and drums support a clear preserved vocal; dynamic verse and chorus. Guitar does not mask the singer.',
            duration=6, instruments=('guitar', 'bass', 'drums'), preset='traditional_heavy_metal',
            source_sha256=sha256_file(HERE / 'cpu_fixtures/guitar_di_raw.wav'))
        path = HERE / 'qwen_live_reinstrument_plan.json'
        summary = {'duration': plan['plan']['duration_seconds'], 'sections': len(plan['plan']['sections']),
                   'instruments': list(plan['plan']['tracks']), 'model': plan['writer_model']}
    else:
        plan = write_song('Create a short ORIGINAL instrumental heavy metal idea, with guitar, bass and drums, a quiet verse and energetic chorus, with a complete ending.',
                          30, instrumental=True)
        path = HERE / 'qwen_live_creation_plan.json'
        summary = {'duration': plan['duration_seconds'], 'sections': len(plan['production_plan']['sections']),
                   'instruments': list(plan['production_plan']['tracks']), 'model': plan['writer_model']}
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'valid': True, 'receipt': str(path), **summary}, ensure_ascii=False), flush=True)
finally:
    registry.release(job_id)
