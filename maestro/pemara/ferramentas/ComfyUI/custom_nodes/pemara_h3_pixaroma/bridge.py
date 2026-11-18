"""Opt-in Pixaroma Long Video / Spectrum bridge; unrelated graphs are untouched.

Window identity is a separate history row. The topology contains the complete
ordered window plan AND every native window topology, so a change remains fatal.
Spectrum's ordinary CPU archive, forecasting and audio replay operate unchanged.
"""
from contextvars import ContextVar
import importlib
import sys
import json
from collections import Counter
from .state_reference_routing import reference_payload

from .vendor.node_h3_long_video import _Windows, WRAPPER_KEY, _diffusion_model_kind
from .vendor._h3_long_video_helpers import window_chunks, plan_windows

_scope = ContextVar('pemara_pixaroma_spectrum_window', default=None)

def reviewed_flow_exact_probe(options):
    """Identify Flow's explicit one-call diagnostic, never ordinary sampling."""
    probe = (options or {}).get('h3_flow_exact_probe_context')
    return (isinstance(probe, dict)
            and type(probe.get('outer_step')) is int
            and probe['outer_step'] >= 0
            and (options or {}).get('h3_flow_stage') == 'probe')

def spectrum_module():
    for name, module in tuple(sys.modules.items()):
        if name.endswith('comfyui_spectrum_h3.minimax_h3') and hasattr(module, 'diffusion_model_wrapper'):
            return module
    raise RuntimeError('Spectrum must be loaded and applied before Pixaroma bridge')

def joint_topology(plan, topologies):
    if len(plan) != len(topologies) or not plan:
        raise RuntimeError('Incomplete Pixaroma window topology')
    fields = ('video_shape', 'audio_shape', 'target_audio_rows', 'target_video_rows', 'hidden_width')
    base = dict(topologies[0])
    for item in topologies:
        current = dict(item)
        if any(current[k] != base[k] for k in fields):
            raise RuntimeError('Spectrum requires equal window target geometry')
    return tuple(topologies[0]) + (('pixaroma_plan_v1', tuple(plan)), ('pixaroma_native_topologies', tuple(topologies)))

def install_hooks(module):
    if getattr(module.branch_labels, '_pemara_pixaroma_v1', False):
        return
    original_labels = module.branch_labels
    original_topology = module.topology_signature
    def labels(options):
        value = original_labels(options)
        scope = _scope.get()
        if scope is None or value is None:
            return value
        return tuple((*label, 'pixaroma_window', scope['window']) for label in value)
    def topology(*args, **kwargs):
        value = original_topology(*args, **kwargs)
        scope = _scope.get()
        if scope is None:
            return value
        if value != scope['native']:
            raise RuntimeError('Native topology changed inside Pixaroma window')
        return scope['joint']
    labels._pemara_pixaroma_v1 = True
    module.branch_labels = labels
    module.topology_signature = topology
    module._pemara_pixaroma_native_topology = original_topology

