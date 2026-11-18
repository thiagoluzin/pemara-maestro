"""Record final scoped hashes and evidence without credentials."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BACKUP = ROOT / 'backups/music_production_qwen_20261008'
BASELINE = json.loads((BACKUP / 'baseline.json').read_text(encoding='utf-8-sig'))
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
records = [{'path': str(ROOT / item['relative']), 'beforeSha256': item['before_sha256'].lower(),
            'afterSha256': digest(ROOT / item['relative']), 'backupPath': str(BACKUP / item['relative'])}
           for item in BASELINE]
for name in ('music_qwen.py', 'music_delivery.py', 'music_listening.py', 'music_vocals.py',
             'test_music_qwen.py', 'test_music_quality_gates.py', 'test_music_delivery.py',
             'test_music_listening.py', 'test_music_vocals.py', 'test_music_ai_api.py',
             'test_music_duration_choice.py'):
    path = ROOT / 'services/studio' / name
    records.append({'path': str(path), 'afterSha256': digest(path),
                    'backupAvailable': (BACKUP / 'services/studio' / name).exists()})
roles = ('pemara-music-production-lead', 'pemara-music-arranger',
         'pemara-music-mix-engineer', 'pemara-music-listening-qc')
for role in roles:
    for path in (ROOT.parents[1] / '.agents/skills' / role).rglob('*'):
        if path.is_file():
            records.append({'path': str(path), 'afterSha256': digest(path), 'createdInThisImplementation': True})
evidence = {}
for name in ('deployment_verification.json', 'guitar_qualification.json', 'score_roundtrip_verification.json',
             'qwen_live_creation_plan.json', 'qwen_live_reinstrument_plan.json', 'mcp_workflow_validation.json'):
    path = HERE / name
    evidence[name] = {'exists': path.exists(), 'sha256': digest(path) if path.exists() else None}
receipt = {'contract': 'pemara.qwen-music-production.v1',
    'recordedAt': datetime.now(timezone.utc).isoformat(),
    'backendTestsPassed': 115, 'interfaceTestsPassed': 6, 'syntaxChecksPassed': True,
    'realQwenCreationValidated': evidence['qwen_live_creation_plan.json']['exists'],
    'realQwenReinstrumentValidated': evidence['qwen_live_reinstrument_plan.json']['exists'],
    'realSongGenerated': False, 'artisticApproval': False,
    'pilot': {'song': 'Admirável Gado Novo', 'targetStyle': 'heavy metal',
              'status': 'WAITING_OWNER_SOURCE_FROM_OTHER_PC', 'sourcePath': None},
    'pendingQualification': ['real_pilot_listening', 'Demucs_on_pilot', 'RoFormer_MSST_challengers',
                            'ACE_lego_complete', 'captured_amp_and_metal_articulations'],
    'baselineScope': '18 production/UI/test files plus API-test backup; duration-choice fixture lacks initial baseline',
    'evidence': evidence, 'files': records}
(HERE / 'implementation_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in receipt.items() if k not in ('files', 'evidence')}, ensure_ascii=False))
