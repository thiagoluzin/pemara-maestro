"""Separate a scene's DiT spatial reference from Qwen-only identity crops.

Pure conditioning metadata selection: no model patch, latent/output mutation,
image generation, resampling, or audio replacement. Explicit opt-in graph node.
"""
import json


class MiniMaxH3SceneLatentReference:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'conditioning': ('CONDITIONING',),
                             'expected_image_count': ('INT', {'default': 5, 'min': 1, 'max': 8})}}

    RETURN_TYPES = ('CONDITIONING', 'STRING')
    RETURN_NAMES = ('conditioning', 'role_evidence')
    FUNCTION = 'select'
    CATEGORY = 'conditioning/minimax'
    DESCRIPTION = 'Keep only the first (physical scene) image latent as a DiT reference. Preserve all Qwen identity-reference embeddings and temporal keyframes. Reject missing/mismatched latent references.'

    def select(self, conditioning, expected_image_count):
        out = []
        for emb, metadata in conditioning:
            refs = metadata.get('minimax_refs')
            if not isinstance(refs, list):
                raise ValueError('H3 scene role control requires VAE-encoded image refs')
            images = [r for r in refs if r.get('kind') == 'image']
            if len(images) != expected_image_count:
                raise ValueError('H3 image count differs from the exact graph role contract')
            scene = images[0]
            if scene.get('latent') is None or scene.get('latent_w', 0) <= 0 or scene.get('latent_h', 0) <= 0:
                raise ValueError('H3 physical scene image latent is incomplete')
            copy = metadata.copy()
            copy['minimax_refs'] = [scene]
            out.append([emb, copy])
        if not out:
            raise ValueError('H3 scene conditioning is empty')
        return out, json.dumps({'qwenEmbeddingsPreserved': True, 'ditImageRefs': 1,
                                'imageIdentityRefsLatentExcluded': expected_image_count - 1,
                                'videoRefsLatentExcluded': True, 'keyframesPreserved': True})


NODE_CLASS_MAPPINGS = {'MiniMaxH3SceneLatentReference': MiniMaxH3SceneLatentReference}
NODE_DISPLAY_NAME_MAPPINGS = {'MiniMaxH3SceneLatentReference': 'MiniMax H3 Scene Latent Reference Roles'}
