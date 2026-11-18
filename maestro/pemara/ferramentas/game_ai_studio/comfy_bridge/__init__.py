"""Run isolated game 3D models through the existing local Comfy queue."""
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import uuid
import numpy as np
from PIL import Image
import folder_paths
import comfy.model_management as mm

PROJECT = Path('E:/Pemara/maestro/pemara')
PYTHON = Path('D:/PemaraRuntimes/maestro-game-ai/envs/three-d/Scripts/python.exe')
RUNNER = PROJECT / 'ferramentas/game_ai_studio/three_d_runner.py'
spec = importlib.util.spec_from_file_location('maestro_3d_gpu_lease', PROJECT / 'services/studio/gpu_lease.py')
lease_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lease_module)

class MaestroGame3D:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',), 'engine': (['trellis2', 'pixal3d'],),
            'seed': ('INT', {'default': 42, 'min': 0, 'max': 2147483647})},
            'hidden': {'prompt': 'PROMPT'}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('glb_file',)
    FUNCTION = 'generate'
    CATEGORY = 'Maestro/Jogos'
    OUTPUT_NODE = True
    PEMARA_EXPORT_KIND = 'glb'

    def generate(self, image, engine, seed, prompt=None):
        if engine not in ('trellis2', 'pixal3d'):
            raise ValueError('Motor 3D inválido')
        if image.shape[0] != 1:
            raise ValueError('Envie uma imagem por geração')
        job_id = uuid.uuid4().hex
        root = Path(folder_paths.get_output_directory()) / 'maestro_game3d' / job_id
        root.mkdir(parents=True)
        source = root / 'input.png'
        Image.fromarray(np.clip(image[0].cpu().numpy() * 255, 0, 255).astype(np.uint8)).save(source)
        output = root / 'asset.glb'
        lease = lease_module.GpuLeaseRegistry(PROJECT / 'dados/studio/gpu_lease.json')
        lease.acquire(owner='maestro-game-3d', operation=engine, job_id=job_id)
        process = None
        try:
            mm.unload_all_models()
            mm.soft_empty_cache()
            with (root / 'inference.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen([str(PYTHON), '-u', str(RUNNER), '--image', str(source),
                    '--output', str(output), '--engine', engine, '--seed', str(seed)],
                    stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                deadline = time.monotonic() + 1800
                while process.poll() is None:
                    mm.throw_exception_if_processing_interrupted()
                    if time.monotonic() > deadline:
                        raise TimeoutError('Geração 3D excedeu 30 minutos')
                    time.sleep(0.5)
                if process.returncode or not output.is_file():
                    tail = (root / 'inference.log').read_text(encoding='utf-8', errors='replace')[-3500:]
                    raise RuntimeError('Geração 3D falhou: ' + tail)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            lease.release(job_id)
        return {'ui': {'files': [{'filename': 'asset.glb', 'subfolder': 'maestro_game3d/' + job_id, 'type': 'output'}],
                       'text': [str(output)]}, 'result': (str(output),)}

NODE_CLASS_MAPPINGS = {'MaestroGame3D': MaestroGame3D}
NODE_DISPLAY_NAME_MAPPINGS = {'MaestroGame3D': 'Maestro · Imagem para objeto 3D'}
