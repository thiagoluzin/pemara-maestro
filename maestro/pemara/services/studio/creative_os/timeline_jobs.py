"""Continuous timeline takes use the same durable generation/review records."""
import json
from pathlib import Path
from .assets import file_hash
from .ir import CreativeError, digest, identifier
from .timeline_director import compile_timeline


def qualification(root,nodes,runtime):
    try:
        data=json.loads((Path(root)/'timeline_qualification_20260907.json').read_text(encoding='utf-8'))
        required={'MiniMaxH3TimelinePlanner','MiniMaxH3FiniteSegmentExpansion','MiniMaxH3FiniteSegmentSampler'}
        if data.get('technical_status')!='PASS' or not required <= set(nodes): return None
        if (runtime.get('system') or {}).get('comfyui_version')!='0.34.2': return None
        if not data.get('files') or any(file_hash(p)!=sha for p,sha in data['files'].items()): return None
        return {'integrated':True,'enabled':True,'experimental':True,'auto_route':False,
            'scope':'Continuous text-only H3 Production take; two 124-frame segments, 22-frame overlap, silent export',
            'requires_human_review':True,'reason':'PINNED_TIMELINE_BENCHMARK_PASS'}
    except (OSError,ValueError,KeyError): return None


def prepare(service,shot_id,*,seed,segment_count=2):
    shot=service.store.get('shots',shot_id)
    c=compile_timeline(shot['ir'],seed=seed,segment_count=segment_count)
    return {k:v for k,v in c.items() if k not in {'graph','base_spec'}}


def generate(service,shot_id,key,*,seed,segment_count=2):
    identifier(key)
    shot=service.store.get('shots',shot_id)
    c=compile_timeline(shot['ir'],seed=seed,segment_count=segment_count)
    spec=c['base_spec']
    spec['creative_timeline_request']={'ir':shot['ir'],'segment_count':segment_count}
    request_hash=digest([shot['ir_hash'],spec])
    generation_id=digest(['timeline',shot_id,key])
    with service.store.transaction() as con:
        old=service.store.read(con,'generations',generation_id)
        if old:
            if old['request_hash']!=request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT','Chave já identifica outra timeline.',409)
            return old
    if not service.bridge.capabilities().get('optional',{}).get('h3_timeline_director',{}).get('enabled'):
        raise CreativeError('TIMELINE_UNAVAILABLE','Timeline não qualificada no runtime atual.',409)
    if c['segment_count']!=2 or c['segment_frames']!=124:
        raise CreativeError('TIMELINE_SCOPE','Qualificação inicial: dois segmentos de 124 frames.',409)
    if service.bridge.prepare: spec=service.bridge.prepare(spec,{}, {})
    with service.store.transaction() as con:
        old=service.store.read(con,'generations',generation_id)
        if old:
            if old['request_hash']!=request_hash: raise CreativeError('IDEMPOTENCY_CONFLICT','Chave já identifica outra timeline.',409)
            return old
        record=service.store.write(con,'generations',generation_id,{
            'shot_id':shot_id,'project_id':shot['ir']['project_id'],'ir':shot['ir'],'engine_id':'minimax_h3',
            'parent_generation_id':None,'request_hash':request_hash,'request_spec':spec,'references':[],
            'status':'submitting','human_verdict':None,'job_id':None,'artifacts':[],
            'transport':service.bridge.transport,'source':'timeline_director',
            'timeline_contract':{k:v for k,v in c.items() if k not in {'graph','base_spec'}},
            'restart_policy':'NO_BLIND_REPLAY'},create=True)
    try: job_id=service.bridge.submit(spec)
    except Exception as exc:
        service.store.put('generations',{**record,'status':'submission_failed','error':str(exc)},
            entity_id=generation_id,expected=record['revision'],create=False)
        raise
    return service.store.put('generations',{**record,'status':'queued','job_id':job_id},
        entity_id=generation_id,expected=record['revision'],create=False)
