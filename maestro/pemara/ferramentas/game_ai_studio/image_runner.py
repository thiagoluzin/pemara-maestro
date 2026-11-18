"""Explicit offline image generation for the Maestro backend."""
from argparse import ArgumentParser
from pathlib import Path
import json
import os
import subprocess
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODELS = Path('D:/PemaraRuntimes/maestro-game-ai/models')
ENGINES = {
    'flux2-klein': ('black-forest-labs--FLUX.2-klein-4B', 'Flux2KleinPipeline', 4, 1.0),
    'z-image-turbo': ('Tongyi-MAI--Z-Image-Turbo', 'ZImagePipeline', 9, 0.0),
    'z-image': ('Tongyi-MAI--Z-Image', 'ZImagePipeline', 50, 4.0),
}

def main():
    parser = ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    model, class_name, steps, guidance = ENGINES[spec['engine']]
    model_path = MODELS / model
    if not (model_path / 'maestro-weights-verified.json').is_file():
        raise RuntimeError('Pesos ainda não verificados.')
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path.insert(0, str(PROJECT / 'services/studio'))
    from gpu_lease import GpuLeaseRegistry
    lease = GpuLeaseRegistry(PROJECT / 'dados/studio/gpu_lease.json')
    lease.acquire(owner='maestro', operation='game_image', job_id=spec['jobId'])
    try:
        from game_gpu_admission import admit
        admit(20000)
        os.environ['HF_HUB_OFFLINE'] = '1'
        import torch
        import diffusers
        pipeline = getattr(diffusers, class_name).from_pretrained(str(model_path), torch_dtype=torch.bfloat16, local_files_only=True)
        pipeline.enable_model_cpu_offload()
        result = pipeline(prompt=spec['prompt'], width=spec['width'], height=spec['height'],
                          num_inference_steps=steps, guidance_scale=guidance,
                          generator=torch.Generator('cpu').manual_seed(spec['seed']))
        result.images[0].save(args.output)
    finally:
        lease.release(spec['jobId'])

if __name__ == '__main__':
    main()
