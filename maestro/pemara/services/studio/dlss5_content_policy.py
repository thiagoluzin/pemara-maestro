"""Explicit content routing: never infer actor safety from a franchise or pixels."""
from pathlib import Path
import json
from contextvars import ContextVar
from functools import wraps

VERSION = 'dlss5_anchors_only_20261022_v2'
KINDS = ('unknown', 'live_action', 'animation', 'mixed')
PROTECTED = frozenset({'live_action', 'mixed'})
_CURRENT = ContextVar('pemara_dlss5_content_kind', default='unknown')


def current_kind():
    return _CURRENT.get()


def with_content_kind(function):
    @wraps(function)
    def scoped(*args, **kwargs):
        kind = normalize(kwargs.pop('content_kind', 'unknown'))
        token = _CURRENT.set(kind)
        try:
            return function(*args, **kwargs)
        finally:
            _CURRENT.reset(token)
    return scoped


def graph_stage(graph):
    stages = {node.get('inputs',{}).get('stage','final') for node in (graph or {}).values()
              if isinstance(node,dict) and node.get('class_type') == 'PemaraDLSS5ContentPolicy'}
    if len(stages)>1 or any(s not in {'final','native_preview'} for s in stages):
        raise ValueError('Etapa DLSS deve ser final ou native_preview, sem conflito.')
    return next(iter(stages),'final')


def normalize(value):
    value = str(value or 'unknown').strip().lower()
    if value not in KINDS:
        raise ValueError('content_kind deve ser live_action, animation, mixed ou unknown.')
    return value


def graph_kind(graph):
    """Use a declared workflow type; a protected exporter implies live action."""
    kinds = set()
    protected_export = False
    for node in (graph or {}).values():
        if not isinstance(node, dict):
            continue
        cls = node.get('class_type')
        if cls in {'PemaraDLSS5ContentPolicy', 'PemaraUpscaleRequiredSave', 'PemaraLanczosUpscaleRequiredSave'}:
            kind = normalize(node.get('inputs', {}).get('content_kind'))
            if kind != 'unknown': kinds.add(kind)
        if cls == 'PemaraSaveActorProtectedImage': protected_export = True
    if len(kinds) > 1:
        raise ValueError('Workflow possui tipos de conteudo conflitantes.')
    kind = next(iter(kinds), 'live_action' if protected_export else 'unknown')
    if protected_export and kind == 'animation':
        raise ValueError('Exportador de atores live action conflita com tipo animation.')
    return kind


def sidecar(path):
    return Path(str(path) + '.dlss5.content.json')


def resolve(path, *, content_kind=None, protection_requested=False, existing=None, source_sha256=None):
    declared = normalize(content_kind)
    contract = sidecar(path)
    if contract.is_file():
        data = json.loads(contract.read_text(encoding='utf-8'))
        hashes = {source_sha256}
        if existing: hashes.add(existing.get('source_sha256'))
        if data.get('schema_version') != '1.0' or data.get('source_sha256') not in hashes:
            raise ValueError('Tipo de conteudo nao pertence aos bytes desta fonte.')
        stored = normalize(data.get('content_kind'))
        if declared != 'unknown' and stored != declared:
            raise ValueError('Tipo de conteudo explicito conflita com o contrato da fonte.')
        declared = stored
    if declared == 'unknown' and existing:
        declared = normalize(existing.get('content_kind'))
    if declared == 'unknown' and protection_requested:
        declared = 'live_action'
    if declared == 'unknown' and not existing:
        raise ValueError('Definir content_kind antes do DLSS integral obrigatorio.')
    if existing:
        stored = normalize(existing.get('content_kind'))
        if stored != 'unknown' and declared != 'unknown' and stored != declared:
            raise ValueError('Tipo de conteudo conflita com recibo existente; fonte nativa exigida.')
        if stored == 'unknown' and declared != 'unknown':
            raise ValueError('Recibo historico sem tipo nao reclassifica a fonte; usar fonte nativa.')

    return declared


def status():
    return {'version':VERSION, 'selection':'explicit_workflow_or_source_contract',
            'live_action':'full_frame_required',
            'mixed':'full_frame_required',
            'animation':'full_frame_required', 'anchors':'full_frame_required', 'video_dlss5_allowed':False,
            'videos':'forbidden_by_owner', 'scope':'anchors_only',
            'actor_masks_required':False, 'automatic_masks':False, 'unknown':'blocked_before_render',
            'automatic_visual_classification':False,
            'historical_media_auto_migration':False}
