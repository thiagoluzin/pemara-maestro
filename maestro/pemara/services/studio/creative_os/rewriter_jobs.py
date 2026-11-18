"""Durable optional prompt rewriting with immutable input and human application gate."""
from .adapters import H3Adapter, description
from .h3_rewriter import workflow
from .ir import CreativeError, digest, identifier
from .prompt_proposals import proposal_data


def start(service,shot_id,key,seed):
    identifier(key)
    shot=service.store.get('shots',shot_id)
    spec=H3Adapter().build_job(shot['ir'],{'seed':seed})
    spec.update(mode='prompt_rewrite',prompt=description(shot['ir']))
    graph=workflow(spec['prompt'],spec['video_duration'],seed)
    job_key=digest([shot_id,key]);request_hash=digest([shot['ir_hash'],seed])
    with service.store.transaction() as con:
        old=service.store.read(con,'rewriter_jobs',job_key)
        if old:
            if old['request_hash']!=request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT','Chave de reescrita já identifica outro pedido.',409)
            return old
    if not service.bridge.capabilities().get('optional',{}).get('h3_prompt_rewriter',{}).get('enabled'):
        raise CreativeError('REWRITER_UNAVAILABLE','Rewriter não qualificado no runtime atual.',409)
    if service.bridge.prepare: spec=service.bridge.prepare(spec,{}, {})
    with service.store.transaction() as con:
        old=service.store.read(con,'rewriter_jobs',job_key)
        if old:
            if old['request_hash']!=request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT','Pedido de reescrita divergente.',409)
            return old
        record=service.store.write(con,'rewriter_jobs',job_key,{'shot_id':shot_id,'source_ir_hash':shot['ir_hash'],
            'source_prompt_hash':digest(spec['prompt']),'workflow_hash':digest(graph),'request_hash':request_hash,
            'state':'SUBMITTING','job_id':None,'proposal_id':None,'transport':service.bridge.transport,
            'restart_policy':'NO_BLIND_REPLAY'},create=True)
    try: job_id=service.bridge.submit(spec)
    except Exception as exc:
        service.store.put('rewriter_jobs',{**record,'state':'SUBMISSION_FAILED','error':str(exc)},entity_id=job_key,expected=record['revision'],create=False)
        raise
    return service.store.put('rewriter_jobs',{**record,'state':'QUEUED','job_id':job_id},entity_id=job_key,expected=record['revision'],create=False)


def sync(service,key):
    record=service.store.get('rewriter_jobs',key)
    if not record.get('job_id') or record['state'] in {'DONE','ERROR','CANCELED','STALE_IR','PROVENANCE_MISSING'}: return record
    job=service.bridge.status(record['job_id'])
    if not job: raise CreativeError('JOB_UNKNOWN','Job de reescrita ausente; nenhum reenvio automático.',409)
    state=str(job.get('status','queued')).upper()
    if state!='DONE':
        return service.store.put('rewriter_jobs',{**record,'state':state,'error':job.get('error')},entity_id=key,expected=record['revision'],create=False)
    result=job.get('result') or {}; origin=result.get('rewriter') or {}; prompt_id=result.get('prompt_id') or job.get('prompt_id')
    provenance=service.bridge.provenance(prompt_id) if service.bridge.provenance and prompt_id else {}
    verified=(origin.get('source_prompt_hash')==record['source_prompt_hash'] and
        origin.get('workflow_hash')==record['workflow_hash'] and (provenance or {}).get('workflow_hash')==record['workflow_hash'])
    with service.store.transaction() as con:
        current=service.store.read(con,'rewriter_jobs',key)
        if current['state']=='DONE': return current
        shot=service.store.read(con,'shots',record['shot_id'])
        if shot['ir_hash']!=record['source_ir_hash'] or not verified:
            state='STALE_IR' if shot['ir_hash']!=record['source_ir_hash'] else 'PROVENANCE_MISSING'
            return service.store.write(con,'rewriter_jobs',key,{**current,'state':state,'result_text':result.get('text'),
                'error':'Original mudou ou proveniência não foi confirmada; sugestão não aplicada.'},expected=current['revision'])
        data=proposal_data(shot,result.get('text'),{'prompt_id':prompt_id,'job_id':record['job_id'],'workflow_hash':record['workflow_hash']})
        data['provenance_verified']=True
        proposal_id=digest(['rewriter_proposal',key])
        service.store.write(con,'prompt_proposals',proposal_id,data,create=True)
        return service.store.write(con,'rewriter_jobs',key,{**current,'state':'DONE','proposal_id':proposal_id},expected=current['revision'])
