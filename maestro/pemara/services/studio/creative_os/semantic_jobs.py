"""Durable advisory visual reviews, isolated from human verdicts and ranking."""
import hashlib
from .assets import file_hash, safe_path
from .adapters import description
from .ir import CreativeError, digest, identifier
from .semantic_critic import contact_sheet, workflow, parse


def start(service, generation_id, artifact_sha, key):
    identifier(key)
    generation = service.sync(generation_id)
    if generation['status'] != 'done': raise CreativeError('GENERATION_NOT_READY', 'Aguarde o vídeo.', 409)
    artifact = next((a for a in generation['artifacts'] if a['kind'] == 'video' and a['sha256'] == artifact_sha), None)
    if not artifact: raise CreativeError('ARTIFACT_MISMATCH', 'Informe o hash exato do vídeo.', 409)
    brief = description(generation['ir'])
    job_key = digest(['semantic_review', generation_id, key])
    request_hash = digest([artifact_sha, brief])
    with service.store.transaction() as con:
        old = service.store.read(con, 'semantic_jobs', job_key)
        if old:
            if old['request_hash'] != request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT', 'Chave de outro pedido.', 409)
            return old
    sheet, frames = contact_sheet(safe_path(service.root, artifact['relative_path']), artifact_sha)
    sheet_sha = hashlib.sha256(sheet).hexdigest()
    graph = workflow(brief, 'creative_os_critic/' + sheet_sha + '.png')
    spec = {'mode': 'semantic_review', 'engine_id': generation['engine_id'], 'prompt': brief,
        'seed': 0, 'video_duration': 5}
    with service.store.transaction() as con:
        old = service.store.read(con, 'semantic_jobs', job_key)
        if old:
            if old['request_hash'] != request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT', 'Chave de outro pedido.', 409)
            return old
        record = service.store.write(con, 'semantic_jobs', job_key, {'generation_id': generation_id,
            'artifact_sha256': artifact_sha, 'source_prompt_hash': digest(brief), 'request_hash': request_hash,
            'workflow_hash': digest(graph), 'sheet_sha256': sheet_sha, 'sample_frames': frames,
            'state': 'SUBMITTING', 'job_id': None, 'restart_policy': 'NO_BLIND_REPLAY',
            'advisory_only': True, 'transport': service.bridge.transport}, create=True)
    try: job_id = service.bridge.submit(spec, base_bytes=sheet, base_name='semantic_contact_sheet.png')
    except Exception as exc:
        service.store.put('semantic_jobs', {**record, 'state': 'SUBMISSION_FAILED', 'error': str(exc)}, entity_id=job_key, expected=record['revision'], create=False)
        raise
    return service.store.put('semantic_jobs', {**record, 'state': 'QUEUED', 'job_id': job_id}, entity_id=job_key, expected=record['revision'], create=False)


def sync(service, key):
    record = service.store.get('semantic_jobs', key)
    if not record.get('job_id') or record['state'] in {'DONE', 'ERROR', 'CANCELED', 'PROVENANCE_MISSING'}: return record
    job = service.bridge.status(record['job_id'])
    if not job: raise CreativeError('JOB_UNKNOWN', 'Job ausente; nenhum reenvio automático.', 409)
    state = str(job.get('status', 'queued')).upper()
    if state != 'DONE':
        return service.store.put('semantic_jobs', {**record, 'state': state, 'error': job.get('error')}, entity_id=key, expected=record['revision'], create=False)
    result = job.get('result') or {}; prompt_id = result.get('prompt_id') or job.get('prompt_id')
    origin = service.bridge.provenance(prompt_id) if service.bridge.provenance and prompt_id else {}
    generation = service.store.get('generations', record['generation_id'])
    artifact = next((a for a in generation['artifacts'] if a['kind'] == 'video' and a['sha256'] == record['artifact_sha256']), None)
    verified = bool(artifact) and file_hash(safe_path(service.root, artifact['relative_path'])) == record['artifact_sha256']
    verified = verified and all(result.get(k) == record[k] for k in ('source_prompt_hash', 'sheet_sha256', 'workflow_hash')) and (origin or {}).get('workflow_hash') == record['workflow_hash']
    if not verified:
        return service.store.put('semantic_jobs', {**record, 'state': 'PROVENANCE_MISSING', 'result_text': result.get('text')}, entity_id=key, expected=record['revision'], create=False)
    review = parse(result.get('text'))
    with service.store.transaction() as con:
        current = service.store.read(con, 'semantic_jobs', key)
        if current['state'] == 'DONE': return current
        return service.store.write(con, 'semantic_jobs', key, {**current, 'state': 'DONE', 'review': review}, expected=current['revision'])
