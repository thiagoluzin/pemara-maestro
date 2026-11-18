"""Explicit project-scoped control video; no implicit reference or engine fallback."""
import copy
import json
import math
import re
import subprocess
from pathlib import Path
from .adapters import H3Adapter
from .assets import file_hash
from .ir import CreativeError,digest,validate_ir

WEIGHT='minimax_h3_fun_controlnet_union_pruned_bf16.safetensors'
WEIGHT_SHA='57fe1e64928a63a55e3cd4586b55cd5d0eb4980648b6f31e5d9dac16fe7f1c48'


def validate_request(request, *, engine_id, native_audio, profile):
    if engine_id!='minimax_h3' or native_audio or profile!='h3_production':
        raise CreativeError('CONTROL_SCOPE','Fun Control exige H3 Production explícito, sem áudio.')
    fields={'ir','asset_id','asset_sha256','strength','control_kind'}
    if not isinstance(request,dict) or set(request)!=fields:
        raise CreativeError('CONTROL_REQUEST','Pedido de controle incompleto ou com campos desconhecidos.')
    ir=validate_ir(request['ir'])
    if request['control_kind'] not in {'depth','canny','pose','hed','mlsd'}:
        raise CreativeError('CONTROL_KIND','Escolha o tipo do vídeo de controle já preparado.')
    if not isinstance(request['asset_id'],str) or not isinstance(request['asset_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',request['asset_sha256']):
        raise CreativeError('CONTROL_ASSET','Asset e checksum são obrigatórios.')
    strength=request['strength']
    if type(strength) not in (int,float) or not math.isfinite(strength) or not 0 <= strength <= 2:
        raise CreativeError('CONTROL_STRENGTH','Força deve ficar entre 0 e 2.')
    # References and control-source instructions must never be silently dropped.
    spec=H3Adapter().build_job(ir,{'seed':0,'h3_quality_profile':'h3_production'})
    if spec['enable_minimax_h3_native_audio']:
        raise CreativeError('CONTROL_AUDIO','O IR solicita áudio fora desta qualificação.')
    if not 4 <= ir['duration_seconds'] <= 5.5:
        raise CreativeError('CONTROL_DURATION','Qualificação inicial: janela Production de 124 frames.')
    return spec


def verify_video(path):
    path=Path(path)
    if path.suffix.lower() not in {'.mp4','.mov','.mkv','.webm'} or path.stat().st_size>512*1024*1024:
        raise CreativeError('CONTROL_VIDEO','Vídeo de controle inválido ou maior que 512 MB.')
    try:
        result=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],capture_output=True,timeout=30,check=True)
        streams=json.loads(result.stdout)['streams']
        videos=[s for s in streams if s.get('codec_type')=='video']
        v=videos[0] if len(videos)==1 else {}
        if (v.get('width'),v.get('height'),int(v.get('nb_frames',0)),v.get('r_frame_rate'))!=(1088,608,124,'24/1'):
            raise ValueError('geometry')
    except (subprocess.SubprocessError,ValueError,KeyError,IndexError) as exc:
        raise CreativeError('CONTROL_GEOMETRY','Controle deve conter 1088×608, 124 frames e 24 fps.') from exc
    return {'width':1088,'height':608,'frames':124,'fps':24}


def patch_graph(graph,filename,strength):
    graph=copy.deepcopy(graph)
    if not isinstance(filename,str) or filename.startswith('/') or '\\' in filename or '..' in filename.split('/') or ':' in filename:
        raise CreativeError('CONTROL_FILENAME','Nome de entrada inválido.')
    def single(kind):
        matches=[n for n in graph.values() if n.get('class_type')==kind]
        if len(matches)!=1: raise CreativeError('CONTROL_GRAPH',f'Grafo exige um {kind}.')
        return matches[0]
    guider=single('BasicGuider')
    cond=single('MiniMaxH3ImageToVideo')
    for key in ('creative_control_loader','creative_control_video','creative_control_frames','creative_control_apply'):
        if key in graph: raise CreativeError('CONTROL_GRAPH','Controle já presente no grafo.')
    graph['creative_control_loader']={'class_type':'H3FunControlLoader','inputs':{'control_net_name':WEIGHT}}
    graph['creative_control_video']={'class_type':'LoadVideo','inputs':{'file':filename}}
    graph['creative_control_frames']={'class_type':'GetVideoComponents','inputs':{'video':['creative_control_video',0]}}
    graph['creative_control_apply']={'class_type':'H3FunControlApply','inputs':{'model':guider['inputs']['model'],
        'control_net':['creative_control_loader',0],'vae':cond['inputs']['vae'],'control_video':['creative_control_frames',0],
        'strength':strength,'start_percent':0.0,'end_percent':1.0}}
    guider['inputs']['model']=['creative_control_apply',0]
    from h3_workflow import ensure_h3_sage_attention
    return ensure_h3_sage_attention(graph)


def apply_in_worker(ns,graph,request):
    service=ns['_CREATIVE_OS']
    path,asset=service.assets.resolve(request['asset_id'],request['ir']['project_id'])
    if asset['role']!='motion_reference' or asset['sha256']!=request['asset_sha256']:
        raise CreativeError('CONTROL_CHANGED','O controle mudou ou tem outro papel; nenhum envio realizado.',409)
    verify_video(path)
    import hashlib
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=request['asset_sha256']:
        raise CreativeError('CONTROL_CHANGED','O controle mudou durante a leitura.',409)
    filename=ns['_save_comfy_input_video'](data,path.name)
    from .integration import export_graph
    patched=export_graph(patch_graph(graph,filename,request['strength']),
        {'SaveVideo':{'input':{'required':{'format':['COMFY_DYNAMICCOMBO_V3']}}}})
    return patched,{'source_ir_hash':digest(request['ir']),'asset_sha256':asset['sha256'],
        'control_kind':request['control_kind'],'strength':request['strength'],'workflow_hash':digest(patched),
        'control_kind_verified':'USER_DECLARED_PREPROCESSED_INPUT','human_verdict':None}


def qualification(root,nodes,runtime):
    try:
        data=json.loads((Path(root)/'fun_control_qualification_20260907.json').read_text(encoding='utf-8'))
        if data.get('technical_status')!='PASS' or not {'H3FunControlApply','H3FunControlLoader'} <= set(nodes):return None
        if (runtime.get('system') or {}).get('comfyui_version')!='0.34.2':return None
        if not data.get('files') or any(file_hash(p)!=sha for p,sha in data['files'].items()):return None
        return {'integrated':True,'enabled':True,'experimental':True,'auto_route':False,
            'scope':'H3 Production silent 124-frame take with explicit preprocessed control asset',
            'requires_human_review':True,'reason':'PINNED_FUN_CONTROL_BENCHMARK_PASS'}
    except (OSError,ValueError,KeyError):return None
