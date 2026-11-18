"""Isolated TRELLIS inference worker. Called by the Maestro Comfy output node."""
import argparse
import gc
import importlib
import json
import os
from pathlib import Path
import sys
import types

RUNTIME = Path('D:/PemaraRuntimes/maestro-game-ai')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--engine', choices=['trellis2', 'pixal3d'], default='trellis2')
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', ATTN_BACKEND='sdpa')
    sys.path.insert(0, str(RUNTIME / 'apps/ComfyUI'))
    # Load the model package without loading the node registry or starting a server.
    package = types.ModuleType('maestro_trellis')
    package.__path__ = [str(RUNTIME / 'apps/ComfyUI-Trellis2')]
    sys.modules[package.__name__] = package
    sys.argv = [sys.argv[0], '--cpu'] if args.preflight else [sys.argv[0]]
    module = importlib.import_module('maestro_trellis.trellis2.pipelines.trellis2_image_to_3d')
    sparse = importlib.import_module('maestro_trellis.trellis2.modules.sparse.config')
    sparse.set_attn_backend('sdpa')
    import folder_paths
    from PIL import Image
    import torch
    torch.hub.set_dir(str(RUNTIME / 'torch_hub'))
    if args.engine == 'pixal3d':
        for relative in ('torch_hub/valeoai_NAF_main/hubconf.py', 'torch_hub/checkpoints/naf_release.pth'):
            if not (RUNTIME / relative).is_file():
                raise FileNotFoundError('Dependência local NAF ausente: ' + relative)
    from comfy.utils import ProgressBar
    import trimesh
    folder_paths.models_dir = str(RUNTIME / 'apps/ComfyUI/models')
    model_dir = Path(folder_paths.models_dir) / ('TencentARC/Pixal3D' if args.engine == 'pixal3d' else 'microsoft/TRELLIS.2-4B')
    pipeline = module.Trellis2ImageTo3DPipeline.from_pretrained(str(model_dir), keep_models_loaded=False, isPixal3D=args.engine == 'pixal3d')
    if args.preflight:
        print('PREFLIGHT_OK', args.engine, flush=True)
        return
    if args.engine == 'pixal3d':
        from check_natten import verify
        verify()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Output already exists')
    pipeline.cuda()
    image = Image.open(args.image).convert('RGB')
    rembg = importlib.import_module('maestro_trellis.trellis2.pipelines.rembg')
    pipeline.rembg_model = rembg.BiRefNet(str(RUNTIME / 'models/BiRefNet'))
    image = pipeline.preprocess_image(image)
    image.save(output.with_name(output.stem + '_foreground.png'))
    pipeline.rembg_model = None
    gc.collect()
    torch.cuda.empty_cache()
    params = {'steps': 12}
    if args.engine == 'pixal3d':
        result = pipeline.run_pixal3d(image, camera_params={'camera_angle_x': 0.6981317, 'distance': 2.0, 'mesh_scale': 1.0},
            seed=args.seed, pipeline_type='1024_cascade', sparse_structure_sampler_params=params,
            shape_slat_sampler_params=params, generate_texture_slat=False)
    else:
        result = pipeline.run(image, seed=args.seed, pipeline_type='512',
            sparse_structure_sampler_params=params, shape_slat_sampler_params=params,
            generate_texture_slat=False, pbar=ProgressBar(5))
    mesh = result[0]
    geometry = trimesh.Trimesh(vertices=mesh.vertices.cpu().numpy(), faces=mesh.faces.cpu().numpy(), process=False)
    if not len(geometry.faces) or not len(geometry.vertices):
        raise RuntimeError('Empty mesh')
    output.parent.mkdir(parents=True, exist_ok=True)
    geometry.export(str(output), file_type='glb')
    receipt = {'engine': args.engine, 'vertices': len(geometry.vertices), 'faces': len(geometry.faces),
        'output': str(output), 'technicalInferencePassed': True, 'artisticApproval': False, 'textured': False}
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    main()
