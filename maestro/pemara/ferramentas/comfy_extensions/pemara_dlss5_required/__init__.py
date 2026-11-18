"""Enforce DLSS 5 on newly saved visual outputs, including imported/replayed graphs."""
import functools
import inspect
import json
import logging
from pathlib import Path
import subprocess
import sys
import threading

STUDIO = Path(r'E:\Pemara\maestro\pemara\services\studio')
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))
import dlss5_finishing as finishing
import upscaling_required as upscale_policy
import folder_paths
import nodes
from server import PromptServer

_LOCK = threading.RLock()
_WRAPPED = set()
VIDEO_SUFFIXES = {'.gif','.apng','.mp4','.mov','.mkv','.webm','.avi'}

def anchor_exporter(cls):
    if getattr(cls, 'PEMARA_EXPORT_KIND', None) == 'glb':
        return False
    spec=cls.INPUT_TYPES()
    types=[v[0] for section in ('required','optional') for v in spec.get(section,{}).values()]
    return 'VIDEO' not in types and 'VIDEO' not in getattr(cls,'RETURN_TYPES',())

MEDIA_SUFFIXES = {'.png','.jpg','.jpeg','.webp','.gif','.apng','.mp4','.mov','.mkv','.webm','.avi'}

def visual_exporter(cls):
    if not getattr(cls, 'OUTPUT_NODE', False):
        return False
    spec = cls.INPUT_TYPES()
    types = [value[0] for section in ('required','optional') for value in spec.get(section,{}).values()]
    return any(isinstance(t,str) and t in {'IMAGE','VIDEO'} for t in types) or any(t in {'IMAGE','VIDEO'} for t in getattr(cls,'RETURN_TYPES',()))

def media_records(data, suffixes=MEDIA_SUFFIXES):
    if isinstance(data,dict):
        if isinstance(data.get('filename'),str) and Path(data['filename']).suffix.lower() in suffixes:
            yield data
        else:
            for value in data.values():
                yield from media_records(value, suffixes)
    elif isinstance(data,(list,tuple)):
        for value in data:
            yield from media_records(value, suffixes)

