"""One-shot owner-authorized recovery for the completed EP03 render.

Called exclusively by the MCP lifecycle; no generation or HTTP client here.
Default lost-listener protection remains unchanged without a fresh receipt.
"""
import hashlib
import json
import time
from pathlib import Path


def recover(lifecycle, pid):
    l = lifecycle
    request_path = l.STATE / 'completed_ep03_recovery.json'
    request = json.loads(request_path.read_text(encoding='utf-8'))
    active = json.loads((l.STATE / 'runtime.json').read_text(encoding='utf-8'))
    proc = l.exact_process(pid)
    now = time.time()
    if (request.get('authorization') != 'Se vira e arruma'
            or request.get('runtime') != active or active['pid'] != pid
            or proc.create_time() != active['created']
            or not 0 <= now - request['requested_at'] < 120
            or now - request['idle_sample_at'] < 60
            or proc.cpu_times().user + proc.cpu_times().system - request['idle_sample_cpu'] > .5
            or proc.memory_info().rss > 512 * 1024 ** 2
            or proc.children(recursive=True) or l.listener() is not None):
        raise RuntimeError('EP03 recovery identity, authorization or inactivity check failed; preserved.')
    output = l.BASE / 'ferramentas/ComfyUI/output/REBELIAO_EP03_FHD60_20261103/T01_blank_seed3b_rife60_80eff5a1ff1b.mp4'
    receipt = json.loads(Path(str(output) + '.upscaling.json').read_text(encoding='utf-8'))
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if (not receipt.get('technical_pass') or receipt.get('output_sha256') != digest
            or digest != '3a8e3476c31b75ee6fa5c82e7e6ddd62d9a041753047c481b58f824e53347d1c'
            or receipt.get('frames') != 900 or receipt.get('fps') != 60):
        raise RuntimeError('Completed EP03 output differs; preserved.')
    # Recheck races immediately before the explicitly authorized service stop.
    if l.listener() is not None or proc.create_time() != active['created'] or proc.children(recursive=True):
        raise RuntimeError('EP03 listener/process changed; preserved.')
    archive = l.STATE / 'owner_authorized_recovery_history' / f'{pid}-{int(now)}-ep03.json'
    l.write_json(archive, {**request, 'completed_output_sha256': digest,
                          'reason': 'Owner requested repair; completed output retained, no listener, idle process, no child render'})
    proc.kill()
    _, alive = l.psutil.wait_procs([proc], timeout=10)
    if alive or l.listener() is not None:
        raise RuntimeError('EP03 recovery stop not confirmed; request retained.')
    request_path.unlink()
    l.register(None)
    return {'stopped': True, 'pid': pid, 'owner_authorized_ep03_recovery': True, 'evidence': str(archive)}
