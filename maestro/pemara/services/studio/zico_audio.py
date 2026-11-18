"""Local ZICO integration; existing Maestro generators retain their own jobs/gates."""
from pathlib import Path
import json
import shutil
import subprocess
import uuid
import threading
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'ferramentas/audio_neural/zico_audio_studio'
OUTPUTS = ROOT / 'outputs'

class RouteRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)
    language: str = 'pt-br'
    fidelity: str = 'balanced'

class MixRequest(BaseModel):
    dialogue: str | None = None
    music: str | None = None
    sfx: list[str] = Field(default_factory=list, max_length=16)
    target_lufs: float = Field(default=-14, ge=-36, le=-9)

class FishRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    seed: int = Field(default=42, ge=0, le=2147483647)

class GameProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    brief: str = Field(default='', max_length=8000)

class GameExportRequest(BaseModel):
    jobId: str = Field(pattern=r'^[a-f0-9]{32}$')
    kind: str = Field(pattern=r'^(jobs|image_jobs)$')

GAME_ROOT = PROJECT / 'ferramentas/game_ai_studio'
GAME_PROJECTS = PROJECT / 'dados/game_ai/projects'

def game_catalog():
    manifest = json.loads((GAME_ROOT / 'components.json').read_text(encoding='utf-8-sig'))
    receipt_path = GAME_ROOT / 'installation_receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.is_file() else {}
    installed = receipt.get('components', {})
    rows = []
    for item in manifest['components']:
        entry = installed.get(item['id'], {})
        required = entry.get('requiredPaths', [])
        available = bool(required) and all(Path(p).exists() for p in required)
        status = entry.get('status', 'Instalação e validação pendentes')
        if required and not available:
            status = 'Arquivos necessários incompletos; instalação pendente'
        rows.append({**item, 'status': status, 'filesPresent': available})
    return {'components': rows, 'generationEnabled': False, 'nativeIntegrationRevision': 2,
            'staticAssetProcessing': bool(shutil.which('blender')) or Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe').is_file()}

def game_projects():
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(GAME_PROJECTS.glob('*/project.json'))]

def create_game_project(body):
    project_id = uuid.uuid4().hex
    folder = GAME_PROJECTS / project_id
    for child in ('references', 'assets', 'exports'):
        (folder / child).mkdir(parents=True, exist_ok=True)
    data = {'id': project_id, 'name': body.name.strip(), 'brief': body.brief,
            'status': 'briefing', 'generationEnabled': False}
    (folder / 'project.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data

def fish_job(body):
    if not (ROOT/'all_weights_verified.json').is_file():
        raise HTTPException(503,'Pesos Fish Speech ainda não verificados.')
    job_id=uuid.uuid4().hex
    folder=OUTPUTS/job_id
    folder.mkdir(parents=True)
    (folder/'text.txt').write_text(body.text,encoding='utf-8')
    def state(status, **fields):
        data={'jobId':job_id,'engine':'fish_speech','status':status,**fields}
        temporary=folder/'job.tmp'
        temporary.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        temporary.replace(folder/'job.json')
        return data
    initial=state('queued')
    def worker():
        state('running')
        try:
            with (folder/'inference.log').open('w',encoding='utf-8') as log:
                result=subprocess.run([str(ROOT/'engines/fish/repo/.venv/Scripts/python.exe'),str(ROOT/'scripts/fish_runner.py'),
                    '--text-file',str(folder/'text.txt'),'--output',str(folder/'master.wav'),'--job-id',job_id,'--seed',str(body.seed)],
                    stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            if result.returncode or not (folder/'master.wav').is_file():
                raise RuntimeError('Falha na geração; consulte inference.log do job.')
            from video_sound import probe_audio
            qc=probe_audio(folder/'master.wav')
            state('done',reviewStatus='PENDING_HUMAN_REVIEW',qc=qc,url=f'/api/zico/outputs/{job_id}')
        except Exception as exc:
            state('error',message=str(exc))
    threading.Thread(target=worker,name='zico-'+job_id[:8],daemon=True).start()
    return initial

def capabilities():
    receipt_path = ROOT / 'installation_receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig')) if receipt_path.exists() else {}
    return {'post': {'mix_master': bool(shutil.which('ffmpeg')), 'sampleRate': 48000}, 'nativeIntegrationRevision': 2,
            'engines': receipt.get('engines', []),
            'generationPolicy': 'explicit_engine_and_human_review',
            'inferenceTests': receipt.get('validation', {}).get('inferenceTests', {})}

