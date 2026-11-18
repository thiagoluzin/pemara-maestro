"""Prepare a same-scope retry; preserve the rejected render and all approvals."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent / 'video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

workflow = read(PROJECT / 'workflows/T01_master_30s_native_audio_face_refine.api.json')
workflow['21'] = {'class_type': 'PemaraH3SageLongSequencePatch',
                  'inputs': {'model': ['20', 0], 'head_chunks': 4}}
workflow['7']['inputs']['model'] = ['21', 0]
workflow['8']['inputs']['model'] = ['21', 0]
prefix = 'RE2_LEON_FIRST_LICKER/T01_master_native_audio_face_refine_attempt02'
workflow['16']['inputs']['filename_prefix'] = prefix
workflow['pemara_face_refine_15']['inputs']['filename_prefix'] = prefix
workflow['22'] = {'class_type': 'SaveLatent',
                  'inputs': {'samples': ['12', 0], 'filename_prefix': prefix + '_video_latent'}}
workflow['23'] = {'class_type': 'SaveLatent',
                  'inputs': {'samples': ['12', 1], 'filename_prefix': prefix + '_audio_latent'}}
target = PROJECT / 'workflows/T01_master_30s_native_audio_face_refine_attempt02.api.json'
if target.exists():
    assert read(target) == workflow, 'Existing attempt02 differs; preserve before editing.'
else:
    write(target, workflow)
request = read(PROJECT / 'production_request.json')
request.update(status='RETRY_PREPARED', activeSubmission='submission_attempt02.json')
request['technicalRetry'] = {
    'reason': 'Sage CUDA large fused-QKV stride exceeds uint32 address span at 30s Master resolution',
    'previousPromptId': 'bf3c1214-60ef-489f-a3d9-b49659c3bb3c',
    'previousStatus': 'COMPLETED_QC_REJECTED',
    'correction': 'Compact independent head groups before RMSNorm/RoPE and Sage quantization',
    'kernelDiagnosticPromptId': '050a0433-c1ee-474f-9ab7-df3806c536ef',
    'resolutionStepsDurationAudioUnchanged': True,
    'videoApproved': False,
}
write(PROJECT / 'production_request.json', request)
receipt = {
    'recordedAt': datetime.now(timezone.utc).isoformat(),
    'prompt_id': '050a0433-c1ee-474f-9ab7-df3806c536ef',
    'status': 'COMPLETED', 'source_element_span': 4838385664,
    'uint32_max': 4294967295,
    'original_q_scale_max_error': 0.0019685039296746254,
    'original_k_scale_max_error': 0.0019685039296746254,
    'compact_q_scale_max_error': 0.0, 'compact_k_scale_max_error': 0.0,
    'full_forward_constant_v_max_error': 0.0, 'full_forward_finite': True,
    'frames_generated': 0, 'model_weights_changed': False,
    'source': str(ROOT / 'node/stable_sage.py'),
    'sourceSha256': hashlib.sha256((ROOT / 'node/stable_sage.py').read_bytes()).hexdigest(),
    'scope': 'Numerical CUDA kernel regression; not final video or artistic approval',
}
write(PROJECT / 'qc/sage_long_sequence_correction.json', receipt)
print(json.dumps({'workflow': str(target), 'kernelDiagnostic': receipt['status']}))