class SpectrumWindows(_Windows):
    def __init__(self, n, stride, window_conditionings=(), reference_states=False):
        super().__init__(n, stride)
        self.events = Counter()
        self.window_conditionings = tuple(window_conditionings)
        self._prepared_text = None
        self.reference_states = reference_states
        self._reference_plan = ()

    def _window_payload(self, payload, l0, l1, a0, a1, audio_t):
        if self.reference_states:
            key = (l0, l1, a0, a1)
            if len(self._reference_plan) != 4 or len(self.window_conditionings) != 4:
                raise RuntimeError('State references require the reviewed four-window plan')
            try:
                index = self._reference_plan.index(key)
            except ValueError as exc:
                raise RuntimeError('Unplanned reference window') from exc
            payload = reference_payload(payload, self.window_conditionings[index], 1)
        return super()._window_payload(payload, l0, l1, a0, a1, audio_t)

    def window_text(self, inner, context, payload, count):
        """Opt-in local text states; guides, references and sound stay global.

        Each window sees only its current dramatic state instead of replaying
        the complete story. Refine Qwen states with the native loaded H3 module,
        exactly as MiniMaxH3.extra_conds does. Never silently reuse a short plan.
        """
        if not self.window_conditionings:
            return [(context, payload.get('text_token_tags'))] * count
        if len(self.window_conditionings) != count:
            raise RuntimeError('Pixaroma direction count must match the native window plan')
        key = (id(inner), str(context.device), context.dtype)
        if self._prepared_text is None or self._prepared_text[0] != key:
            prepared = []
            for conditioning in self.window_conditionings:
                if len(conditioning) != 1:
                    raise RuntimeError('Window direction requires one positive conditioning entry')
                raw, metadata = conditioning[0]
                if raw.ndim != 3 or raw.shape[0] != 1 or context.shape[0] != 1:
                    raise RuntimeError('Window direction requires native batch-one text states')
                text = inner.preprocess_text_embeds(raw.to(device=context.device, dtype=context.dtype))
                if text.shape[-1] != context.shape[-1]:
                    raise RuntimeError('Window text has an incompatible hidden width')
                prepared.append((text, metadata.get('minimax_token_tags')))
            self._prepared_text = (key, prepared)
            print('[PEMARA Pixaroma] Explicit local direction for {} windows; text routed; state-reference replacement is explicitly opt-in'.format(count))
        return self._prepared_text[1]
    def __call__(self, executor, x, timestep, context, transformer_options=None, **kwargs):
        module = spectrum_module()
        options = transformer_options or {}
        runtime = options.get(module.RUNTIME_KEY)
        if runtime is None or options.get(module.RUN_ID_KEY) is None:
            if reviewed_flow_exact_probe(options):
                if (self.window_conditionings or self.reference_states
                        or not isinstance(x, (tuple, list)) or len(x) != 2
                        or plan_windows(x[0].shape[2], x[1].shape[-1], self.n, self.stride) is not None):
                    raise RuntimeError('Flow exact probe requires one native Pixaroma context without state replacement')
                # Flow's handoff probe is one exact diagnostic evaluation outside
                # a denoising schedule. The model retains Sage and Spectrum;
                # the latter's own wrapper handles an explicit exact call here.
                # All real low/high samplers still require active Spectrum and
                # actual + forecast + audio-replay evidence below.
                result = super().__call__(executor, x, timestep, context, options, **kwargs)
                self.events[('flow_exact_probe', 'actual', 0)] += 1
                return result
            raise RuntimeError('Pixaroma bridge requires active Spectrum sampling; refusing fallback')
        if not isinstance(x, (tuple, list)) or len(x) != 2:
            raise RuntimeError('Expected native H3 audiovisual pair')
        video, audio = x
        plan = plan_windows(video.shape[2], audio.shape[-1], self.n, self.stride)
        if plan is None:
            # A sufficiently large explicit window is ONE native full-context
            # call. Keep Spectrum history/replay auditing active; no temporal
            # subdivision or window blending is performed by the vendor path.
            plan = [(0, video.shape[2], 0, audio.shape[-1])]
            if self._told != video.shape[2]:
                self._told = video.shape[2]
                print('[PEMARA Pixaroma] Explicit ONE native temporal context; no overlapping-window blend')
        self._reference_plan = tuple(tuple(win) for win in plan)
        inner = executor.class_obj
        if not module.is_native_minimax_h3(inner):
            raise RuntimeError('Unsupported H3 inner model')
        payload = kwargs.get('minimax_payload') or {}
        window_text = self.window_text(inner, context, payload, len(plan))
        topologies = []
        for index, (l0, l1, a0, a1) in enumerate(plan):
            local = self._window_payload(payload, l0, l1, a0, a1, audio.shape[-1])
            local['text_token_tags'] = window_text[index][1]
            vx, ax = video[:, :, l0:l1], audio[..., a0:a1]
            current_context = window_text[index][0]
            layout = module._resolve_layout(inner, current_context, vx, ax, local)
            topologies.append(module._pemara_pixaroma_native_topology(inner, vx, ax, current_context, layout, options, local))
        joint = joint_topology(plan, topologies)
        call_index = 0
        def scoped_executor(*args, **kw):
            nonlocal call_index
            index = call_index
            call_index += 1
            token = _scope.set({'window': tuple(plan[index]), 'native': topologies[index], 'joint': joint})
            try:
                args = list(args)
                args[2] = window_text[index][0]
                kw['minimax_payload'] = dict(kw['minimax_payload'], text_token_tags=window_text[index][1])
                result = executor(*args, **kw)
                if runtime.disabled_reason:
                    raise RuntimeError('Spectrum forecasting disabled: ' + runtime.disabled_reason)
                phase = runtime.offline_phase or 'causal'
                mode = 'actual' if options.get('spectrum_h3_actual') else 'forecast'
                self.events[(phase, mode, index)] += 1
                return result
            finally:
                _scope.reset(token)
        result = super().__call__(scoped_executor, x, timestep, context, options, **kwargs)
        if call_index != len(plan):
            raise RuntimeError('Incomplete temporal window execution')
        return result

