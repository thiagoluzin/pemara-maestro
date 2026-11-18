"""Bounded local GLB preparation, separate from GPU image/rigging engines."""
from pathlib import Path
import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'dados/game_ai'
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
RUNNER = PROJECT / 'ferramentas/game_ai_studio/prepare_glb.py'
MAX_BYTES = 256 * 1024 * 1024
_gate = threading.BoundedSemaphore(1)

def valid_id(value):
    return len(value) == 32 and all(c in '0123456789abcdef' for c in value)

def state(folder, status, **kwargs):
    now = datetime.now(timezone.utc).isoformat()
    previous = {}
    if (folder / 'job.json').is_file():
        previous = json.loads((folder / 'job.json').read_text(encoding='utf-8'))
    data = {'jobId': folder.name, 'status': status, 'createdAt': previous.get('createdAt', now), 'updatedAt': now, **kwargs}
    temporary = folder / 'job.tmp'
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder / 'job.json')
    return data

def worker(folder, project_id, operation='static'):
    lease = None
    try:
        state(folder, 'running', projectId=project_id, engine=operation)
        target = folder / 'asset.glb'
        if operation == 'skintokens':
            from gpu_lease import GpuLeaseRegistry
            from game_gpu_admission import admit
            registry = GpuLeaseRegistry(PROJECT / 'dados/studio/gpu_lease.json')
            registry.acquire(owner='maestro', operation='game_rigging', job_id=folder.name)
            lease = registry
            admit(20000)
            def wsl_path(path):
                value = path.resolve().as_posix()
                return '/mnt/' + value[0].lower() + value[2:]
            command = ['wsl.exe', '-d', 'Ubuntu-24.04', '-u', 'root', '--cd', '/mnt/d/PemaraRuntimes/maestro-game-ai/apps/SkinTokens',
                '--', 'env', 'HF_HUB_OFFLINE=1', 'timeout', '--kill-after=30s', '1800s',
                '/opt/maestro-game-ai/envs/skintokens/bin/python', 'demo.py', '--input', wsl_path(folder/'source.glb'),
                '--output', wsl_path(target), '--use_transfer']
            timeout = 1860
        else:
            command = [str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
                '--python', str(RUNNER), '--', str(folder/'source.glb'), str(target)]
            timeout = 600
        with (folder / 'blender.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode or not target.is_file():
            message = 'Não foi possível criar o esqueleto. Consulte o relatório de processamento.' if operation == 'skintokens' else 'Não foi possível preparar o objeto. Consulte o relatório de processamento; arquivos com esqueleto exigem a rota de rigging.'
            raise RuntimeError(message)
        state(folder, 'done', projectId=project_id, engine=operation, reviewStatus='PENDING_HUMAN_REVIEW',
              url=f'/api/zico/games/assets/{folder.name}/output')
    except Exception as exc:
        state(folder, 'error', projectId=project_id, engine=operation, message=str(exc))
    finally:
        try:
            if lease is not None:
                lease.release(folder.name)
        finally:
            _gate.release()

def create_game_assets_router(is_internal):
    router = APIRouter(prefix='/api/zico/games/assets')

    def check(request):
        if not is_internal(request):
            raise HTTPException(403, 'Disponível somente no Maestro autenticado.')

    def folder_for(job_id):
        if not valid_id(job_id):
            raise HTTPException(404)
        folder = ROOT / 'jobs' / job_id
        if not (folder / 'job.json').is_file():
            raise HTTPException(404)
        return folder

    @router.post('', status_code=202)
    async def prepare(request: Request, project_id: str = Form(...), asset: UploadFile = File(...), operation: Literal['static', 'skintokens'] = Form('static')):
        check(request)
        if not valid_id(project_id) or not (ROOT / 'projects' / project_id / 'project.json').is_file():
            raise HTTPException(400, 'Selecione um projeto existente.')
        if not BLENDER.is_file():
            raise HTTPException(503, 'Blender não encontrado.')
        if operation == 'skintokens' and not Path('D:/PemaraRuntimes/maestro-game-ai/logs/skintokens-runtime.json').is_file():
            raise HTTPException(503, 'O pipeline de rigging ainda está em validação.')
        if Path(asset.filename or '').suffix.lower() != '.glb':
            raise HTTPException(400, 'Envie um arquivo GLB.')
        if not _gate.acquire(blocking=False):
            raise HTTPException(409, 'Já existe um objeto em processamento. Aguarde sua conclusão.')
        folder = ROOT / 'jobs' / uuid.uuid4().hex
        try:
            folder.mkdir(parents=True)
            count = 0
            with (folder / 'source.glb').open('xb') as output:
                while chunk := await asset.read(1024 * 1024):
                    count += len(chunk)
                    if count > MAX_BYTES:
                        raise HTTPException(413, 'O limite é 256 MB por arquivo.')
                    output.write(chunk)
            with (folder / 'source.glb').open('rb') as source:
                if source.read(4) != b'glTF':
                    raise HTTPException(400, 'Cabeçalho GLB inválido.')
            initial = state(folder, 'queued', projectId=project_id, engine=operation)
            threading.Thread(target=worker, args=(folder, project_id, operation), daemon=True).start()
            return initial
        except BaseException:
            _gate.release()
            raise
        finally:
            await asset.close()

    @router.get('/{job_id}')
    def status(request: Request, job_id: str):
        check(request)
        return json.loads((folder_for(job_id) / 'job.json').read_text(encoding='utf-8'))

    @router.get('/{job_id}/output')
    def output(request: Request, job_id: str):
        check(request)
        target = folder_for(job_id) / 'asset.glb'
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type='model/gltf-binary', filename='maestro_asset.glb')

    return router

