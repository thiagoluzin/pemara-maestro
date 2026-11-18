"""Record an already-submitted owned MCP retry without generating anything."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent / 'video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'

def read(name):
    return json.loads((PROJECT / name).read_text(encoding='utf-8-sig'))

def write(name, value):
    path = PROJECT / name
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

prompt_id = sys.argv[1]
now = datetime.now(timezone.utc).isoformat()
workflow = 'workflows/T01_master_30s_native_audio_face_refine_attempt02.api.json'
submission = {'prompt_id': prompt_id, 'recordedAt': now, 'workflow': workflow,
              'workflowSha256': hashlib.sha256((PROJECT / workflow).read_bytes()).hexdigest(),
              'engine': 'minimax_h3', 'ownerApproval': 'Aprovado', 'status': 'RUNNING',
              'nativeAudio': True, 'faceRefine': True, 'requestedDeliverySeconds': 30,
              'originalFrameCount': 736, 'sageLongSequenceCorrection': True}
if (PROJECT / 'submission_attempt02.json').exists():
    assert read('submission_attempt02.json')['prompt_id'] == prompt_id
else:
    write('submission_attempt02.json', submission)
for name in ('production_request.json', 'project_manifest.json', 'take_queue.json'):
    backup = ROOT / 'rollback' / ('before_attempt02_' + name)
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():
        shutil.copy2(PROJECT / name, backup)
request = read('production_request.json')
request.update(status='RUNNING', activeSubmission='submission_attempt02.json', nativePromptId=prompt_id)
write('production_request.json', request)
manifest = read('project_manifest.json')
manifest.update(updated_at=now)
manifest['external_render'].update(prompt_id=prompt_id, status='RUNNING', active_submission='submission_attempt02.json')
manifest['external_render']['previous_attempts'] = [
    {'prompt_id': 'bf3c1214-60ef-489f-a3d9-b49659c3bb3c', 'status': 'COMPLETED_QC_REJECTED',
     'receipt': 'qc/attempt01_review.json'}]
write('project_manifest.json', manifest)
queue = read('take_queue.json')
for take in queue['takes']:
    if take['id'] == 'T01':
        take['video'].update(status='running', external_prompt_id=prompt_id)
        take['notes'] = 'Segunda tentativa MCP: correcao Sage para sequencia longa. Mesmas ancoras aprovadas, resolucao, steps, duracao e audio. Primeira tentativa rejeitada pelo QC tecnico e preservada.'
write('take_queue.json', queue)
print(json.dumps({'prompt_id': prompt_id, 'status': 'RUNNING', 'attempt': 2}))
