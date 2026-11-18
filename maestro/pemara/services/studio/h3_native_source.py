"""Native Source Continuation for newly built base-H3 production graphs."""
from copy import deepcopy
import json
from pathlib import Path

NODE = 'H3NativeSourceContinuationHandoff'
VDN_NODES = {'ApplyVDNH3', 'ApplyVDNH3Advanced'}
CONTINUATION_CONSUMERS = {'H3ContinuumSamplerProduction', 'H3ContinuumSamplerV3',
                          'H3ContinuumSamplerV34', 'PemaraH3NativeStateReferences',
                          'PemaraH3NativeStateEndpoints'}
POLICY = json.loads(Path(__file__).with_name('h3_native_source.json').read_text(encoding='utf-8'))
LEGACY = {'H3PartitionedExactPrefixDiagnosticHandoff', 'H3ProgressiveHandoff',
          'H3ProgressiveTargetInputHandoff'}


def unwrap_native_source(graph):
    """Rebuild the mandatory acceleration chain upstream of existing Flow nodes."""
    saved = {}
    for key, node in list(graph.items()):
        if node.get('class_type') != NODE:
            continue
        saved[key] = deepcopy(node)
        parent = node['inputs']['model']
        for consumer in graph.values():
            if consumer.get('inputs', {}).get('model') == [key, 0]:
                consumer['inputs']['model'] = list(parent)
        del graph[key]
    return saved


def ensure_native_source(graph, consumers, saved=None):
    # Historical explicit Flow controls and FastH3/Turbo retain their own route.
    if any(n.get('class_type') in LEGACY for n in graph.values()):
        return graph
    if any(str(n.get('inputs', {}).get('unet_name', '')).startswith('fastvideo_') for n in graph.values()):
        return graph
    groups = {}
    for n in list(graph.values()):
        if n.get('class_type') in consumers:
            source = tuple(n['inputs']['model'])
            groups.setdefault(source, []).append(n)
    if len(groups) > 1:
        sampling = {source for source, nodes in groups.items()
                    if any(n.get('class_type') != 'BasicScheduler' for n in nodes)}
        if len(sampling) != 1:
            raise ValueError('H3_NATIVE_MODEL_PATH: a sequencia exige um mesmo MODEL para os amostradores.')
        # The scheduler must use the actual guider's controlled model as well.
        source = next(iter(sampling))
        groups = {source: [n for nodes in groups.values() for n in nodes]}
    source, targets = next(iter(groups.items()))
    from h3_acceleration import model_chain
    vdn = [n for _, n in model_chain(graph, source[0])
           if n.get('class_type') in VDN_NODES]
    if not vdn:
        if saved or any(n.get('class_type') in CONTINUATION_CONSUMERS for n in targets):
            raise ValueError('H3_NATIVE_VDN_REQUIRED: continuacao exige VDN-H3 conectado antes do Flow; nenhum job foi enviado.')
        # An ordinary single take uses the selected H3 + Sage + Spectrum.
        # Never inject an unqualified continuation adapter into its MODEL.
        return graph
    if any(float(n.get('inputs', {}).get('strength', 1)) <= 0 for n in vdn):
        raise ValueError('H3_NATIVE_VDN_REQUIRED: VDN-H3 deve estar ativo antes do Flow.')
    if saved:
        if len(saved) != 1:
            raise ValueError('H3_NATIVE_MODEL_PATH: multiplos modelos de continuidade.')
        key, node = next(iter(saved.items()))
    else:
        key = 'pemara_h3_native_source'
        if key in graph:
            raise ValueError('H3_NATIVE_NODE_ID: identificador reservado ocupado.')
        trajectory, provider = key + '_trajectory', key + '_upscaler'
        graph[trajectory] = {'class_type': 'H3FlowTrajectory', 'inputs': {'storage': 'system_ram', 'max_runs': 4}}
        graph[provider] = {'class_type': 'MinimaxH3LatentUpscaler3DProvider', 'inputs': deepcopy(POLICY['provider'])}
        node = {'class_type': NODE, 'inputs': {**deepcopy(POLICY['settings']),
                'trajectory': [trajectory, 0], 'learned_upscaler': [provider, 0]}}
    node['inputs']['model'] = list(source)
    graph[key] = node
    for target in targets:
        target['inputs']['model'] = [key, 0]
    return graph


def validate_native_source(graph, consumers):
    native = {k: n for k, n in graph.items() if n.get('class_type') == NODE}
    if not native:
        return
    if len(native) != 1:
        raise ValueError('H3_NATIVE_MODEL_PATH: somente um MODEL por sequencia.')
    key, node = next(iter(native.items()))
    from h3_acceleration import model_chain
    vdn = [n for _, n in model_chain(graph, key) if n.get('class_type') in VDN_NODES]
    if not vdn or any(float(n.get('inputs', {}).get('strength', 1)) <= 0 for n in vdn):
        raise ValueError('H3_NATIVE_VDN_REQUIRED: continuacao exige VDN-H3 ativo antes do Flow.')
    if node['inputs'].get('source_prefix_projection') != 'native_source_carry':
        raise ValueError('H3_NATIVE_CARRY_REQUIRED: reconstrucao bicubica nao e a rota principal.')
    for n in graph.values():
        if n.get('class_type') in consumers and n['inputs']['model'] != [key, 0]:
            raise ValueError('H3_NATIVE_MODEL_PATH: scheduler e amostradores devem compartilhar o MODEL.')
