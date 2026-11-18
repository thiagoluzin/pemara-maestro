"""Text-only regression for the reported vocal metal request; no audio submission."""
from pathlib import Path
import json
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/studio'))
from gpu_lease import GpuLeaseRegistry
from music_writer import write_song
import music_writer
from test_music_writer_contract import PROMPT

HERE = Path(__file__).resolve().parent
registry = GpuLeaseRegistry(ROOT / 'dados/studio/gpu_lease.json')
job_id = 'qwen_instruments_fix_validation_20261008'
registry.acquire(owner='codex', operation='qwen_instruments_fix_text_validation', job_id=job_id,
                 project_id='music_studio', take_id='technical_text_fixture')
try:
    original_request = music_writer.request_json
    responses = []
    def record_request(*args, **kwargs):
        raw, metadata = original_request(*args, **kwargs)
        responses.append({'response': raw, 'metadata': metadata})
        (HERE / 'qwen_instruments_fix_live_responses.json').write_text(
            json.dumps(responses, ensure_ascii=False, indent=2), encoding='utf-8')
        return raw, metadata
    music_writer.request_json = record_request
    plan = write_song(PROMPT, None)
    (HERE / 'qwen_instruments_fix_live_plan.json').write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'valid': True, 'duration': plan['duration_seconds'], 'language': plan['vocal_language'],
        'instrumental': plan['instrumental'], 'instruments': list(plan['production_plan']['tracks']),
        'validationAttempts': plan['writer_validation_attempts'], 'model': plan['writer_model'],
        'writerUnloaded': plan['writer_unloaded'], 'audioSubmitted': False}, ensure_ascii=False), flush=True)
finally:
    registry.release(job_id)