class AuditRun:
    def __init__(self, windows):
        self.windows = windows
    def __call__(self, executor, *args, **kwargs):
        self.windows.events.clear()
        options = getattr(executor.class_obj, 'model_options', {}) or {}
        probe = reviewed_flow_exact_probe(options.get('transformer_options', {}))
        if probe:
            sampler = args[2] if len(args) > 2 else kwargs.get('sampler')
            sigmas = args[3] if len(args) > 3 else kwargs.get('sigmas')
            if (sigmas is None or len(sigmas) != 1
                    or getattr(getattr(sampler, 'sampler_function', None), '__name__', '') != '_h3_flow_exact_probe'):
                raise RuntimeError('Unverified Flow probe sampler; ordinary Spectrum audit remains mandatory')
            result = executor(*args, **kwargs)
            if self.windows.events != Counter({('flow_exact_probe', 'actual', 0): 1}):
                raise RuntimeError('Flow exact probe did not execute exactly one native model call')
            print('[PEMARA Pixaroma Flow probe receipt] ' + json.dumps({'exact_probe_calls': 1, 'native_contexts': 1, 'sampling_fallback': False}))
            return result
        result = executor(*args, **kwargs)
        events = self.windows.events
        actual = sum(count for (phase, mode, index), count in events.items() if mode == 'actual')
        forecast = sum(count for (phase, mode, index), count in events.items() if phase != 'replay' and mode == 'forecast')
        replay = sum(count for (phase, mode, index), count in events.items() if phase == 'replay')
        if not (actual and forecast and replay):
            raise RuntimeError('Pixaroma/Spectrum audit requires actual + causal forecast + audio replay: ' + str(events))
        print('[PEMARA Pixaroma receipt] ' + json.dumps({'actual_window_calls': actual,
              'causal_forecast_window_calls': forecast, 'replay_window_calls': replay,
              'per_window': {str(k): v for k,v in events.items()}}))
        return result

class PemaraPixaromaSpectrumLongVideo:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',),
                            'window_seconds': ('FLOAT', {'default': 10., 'min': 4., 'max': 30., 'step': .5}),
                            'overlap_seconds': ('FLOAT', {'default': 1.5, 'min': .5, 'max': 7., 'step': .5})},
                'optional': {**{f'window_direction_{i}': ('CONDITIONING',) for i in range(1, 5)},
                             'window_reference_states': ('BOOLEAN', {'default': False})}}
    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'apply'
    CATEGORY = 'PEMARA/H3/Experimental'
    def apply(self, model, window_seconds, overlap_seconds, **kwargs):
        module = spectrum_module()
        install_hooks(module)
        kind = _diffusion_model_kind()
        wrappers = model.wrappers.get(kind, {})
        spectrum_key = module.WRAPPER_KEY
        if set(wrappers) != {spectrum_key} or len(wrappers[spectrum_key]) != 1:
            raise RuntimeError('Bridge requires exactly the reviewed Spectrum diffusion wrapper')
        patched = model.clone()
        directions = []
        for i in range(1, 5):
            item = kwargs.get(f'window_direction_{i}')
            if item is not None:
                if len(directions) != i - 1:
                    raise RuntimeError('Window directions must be consecutive from one')
                directions.append(item)
        if window_seconds > 15.:
            # Local opt-in full-context route for a large card, not an upstream
            # claimed long-window benchmark. Native H3 grid is17n+5frames.
            n = max(1, int(round((window_seconds * 24. - 5.) / 17.)))
            chunks = (n, n)
        else:
            chunks = window_chunks(window_seconds, overlap_seconds)
        windows = SpectrumWindows(*chunks, directions, reference_states=kwargs.get('window_reference_states', False))
        patched.wrappers[kind] = {
            WRAPPER_KEY: [windows],
            spectrum_key: list(wrappers[spectrum_key])}
        import comfy.patcher_extension
        outer = comfy.patcher_extension.WrappersMP.OUTER_SAMPLE
        patched.wrappers[outer] = {'pemara_pixaroma_audit': [AuditRun(windows)], **patched.wrappers.get(outer, {})}
        print('[PEMARA Pixaroma] Window-isolated Spectrum history and audio replay bridge enabled')
        return (patched,)
