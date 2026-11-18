"""Owner-required H3 Spectrum policy, independent of resolution and profile."""
from copy import deepcopy
import json
from pathlib import Path

PROFILE = 'h3_master_fbc20'  # Persisted ID now resolves to Master with Spectrum.
SPECTRUM_PROFILE = 'h3_master_spectrum20'
PROFILES = (PROFILE, SPECTRUM_PROFILE)
NODE = 'ApplyMiniMaxH3FirstBlockCache'  # Removed on regeneration; never stack caches.
SPECTRUM_NODE = 'SpectrumApplyMiniMaxH3'
SAGE_NODE = 'MiniMaxH3MemoryEfficientSageAttentionPatch'
GUARD_NODE = 'PemaraH3SageLongSequencePatch'
SAMPLING_CONSUMERS = {'BasicGuider', 'BasicScheduler', 'CFGGuider', 'KSampler',
                      'KSamplerAdvanced', 'MiniMaxH3MotionDirector',
                      'MiniMaxH3FiniteSegmentSampler', 'H3ContinuumSamplerProduction',
                      'H3ContinuumSamplerV3', 'H3ContinuumSamplerV34', 'PemaraH3NativeStateReferences',
                      'PemaraH3NativeStateEndpoints'}
REQUIRED_NODES = (SAGE_NODE, GUARD_NODE, SPECTRUM_NODE)
SPECTRUM_SETTINGS = json.loads(
    Path(__file__).with_name('h3_spectrum_master20.json').read_text(encoding='utf-8'))


def model_chain(graph, source):
    seen, chain = set(), []
    while True:
        key = str(source)
        if key in seen or key not in graph:
            raise ValueError('H3_GRAPH_MODEL_PATH_INVALID: ciclo ou modelo ausente.')
        seen.add(key)
        node = graph[key]
        chain.append((key, node))
        parent = node.get('inputs', {}).get('model')
        if not isinstance(parent, (list, tuple)) or len(parent) != 2:
            return chain
        source = parent[0]


def _check_sampler(graph):
    for node in graph.values():
        sampler = node.get('inputs', {}).get('sampler_name')
        if sampler is not None and sampler != 'res_multistep':
            raise ValueError('H3_SPECTRUM_SAMPLER_UNSUPPORTED: Sage + Spectrum exigem RES multistep; nenhum fallback sera usado.')


def prepare_spectrum(graph):
    """Remove old cache wrappers before restoring the required ordered chain."""
    _check_sampler(graph)
    for key, node in list(graph.items()):
        if node.get('class_type') not in {NODE, SPECTRUM_NODE}:
            continue
        parent = node.get('inputs', {}).get('model')
        if not isinstance(parent, (list, tuple)) or len(parent) != 2:
            if any(n.get('inputs', {}).get('model') == [key, 0] for n in graph.values()):
                raise ValueError('H3_SPECTRUM_MODEL_MISSING: acelerador sem modelo.')
        else:
            model_chain(graph, key)
            for consumer in graph.values():
                if consumer.get('inputs', {}).get('model') == [key, 0]:
                    consumer['inputs']['model'] = list(parent)
        del graph[key]


def ensure_spectrum(graph):
    """Wrap all sampling paths after their existing patches and protected Sage."""
    sources = {}
    consumers = [n for n in graph.values() if n.get('class_type') in SAMPLING_CONSUMERS]
    for consumer in consumers:
        source = consumer['inputs']['model']
        chain = model_chain(graph, source[0])
        classes = [n.get('class_type') for _, n in chain]
        if any('cache' in kind.lower() for kind in classes if kind):
            raise ValueError('H3_SPECTRUM_CACHE_CONFLICT: remova o outro cache antes de gerar.')
        if SAGE_NODE not in classes:
            raise ValueError('H3_GRAPH_SAGE_REQUIRED: Spectrum exige Sage conectado.')
        protected = any(n.get('class_type') == GUARD_NODE and
                        n.get('inputs', {}).get('head_chunks') == 4 and
                        SAGE_NODE in classes[i + 1:]
                        for i, (_, n) in enumerate(chain))
        source_key = (str(source[0]), source[1])
        if source_key not in sources:
            model = list(source)
            if not protected:
                guard_id = _free_id(graph, 'pemara_spectrum_guard_' + str(source[0]))
                graph[guard_id] = {'class_type': GUARD_NODE,
                                   'inputs': {'model': model, 'head_chunks': 4}}
                model = [guard_id, 0]
            patch_id = _free_id(graph, 'pemara_h3_spectrum_' + str(model[0]))
            graph[patch_id] = {'class_type': SPECTRUM_NODE,
                               'inputs': {'model': model, **SPECTRUM_SETTINGS}}
            sources[source_key] = [patch_id, 0]
        consumer['inputs']['model'] = list(sources[source_key])
    validate_spectrum(graph)
    return graph


def _free_id(graph, prefix):
    while prefix in graph:
        prefix += '_'
    return prefix


def validate_spectrum(graph):
    """Validate enabled configuration and ordering on every actual model path."""
    _check_sampler(graph)
    consumers = [n for n in graph.values() if n.get('class_type') in SAMPLING_CONSUMERS]
    if not consumers:
        raise ValueError('H3_SPECTRUM_PATH_MISSING: nenhum caminho de amostragem.')
    for consumer in consumers:
        chain = model_chain(graph, consumer['inputs']['model'][0])
        classes = [n.get('class_type') for _, n in chain]
        if classes.count(SPECTRUM_NODE) != 1:
            raise ValueError('H3_GRAPH_SPECTRUM_REQUIRED: Spectrum conectado e obrigatorio em todo workflow H3.')
        index = classes.index(SPECTRUM_NODE)
        patch = chain[index][1]['inputs']
        if {k: v for k, v in patch.items() if k != 'model'} != SPECTRUM_SETTINGS:
            raise ValueError('H3_GRAPH_SPECTRUM_CONFIG: Spectrum desligado ou fora da configuracao aprovada.')
        following = classes[index + 1:]
        if GUARD_NODE not in following or SAGE_NODE not in following or following.index(GUARD_NODE) > following.index(SAGE_NODE):
            raise ValueError('H3_GRAPH_SPECTRUM_ORDER: exige Sage -> protecao -> Spectrum.')
        guard = chain[index + 1 + following.index(GUARD_NODE)][1]
        if guard['inputs'].get('head_chunks') != 4:
            raise ValueError('H3_GRAPH_SPECTRUM_GUARD: exige protecao Sage de quatro grupos.')
        if any('cache' in kind.lower() for kind in classes if kind):
            raise ValueError('H3_SPECTRUM_CACHE_CONFLICT: nao combinar caches.')
    return True


def apply_master_cache(graph, profile_id):
    """Compatibility entry point: every profile now uses the required policy."""
    from h3_workflow import ensure_h3_sage_attention
    return ensure_h3_sage_attention(deepcopy(graph))
