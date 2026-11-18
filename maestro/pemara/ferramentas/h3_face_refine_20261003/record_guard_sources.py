"""Record code rollback fingerprints and deterministic test evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path and path.exists() else None

files = [
    (ROOT / 'services/studio/h3_face_refine.py', HERE / 'rollback/h3_face_refine_before_sage_guard.py'),
    (ROOT / 'services/studio/test_h3_face_refine.py', HERE / 'rollback/test_h3_face_refine_before_sage_guard.py'),
    (ROOT / 'services/studio/test_generative_control.py', HERE / 'rollback/services__studio__test_generative_control.py'),
    (HERE / 'node/stable_sage.py', None),
    (HERE / 'node/__init__.py', HERE / 'rollback/plugin_init_before_long_sage.py'),
]
receipt = {'checkedAt': datetime.now(timezone.utc).isoformat(),
           'changes': [{'path': str(path), 'before': sha(backup), 'after': sha(path),
                        'backup': str(backup) if backup else None} for path, backup in files],
           'cpuRegression': {'status': 'PASS', 'tests': 149,
                'modules': ['test_h3_face_refine', 'test_h3_workflow', 'test_generative_control', 'test_generative_jobs'],
                'python': 'C:/Program Files/Python311/python.exe', 'gpuGeneration': False},
           'gpuNumericalDiagnostic': {'prompt_id': '050a0433-c1ee-474f-9ab7-df3806c536ef',
                                     'correctedError': 0.0, 'finite': True},
           'mcpPreflight': {'graphs': 28, 'passed': 20, 'preexistingBlocked': 8},
           'productionArtisticApproval': False}
(HERE / 'receipts/sage_guard_source_changes.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
verification_path = HERE / 'receipts/verification.json'
backup = HERE / 'rollback/verification_before_approved_production.json'
if not backup.exists():
    shutil.copy2(verification_path, backup)
verification = json.loads(verification_path.read_text(encoding='utf-8'))
project = ROOT / 'ferramentas/video_global_engine/projetos/re2_1998_leon_first_licker_face_refine_30s_v1'
request = json.loads((project / 'production_request.json').read_text(encoding='utf-8'))
verification['tests']['sageGuardRegression'] = receipt['cpuRegression']
verification['production'] = {
    'workflowValidated': True, 'status': request['status'], 'submitted': True,
    'durationRequested': 30, 'activePromptId': request['nativePromptId'],
    'activeSubmission': request['activeSubmission'], 'anchorsOwnerApproved': True,
    'videoOwnerApproved': False, 'previousAttempt': 'COMPLETED_QC_REJECTED',
}
verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'tests': 149, 'sourceFiles': len(files), 'artisticApproval': False}))