def verify_glb(path):
    path.stat()
    python = Path('D:/PemaraRuntimes/maestro-game-ai/envs/three-d/Scripts/python.exe')
    worker = Path(__file__).with_name('verify_glb.py')
    process = subprocess.run([str(python), str(worker), str(path)], capture_output=True,
        text=True, encoding='utf-8', timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    if process.returncode:
        raise finishing.DLSS5RequiredError('GLB: verificacao 3D falhou: ' + process.stderr[-3500:])
    return json.loads(process.stdout)


def finish_result(result, name, *, content_kind=None, stage='final', export_kind=None):
    ui = result.get('ui',{}) if isinstance(result,dict) else getattr(result,'ui',None)
    if hasattr(ui,'as_dict'):
        ui = ui.as_dict()
    records = list(media_records(ui, MEDIA_SUFFIXES | {'.glb'} if export_kind == 'glb' else MEDIA_SUFFIXES))
    if not records:
        raise finishing.DLSS5RequiredError(f'DLSS 5: exportador visual {name} sem arquivo verificavel; sem entrega.')
    # This runs inside ComfyUI's serial execution, after sampling. Release model
    # cache before the D3D12 pass; no external queue/client or second GPU job.
    import comfy.model_management as mm
    if any(Path(r['filename']).suffix.lower() in MEDIA_SUFFIXES - VIDEO_SUFFIXES for r in records):
        mm.unload_all_models()
        mm.soft_empty_cache()
    finished = []
    for record in records:
        kind = record.get('type','output')
        base = Path(folder_paths.get_temp_directory() if kind == 'temp' else folder_paths.get_output_directory()).resolve()
        if kind not in {'output','temp'}:
            raise finishing.DLSS5RequiredError('DLSS 5: nao tratar arquivo de entrada como saida.')
        path = (base / record.get('subfolder','') / record['filename']).resolve()
        if not path.is_relative_to(base):
            raise finishing.DLSS5RequiredError('DLSS 5: arquivo saiu da raiz de output.')
        if path.suffix.lower() == '.glb':
            returned = result.get('result', ()) if isinstance(result, dict) else ()
            if len(returned) != 1 or not isinstance(returned[0], str) or Path(returned[0]).resolve() != path:
                raise finishing.DLSS5RequiredError('GLB: glb_file diverge do arquivo publicado na UI.')
            receipt = verify_glb(path)
            receipt.update({'exporter':name, 'content_kind':finishing.content_policy.normalize(content_kind),
                'stage':'asset_native', 'requested_stage':stage})
            finishing._atomic_json(Path(str(path)+'.verification.json'), receipt)
            record['glb_validation'] = receipt
            finished.append(path)
            continue
        if path.suffix.lower() in VIDEO_SUFFIXES:
            declared=finishing.content_policy.normalize(content_kind)
            if declared=='unknown':
                raise finishing.DLSS5RequiredError('Declarar content_kind no video nativo.')
            digest=finishing.sha(path)
            finishing._atomic_json(Path(str(path)+'.finishing_policy.json'), {
                'policy':'dlss5_anchors_only_20261011_v1','content_kind':declared,
                'media_role':'video','dlss5_applied':False,'sha256':digest,
                'source_bytes_untouched_by_export_hook':True})
            finished.append(path)
            record['finishing_policy']={'dlss5_applied':False,'policy':'dlss5_anchors_only_20261011_v1'}
            continue
        receipt = finishing.finish_file(path, content_kind=content_kind)
        finished.append(path)
        record['dlss5'] = {'required':True, 'profile':receipt['profile'], 'technical_pass':True}
    # SaveVideo returns VIDEO downstream; it must point to the finished bytes.
    if name == 'SaveVideo' and not isinstance(result,dict):
        from comfy_api.latest import io, VideoFromFile
        return io.NodeOutput(VideoFromFile(str(finished[0])), ui=ui)
    return result


def call_content_kind(function, args, kwargs):
    # Legacy hidden PROMPT argument and V3's per-execution hidden holder.
    values = inspect.signature(function).bind_partial(*args, **kwargs).arguments
    prompt = values.get('prompt')
    if prompt is None and args:
        prompt = getattr(getattr(args[0], 'hidden', None), 'prompt', None)
    return finishing.content_policy.graph_kind(prompt), finishing.content_policy.graph_stage(prompt)

def wrap_exporter(name, cls):
    with _LOCK:
        if cls in _WRAPPED:
            return
        method = cls.FUNCTION
        descriptor = inspect.getattr_static(cls,method)
        function = descriptor.__func__ if isinstance(descriptor,(classmethod,staticmethod)) else descriptor
        if inspect.iscoroutinefunction(function):
            @functools.wraps(function)
            async def wrapper(*args,**kwargs):
                if anchor_exporter(cls):
                    finishing.preflight()
                kind, stage = call_content_kind(function, args, kwargs)
                return finish_result(await function(*args,**kwargs),name, content_kind=kind, stage=stage, export_kind=getattr(cls,'PEMARA_EXPORT_KIND',None))
        else:
            @functools.wraps(function)
            def wrapper(*args,**kwargs):
                if anchor_exporter(cls):
                    finishing.preflight()
                kind, stage = call_content_kind(function, args, kwargs)
                return finish_result(function(*args,**kwargs),name, content_kind=kind, stage=stage, export_kind=getattr(cls,'PEMARA_EXPORT_KIND',None))
        setattr(cls,method,classmethod(wrapper) if isinstance(descriptor,classmethod) else staticmethod(wrapper) if isinstance(descriptor,staticmethod) else wrapper)
        # Cached legacy saves must not skip the newly required finishing stage.
        cls.IS_CHANGED = classmethod(lambda cls,*args,**kwargs: float('nan'))
        _WRAPPED.add(cls)
        logging.info('[Pemara DLSS5] mandatory export: %s',name)

def on_prompt(payload):
    graph = payload.get('prompt',{})
    affected = []
    try:
        upscale_policy.assert_content_graph(graph)
        kind = finishing.content_policy.graph_kind(graph)
        stage = finishing.content_policy.graph_stage(graph)
        for node in graph.values():
            cls = nodes.NODE_CLASS_MAPPINGS.get(node.get('class_type'))
            if cls is not None and visual_exporter(cls):
                affected.append(node)
                wrap_exporter(node['class_type'],cls)
        if affected:
            if kind == 'unknown':
                raise finishing.DLSS5RequiredError('Definir live_action ou animation no workflow antes de exportar midia nova.')
            if any(node['class_type'] == 'PemaraSaveActorProtectedImage' for node in affected):
                raise finishing.DLSS5RequiredError('DLSS integral obrigatorio: substituir exportador seletivo por SaveImage e politica explicita.')
            needs_nr=any(anchor_exporter(nodes.NODE_CLASS_MAPPINGS[n['class_type']]) for n in affected)
            if needs_nr:
                finishing.preflight()
            payload.setdefault('extra_data',{})['pemara_dlss5'] = {'policy':'dlss5_anchors_only_20261011_v1','anchors_required':True,'video_dlss5_allowed':False,'content_kind':kind}
    except Exception as error:
        # ComfyUI swallows exceptions from prompt handlers. An invalid class
        # instead makes prompt validation fail closed, before any render runs.
        logging.exception('[Pemara DLSS5] required preflight blocked')
        for node in affected:
            node['class_type'] = 'PemaraDLSS5Blocked_RuntimeUnavailable'
        if not affected:
            graph['pemara_dlss5_blocked']={'class_type':'PemaraDLSS5Blocked_RuntimeUnavailable','inputs':{}}
    return payload

class PemaraDLSS5Policy:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{}}
    RETURN_TYPES = ('STRING',)
    FUNCTION = 'status'
    CATEGORY = 'Pemara/Finishing'
    def status(self):
        return (json.dumps(finishing.preflight()),)

