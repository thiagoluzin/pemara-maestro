"""Installation smoke test. Comfy service preflight is performed separately via MCP."""
from pathlib import Path
import json
import os
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'services/studio'))
from gpu_lease import GpuLeaseRegistry
from image_runner import ENGINES, MODELS

engine = sys.argv[1] if len(sys.argv) > 1 else 'flux2-klein'
model, class_name, steps, guidance = ENGINES[engine]
root = Path('D:/PemaraRuntimes/maestro-game-ai/logs') / ('smoke-' + engine + '-' + uuid.uuid4().hex[:8])
root.mkdir()
lease = GpuLeaseRegistry(HERE.parents[1] / 'dados/studio/gpu_lease.json')
job_id = 'game-install-' + uuid.uuid4().hex
lease.acquire(owner='maestro-install', operation='image_runtime_smoke', job_id=job_id)
try:
    os.environ['HF_HUB_OFFLINE'] = '1'
    import torch
    import diffusers
    start = time.time()
    pipe = getattr(diffusers, class_name).from_pretrained(str(MODELS / model), torch_dtype=torch.bfloat16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    output = pipe(prompt='A single plain gray ceramic cube on a white background, product photograph.',
                  width=512, height=512, num_inference_steps=steps, guidance_scale=guidance,
                  generator=torch.Generator('cpu').manual_seed(42)).images[0]
    output.save(root / 'sample.png')
    result = {'engine': engine, 'width': output.width, 'height': output.height, 'elapsedSeconds': round(time.time()-start, 2),
              'output': str(root / 'sample.png'), 'technicalInferencePassed': True, 'artisticApproval': False}
    (root / 'receipt.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (MODELS / model / 'maestro-runtime-verified.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
finally:
    lease.release(job_id)
