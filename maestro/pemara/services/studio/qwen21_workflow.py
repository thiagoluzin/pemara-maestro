"""Native ComfyUI Qwen-Image 2.1 generation and reference-image editing."""
MODEL = 'qwen_image_2.1_int8_convrot.safetensors'
CLIP = 'qwen3vl_8b_int8_convrot.safetensors'
VAE = 'qwen_image_2.1_vae_bf16.safetensors'


def build_workflow(prompt, negative, model, width, height, steps, cfg, seed, prefix,
                   base_image_name=None):
    if model != MODEL:
        raise ValueError('O Qwen antigo foi substituído pelo Qwen-Image 2.1. Selecione o novo modelo.')
    graph = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': model, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': CLIP, 'type': 'qwen_image', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': VAE}},
        '4': {'class_type': 'TextEncodeQwenImage21', 'inputs': {
            'clip': ['2', 0], 'prompt': prompt, 'negative_prompt': negative or '', 'resolution': 0,
            'images': {}}},
        '5': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '6': {'class_type': 'KSampler', 'inputs': {
            'model': ['1', 0], 'positive': ['4', 0], 'negative': ['4', 1],
            'latent_image': ['5', 0], 'seed': seed, 'steps': steps, 'cfg': cfg,
            'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['6', 0], 'vae': ['3', 0]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': prefix}},
    }
    if base_image_name:
        graph['9'] = {'class_type': 'LoadImage', 'inputs': {'image': base_image_name}}
        graph['10'] = {'class_type': 'ImageScale', 'inputs': {
            'image': ['9', 0], 'upscale_method': 'lanczos', 'width': width, 'height': height, 'crop': 'disabled'}}
        graph['4']['inputs'].update({'vae': ['3', 0], 'images.image_1': ['10', 0]})
        # The encoder supplies the latent matching the reference's resized dimensions.
        graph['6']['inputs']['latent_image'] = ['4', 2]
        del graph['5']
    return graph
