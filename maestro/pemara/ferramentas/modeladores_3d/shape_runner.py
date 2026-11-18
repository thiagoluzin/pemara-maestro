"""Isolated geometry worker; generation is invoked only by the Comfy node."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path('D:/PemaraRuntimes/maestro-game-ai')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--engine', required=True, choices=['hunyuan3d_2_1', 'triposg'])
    p.add_argument('--image')
    p.add_argument('--output')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--preflight', action='store_true')
    args = p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import torch
    import numpy as np
    from PIL import Image
    if args.engine == 'triposg':
        sys.path.insert(0, str(ROOT / 'apps/TripoSG'))
        from triposg.pipelines.pipeline_triposg import TripoSGPipeline
        model = ROOT / 'models/TripoSG'
        pipe = TripoSGPipeline.from_pretrained(str(model), local_files_only=True, torch_dtype=torch.float16)
    else:
        sys.path.insert(0, str(ROOT / 'apps/Hunyuan3D-2.1/hy3dshape'))
        from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
        pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            str(ROOT / 'models/Hunyuan3D-2.1'), device='cpu', dtype=torch.float16)
    if args.preflight:
        print(json.dumps({'engine': args.engine, 'cpuModelLoad': True, 'generationTested': False}))
        return
    if not args.image or not args.output:
        p.error('--image and --output are required for generation')
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    image = Image.open(args.image).convert('RGBA')
    if image.getchannel('A').getextrema() == (255, 255):
        os.environ['U2NET_HOME'] = 'D:/PemaraAI/model-caches/u2net'
        if not Path(os.environ['U2NET_HOME'], 'u2net.onnx').is_file():
            raise FileNotFoundError('Local background-removal model is missing')
        from rembg import remove, new_session
        image = remove(image, session=new_session('u2net', providers=['CPUExecutionProvider']))
    image.save(output.with_name(output.stem + '_foreground.png'))
    if args.engine == 'triposg':
        bbox = image.getchannel('A').getbbox()
        if bbox is None:
            raise ValueError('No foreground detected')
        image = image.crop(bbox)
        side = int(max(image.size) * 1.2)
        canvas = Image.new('RGBA', (side, side))
        canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
        image = canvas
        background = Image.new('RGBA', image.size, 'white')
        image = Image.alpha_composite(background, image).convert('RGB')
        pipe.to('cuda')
        result = pipe(image=image, generator=torch.Generator('cuda').manual_seed(args.seed),
                      use_flash_decoder=False, num_inference_steps=50)
        mesh = result.meshes[0]
    else:
        pipe.to('cuda')
        mesh = pipe(image=image, num_inference_steps=50, octree_resolution=256,
                    generator=torch.Generator('cuda').manual_seed(args.seed))[0]
    if not len(mesh.vertices) or not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise RuntimeError('Invalid or empty geometry')
    output.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(output), file_type='glb')
    receipt = {'engine': args.engine, 'vertices': len(mesh.vertices), 'faces': len(mesh.faces),
               'output': str(output), 'technicalInferencePassed': True,
               'artisticApproval': False, 'printReady': False, 'textured': False}
    output.with_suffix('.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    main()
