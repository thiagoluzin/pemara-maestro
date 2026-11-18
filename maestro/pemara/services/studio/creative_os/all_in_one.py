"""Headless expansion of pinned All-In-One templates; H3OneNode is not executable."""
import json
from pathlib import Path
from .assets import file_hash
from .ir import CreativeError,digest

SOURCE=Path(r'E:\Pemara\maestro\runtimes\creative-os-lab-20260907\sources\h3_all_in_one')


def build(*,prompt,seed,width=1088,height=608,frames=124,steps=10,first_frame='',last_frame='',native_audio=False):
    if type(seed) is not int or not 0<=seed<2**63:raise CreativeError('INVALID_SEED','All-In-One exige seed explícita.')
    if (width,height,steps)!=(1088,608,10) or frames not in range(124,363,17) or native_audio:
        raise CreativeError('ALL_IN_ONE_SCOPE','Qualificação inicial: H3 Production horizontal, sem áudio.')
    if not isinstance(prompt,str) or not prompt.strip():raise CreativeError('DESCRIPTION_REQUIRED','Descreva o plano.')
    mode='i2v' if first_frame or last_frame else 't2v'
    path=SOURCE/'workflows'/(mode+'.json')
    graph=json.loads(path.read_text(encoding='utf-8'))
    # Port of _patchCommon/_buildWorkflow for the two native video modes.
    # The external visual H3OneNode only manages UI; never enqueue that no-op.
    graph['6']['inputs'].update(prompt=prompt,width=width,height=height,length=frames)
    graph['8']['inputs']['noise_seed']=seed
    graph['9']['inputs'].update(steps=steps,scheduler='simple')
    graph['10']['inputs']['sampler_name']='res_multistep'
    graph['14']['inputs'].pop('audio',None)
    graph.pop('13',None)
    if mode=='i2v':graph.pop('4',None)
    graph['15']['inputs']={'video':['14',0],'filename_prefix':'creative_os/all_in_one_'+mode,'format':'mp4','format.codec':'h264'}
    for key,name,index in [('first_frame',first_frame,'200'),('last_frame',last_frame,'201')]:
        if not name:continue
        if not isinstance(name,str) or name.startswith('/') or '\\' in name or ':' in name or '..' in name.split('/'):
            raise CreativeError('ALL_IN_ONE_INPUT','Nome de imagem inválido.')
        graph[index]={'class_type':'LoadImage','inputs':{'image':name}}
        graph['6']['inputs'][key]=[index,0]
    from h3_workflow import ensure_h3_sage_attention
    graph = ensure_h3_sage_attention(graph)
    return {'graph':graph,'workflow_hash':digest(graph),'mode':mode,'template_sha256':file_hash(path),
        'source_commit':'6c9666c91a994898f00ad0bb9f2608df3ee5322a','headless_expansion':True,'human_verdict':None}


def qualification(root,nodes,runtime):
    try:
        data=json.loads((Path(root)/'all_in_one_qualification_20260907.json').read_text(encoding='utf-8'))
        if data.get('technical_status')!='PASS' or (runtime.get('system') or {}).get('comfyui_version')!='0.34.2':return None
        if not {'MiniMaxH3ReferenceToVideo','MiniMaxH3ImageToVideo'} <= set(nodes):return None
        if not data.get('files') or any(file_hash(p)!=sha for p,sha in data['files'].items()):return None
        return {'integrated':True,'enabled':True,'experimental':True,'auto_route':False,
            'scope':'Pinned headless T2V/I2V template expansion; H3 Production horizontal, silent output',
            'requires_human_review':True,'reason':'PINNED_ALL_IN_ONE_TEMPLATE_BENCHMARK_PASS'}
    except (OSError,ValueError,KeyError):return None
