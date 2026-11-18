"""Collect finished MCP evidence and preserved native source; no service calls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent / 'video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)
status = json.loads((PROJECT / 'qc/mcp_attempt02_status.json').read_text(encoding='utf-8'))
assert status['status'] == 'completed', 'Only terminal MCP completion can enter QC'
submission_path = PROJECT / 'submission_attempt02.json'
submission = json.loads(submission_path.read_text(encoding='utf-8'))
assert status['prompt_id'] == submission['prompt_id']
text = status['text_outputs']['pemara_face_refine_15'][0]
node = json.loads(text)
report_path = Path(node['report'])
report = json.loads(report_path.read_text(encoding='utf-8'))
original = Path(report['original']['path'])
assert sha(original) == report['original']['sha256'], 'Preserved original hash changed'
destination = PROJECT / 'takes/native_attempt02/original_before_refine.mp4'
if destination.exists():
    assert sha(destination) == report['original']['sha256']
else:
    shutil.copy2(original, destination)
report_copy = PROJECT / 'qc/face_refine_attempt02.json'
if report_copy.exists():
    assert sha(report_copy) == sha(report_path)
else:
    shutil.copy2(report_path, report_copy)
timing = {'faceRefineProcessingSeconds': round(report_path.stat().st_mtime-original.stat().st_mtime, 3),
          'scope': 'Observed wall time: CPU detection, H3 face windows and compositing; excludes final MP4 encoding',
          'originalSavedAt': datetime.fromtimestamp(original.stat().st_mtime, timezone.utc).isoformat(),
          'reportSavedAt': datetime.fromtimestamp(report_path.stat().st_mtime, timezone.utc).isoformat(),
          'detectedFaces': report.get('detected_faces', 0), 'tracks': len(report['tracks']),
          'windows': len(report['windows']), 'identityVerified': False,
          'reportSha256': sha(report_path), 'originalSha256': sha(original)}
write(PROJECT / 'qc/face_refine_attempt02_timing.json', timing)
submission.update(status='COMPLETED_PENDING_QC', faceRefineApplied=bool(report['tracks']),
                  timingReceipt='qc/face_refine_attempt02_timing.json')
write(submission_path, submission)
request_path = PROJECT / 'production_request.json'
request = json.loads(request_path.read_text(encoding='utf-8'))
request['status'] = 'COMPLETED_PENDING_QC'
write(request_path, request)
print(json.dumps({'original': str(destination), 'report': str(report_copy), 'timing': timing}, ensure_ascii=False))
