"""GPU installation test on the upstream example; Comfy preflight occurs via MCP."""
from pathlib import Path
import json
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
ROOT = Path('D:/PemaraRuntimes/maestro-game-ai')
output = ROOT / 'logs' / ('smoke-skintokens-' + uuid.uuid4().hex[:8])
output.mkdir()
sys.path.insert(0, str(PROJECT/'services/studio'))
from gpu_lease import GpuLeaseRegistry
lease = GpuLeaseRegistry(PROJECT/'dados/studio/gpu_lease.json')
job_id = 'rig-install-' + uuid.uuid4().hex
lease.acquire(owner='maestro-install', operation='skintokens_runtime_smoke', job_id=job_id)
try:
    target = output / 'sample.glb'
    wsl_target = '/mnt/d/' + target.as_posix()[3:]
    subprocess.run(['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--cd', '/mnt/d/PemaraRuntimes/maestro-game-ai/apps/SkinTokens',
        '--', 'env', 'HF_HUB_OFFLINE=1', 'timeout', '--kill-after=30s', '1800s',
        '/opt/maestro-game-ai/envs/skintokens/bin/python', 'demo.py', '--input', 'examples/giraffe.glb',
        '--output', wsl_target, '--use_transfer'], check=True, timeout=1860)
    subprocess.run(['C:/Program Files/Blender Foundation/Blender 5.2/blender.exe', '--background', '--factory-startup',
                    '--python-exit-code', '1', '--python', str(HERE/'check_rig_glb.py'), '--', str(target)], check=True, timeout=120)
    result = json.loads(target.with_suffix('.validation.json').read_text(encoding='utf-8'))
    result.update(engine='skintokens', technicalInferencePassed=True, artisticApproval=False)
    (ROOT/'logs/skintokens-runtime.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
finally:
    lease.release(job_id)