def route(r):
    task = r.task.casefold()
    if any(s in task for s in ('trocar instrumento', 'reorquestr', 'trocar instrumentação', 'mudar instrumentos', 'reinstrument')):
        raise HTTPException(410, 'Reinstrumentação removida pelo proprietário. Criação de músicas permanece disponível.')
    elif any(s in task for s in ('efeito', 'foley', 'som do vídeo', 'som do video')):
        engine, mode, endpoint = 'mmaudio', 'video_to_audio', '/api/video-sound/providers'
    elif any(s in task for s in ('música', 'musica', 'trilha')):
        engine, mode, endpoint = 'yue2_local', 'music', '/api/generative/jobs'
    elif any(s in task for s in ('diálogo', 'dialogo')):
        engine, mode, endpoint = 'fish_speech', 'dialogue', None
    elif any(s in task for s in ('atuar', 'gritar', 'sussurr', 'voz')):
        engine, mode, endpoint = 'qwen3_tts', 'expressive', None
    else:
        engine, mode, endpoint = 'chatterbox', 'narration', None
    return {'engine': engine, 'mode': mode, 'language': r.language, 'maestroEndpoint': endpoint,
            'submitted': False, 'message': 'Sugestão de rota; escolha explícita antes de gerar.'}

def mix(r):
    sources = [Path(p).resolve() for p in [r.dialogue, r.music, *r.sfx] if p]
    if not sources:
        raise HTTPException(400, 'Informe ao menos uma faixa.')
    for source in sources:
        if not source.is_file() or source.suffix.lower() not in {'.wav','.flac','.mp3','.m4a','.aac','.ogg','.opus'}:
            raise HTTPException(400, 'Entrada precisa ser um arquivo de áudio local existente.')
    job_id = uuid.uuid4().hex
    folder = OUTPUTS / job_id
    folder.mkdir(parents=True)
    target = folder / 'master.wav'
    argv = ['ffmpeg','-nostdin','-hide_banner','-v','error']
    for source in sources:
        argv += ['-i', str(source)]
    # Real one-pass loudnorm; do not claim two-pass mastering.
    filters = f'amix=inputs={len(sources)}:duration=longest:normalize=0,loudnorm=I={r.target_lufs}:TP=-1:LRA=11'
    result = subprocess.run([*argv,'-filter_complex',filters,'-ar','48000','-c:a','pcm_s24le',str(target)],
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
    if result.returncode:
        raise HTTPException(422, result.stderr[-1200:])
    return {'jobId':job_id,'output':str(target),'reviewStatus':'PENDING_HUMAN_REVIEW',
            'url':f'/api/zico/outputs/{job_id}', 'normalization':'loudnorm_single_pass'}

def create_zico_router(is_internal_request):
    router = APIRouter(prefix='/api/zico', tags=['ZICO áudio'])

    def check(request):
        if not is_internal_request(request):
            raise HTTPException(403, 'Disponível somente no acesso interno do Maestro.')

    @router.get('', response_class=HTMLResponse)
    def page(request: Request):
        check(request)
        return (ROOT / 'app/panel.html').read_text(encoding='utf-8')

    @router.get('/capabilities')
    def status(request: Request):
        check(request)
        return capabilities()

    @router.get('/games/catalog')
    def games_catalog_api(request: Request):
        check(request)
        return game_catalog()

    @router.get('/games/projects')
    def games_projects_api(request: Request):
        check(request)
        return {'projects': game_projects()}

    @router.get('/games/jobs')
    def games_jobs_api(request: Request):
        check(request)
        results = []
        for kind in ('jobs', 'image_jobs'):
            for path in (GAME_PROJECTS.parent / kind).glob('*/job.json'):
                try:
                    data = json.loads(path.read_text(encoding='utf-8'))
                    results.append({**data, 'kind': kind})
                except (OSError, ValueError):
                    continue
        return {'jobs': sorted(results, key=lambda job: job.get('updatedAt', ''), reverse=True)[:100]}

    @router.get('/games/unity-package')
    def unity_package(request: Request):
        check(request)
        target = GAME_ROOT / 'maestro-unity-bridge.zip'
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type='application/zip', filename=target.name)

    @router.post('/games/export')
    def export_game_asset(request: Request, body: GameExportRequest):
        check(request)
        folder = GAME_PROJECTS.parent / body.kind / body.jobId
        status_file = folder / 'job.json'
        if not status_file.is_file() or json.loads(status_file.read_text(encoding='utf-8')).get('status') != 'done':
            raise HTTPException(409, 'A produção precisa estar concluída para exportar.')
        name = 'image.png' if body.kind == 'image_jobs' else 'asset.glb'
        source = folder / name
        if not source.is_file():
            raise HTTPException(404)
        target_folder = GAME_PROJECTS.parent / 'data/outbox' / body.jobId
        target_folder.mkdir(parents=True, exist_ok=True)
        target = target_folder / name
        if target.exists():
            raise HTTPException(409, 'Este resultado já foi exportado; o arquivo existente foi preservado.')
        with target.open('xb') as output, source.open('rb') as source_file:
            shutil.copyfileobj(source_file, output)
        return {'exported': True, 'message': 'Disponível na pasta de exportação para o Unity.'}

    @router.post('/games/projects', status_code=201)
    def games_create_api(request: Request, body: GameProjectRequest):
        check(request)
        return create_game_project(body)

    @router.post('/route')
    def route_api(request: Request, body: RouteRequest):
        check(request)
        return route(body)

    @router.post('/mix')
    def mix_api(request: Request, body: MixRequest):
        check(request)
        return mix(body)

    @router.post('/uploads', status_code=201)
    async def upload_api(request: Request, audio: UploadFile = File(...)):
        check(request)
        suffix = Path(audio.filename or '').suffix.lower()
        if suffix not in {'.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg', '.opus'}:
            raise HTTPException(400, 'Formato de áudio não suportado.')
        folder = ROOT / 'uploads' / uuid.uuid4().hex
        folder.mkdir(parents=True)
        target = folder / ('source' + suffix)
        count = 0
        try:
            with target.open('xb') as output:
                while chunk := await audio.read(1024 * 1024):
                    count += len(chunk)
                    if count > 128 * 1024 * 1024:
                        raise HTTPException(413, 'O limite por faixa é 128 MB.')
                    output.write(chunk)
            if count == 0:
                raise HTTPException(400, 'Arquivo vazio.')
            return {'path': str(target), 'size': count}
        finally:
            await audio.close()

    @router.post('/fish/jobs', status_code=202)
    def fish_api(request: Request, body: FishRequest):
        check(request)
        return fish_job(body)

    @router.get('/jobs/{job_id}')
    def job_api(request: Request, job_id: str):
        check(request)
        if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise HTTPException(404)
        target=OUTPUTS/job_id/'job.json'
        if not target.is_file():raise HTTPException(404)
        return json.loads(target.read_text(encoding='utf-8'))

    @router.get('/jobs')
    def audio_jobs_api(request: Request):
        check(request)
        rows = []
        for folder in OUTPUTS.glob('*'):
            if not folder.is_dir() or len(folder.name) != 32 or any(c not in '0123456789abcdef' for c in folder.name):
                continue
            job_file = folder / 'job.json'
            if job_file.is_file():
                data = json.loads(job_file.read_text(encoding='utf-8'))
            elif (folder / 'master.wav').is_file():
                data = {'jobId': folder.name, 'engine': 'mixagem', 'status': 'done', 'url': f'/api/zico/outputs/{folder.name}'}
            else:
                continue
            rows.append({**data, 'updatedAt': folder.stat().st_mtime})
        return {'jobs': sorted(rows, key=lambda job: job['updatedAt'], reverse=True)[:30]}

    @router.get('/outputs/{job_id}')
    def output_api(request: Request, job_id: str):
        check(request)
        if len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
            raise HTTPException(404)
        target = OUTPUTS / job_id / 'master.wav'
        if not target.is_file():
            raise HTTPException(404)
        return FileResponse(target, media_type='audio/wav', filename='zico_master.wav')
    return router
