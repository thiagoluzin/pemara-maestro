"""Explicit control assets over Maestro's normal autonomous video queue."""
from .fun_control import validate_request,verify_video
from .ir import CreativeError,digest,identifier


def import_control(service,data,filename):
    import hashlib
    from pathlib import Path
    suffix=Path(filename or '').suffix.lower()
    if suffix not in {'.mp4','.mov','.mkv','.webm'} or not data or len(data)>512*1024*1024:
        raise CreativeError('CONTROL_VIDEO','Envie um vídeo de controle de até 512 MB.')
    project='maestro_control'
    folder=(service.assets.root/project/'control_inputs').resolve()
    if service.assets.root not in folder.parents:raise CreativeError('CONTROL_PATH','Destino fora da pasta de projetos.')
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/(hashlib.sha256(data).hexdigest()+suffix)
    if path.exists():
        if path.read_bytes()!=data:raise CreativeError('CONTROL_CHANGED','Arquivo existente diverge.',409)
    else:
        with path.open('xb') as stream:stream.write(data)
    verify_video(path)
    return service.assets.register(project,'control_inputs/'+path.name,'motion_reference')


def generate(service,shot_id,key,*,asset_id,control_kind,strength=1.0,seed):
    identifier(key)
    if type(seed) is not int or not 0 <= seed < 2**63:raise CreativeError('INVALID_SEED','Informe seed explícita.')
    shot=service.store.get('shots',shot_id)
    path,asset=service.assets.resolve(asset_id,shot['ir']['project_id'])
    if asset['role']!='motion_reference':raise CreativeError('CONTROL_ROLE','Escolha um asset de motion_reference.')
    request={'ir':shot['ir'],'asset_id':asset_id,'asset_sha256':asset['sha256'],'control_kind':control_kind,'strength':strength}
    spec=validate_request(request,engine_id='minimax_h3',native_audio=False,profile='h3_production')
    spec.update(seed=seed,creative_fun_control_request=request)
    request_hash=digest(spec);generation_id=digest(['fun_control',shot_id,key])
    with service.store.transaction() as con:
        old=service.store.read(con,'generations',generation_id)
        if old:
            if old['request_hash']!=request_hash:raise CreativeError('IDEMPOTENCY_CONFLICT','Chave já identifica outro controle.',409)
            return old
    if not service.bridge.capabilities().get('optional',{}).get('h3_fun_control',{}).get('enabled'):
        raise CreativeError('CONTROL_UNAVAILABLE','Fun Control não qualificado no runtime atual.',409)
    verify_video(path)
    if service.bridge.prepare:spec=service.bridge.prepare(spec,{}, {})
    with service.store.transaction() as con:
        old=service.store.read(con,'generations',generation_id)
        if old:
            if old['request_hash']!=request_hash:raise CreativeError('IDEMPOTENCY_CONFLICT','Chave já identifica outro controle.',409)
            return old
        record=service.store.write(con,'generations',generation_id,{'shot_id':shot_id,'project_id':shot['ir']['project_id'],
            'ir':shot['ir'],'engine_id':'minimax_h3','parent_generation_id':None,'request_hash':request_hash,'request_spec':spec,
            'references':[{'asset_id':asset['id'],'sha256':asset['sha256'],'role':'motion_reference'}],
            'status':'submitting','human_verdict':None,'job_id':None,'artifacts':[],
            'transport':service.bridge.transport,'source':'fun_control','restart_policy':'NO_BLIND_REPLAY'},create=True)
    try:job_id=service.bridge.submit(spec)
    except Exception as exc:
        service.store.put('generations',{**record,'status':'submission_failed','error':str(exc)},
            entity_id=generation_id,expected=record['revision'],create=False)
        raise
    return service.store.put('generations',{**record,'status':'queued','job_id':job_id},
        entity_id=generation_id,expected=record['revision'],create=False)
