"""GPU admission used by autonomous Maestro subprocesses holding the GPU lease."""
import json
import subprocess
import time
import urllib.request

def admit(minimum_free_mb):
    with urllib.request.urlopen('http://127.0.0.1:8188/queue', timeout=10) as response:
        queue = json.load(response)
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('ComfyUI ocupado; aguarde a fila.')

    def memory():
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.free', '--format=csv,noheader,nounits'],
                                capture_output=True, text=True, check=True)
        return tuple(map(int, result.stdout.splitlines()[0].split(',')))

    used, free = memory()
    if used <= 4096 and free >= minimum_free_mb:
        return
    # Release only idle Comfy model cache; never terminate another process.
    request = urllib.request.Request('http://127.0.0.1:8188/free',
        data=json.dumps({'unload_models': True, 'free_memory': True}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=10):
        pass
    for _ in range(10):
        time.sleep(1)
        used, free = memory()
        if used <= 4096 and free >= minimum_free_mb:
            return
    raise RuntimeError('GPU ocupada por outro trabalho. Aguarde para gerar; nenhum processo foi interrompido.')
