"""Authenticated read-only Studio check; credentials never leave process memory."""
from pathlib import Path
import sys
import json
import urllib.request
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'services/studio'))
import main
token = main._internal_token()
if not token:
    raise RuntimeError('Credencial interna indisponivel; nenhuma alteracao de autenticacao foi feita.')
request = urllib.request.Request('http://127.0.0.1:8029/api/music-reinstrument/status',
                                headers={'X-Studio-Internal-Token': token})
with urllib.request.urlopen(request, timeout=60) as response:
    state = json.load(response)
receipt = {'httpStatus': 200, 'productionContract': state.get('productionContract'),
    'coordinator': state.get('coordinator'), 'defaultEngine': state.get('defaultEngine'),
    'enginesConfigured': {k: v.get('configured') for k, v in state.get('engines', {}).items()},
    'sampledGuitarReady': state.get('engines', {}).get('score_first_muscriptor', {})
        .get('sampledInstruments', {}).get('instruments', {}).get('guitar', {}).get('ready'),
    'availabilityIsInferenceProof': False}
(Path(__file__).resolve().parent / 'deployment_verification.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(receipt, ensure_ascii=False), flush=True)
assert receipt['productionContract'] == 'pemara.qwen-music-production.v1', receipt
assert receipt['sampledGuitarReady'] is True
