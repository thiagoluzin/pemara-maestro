"""Persistent local voice library and ComfyUI-backed narration jobs.

Only Maestro's autonomous backend uses the HTTP client below. Codex operates
ComfyUI through its MCP, including validation and any qualification generation.
No cloud provider, fallback engine, or visual finishing enters this audio route.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid
import wave
from contextlib import contextmanager

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from voice_studio_models import NarrationCreate, ReviewCreate, VoiceCreate

BASE = Path(__file__).resolve().parents[2]
ROOT = BASE / 'dados/studio/voice_studio'
RUNTIME = Path(os.environ.get('PEMARA_DRAMA3_SOURCE', 'E:/a terra rejeita/Ferramentas/Drama3/source'))
MODELS = Path(os.environ.get('PEMARA_DRAMA3_MODELS', 'G:/Pemara_AI_Models/Drama3/Eng-Ahmd_57d3598'))
ACTIVE = ('QUEUED', 'SUBMITTING', 'RUNNING', 'CANCELLING', 'SUBMISSION_UNCERTAIN')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(40):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(min(.025 * (attempt + 1), .15))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def identifier(value):
    if not re.fullmatch(r'[a-f0-9]{32}', value):
        raise HTTPException(404, 'Registro não encontrado.')
    return value


class LocalComfy:
    def __init__(self, url=None):
        self.url = (url or os.environ.get('PEMARA_COMFY_URL', 'http://127.0.0.1:8188')).rstrip('/')
        parsed = urllib.parse.urlsplit(self.url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError('O estúdio de voz exige o ComfyUI local.')

    def __call__(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.url + path, data=data, headers={'Content-Type': 'application/json'})
        # Even a machine-level HTTP proxy must not route local voice traffic out.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=12) as response:
            return json.load(response)


class VoiceStudio:
    engine_label = 'Drama 3'
    route_prefix = '/api/studio/api/voice-studio'

    @staticmethod
    def result_complete(result):
        return result['metrics'].get('complete') and result['metrics'].get('finish_reason') == 'eos'

    def __init__(self, root=ROOT, *, comfy=None, lease=None, launcher=None, runtime=RUNTIME, models=MODELS):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.runtime, self.models = Path(runtime), Path(models)
        self.comfy, self.lease = comfy or LocalComfy(), lease
        self.launcher = launcher or self._launch
        self._threads = set()
        self._mutex = threading.RLock()
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS voices (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, signature TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, data TEXT NOT NULL)')

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.root / 'library.sqlite3', timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _save(self, record):
        with self.db() as db:
            db.execute('UPDATE jobs SET status=?, data=? WHERE id=?', (record['status'], json.dumps(record, ensure_ascii=False), record['id']))

    def raw(self, job_id):
        with self.db() as db:
            row = db.execute('SELECT data FROM jobs WHERE id=?', (identifier(job_id),)).fetchone()
        if not row:
            raise HTTPException(404, 'Narração não encontrada.')
        return json.loads(row[0])

    def folder(self, job_id):
        return self.root / 'jobs' / identifier(job_id)

    def voices(self):
        with self.db() as db:
            rows = db.execute('SELECT data FROM voices ORDER BY rowid DESC').fetchall()
        return [json.loads(row[0]) for row in rows]

    def voice(self, voice_id, *, verify=False):
        with self.db() as db:
            row = db.execute('SELECT data FROM voices WHERE id=?', (identifier(voice_id),)).fetchone()
        if not row:
            raise HTTPException(404, 'Voz não encontrada.')
        result = json.loads(row[0])
        if verify and digest(self.root / 'voices' / voice_id / 'reference.wav') != result['sha256']:
            raise HTTPException(409, 'A referência desta voz foi alterada. Cadastre uma nova referência.')
        return result

    def register_voice(self, voice_id, options, source):
        """Decode and bound the reference before making it available for cloning."""
        folder = self.root / 'voices' / identifier(voice_id)
        target = folder / 'reference.wav'
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            raise HTTPException(503, 'FFmpeg local indisponível para preparar a referência.')
        try:
            subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-n', '-i', str(source), '-t', '61', '-vn',
                            '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', str(target)],
                           check=True, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with wave.open(str(target)) as audio:
                duration = audio.getnframes() / audio.getframerate()
            if not 1 <= duration <= 60:
                raise ValueError('Use uma referência de 1 a 60 segundos; o arquivo original foi preservado.')
        except (OSError, subprocess.SubprocessError, wave.Error, ValueError) as error:
            raise HTTPException(422, str(error) if isinstance(error, ValueError) else 'Não foi possível ler o áudio. Use WAV, MP3, M4A, OGG ou FLAC válidos.') from error
        record = {'id': voice_id, **options.model_dump(), 'duration': duration, 'sha256': digest(target),
                  'createdAt': time.time(), 'authorizationRecordedAt': time.time(), 'origin': 'operator_reference',
                  'previewUrl': f'/api/studio/api/voice-studio/voices/{voice_id}/audio'}
        write_json(folder / 'voice.json', record)
        with self.db() as db:
            db.execute('INSERT INTO voices VALUES (?, ?)', (voice_id, json.dumps(record, ensure_ascii=False)))
        return record

    def capabilities(self):
        files = [self.runtime / '.venv/Scripts/python.exe', self.models / 'model/manifest.json',
                 self.models / 'model/model.gguf', self.models / 'codec/codec.gguf']
        installed = all(path.is_file() for path in files)
        try:
            catalog = self.comfy('/object_info/PemaraDrama3Studio')
            connected = 'PemaraDrama3Studio' in catalog
            online = True
        except Exception:
            online, connected = False, False
        return {'engine': 'Drama 3 local', 'installed': installed, 'online': online, 'connected': connected,
                'ready': installed and connected, 'mp3': bool(shutil.which('ffmpeg')),
                'message': ('Pronto para narrar e clonar vozes.' if installed and connected else
                            'ComfyUI indisponível.' if not online else
                            'A ponte do estúdio precisa ser carregada no ComfyUI.' if not connected else
                            'Verifique a instalação local do Drama 3.')}

    @staticmethod
    def graph(job_id):
        return {'1': {'class_type': 'PemaraDrama3Studio', 'inputs': {'job_id': identifier(job_id)}}}

    def create(self, body: NarrationCreate):
        payload = body.model_dump()
        signature = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._mutex, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT signature, data FROM jobs WHERE id=?', (body.requestId,)).fetchone()
            if row:
                if row[0] != signature:
                    raise HTTPException(409, 'Este identificador já foi usado para outra narração.')
                return json.loads(row[1])
            busy = db.execute('SELECT id FROM jobs WHERE status IN (?,?,?,?,?) LIMIT 1', ACTIVE).fetchone()
            if busy:
                raise HTTPException(409, 'Já existe uma narração em andamento. Acompanhe-a no histórico.')
            voice = self.voice(body.voiceId, verify=True) if body.voiceId else None
            folder = self.folder(body.requestId)
            folder.mkdir(parents=True, exist_ok=True)
            reference = None
            if voice:
                shutil.copy2(self.root / 'voices' / voice['id'] / 'reference.wav', folder / 'reference.wav')
                reference = {key: voice[key] for key in ('id', 'name', 'transcript', 'sha256', 'authorized', 'authorizationRecordedAt')}
            request = {'schema': 'pemara-voice-studio-v1', 'id': body.requestId, 'settings': payload,
                       'reference': reference, 'engine': 'Drama 3 local', 'createdAt': time.time()}
            write_json(folder / 'request.json', request)
            write_json(folder / 'workflow.api.json', self.graph(body.requestId))
            record = {'id': body.requestId, 'status': 'QUEUED', 'title': body.title, 'text': body.text,
                      'voiceName': voice['name'] if voice else 'Voz livre do modelo', 'voiceId': body.voiceId,
                      'settings': payload, 'createdAt': request['createdAt'], 'review': {'decision': 'pending', 'note': ''},
                      'requestSha256': digest(folder / 'request.json'), 'promptId': None, 'error': None}
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?)', (record['id'], signature, record['status'], record['createdAt'], json.dumps(record, ensure_ascii=False)))
        self.launcher(record['id'])
        return self.get(record['id'])

    def _launch(self, job_id, resume=False):
        with self._mutex:
            if job_id in self._threads:
                return
            self._threads.add(job_id)
        threading.Thread(target=self._run, args=(job_id, resume), daemon=True, name='maestro-narration-' + job_id[:8]).start()

    def recover(self):
        with self.db() as db:
            rows = db.execute('SELECT data FROM jobs WHERE status IN (?,?,?,?,?)', ACTIVE).fetchall()
        for row in rows:
            record = json.loads(row[0])
            if (self.folder(record['id']) / 'result.json').exists():
                self.get(record['id'])
            elif record.get('promptId'):
                self._launch(record['id'], resume=True)
            elif record['status'] in ('SUBMITTING', 'SUBMISSION_UNCERTAIN', 'CANCELLING'):
                record.update(status='SUBMISSION_UNCERTAIN', error='Encontre ou cancele esta tentativa antes de reenviar. O servidor não confirmou o identificador do prompt.')
                self._save(record)
            else:
                record.update(status='INTERRUPTED', error='O servidor reiniciou antes de confirmar o envio. A tentativa foi preservada e não será reenviada automaticamente.')
                self._save(record)

    def _run(self, job_id, resume=False):
        reserved = False
        try:
            record = self.raw(job_id)
            folder = self.folder(job_id)
            if resume and self.lease:
                current = self.lease.status()
                if current.get('jobId') == job_id and not current.get('active'):
                    self.lease.release(job_id)
                try:
                    self.lease.acquire(owner='maestro_voice_studio', operation='drama3_narration', job_id=job_id)
                    reserved = True
                except Exception:
                    # Existing engine execution still belongs to this job.
                    # Continue monitoring it without resubmitting or stopping it.
                    pass
            if not resume:
                if (folder / 'cancel.flag').exists():
                    record['status'] = 'CANCELLED'; self._save(record); return
                capability = self.capabilities()
                if not capability['ready']:
                    raise RuntimeError(capability.get('message') or f'{self.engine_label} ou sua ponte local indisponível.')
                if self.lease:
                    self.lease.acquire(owner='maestro_voice_studio', operation='drama3_narration', job_id=job_id)
                    reserved = True
                # Do not unload or interrupt somebody else's work.
                queue = self.comfy('/queue')
                if queue.get('queue_running') or queue.get('queue_pending'):
                    raise RuntimeError('O ComfyUI está ocupado. Aguarde o trabalho atual e crie uma nova tentativa.')
                record['status'] = 'SUBMITTING'; self._save(record)
                try:
                    result = self.comfy('/prompt', {'prompt': self.graph(job_id), 'client_id': 'maestro-voice-' + job_id})
                except Exception:
                    record.update(status='SUBMISSION_UNCERTAIN', error='O envio não foi confirmado. Verifique a fila antes de repetir; não houve reenvio automático.')
                    self._save(record)
                    return
                if not result.get('prompt_id') or result.get('node_errors') or result.get('error'):
                    raise RuntimeError('O ComfyUI recusou o workflow de voz. Verifique a ponte instalada.')
                record.update(status='QUEUED', promptId=result['prompt_id']); self._save(record)
            prompt_id = self.raw(job_id)['promptId']
            while True:
                current = self.get(job_id)
                if current['status'] not in ACTIVE:
                    break
                if reserved:
                    self.lease.heartbeat(job_id)
                try:
                    history = self.comfy('/history/' + urllib.parse.quote(prompt_id, safe='')).get(prompt_id)
                    if history:
                        status = history.get('status', {})
                        if status.get('status_str') == 'error':
                            raise RuntimeError(f'{self.engine_label} encerrou a tentativa. Consulte o detalhe e preserve o áudio anterior.')
                        if status.get('completed') and not (folder / 'result.json').exists():
                            raise RuntimeError('O ComfyUI terminou sem um recibo de áudio válido.')
                    queue = self.comfy('/queue')
                    live = {str(row[1]) for key in ('queue_running', 'queue_pending') for row in queue.get(key, []) if len(row) > 1}
                    if not history and prompt_id not in live:
                        current.update(status='CANCELLED' if (folder / 'cancel.flag').exists() else 'INTERRUPTED',
                                       error=None if (folder / 'cancel.flag').exists() else 'A tentativa saiu da fila sem resultado. Nenhum reenvio automático foi feito.')
                        self._save(current); break
                except (OSError, TimeoutError):
                    pass  # Reattach to this same prompt after a temporary outage.
                time.sleep(2)
        except Exception as error:
            with self._mutex:
                record = self.raw(job_id)
                if record['status'] in ACTIVE:
                    record.update(status='CANCELLED' if (self.folder(job_id) / 'cancel.flag').exists() else 'FAILED',
                                  error=str(error)[:1000])
                    self._save(record)
        finally:
            if reserved:
                self.lease.release(job_id)
            with self._mutex:
                self._threads.discard(job_id)

    def get(self, job_id):
        with self._mutex:
            record, folder = self.raw(job_id), self.folder(job_id)
            result_path = folder / 'result.json'
            if result_path.exists() and record['status'] in (*ACTIVE, 'COMPLETED'):
                try:
                    result = read_json(result_path)
                    if result['requestSha256'] != record['requestSha256'] or digest(folder / 'request.json') != record['requestSha256']:
                        raise ValueError('A receita da narração foi alterada.')
                    if digest(folder / 'speech.wav') != result['wavSha256'] or not self.result_complete(result):
                        raise ValueError('O áudio está incompleto ou sua integridade foi alterada.')
                    record.update(status='COMPLETED', result=result, error=None)
                except (KeyError, ValueError, OSError) as error:
                    record.update(status='INTEGRITY_ERROR', error=str(error))
                self._save(record)
            elif (folder / 'error.json').exists() and record['status'] in ACTIVE:
                error = read_json(folder / 'error.json')
                record.update(status='CANCELLED' if error.get('cancelled') else 'FAILED', error=error.get('message', 'Falha no motor local.'))
                self._save(record)
            elif (folder / 'progress.json').exists() and record['status'] in ACTIVE:
                progress = read_json(folder / 'progress.json')
                record['progress'] = progress
                if record['status'] != 'CANCELLING':
                    record['status'] = 'RUNNING'
                self._save(record)
            if record['status'] == 'COMPLETED':
                record['audioUrl'] = f'{self.route_prefix}/jobs/{job_id}/audio/wav'
                if record['result'].get('mp3Sha256'):
                    record['mp3Url'] = f'{self.route_prefix}/jobs/{job_id}/audio/mp3'
            return record

    def jobs(self, page=1, page_size=20):
        with self.db() as db:
            total = db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
            rows = db.execute('SELECT id FROM jobs ORDER BY created DESC LIMIT ? OFFSET ?', (page_size, (page - 1) * page_size)).fetchall()
        return {'total': total, 'jobs': [self.get(row[0]) for row in rows]}

    def cancel(self, job_id):
        with self._mutex:
            record = self.get(job_id)
            if record['status'] not in ACTIVE:
                return record
            (self.folder(job_id) / 'cancel.flag').touch()
            if record['status'] == 'SUBMISSION_UNCERTAIN' and not record.get('promptId'):
                # The flag prevents a late node from starting this job. A node
                # already in progress observes it and stops its own worker.
                record.update(status='CANCELLED', error='Cancelamento registrado. Um envio tardio desta tentativa permanece bloqueado.')
                self._save(record)
                return self.get(job_id)
            record['status'] = 'CANCELLING'; self._save(record)
            if record.get('promptId'):
                try:
                    self.comfy('/queue', {'delete': [record['promptId']]})
                except Exception:
                    pass  # The per-job flag also cancels a running node; no global interrupt.
            return self.get(job_id)

    def review(self, job_id, body):
        with self._mutex:
            record = self.get(job_id)
            if record['status'] != 'COMPLETED':
                raise HTTPException(409, 'Somente uma narração concluída e íntegra pode ser avaliada.')
            review = {**body.model_dump(), 'createdAt': time.time(), 'wavSha256': record['result']['wavSha256']}
            folder = self.folder(job_id) / 'reviews'; folder.mkdir(exist_ok=True)
            write_json(folder / (uuid.uuid4().hex + '.json'), review)
            record['review'] = review; self._save(record)
            return self.get(job_id)


def create_voice_studio_router(service, is_internal):
    router = APIRouter(prefix='/api/voice-studio')

    def authorize(request: Request):
        if not is_internal(request):
            raise HTTPException(403, 'Abra o estúdio pelo Maestro autenticado.')

    async def body(request, model):
        authorize(request)
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            raise HTTPException(415, 'Envie os dados como JSON.')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 100_000:
                raise HTTPException(413, 'Texto acima do limite de tamanho.')
        try:
            return model.model_validate_json(bytes(raw))
        except ValueError as error:
            raise HTTPException(422, 'Revise texto, voz, modo e limites dos controles.') from error

    @router.get('/status')
    def status(request: Request):
        authorize(request)
        return service.capabilities()

    @router.get('/voices')
    def voices(request: Request):
        authorize(request)
        return {'voices': service.voices()}

    @router.post('/voices', status_code=201)
    async def voice(request: Request, audio: UploadFile = File(...), metadata: str = Form(...)):
        authorize(request)
        try:
            if len(metadata) > 24_000:
                raise ValueError()
            options = VoiceCreate.model_validate_json(metadata)
        except ValueError:
            raise HTTPException(422, 'Preencha nome, transcrição exata e autorização de uso da voz.')
        suffix = Path(audio.filename or '').suffix.lower()
        if suffix not in {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.webm', '.aac', '.opus'}:
            raise HTTPException(415, 'Use um arquivo de áudio WAV, MP3, M4A, OGG ou FLAC.')
        voice_id = uuid.uuid4().hex
        folder = service.root / 'voices' / voice_id; folder.mkdir(parents=True)
        source = folder / ('source' + suffix)
        try:
            size = 0
            with source.open('xb') as stream:
                while chunk := await audio.read(1024 * 1024):
                    size += len(chunk)
                    if size > 32 * 1024 * 1024:
                        raise HTTPException(413, 'O limite da referência é 32 MB.')
                    stream.write(chunk)
            return await run_in_threadpool(service.register_voice, voice_id, options, source)
        finally:
            await audio.close()

    @router.get('/voices/{voice_id}/audio')
    def reference(request: Request, voice_id: str):
        authorize(request); service.voice(voice_id, verify=True)
        return FileResponse(service.root / 'voices' / voice_id / 'reference.wav', media_type='audio/wav', headers={'Cache-Control': 'private, no-store'})

    @router.post('/jobs', status_code=202)
    async def create(request: Request):
        return await run_in_threadpool(service.create, await body(request, NarrationCreate))

    @router.get('/jobs')
    def jobs(request: Request, page: int = 1, pageSize: int = 20):
        authorize(request)
        if not 1 <= page <= 10000 or not 1 <= pageSize <= 50:
            raise HTTPException(422, 'Paginação inválida.')
        return service.jobs(page, pageSize)

    @router.get('/jobs/{job_id}')
    def job(request: Request, job_id: str):
        authorize(request); return service.get(job_id)

    @router.post('/jobs/{job_id}/cancel')
    def cancel(request: Request, job_id: str):
        authorize(request); return service.cancel(job_id)

    @router.post('/jobs/{job_id}/review')
    async def review(request: Request, job_id: str):
        return service.review(job_id, await body(request, ReviewCreate))

    @router.get('/jobs/{job_id}/recipe')
    def recipe(request: Request, job_id: str):
        authorize(request)
        record = service.get(job_id)
        # Reference audio and filesystem paths stay in the protected local store.
        exported = {'schema': 'pemara-voice-recipe-v1', 'engine': 'Drama 3 local', 'title': record['title'],
                    'settings': record['settings'], 'voiceName': record['voiceName'], 'review': record['review'],
                    'result': record.get('result')}
        from fastapi.responses import JSONResponse
        return JSONResponse(exported, headers={'Content-Disposition': f'attachment; filename="narracao-{job_id}.json"', 'Cache-Control': 'private, no-store'})

    @router.get('/jobs/{job_id}/audio/{format}')
    def audio(request: Request, job_id: str, format: str):
        authorize(request); record = service.get(job_id)
        if format not in ('wav', 'mp3') or record['status'] != 'COMPLETED':
            raise HTTPException(404, 'Áudio indisponível.')
        path = service.folder(job_id) / ('speech.' + format)
        expected = record['result'].get(format + 'Sha256')
        if not expected or not path.is_file() or digest(path) != expected:
            raise HTTPException(409, 'Áudio ausente ou alterado.')
        return FileResponse(path, media_type='audio/wav' if format == 'wav' else 'audio/mpeg',
                            filename='narracao-' + job_id[:8] + '.' + format,
                            content_disposition_type='attachment' if request.query_params.get('download') == '1' else 'inline',
                            headers={'Cache-Control': 'private, no-store'})

    return router