class PemaraSaveActorProtectedImage:
    """Explicit mask export. An automatic model mask is not a reviewed actor matte."""
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',), 'actor_mask': ('MASK',),
            'protected_subjects': ('STRING', {'default': '', 'multiline': True}),
            'mask_review_note': ('STRING', {'default': '', 'multiline': True}),
            'mask_reviewer': ('STRING', {'default': ''}),
            'mask_coverage_checked': ('BOOLEAN', {'default': False}),
            'filename_prefix': ('STRING', {'default': 'actor_protected/anchor'})},
            'hidden': {'prompt':'PROMPT'}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Pemara/Finishing'

    def save(self, images, actor_mask, protected_subjects, mask_review_note, mask_reviewer,
             mask_coverage_checked, filename_prefix, prompt=None):
        import numpy as np
        from PIL import Image
        import uuid
        raise finishing.DLSS5RequiredError('Exportador seletivo historico: novas ancoras exigem DLSS integral; usar SaveImage + PemaraDLSS5ContentPolicy.')



class PemaraLoadLosslessImage:
    @classmethod
    def INPUT_TYPES(cls):
        root = Path(folder_paths.get_input_directory())
        files = sorted(str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*')
            if p.is_file() and p.suffix.lower() in {'.png','.webp'})
        return {'required': {'image': (files, {'image_upload':True})}}
    RETURN_TYPES = ('IMAGE','MASK')
    FUNCTION = 'load'
    CATEGORY = 'Pemara/Finishing'
    def load(self, image):
        import torch
        root = Path(folder_paths.get_input_directory()).resolve()
        path = (root/image).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Fonte fora da raiz de input.')
        rgb, alpha_mask = finishing.actors.load_lossless_image(path)
        return torch.from_numpy(rgb)[None], torch.from_numpy(alpha_mask)[None]
    @classmethod
    def IS_CHANGED(cls, image):
        return finishing.sha(Path(folder_paths.get_input_directory())/image)


class PemaraDLSS5ContentPolicy:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'content_kind': (list(finishing.content_policy.KINDS), {'default':'unknown'}),
                'stage': (['final','native_preview'], {'default':'final'})}}
    RETURN_TYPES = ()
    FUNCTION = 'status'
    OUTPUT_NODE = True
    CATEGORY = 'Pemara/Finishing'
    def status(self, content_kind, stage='final'):
        kind = finishing.content_policy.normalize(content_kind)
        return {'ui': {'text': [json.dumps({**finishing.content_policy.status(),'content_kind':kind,'stage':'final','requested_stage':stage})]}}

NODE_CLASS_MAPPINGS = {'PemaraDLSS5Policy':PemaraDLSS5Policy,
    'PemaraSaveActorProtectedImage': PemaraSaveActorProtectedImage,
    'PemaraLoadLosslessImage': PemaraLoadLosslessImage,
    'PemaraDLSS5ContentPolicy': PemaraDLSS5ContentPolicy}
NODE_DISPLAY_NAME_MAPPINGS = {'PemaraDLSS5Policy':'DLSS 5 obrigatório — política ativa',
    'PemaraSaveActorProtectedImage': 'Histórico — exportador seletivo desativado',
    'PemaraLoadLosslessImage': 'Carregar PNG/WebP exato — fonte e máscara',
    'PemaraDLSS5ContentPolicy': 'Tipo da produção — live action ou animação'}
PromptServer.instance.add_on_prompt_handler(on_prompt)
logging.info('[Pemara DLSS5] required finishing installed; no opt-out or raw fallback')
