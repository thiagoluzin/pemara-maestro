"""Opt-in H3-only attention experiment. No global attention changes."""
import sys

def make_override(sageattn):
    def override(original, q, k, v, heads, mask=None, skip_reshape=False, skip_output_reshape=False, **kwargs):
        # Honor an explicit full-precision request from the model/caller.
        if kwargs.get('low_precision_attention') is False or kwargs.get('attn_precision') is not None:
            return original(q, k, v, heads, mask=mask, skip_reshape=skip_reshape,
                            skip_output_reshape=skip_output_reshape, **kwargs)
        # Flow exact-prefix attention may supply a rectangular/mapped mask.
        # SageAttention has no mask interface: preserve it through the caller's
        # native attention backend. Unmasked H3 calls still use SageAttention.
        if mask is not None:
            return original(q, k, v, heads, mask=mask, skip_reshape=skip_reshape,
                            skip_output_reshape=skip_output_reshape, **kwargs)
        if not skip_reshape:
            raise ValueError('Unexpected H3 attention shape; experiment stopped')
        out = sageattn(q, k, v, tensor_layout='HND', is_causal=False, sm_scale=kwargs.get('scale'))
        if not skip_output_reshape:
            out = out.transpose(1, 2).reshape(q.shape[0], -1, heads * q.shape[-1])
        return out
    return override

class R17H3SageAttention:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'model': ('MODEL',)}}
    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'patch'
    CATEGORY = 'Pemara/Lab'

    def patch(self, model):
        from comfy.ldm.minimax.model import MiniMaxH3Model
        if not isinstance(model.model.diffusion_model, MiniMaxH3Model):
            raise TypeError('This experiment accepts MiniMax H3 only')
        if 'D:/PemaraRuntimes/h3-attention-lab' not in sys.path:
            sys.path.insert(0, 'D:/PemaraRuntimes/h3-attention-lab')
        from sageattention import sageattn
        patched = model.clone()
        patched.model_options['transformer_options']['optimized_attention_override'] = make_override(sageattn)
        return (patched,)

NODE_CLASS_MAPPINGS = {'R17H3SageAttention': R17H3SageAttention}
