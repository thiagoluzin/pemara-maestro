"""Keep SageAttention while bounding fused QKV pointer spans on long H3 sequences."""
import json
import logging
from types import MethodType

import torch

SAFE_ELEMENT_SPAN = 2**31 - 1

def tensor_span(tensor):
    return sum((size - 1) * stride for size, stride in zip(tensor.shape, tensor.stride())) + 1

def _upstream_globals():
    import nodes
    method = nodes.NODE_CLASS_MAPPINGS['MiniMaxH3MemoryEfficientSageAttentionPatch'].execute
    return getattr(method, '__func__', method).__globals__

def _long_forward(self, x, rope_freqs=None, transformer_options=None, *, upstream, chunks):
    options = transformer_options or {}
    shape = x[0].shape if isinstance(x, list) else x.shape
    # The upstream fused QKV buffer has stride 3 * heads * head_dim per row.
    # Short sequences continue through the exact original function.
    span = shape[0] * 3 * self.heads * self.head_dim
    if span <= SAFE_ELEMENT_SPAN:
        return upstream['minimax_sageattn_forward'](self, x, rope_freqs, options)
    if isinstance(x, list):
        x = x.pop()
    dtype, device, sequence = x.dtype, x.device, x.shape[0]
    q, k, v = self.qkv_proj(x).split(self.heads * self.head_dim, dim=-1)
    del x
    q = q.view(1, sequence, self.heads, self.head_dim)
    k = k.view(1, sequence, self.heads, self.head_dim)
    v = v.view(1, sequence, self.heads, self.head_dim)
    out = torch.empty((1, sequence, self.heads, self.head_dim), dtype=dtype, device=device)
    group = max(1, (self.heads + chunks - 1) // chunks)
    for start in range(0, self.heads, group):
        end = min(self.heads, start + group)
        # Compact BEFORE fused RMSNorm/RoPE as well as Sage CUDA quantization.
        # Head groups are independent; frames, KV context and model math stay intact.
        qc = q[:, :, start:end].contiguous()
        kc = k[:, :, start:end].contiguous()
        vc = v[:, :, start:end].contiguous()
        if max(tensor_span(t) for t in (qc, kc, vc)) > SAFE_ELEMENT_SPAN:
            raise RuntimeError('H3 Sage compact group still exceeds safe pointer span')
        if rope_freqs is not None:
            qw = upstream['mm'].cast_to(self.q_norm.weight, device=device)
            kw = upstream['mm'].cast_to(self.k_norm.weight, device=device)
            upstream['_ck'].rms_rope_split_half_(qc, kc, rope_freqs, qw, kw,
                epsilon=self.q_norm.eps, rot_dim=rope_freqs.shape[-3] * 2)
        else:
            qc = self.q_norm(qc)
            kc = self.k_norm(kc)
        qkv = [qc, kc, vc]
        del qc, kc, vc
        value = upstream['_sageattn_int8_fp8_nhd'](qkv, dtype)
        if not bool(torch.isfinite(value).all()):
            raise RuntimeError('Non-finite long-sequence SageAttention output; block corrupted render')
        out[:, :, start:end] = value
        del value
    del q, k, v
    return self.out_proj(out.view(sequence, self.heads * self.head_dim))

class PemaraH3SageLongSequencePatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',), 'head_chunks': ('INT', {'default': 4, 'min': 2, 'max': 16})}}
    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'patch'
    CATEGORY = 'PEMARA/H3/compatibility'

    def patch(self, model, head_chunks):
        upstream = _upstream_globals()
        if upstream.get('_cuda_archs') is None or upstream.get('_ck') is None:
            raise RuntimeError('Required H3 SageAttention backend unavailable')
        cloned = model.clone()
        diffusion = cloned.get_model_object('diffusion_model')
        for index, block in enumerate(diffusion.blocks):
            def forward(attn, x, rope_freqs=None, transformer_options=None, *, _up=upstream, _chunks=head_chunks):
                return _long_forward(attn, x, rope_freqs, transformer_options, upstream=_up, chunks=_chunks)
            cloned.add_object_patch(f'diffusion_model.blocks.{index}.attn.forward', MethodType(forward, block.attn))
        logging.info('[PEMARA H3] Sage long-sequence compact QKV guard connected; head groups=%s', head_chunks)
        return (cloned,)

class PemaraH3SageStrideDiagnostic:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'sequence': ('INT', {'default': 225000, 'min': 256, 'max': 225000})},
                'optional': {'test_forward': ('BOOLEAN', {'default': False})}}
    RETURN_TYPES = ('STRING',)
    FUNCTION = 'probe'
    OUTPUT_NODE = True
    CATEGORY = 'PEMARA/H3/diagnostic'

    def probe(self, sequence, test_forward=False):
        import comfy.model_management as mm
        upstream = _upstream_globals()
        device = mm.get_torch_device()
        fused = torch.empty((1, sequence, 3, 56, 128), dtype=torch.bfloat16, device=device)
        q, k = fused[:, :, 0], fused[:, :, 1]
        fused[:, :, 0].fill_(.25)
        fused[:, :, 1].fill_(.5)
        fused[:, :, 2].fill_(.75)
        span = tensor_span(q)
        outputs = upstream['per_warp_int8_cuda'](q, k, tensor_layout='NHD')
        q_error = float((outputs[1] - .25/127).abs().max())
        k_error = float((outputs[3] - .5/127).abs().max())
        del outputs
        compact_q, compact_k = q[:, :, :14].contiguous(), k[:, :, :14].contiguous()
        outputs = upstream['per_warp_int8_cuda'](compact_q, compact_k, tensor_layout='NHD')
        compact_q_error = float((outputs[1] - .25/127).abs().max())
        compact_k_error = float((outputs[3] - .5/127).abs().max())
        report = {'source_element_span': span, 'uint32_max': 2**32-1,
                  'original_q_scale_max_error': q_error, 'original_k_scale_max_error': k_error,
                  'compact_q_scale_max_error': compact_q_error, 'compact_k_scale_max_error': compact_k_error,
                  'frames_generated': 0, 'models_changed': False}
        del outputs, compact_q, compact_k, q, k
        if test_forward:
            class Norm:
                weight = torch.ones((128,), device=device, dtype=torch.bfloat16)
                eps = 1e-5
                def __call__(self, tensor):
                    return (tensor.float() * torch.rsqrt(tensor.float().square().mean(-1, keepdim=True) + self.eps)).to(tensor.dtype)
            class Fixture:
                heads, head_dim = 56, 128
                q_norm, k_norm = Norm(), Norm()
                qkv_proj = staticmethod(lambda value: fused.view(sequence, 3*56*128))
                out_proj = staticmethod(lambda value: value)
            # Constant V has a known attention result, independent of Q/K or RoPE.
            # This checks the real fused RMSNorm/RoPE and SageAttention kernels.
            rope = torch.zeros((1, sequence, 1, 32, 2, 2), device=device, dtype=torch.bfloat16)
            rope[..., 0, 0] = 1
            rope[..., 1, 1] = 1
            value = _long_forward(Fixture(), torch.empty((sequence, 1), device=device, dtype=torch.bfloat16),
                                  rope, {}, upstream=upstream, chunks=4)
            report['full_forward_constant_v_max_error'] = float((value-.75).abs().max())
            report['full_forward_finite'] = bool(torch.isfinite(value).all())
            del rope, value
        del fused
        torch.cuda.empty_cache()
        value = json.dumps(report)
        logging.info('[PEMARA H3 Sage stride diagnostic] %s', value)
        return {'ui': {'text': [value]}, 'result': (value,)}
