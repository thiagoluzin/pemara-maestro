"""Authenticated image-to-3D jobs through the Maestro's local Comfy queue."""
import io
import json
from pathlib import Path
import shutil
import threading
import time
import uuid
import requests
from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from game_assets import ROOT, valid_id, state

COMFY = 'http://127.0.0.1:8188'
MARKERS = Path('D:/PemaraRuntimes/maestro-game-ai/logs')
COMFY_OUTPUT = Path('E:/Pemara/maestro/pemara/ferramentas/ComfyUI/output').resolve()

def workflow(filename, engine, seed=42):
    if engine not in ('trellis2', 'pixal3d'):
        raise ValueError('Motor 3D inválido')
    return {'1': {'class_type': 'LoadImage', 'inputs': {'image': filename}},
            '2': {'class_type': 'MaestroGame3D', 'inputs': {'image': ['1', 0], 'engine': engine, 'seed': seed}}}

def worker(folder, project_id, engine):
    try:
        with (folder / 'source.png').open('rb') as source:
            response = requests.post(COMFY + '/upload/image', files={'image': (folder.name + '.png', source, 'image/png')}, timeout=30)
        response.raise_for_status()
        uploaded = response.json()
        filename = '/'.join(filter(None, [uploaded.get('subfolder'), uploaded['name']]))
        graph = workflow(filename, engine)
        response = requests.post(COMFY + '/prompt', json={'prompt': graph}, timeout=30)
        response.raise_for_status()
        prompt_id = response.json()['prompt_id']
        state(folder, 'queued', projectId=project_id, engine=engine, promptId=prompt_id)
        deadline = time.monotonic() + 7200
        while time.monotonic() < deadline:
            response = requests.get(COMFY + '/history/' + prompt_id, timeout=15)
            response.raise_for_status()
            history = response.json().get(prompt_id)
            if history:
                if history.get('status', {}).get('status_str') == 'error':
                    raise RuntimeError('O motor 3D falhou. Consulte o registro da geração no ComfyUI.')
                files = history.get('outputs', {}).get('2', {}).get('files', [])
                if files:
                    item = files[0]
                    source = (COMFY_OUTPUT / item.get('subfolder', '') / item['filename']).resolve()
                    if not source.is_relative_to(COMFY_OUTPUT) or source.suffix != '.glb':
                        raise RuntimeError('Saída 3D inválida')
                    shutil.copyfile(source, folder / 'asset.glb')
                    state(folder, 'done', projectId=project_id, engine=engine, promptId=prompt_id,
                        reviewStatus='PENDING_HUMAN_REVIEW', url=f'/api/zico/games/assets/{folder.name}/output')
                    return
            time.sleep(3)
        raise TimeoutError('Tempo de acompanhamento excedido; consulte o prompt antes de repetir a geração.')
    except Exception as exc:
        state(folder, 'error', projectId=project_id, engine=engine, message=str(exc))

def create_game_3d_router(is_internal_request):
    router = APIRouter(prefix='/api/zico/games/3d')

    def check(request):
        if not is_internal_request(request):
            raise HTTPException(403)

    @router.get('/engines')
    def engines(request: Request):
        check(request)
        return {'engines': [{'id': engine, 'available': (MARKERS / (engine + '-runtime.json')).is_file()}
                            for engine in ('trellis2', 'pixal3d')]}

    @router.post('', status_code=202)
    async def generate(request: Request, project_id: str = Form(...), engine: str = Form(...), image: UploadFile = File(...)):
        check(request)
        if not valid_id(project_id) or not (ROOT / 'projects' / project_id / 'project.json').is_file():
            raise HTTPException(404, 'Projeto não encontrado')
        if engine not in ('trellis2', 'pixal3d'):
            raise HTTPException(400, 'Escolha o motor 3D')
        if not (MARKERS / (engine + '-runtime.json')).is_file():
            raise HTTPException(503, 'Motor 3D ainda não validado')
        try:
            data = await image.read(20 * 1024 * 1024 + 1)
            if len(data) > 20 * 1024 * 1024:
                raise HTTPException(413, 'Limite de 20 MB por imagem')
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > 16_000_000:
                    raise HTTPException(400, 'Use uma imagem de até 16 megapixels')
                source.load()
                folder = ROOT / 'jobs' / uuid.uuid4().hex
                folder.mkdir(parents=True)
                source.convert('RGB').save(folder / 'source.png')
            initial = state(folder, 'queued', projectId=project_id, engine=engine)
            threading.Thread(target=worker, args=(folder, project_id, engine), daemon=True).start()
            return initial
        except (UnidentifiedImageError, OSError):
            raise HTTPException(400, 'Imagem inválida')
        finally:
            await image.close()

    return router
