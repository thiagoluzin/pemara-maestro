"""Authenticated, persistent video-to-voice conversion with an explicit local engine."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import Field, StrictBool
from starlette.concurrency import run_in_threadpool

from voice_studio import ROOT, VoiceStudio, digest, identifier, read_json, write_json
from voice_studio_models import StrictModel
from voice_conversion_media import MAX_UPLOAD, SUFFIXES, probe
from voice_conversion_contract import ENGINE, CLI, MODEL, MODEL_SHA, SEPARATOR, SEPARATOR_SHA


class ConversionCreate(StrictModel):
    requestId: str = Field(pattern=r'^[a-f0-9]{32}$')
    mediaId: str = Field(pattern=r'^[a-f0-9]{32}$')
    voiceId: str = Field(pattern=r'^[a-f0-9]{32}$')
    title: str = Field(default='Troca de voz', min_length=1, max_length=120)
    audioTrack: int = Field(ge=0, le=128, strict=True)
    preserveBackground: StrictBool = True
    seed: int = Field(default=123, ge=0, le=2147483647, strict=True)


class VoiceConversion(VoiceStudio):
    engine_label = ENGINE
    route_prefix = '/api/studio/api/voice-conversion'

    def __init__(self, library, root=ROOT / 'conversion', **kwargs):
        super().__init__(root, **kwargs)
        self.library = library
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    def capabilities(self):
        installed = CLI.is_file() and MODEL.is_file() and MODEL.stat().st_size == 3629186752
        separation = SEPARATOR.is_file() and SEPARATOR.stat().st_size == 84059168
        try:
            connected = 'PemaraVoiceConvert' in self.comfy('/object_info/PemaraVoiceConvert')
            online = True
        except Exception:
            online, connected = False, False
        return {'engine': ENGINE, 'installed': installed, 'backgroundReady': separation, 'online': online,
                'connected': connected, 'ready': installed and connected, 'maxSeconds': 300, 'maxUploadBytes': MAX_UPLOAD,
                'message': 'Pronto para trocar a voz.' if installed and connected else
                           'O conversor local está sendo instalado.' if not installed else
                           'Aguardando conexão do conversor com o ComfyUI.'}

    @staticmethod
    def graph(job_id):
        return {'1': {'class_type': 'PemaraVoiceConvert', 'inputs': {'job_id': identifier(job_id)}}}

    @staticmethod
    def result_complete(result):
        return (result.get('metrics', {}).get('complete') is True and
                result.get('metrics', {}).get('finish_reason') == 'converted' and
                result.get('sourceSamples') == result.get('outputSamples') and
                result.get('sampleRate') == 44100)

    def register_media(self, media_id, filename, path):
        info = probe(path)
        record = {'id': media_id, 'name': Path(filename).name[:200], 'file': path.name, **info,
                  'sha256': digest(path), 'createdAt': time.time()}
        write_json(path.parent / 'media.json', record)
        with self.db() as db:
            db.execute('INSERT INTO media VALUES (?,?)', (media_id, json.dumps(record, ensure_ascii=False)))
        return self.public_media(record)

    @staticmethod
    def public_media(record):
        return {key: record[key] for key in ('id', 'name', 'duration', 'hasVideo', 'tracks')}

    def media(self, media_id):
        with self.db() as db:
            row = db.execute('SELECT data FROM media WHERE id=?', (identifier(media_id),)).fetchone()
        if not row:
            raise HTTPException(404, 'Fonte não encontrada.')
        return json.loads(row[0])

    def create(self, body: ConversionCreate):
        payload = body.model_dump()
        signature = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self._mutex, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT signature, data FROM jobs WHERE id=?', (body.requestId,)).fetchone()
            if previous:
                if previous[0] != signature:
                    raise HTTPException(409, 'Este envio já foi usado para outra conversão.')
                return json.loads(previous[1])
            if db.execute("SELECT id FROM jobs WHERE status IN ('QUEUED','SUBMITTING','RUNNING','CANCELLING','SUBMISSION_UNCERTAIN') LIMIT 1").fetchone():
                raise HTTPException(409, 'Uma conversão já está em andamento. Acompanhe-a abaixo.')
            media = self.media(body.mediaId)
            source = self.root / 'media' / body.mediaId / media['file']
            if digest(source) != media['sha256']:
                raise HTTPException(409, 'A fonte foi alterada. Importe o arquivo novamente.')
            if body.audioTrack not in [track['index'] for track in media['tracks']]:
                raise HTTPException(422, 'Selecione uma faixa de áudio da fonte.')
            voice = self.library.voice(body.voiceId, verify=True)
            if voice['duration'] > 30:
                raise HTTPException(422, 'Para conversão, cadastre uma referência de voz de até 30 segundos.')
            folder = self.folder(body.requestId); folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.library.root / 'voices' / voice['id'] / 'reference.wav', folder / 'reference.wav')
            reference = {key: voice[key] for key in ('id', 'name', 'sha256', 'authorized', 'authorizationRecordedAt')}
            request = {'schema': 'pemara-voice-conversion-v1', 'id': body.requestId, 'settings': payload,
                       'source': media, 'reference': reference, 'engine': ENGINE, 'createdAt': time.time()}
            write_json(folder / 'request.json', request); write_json(folder / 'workflow.api.json', self.graph(body.requestId))
            record = {'id': body.requestId, 'status': 'QUEUED', 'title': body.title, 'text': '', 'voiceName': voice['name'],
                      'voiceId': voice['id'], 'mediaId': body.mediaId, 'sourceName': media['name'], 'sourceDuration': media['duration'],
                      'engine': ENGINE, 'settings': payload, 'createdAt': request['createdAt'],
                      'review': {'decision': 'pending', 'note': ''}, 'requestSha256': digest(folder / 'request.json'),
                      'promptId': None, 'error': None}
            db.execute('INSERT INTO jobs VALUES (?,?,?,?,?)', (record['id'], signature, record['status'], record['createdAt'], json.dumps(record, ensure_ascii=False)))
        self.launcher(record['id'])
        return self.get(record['id'])


def create_conversion_router(service, is_internal, browser_origin_allowed=None):
    router = APIRouter(prefix='/api/voice-conversion')

    def authorize(request):
        if not is_internal(request) or (browser_origin_allowed is not None and not browser_origin_allowed(request)):
            raise HTTPException(403, 'Abra a conversão pelo Maestro autenticado.')

    @router.get('/status')
    def status(request: Request):
        authorize(request); return service.capabilities()

    @router.post('/media', status_code=201)
    async def upload(request: Request, filename: str):
        authorize(request)
        if len(filename) > 500:
            raise HTTPException(422, 'Nome do arquivo acima do limite.')
        suffix = Path(filename).suffix.lower()
        if suffix not in SUFFIXES:
            raise HTTPException(415, 'Use MP4, MOV, MKV, WebM ou um arquivo de áudio.')
        media_id = uuid.uuid4().hex
        folder = service.root / 'media' / media_id; folder.mkdir(parents=True)
        path = folder / ('original' + suffix)
        try:
            size = 0
            with path.open('xb') as output:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > MAX_UPLOAD:
                        raise HTTPException(413, 'O limite por arquivo é 1 GB.')
                    output.write(chunk)
            return await run_in_threadpool(service.register_media, media_id, filename, path)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @router.get('/media/{media_id}')
    def media(request: Request, media_id: str):
        authorize(request); return service.public_media(service.media(media_id))

    @router.get('/media/{media_id}/preview')
    def preview(request: Request, media_id: str):
        authorize(request); record = service.media(media_id)
        return FileResponse(service.root / 'media' / media_id / record['file'], headers={'Cache-Control': 'private, no-store'})

    @router.post('/jobs', status_code=202)
    async def create(request: Request):
        authorize(request)
        if request.headers.get('content-type', '').split(';')[0].lower() != 'application/json':
            raise HTTPException(415, 'Envie os parâmetros como JSON.')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 12000:
                raise HTTPException(413, 'Pedido acima do limite.')
        try:
            options = ConversionCreate.model_validate_json(bytes(raw))
        except ValueError:
            raise HTTPException(422, 'Confira a fonte, a faixa e a voz selecionadas.')
        return await run_in_threadpool(service.create, options)

    @router.get('/jobs')
    def jobs(request: Request, page: int = 1):
        authorize(request)
        if not 1 <= page <= 10000: raise HTTPException(422, 'Página inválida.')
        return service.jobs(page, 20)

    @router.get('/jobs/{job_id}')
    def job(request: Request, job_id: str):
        authorize(request); return service.get(job_id)

    @router.post('/jobs/{job_id}/cancel')
    def cancel(request: Request, job_id: str):
        authorize(request); return service.cancel(job_id)

    @router.get('/jobs/{job_id}/audio/{format}')
    def audio(request: Request, job_id: str, format: str):
        authorize(request); record = service.get(job_id)
        if record['status'] != 'COMPLETED' or format not in ('wav', 'mp3'):
            raise HTTPException(404, 'Conversão ainda indisponível.')
        path = service.folder(job_id) / ('speech.' + format)
        expected = record['result'].get(format + 'Sha256')
        if not expected or not path.is_file() or digest(path) != expected:
            raise HTTPException(409, 'Arquivo ausente ou alterado.')
        return FileResponse(path, media_type='audio/wav' if format == 'wav' else 'audio/mpeg',
                            filename='voz-sincronizada-' + job_id[:8] + '.' + format,
                            content_disposition_type='attachment' if request.query_params.get('download') == '1' else 'inline',
                            headers={'Cache-Control': 'private, no-store'})

    @router.get('/jobs/{job_id}/source-audio')
    def source_audio(request: Request, job_id: str):
        authorize(request); record = service.get(job_id)
        path = service.folder(job_id) / 'original_timeline.wav'
        if record['status'] != 'COMPLETED' or not path.is_file() or digest(path) != record['result'].get('originalTimelineSha256'):
            raise HTTPException(404, 'Áudio original indisponível.')
        return FileResponse(path, media_type='audio/wav', headers={'Cache-Control': 'private, no-store'})

    @router.get('/jobs/{job_id}/receipt')
    def receipt(request: Request, job_id: str):
        authorize(request); record = service.get(job_id)
        return JSONResponse({key: record.get(key) for key in ('id', 'engine', 'sourceName', 'sourceDuration', 'voiceName', 'settings', 'result')},
                            headers={'Content-Disposition': f'attachment; filename="conversao-{job_id}.json"'})

    return router
