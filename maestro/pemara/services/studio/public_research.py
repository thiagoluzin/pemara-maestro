"""Authenticated, bounded public research UI/API backed by the existing Harness."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

BASE = Path(__file__).resolve().parents[2]
HARNESS = Path('E:/Pemara/pemara_harness')
NODE = Path('C:/Program Files/nodejs/node.exe')
ROOT = BASE / 'dados' / 'studio' / 'public_research'
PROJECTS = BASE / 'ferramentas' / 'video_global_engine' / 'projetos'
ID = re.compile(r'^[a-f0-9]{32}$')
TERMINAL = {'READY_FOR_REVIEW', 'INTERRUPTED_REVIEW_REQUIRED', 'INTEGRITY_CHANGED'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path, maximum=3_000_000):
    if path.stat().st_size > maximum:
        raise ValueError('Arquivo de pesquisa acima do limite.')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def public_url(value: str, domains: list[str]):
    url = urlsplit(value)
    host = (url.hostname or '').lower()
    if (url.scheme != 'https' or url.username or url.password or url.query or url.port or
            not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', host) or
            re.fullmatch(r'[\d.]+', host) or
            re.search(r'(?:^|\.)(?:localhost|local|internal|invalid|test)$', host) or host not in domains):
        raise ValueError('Use URLs HTTPS públicas dos domínios informados, sem credenciais, porta ou parâmetros.')
    return value.split('#')[0]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Claim(StrictModel):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,48}$')
    text: str = Field(min_length=1, max_length=1000)
    sourceUrl: str | None = Field(default=None, max_length=2000)
    quote: str | None = Field(default=None, min_length=1, max_length=1000)


class Reference(StrictModel):
    kind: Literal['general', 'character'] = 'general'
    work: str = Field(default='', max_length=200)
    edition: str = Field(default='', max_length=200)
    incarnation: str = Field(default='', max_length=200)

    @model_validator(mode='after')
    def version_required(self):
        if self.kind == 'character' and not all(v.strip() for v in (self.work, self.edition, self.incarnation)):
            raise ValueError('Personagem existente exige obra, edição/época e encarnação/traje definidos.')
        return self


class ResearchCreate(StrictModel):
    requestId: str = Field(pattern=r'^[a-f0-9]{32}$')
    topic: str = Field(min_length=3, max_length=500)
    publicOnly: StrictBool
    allowedDomains: list[str] = Field(min_length=1, max_length=8)
    urls: list[str] = Field(default_factory=list, max_length=3)
    query: str | None = Field(default=None, max_length=500)
    claims: list[Claim] = Field(default_factory=list, max_length=12)
    maxSources: int = Field(default=3, ge=1, le=3)
    projectId: str | None = Field(default=None, pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$')
    reference: Reference = Field(default_factory=Reference)

    @model_validator(mode='after')
    def validate_public_request(self):
        if not self.publicOnly or not self.topic.strip():
            raise ValueError('Confirme que o conteúdo da pesquisa é público.')
        if len(set(c.id for c in self.claims)) != len(self.claims) or any(not c.text.strip() for c in self.claims):
            raise ValueError('As afirmações precisam de texto e identificadores únicos.')
        self.allowedDomains = list(dict.fromkeys(self.allowedDomains))
        for domain in self.allowedDomains:
            if domain != domain.lower() or urlsplit('https://' + domain).hostname != domain:
                raise ValueError('Informe somente nomes de domínio, sem protocolo, caminho ou wildcard.')
            public_url('https://' + domain, [domain])
        self.urls = list(dict.fromkeys(public_url(url, self.allowedDomains) for url in self.urls))
        if len(self.urls) > self.maxSources or not (self.urls or (self.query or '').strip()):
            raise ValueError('Informe URLs ou uma consulta, respeitando o limite de fontes.')
        for claim in self.claims:
            if claim.sourceUrl:
                claim.sourceUrl = public_url(claim.sourceUrl, self.allowedDomains)
        return self


class ReviewCreate(StrictModel):
    requestId: str = Field(pattern=r'^[a-f0-9]{32}$')
    decision: Literal['reviewed', 'needs_sources']
    acceptedClaimIds: list[str] = Field(default_factory=list, max_length=12)
    excludedClaimIds: list[str] = Field(default_factory=list, max_length=12)
    note: str = Field(default='', max_length=2000)


class ResearchService:
    def __init__(self, root=ROOT, *, launcher=None, projects_root=PROJECTS):
        self.root = Path(root).resolve()
        self.projects_root = Path(projects_root).resolve()
        self.launcher = launcher or self._launch
        self._mutex = threading.Lock()
        self._children = {}

    def folder(self, job_id):
        if not ID.fullmatch(job_id):
            raise HTTPException(404, 'Pesquisa não encontrada.')
        folder = (self.root / job_id).resolve()
        if folder.parent != self.root or not (folder / 'record.json').is_file():
            raise HTTPException(404, 'Pesquisa não encontrada.')
        return folder

    @contextmanager
    def admission(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with self._mutex, open(self.root / '.admission.lock', 'a+b') as handle:
            if handle.tell() == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise HTTPException(409, 'Já há um envio de pesquisa em andamento.')
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _update(self, folder, **changes):
        record = read_json(folder / 'record.json')
        record.update(changes, updatedAt=time.time())
        write_json(folder / 'record.json', record)
        return record

    def _manifest(self, folder, expected=None):
        run = (folder / 'run').resolve()
        path = run / 'manifest.json'
        raw = path.read_bytes()
        if expected and digest(raw) != expected:
            raise ValueError('Manifesto alterado.')
        manifest = json.loads(raw)
        if not isinstance(manifest, dict) or not 1 <= len(manifest) <= 80:
            raise ValueError('Manifesto inválido.')
        for name, expected_hash in manifest.items():
            if not re.fullmatch(r'[A-Za-z0-9_./-]{1,160}', name) or '..' in name.split('/'):
                raise ValueError('Caminho de evidência inválido.')
            file = (run / name).resolve()
            if not file.is_relative_to(run) or not file.is_file() or file.stat().st_size > 5_000_000:
                raise ValueError('Evidência fora do escopo.')
            if digest(file.read_bytes()) != expected_hash:
                raise ValueError('Evidência alterada.')
        return digest(raw)

    def _alive(self, record):
        child = self._children.get(record['id'])
        if child is not None:
            return child.poll() is None
        pid = record.get('workerPid')
        if not pid:
            return time.time() - record['createdAt'] < 60
        try:
            import psutil
            process = psutil.Process(pid)
            command = process.cmdline()
            return process.is_running() and Path(command[0]).resolve() == NODE.resolve() and str(self.root / record['id'] / 'run') in command
        except psutil.AccessDenied:
            return True  # Unknown liveness must not admit overlapping requests.
        except (psutil.NoSuchProcess, IndexError):
            return False

    def _refresh(self, folder):
        record = read_json(folder / 'record.json')
        run = folder / 'run'
        if (run / 'manifest.json').is_file() and (run / 'dossier.json').is_file():
            try:
                manifest_hash = self._manifest(folder, record.get('manifestSha256'))
                if record['status'] != 'READY_FOR_REVIEW':
                    record = self._update(folder, status='READY_FOR_REVIEW', manifestSha256=manifest_hash)
            except (ValueError, OSError):
                if record['status'] != 'INTEGRITY_CHANGED':
                    record = self._update(folder, status='INTEGRITY_CHANGED')
        elif record['status'] not in TERMINAL and not self._alive(record):
            record = self._update(folder, status='INTERRUPTED_REVIEW_REQUIRED')
        return record

    def create(self, body: ResearchCreate):
        data = body.model_dump(mode='json')
        body_hash = digest(json.dumps(data, sort_keys=True).encode())
        with self.admission():
            folder = self.root / body.requestId
            if folder.exists():
                old = self.folder(body.requestId)
                if read_json(old / 'record.json')['requestSha256'] != body_hash:
                    raise HTTPException(409, 'Este envio já foi usado com outro conteúdo.')
                return self.get(body.requestId)
            if body.projectId:
                project = (self.projects_root / body.projectId).resolve()
                if project.parent != self.projects_root or not any((project / name).is_file() for name in ('project_manifest.json', 'take_queue.json', 'project.json')):
                    raise HTTPException(422, 'Projeto não encontrado para vincular a pesquisa.')
            for record in self.records():
                if record['status'] not in TERMINAL:
                    raise HTTPException(409, 'Uma pesquisa está em andamento. Aguarde o resultado antes de iniciar outra.')
            folder.mkdir()
            spec = {'schemaVersion': 1, 'id': 'maestro-' + body.requestId, 'topic': body.topic.strip(), 'publicOnly': True,
                    'allowedDomains': body.allowedDomains, 'urls': body.urls, 'claims': [c.model_dump(exclude_none=True) for c in body.claims],
                    'maxSources': body.maxSources, 'threshold': 0.9, 'model': 'gemini-decision-1'}
            if (body.query or '').strip():
                spec['query'] = body.query.strip()
            write_json(folder / 'request.json', data)
            write_json(folder / 'spec.json', spec)
            write_json(folder / 'record.json', {'id': body.requestId, 'requestSha256': body_hash, 'status': 'QUEUED',
                       'topic': body.topic.strip(), 'projectId': body.projectId, 'reference': body.reference.model_dump(),
                       'createdAt': time.time(), 'updatedAt': time.time()})
            try:
                self.launcher(body.requestId)
            except Exception:
                self._update(folder, status='INTERRUPTED_REVIEW_REQUIRED')
            return self.get(body.requestId)

    def _launch(self, job_id):
        threading.Thread(target=self._run, args=(job_id,), name='public-research-' + job_id, daemon=True).start()

    def _run(self, job_id):
        folder = self.folder(job_id)
        try:
            if not NODE.is_file() or not (HARNESS / 'bin/pemara-harness.mjs').is_file():
                raise RuntimeError('Runtime ausente.')
            # Fixed executable and argv; user strings exist only in the bounded JSON spec.
            command = [str(NODE), str(HARNESS / 'bin/pemara-harness.mjs'), 'research', '--spec', str(folder / 'spec.json'), '--output', str(folder / 'run')]
            keep = {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'LOCALAPPDATA', 'APPDATA', 'GEMINI_API_KEY', 'GOOGLE_API_KEY'}
            env = {key: value for key, value in os.environ.items() if key.upper() in keep}
            with open(folder / 'harness-stdout.json', 'wb') as out, open(folder / 'harness-stderr.log', 'wb') as err:
                child = subprocess.Popen(command, cwd=str(HARNESS), env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                         shell=False, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                self._children[job_id] = child
                self._update(folder, status='RUNNING', workerPid=child.pid)
                try:
                    child.wait(timeout=480)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait(timeout=10)
            self._refresh(folder)
            if read_json(folder / 'record.json')['status'] not in TERMINAL:
                self._update(folder, status='INTERRUPTED_REVIEW_REQUIRED')
        except Exception:
            self._update(folder, status='INTERRUPTED_REVIEW_REQUIRED')
        finally:
            self._children.pop(job_id, None)

    def records(self):
        if not self.root.exists():
            return []
        records = []
        for path in self.root.iterdir():
            if ID.fullmatch(path.name) and path.is_dir() and (path / 'record.json').is_file():
                row = read_json(path / 'record.json')
                records.append(row if row['status'] in TERMINAL else self._refresh(path))
        return sorted(records, key=lambda row: row['createdAt'], reverse=True)

    def get(self, job_id):
        folder = self.folder(job_id)
        record = self._refresh(folder)
        result = {key: record.get(key) for key in ['id', 'status', 'topic', 'projectId', 'reference', 'createdAt', 'updatedAt']}
        result.update(integrity='incomplete', findings=[], sources=[], reviewQueue=[], review=None, mediaApproved=False)
        if record['status'] == 'READY_FOR_REVIEW':
            report = read_json(folder / 'run/dossier.json')
            result.update(integrity='ok', findings=report.get('findings', []), reviewQueue=report.get('reviewQueue', []),
                          verification=report.get('verification', {}), consumption=report.get('consumption', {}), durationMs=report.get('durationMs'))
            for source in report.get('sources', []):
                try:
                    safe_url = public_url(source['url'], read_json(folder / 'spec.json')['allowedDomains'])
                except (KeyError, ValueError):
                    continue
                metadata = source.get('metadata') or {}
                result['sources'].append({key: source.get(key) for key in ['id', 'ok', 'fetchedAt', 'markdownSha256', 'verificationEligible', 'verificationReason']} |
                                         {'url': safe_url, 'cacheState': metadata.get('cacheState'), 'statusCode': metadata.get('statusCode')})
            reviews = sorted((folder / 'reviews').glob('*.json')) if (folder / 'reviews').exists() else []
            if reviews:
                result['review'] = max((read_json(path) for path in reviews), key=lambda row: row['createdAt'])
        elif record['status'] == 'INTEGRITY_CHANGED':
            result['integrity'] = 'changed'
        return result

    def review(self, job_id, body: ReviewCreate):
        with self.admission():
            current = self.get(job_id)
            if current['integrity'] != 'ok':
                raise HTTPException(409, 'A pesquisa precisa estar concluída e com as evidências íntegras.')
            findings = {item['id']: item for item in current['findings']}
            accepted, excluded = set(body.acceptedClaimIds), set(body.excludedClaimIds)
            if accepted & excluded or (accepted | excluded) - findings.keys() or any(findings[key]['status'] != 'SUPPORTED' for key in accepted):
                raise HTTPException(422, 'Somente afirmações sustentadas podem ser aceitas; as demais precisam ser excluídas ou receber novas fontes.')
            if body.decision == 'reviewed' and (accepted | excluded != findings.keys() or (findings and not accepted)):
                raise HTTPException(422, 'Revise cada afirmação e aceite ao menos uma sustentada, ou solicite novas fontes.')
            if body.decision == 'needs_sources' and len(body.note.strip()) < 3:
                raise HTTPException(422, 'Descreva quais fontes ou informações faltam.')
            record = body.model_dump() | {'createdAt': time.time(), 'actor': 'maestro_authenticated_operator', 'mediaApproved': False}
            folder = self.folder(job_id)
            path = folder / 'reviews' / (body.requestId + '.json')
            if path.exists():
                previous = read_json(path)
                if any(previous[key] != record[key] for key in body.model_dump()):
                    raise HTTPException(409, 'Este envio de revisão já foi usado.')
            else:
                write_json(path, record)
            return self.get(job_id)


def create_research_router(service, is_internal):
    router = APIRouter(prefix='/api/research')

    def authorize(request):
        if not is_internal(request):
            raise HTTPException(403, 'Disponível somente no Maestro autenticado.')

    async def body(request, model):
        authorize(request)
        if request.headers.get('content-type', '').split(';', 1)[0].lower() != 'application/json':
            raise HTTPException(415, 'Envie os dados da pesquisa como JSON.')
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 32_768:
                raise HTTPException(413, 'Pesquisa acima do limite de tamanho.')
        try:
            return model.model_validate_json(bytes(raw))
        except ValueError:
            raise HTTPException(422, 'Revise os campos: dados públicos, domínios, URLs, versão do personagem e limite de fontes.')

    @router.get('/jobs')
    def jobs(request: Request, page: int = 1, pageSize: int = 20):
        authorize(request)
        if not 1 <= page <= 10000 or not 1 <= pageSize <= 50:
            raise HTTPException(422, 'Paginação inválida.')
        records = service.records()
        return {'jobs': [{key: row.get(key) for key in ['id', 'status', 'topic', 'projectId', 'reference', 'createdAt', 'updatedAt']}
                         for row in records[(page - 1) * pageSize:page * pageSize]], 'total': len(records)}

    @router.post('/jobs', status_code=202)
    async def create(request: Request):
        return service.create(await body(request, ResearchCreate))

    @router.get('/jobs/{job_id}')
    def get(job_id: str, request: Request):
        authorize(request)
        return service.get(job_id)

    @router.post('/jobs/{job_id}/reviews', status_code=201)
    async def review(job_id: str, request: Request):
        return service.review(job_id, await body(request, ReviewCreate))

    @router.get('/jobs/{job_id}/sources/{source_id}')
    def source(job_id: str, source_id: str, request: Request):
        authorize(request)
        current = service.get(job_id)
        if current['integrity'] != 'ok' or not re.fullmatch(r'S[1-3]', source_id) or not any(s['id'] == source_id and s['ok'] for s in current['sources']):
            raise HTTPException(404, 'Fonte indisponível.')
        return PlainTextResponse((service.folder(job_id) / 'run/sources' / (source_id + '.md')).read_text(encoding='utf-8'))

    @router.get('/jobs/{job_id}/dossier')
    def dossier(job_id: str, request: Request):
        authorize(request)
        if service.get(job_id)['integrity'] != 'ok':
            raise HTTPException(409, 'Dossiê indisponível ou alterado.')
        return PlainTextResponse((service.folder(job_id) / 'run/dossier.md').read_text(encoding='utf-8'),
                                 headers={'Content-Disposition': f'attachment; filename="pesquisa-{job_id}.md"'})

    return router
