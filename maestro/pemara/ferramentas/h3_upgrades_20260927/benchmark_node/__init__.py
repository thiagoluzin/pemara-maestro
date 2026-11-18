"""Local synthetic VAE comparison, invoked only through a ComfyUI workflow."""
import json
import math
import time
from pathlib import Path

import torch
import folder_paths


class PemaraH3VAECompare:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "baseline": ("VAE",), "candidate": ("VAE",),
            "width": ("INT", {"default": 1088, "min": 32, "max": 1344}),
            "height": ("INT", {"default": 608, "min": 32, "max": 1344}),
            "frames": ("INT", {"default": 73, "min": 22, "max": 141}),
        }}

    RETURN_TYPES = ()
    FUNCTION = "compare"
    OUTPUT_NODE = True
    CATEGORY = "PEMARA/H3 validation"

    def compare(self, baseline, candidate, width, height, frames):
        x = torch.linspace(0, 1, width)[None, None, :, None]
        y = torch.linspace(0, 1, height)[None, :, None, None]
        t = torch.linspace(0, 1, frames)[:, None, None, None]
        shape = (frames, height, width, 1)
        source = torch.cat([
            (0.5 + 0.4 * torch.sin(12 * x + 2 * t)).expand(shape),
            (0.5 + 0.4 * torch.cos(10 * y - 3 * t)).expand(shape),
            (0.5 + 0.4 * torch.sin(8 * (x + y) + t)).expand(shape),
        ], dim=-1).contiguous()
        rows, outputs = [], []
        for name, vae in (("fp16", baseline), ("int8_convrot", candidate)):
            timings = []
            for run in range(2):
                torch.cuda.synchronize()
                start = time.perf_counter()
                latent = vae.encode(source)
                torch.cuda.synchronize()
                encoded = time.perf_counter()
                decoded = vae.decode(latent)
                torch.cuda.synchronize()
                finished = time.perf_counter()
                timings.append({"encode_seconds": encoded - start,
                                "decode_seconds": finished - encoded,
                                "roundtrip_seconds": finished - start})
            output = decoded.float().cpu()
            rows.append({"vae": name, "runs": timings, "finite": bool(torch.isfinite(output).all()),
                         "output_shape": list(output.shape)})
            outputs.append(output)
            del decoded, latent
        mse = float(torch.mean((outputs[0] - outputs[1]) ** 2))
        result = {"input": "synthetic animated color gradients", "width": width, "height": height,
                  "frames": frames, "results": rows,
                  "candidate_vs_baseline_psnr_db": -10 * math.log10(max(mse, 1e-15)),
                  "max_abs_difference": float(torch.max(torch.abs(outputs[0] - outputs[1]))),
                  "artistic_approval": False}
        path = Path(folder_paths.get_output_directory()) / "PEMARA_H3_UPGRADES_20260927" / "vae_comparison.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return {"ui": {"text": [str(path), json.dumps(result)]}}


NODE_CLASS_MAPPINGS = {"PemaraH3VAECompare": PemaraH3VAECompare}
NODE_DISPLAY_NAME_MAPPINGS = {"PemaraH3VAECompare": "PEMARA H3 VAE Compare (synthetic)"}
