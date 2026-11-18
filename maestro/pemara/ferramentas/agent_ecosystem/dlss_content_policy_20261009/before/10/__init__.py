"""Enforce DLSS 5 on newly saved visual outputs, including imported/replayed graphs."""
import functools
import inspect
import json
import logging
from pathlib import Path
import sys
import threading

STUDIO = Path(r'E:\Pemara\maestro\pemara\services\studio')
if str(STUDIO) not in sys.path:
    sys.path.insert(0, str(STUDIO))
import dlss5_finishing as finishing
import folder_paths
import nodes
from server import PromptServer

_LOCK = threading.RLock()
_WRAPPED = set()
MEDIA_SUFFIXES = {'.png','.jpg','.jpeg','.webp','.gif','.apng','.mp4','.mov','.mkv','.webm','.avi'}

def visual_exporter(cls):
    if not getattr(cls, 'OUTPUT_NODE', False):
        return False
    spec = cls.INPUT_TYPES()
    types = [value[0] for section in ('required','optional') for value in spec.get(section,{}).values()]
    return any(isinstance(t,str) and t in {'IMAGE','VIDEO'} for t in types) or any(t in {'IMAGE','VIDEO'} for t in getattr(cls,'RETURN_TYPES',()))

def media_records(data):
    if isinstance(data,dict):
        if isinstance(data.get('filename'),str) and Path(data['filename']).suffix.lower() in MEDIA_SUFFIXES:
            yield data
        else:
            for value in data.values():
                yield from media_records(value)
    elif isinstance(data,(list,tuple)):
        for value in data:
            yield from media_records(value)

def finish_result(result, name):
    ui = result.get('ui',{}) if isinstance(result,dict) else getattr(result,'ui',None)
    if hasattr(ui,'as_dict'):
        ui = ui.as_dict()
    records = list(media_records(ui))
    if not records:
        raise finishing.DLSS5RequiredError(f'DLSS 5: exportador visual {name} sem arquivo verificavel; sem entrega.')
    # This runs inside ComfyUI's serial execution, after sampling. Release model
    # cache before the D3D12 pass; no external queue/client or second GPU job.
    import comfy.model_management as mm
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
        receipt = finishing.finish_file(path)
        finished.append(path)
        record['dlss5'] = {'required':True, 'profile':receipt['profile'], 'technical_pass':True}
    # SaveVideo returns VIDEO downstream; it must point to the finished bytes.
    if name == 'SaveVideo' and not isinstance(result,dict):
        from comfy_api.latest import io, VideoFromFile
        return io.NodeOutput(VideoFromFile(str(finished[0])), ui=ui)
    return result

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
                finishing.preflight()
                return finish_result(await function(*args,**kwargs),name)
        else:
            @functools.wraps(function)
            def wrapper(*args,**kwargs):
                finishing.preflight()
                return finish_result(function(*args,**kwargs),name)
        setattr(cls,method,classmethod(wrapper) if isinstance(descriptor,classmethod) else staticmethod(wrapper) if isinstance(descriptor,staticmethod) else wrapper)
        # Cached legacy saves must not skip the newly required finishing stage.
        cls.IS_CHANGED = classmethod(lambda cls,*args,**kwargs: float('nan'))
        _WRAPPED.add(cls)
        logging.info('[Pemara DLSS5] mandatory export: %s',name)

def on_prompt(payload):
    graph = payload.get('prompt',{})
    affected = []
    try:
        for node in graph.values():
            cls = nodes.NODE_CLASS_MAPPINGS.get(node.get('class_type'))
            if cls is not None and visual_exporter(cls):
                affected.append(node)
                wrap_exporter(node['class_type'],cls)
        if affected:
            finishing.preflight()
            payload.setdefault('extra_data',{})['pemara_dlss5'] = finishing.preflight()
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
            'filename_prefix': ('STRING', {'default': 'actor_protected/anchor'})}}
    RETURN_TYPES = ()
    FUNCTION = 'save'
    OUTPUT_NODE = True
    CATEGORY = 'Pemara/Finishing'

    def save(self, images, actor_mask, protected_subjects, mask_review_note, mask_reviewer,
             mask_coverage_checked, filename_prefix):
        import numpy as np
        from PIL import Image
        import uuid
        if not mask_coverage_checked or not mask_review_note.strip() or not mask_reviewer.strip():
            raise finishing.DLSS5RequiredError('Revisar cobertura real dos atores antes do acabamento seletivo.')
        subjects = [s.strip() for s in protected_subjects.split(',') if s.strip()]
        if not subjects or len(images) != len(actor_mask):
            raise finishing.DLSS5RequiredError('Informar sujeitos e uma mascara exata por imagem, sem broadcast.')
        base = Path(folder_paths.get_output_directory()).resolve()
        prefix = (base / filename_prefix).resolve()
        if not prefix.is_relative_to(base) or prefix == base:
            raise finishing.DLSS5RequiredError('Prefixo fora da raiz de output.')
        prefix.parent.mkdir(parents=True, exist_ok=True)
        records = []
        for index, (tensor, matte) in enumerate(zip(images, actor_mask)):
            rgb = tensor.detach().cpu().numpy()
            mask = matte.detach().cpu().numpy()
            if rgb.shape[:2] != mask.shape or mask.ndim != 2 or not np.isfinite(mask).all() or mask.min() < 0 or mask.max() > 1:
                raise finishing.DLSS5RequiredError('Mascara invalida; sem resize/broadcast automatico.')
            name = prefix.name + '_' + uuid.uuid4().hex[:12] + f'_{index:03d}.png'
            path = prefix.parent / name
            mask_path = path.with_name(path.stem + '.actor_mask.png')
            Image.fromarray(np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8)).save(path)
            Image.fromarray(np.rint(mask * 255).astype(np.uint8)).save(mask_path)
            contract = {'schema_version': '1.0', 'mode': finishing.actors.MODE,
                'source_sha256': finishing.sha(path), 'protected_subjects': subjects,
                'mask_review': {'status': 'PASS', 'reviewer': mask_reviewer, 'note': mask_review_note},
                'masks': [{'path': str(mask_path), 'sha256': finishing.sha(mask_path)}]}
            finishing._atomic_json(finishing.actors.sidecar(path), contract)
            import comfy.model_management as mm
            mm.unload_all_models(); mm.soft_empty_cache()
            finishing.finish_file(path, protect_actors=True)
            records.append({'filename': name, 'subfolder': str(path.parent.relative_to(base)), 'type': 'output'})
        return {'ui': {'images': records}}

NODE_CLASS_MAPPINGS = {'PemaraDLSS5Policy':PemaraDLSS5Policy,
    'PemaraSaveActorProtectedImage': PemaraSaveActorProtectedImage}
NODE_DISPLAY_NAME_MAPPINGS = {'PemaraDLSS5Policy':'DLSS 5 obrigatório — política ativa',
    'PemaraSaveActorProtectedImage': 'Salvar âncora — DLSS no cenário, atores protegidos'}
PromptServer.instance.add_on_prompt_handler(on_prompt)
logging.info('[Pemara DLSS5] required finishing installed; no opt-out or raw fallback')
