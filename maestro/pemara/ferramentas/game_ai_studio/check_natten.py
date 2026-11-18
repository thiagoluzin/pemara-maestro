"""Compare bounded-memory NAF attention against eager NATTEN, including edges."""
import json
from pathlib import Path
import torch
from natten import na2d
import importlib.util

def verify():
    spec = importlib.util.spec_from_file_location('naf_local_attention', 'D:/PemaraRuntimes/maestro-game-ai/torch_hub/valeoai_NAF_main/src/layers/local_attention.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    generator = torch.Generator(device='cuda').manual_seed(2718)
    results = []
    for dilation in (1, 2):
        q, k = [torch.randn(1, 20, 20, 2, 64, device='cuda', generator=generator) for _ in range(2)]
        v = torch.randn(1, 20, 20, 2, 256, device='cuda', generator=generator)
        options = dict(kernel_size=(9, 9), dilation=(dilation, dilation), stride=1, backend='flex-fna', scale=0.125)
        expected = torch.cat([na2d(q, k, part, torch_compile=False, **options) for part in v.split(64, -1)], -1)
        actual = module.neighborhood_attention(q, k, v, (9, 9), (dilation, dilation), 0.125)
        torch.testing.assert_close(actual, expected, rtol=0.00002, atol=0.00002)
        results.append({'dilation': dilation, 'maxAbsoluteError': float((actual-expected).abs().max())})
    Path('D:/PemaraRuntimes/maestro-game-ai/logs/natten-numerical-check.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('NATTEN_NUMERICAL_CHECK_OK', results, flush=True)
