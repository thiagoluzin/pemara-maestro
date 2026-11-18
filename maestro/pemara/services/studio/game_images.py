"""Local image engine jobs for Maestro game projects."""
from pathlib import Path
import importlib.util
import json
import subprocess
import threading
import uuid
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from game_assets import ROOT, PROJECT, valid_id, state

RUNTIME = Path('D:/PemaraRuntimes/maestro-game-ai')
PYTHON = RUNTIME / 'envs/images/Scripts/python.exe'
RUNNER = PROJECT / 'ferramentas/game_ai_studio/image_runner.py'
module_spec = importlib.util.spec_from_file_location('maestro_game_image_runner', RUNNER)
runner = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(runner)

class ImageRequest(BaseModel):
    projectId: str
    engine: str
    prompt: str = Field(min_length=1, max_length=4000)
    width: int = Field(default=1024, ge=512, le=1536, multiple_of=32)
    height: int = Field(default=1024, ge=512, le=1536, multiple_of=32)
    seed: int = Field(default=42, ge=0, le=2147483647)

def ready(engine):
    if engine not in runner.ENGINES:
        return False
    model = RUNTIME / 'models' / runner.ENGINES[engine][0]
    return PYTHON.is_file() and (model / 'maestro-weights-verified.json').is_file() and (model / 'maestro-runtime-verified.json').is_file()

def worker(folder, body):
    try:
        state(folder, 'running', projectId=body.projectId, engine=body.engine)
        with (folder / 'inference.log').open('w', encoding='utf-8') as log:
            result = subprocess.run([str(PYTHON), str(RUNNER), '--spec', str(folder / 'spec.json'), '--output', str(folder / 'image.png')],
                                    stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        if result.returncode or not (folder / 'image.png').is_file():
            raise RuntimeError('Não foi possível gerar a imagem. Consulte o registro do job e a disponibilidade da GPU.')
        state(folder, 'done', projectId=body.projectId, engine=body.engine,
              reviewStatus='PENDING_HUMAN_REVIEW', url=f'/api/zico/games/images/{folder.name}/output')
    except Exception as exc:
        state(folder, 'error', projectId=body.projectId, engine=body.engine, message=str(exc))

def create_game_images_router(is_internal):
    router = APIRouter(prefix='/api/zico/games/images')
    def check(request):
        if not is_internal(request):
            raise HTTPException(403, 'Disponível somente no Maestro autenticado.')

    @router.get('/engines')
    def engines(request: Request):
        check(request)
        return {'engines': [{'id': key, 'available': ready(key), 'inferenceTested': ready(key)} for key in runner.ENGINES]}

    @router.post('', status_code=202)
    def create(request: Request, body: ImageRequest):
        check(request)
        if not valid_id(body.projectId) or not (ROOT / 'projects' / body.projectId / 'project.json').is_file():
            raise HTTPException(400, 'Selecione um projeto existente.')
        if body.engine not in runner.ENGINES:
            raise HTTPException(400, 'Motor não reconhecido. Escolha explicitamente um motor disponível.')
        if not ready(body.engine):
            raise HTTPException(503, 'Instalação ou verificação dos pesos ainda pendente.')
        folder = ROOT / 'image_jobs' / uuid.uuid4().hex
        folder.mkdir(parents=True)
        spec = {**body.model_dump(), 'jobId': folder.name}
        (folder / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
        initial = state(folder, 'queued', projectId=body.projectId, engine=body.engine)
        threading.Thread(target=worker, args=(folder, body), daemon=True).start()
        return initial

    def folder_for(job_id):
        if not valid_id(job_id):
            raise HTTPException(404)
        folder = ROOT / 'image_jobs' / job_id
        if not (folder / 'job.json').is_file():
            raise HTTPException(404)
        return folder

    @router.get('/{job_id}')
    def status(request: Request, job_id: str):
        check(request)
        return json.loads((folder_for(job_id) / 'job.json').read_text(encoding='utf-8'))

    @router.get('/{job_id}/output')
    def output(request: Request, job_id: str):
        check(request)
        target = folder_for(job_id) / 'image.png'
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type='image/png', filename='maestro_game_image.png')
    return router
