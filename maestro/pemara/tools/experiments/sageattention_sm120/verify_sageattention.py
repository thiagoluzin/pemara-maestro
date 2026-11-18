from __future__ import annotations

import json
import time
import urllib.request

import torch
import torch.nn.functional as F
from sageattention import sageattn


def assert_comfy_idle() -> None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=3) as response:
            queue = json.load(response)
    except Exception as exc:
        raise SystemExit(f"Nao foi possivel confirmar a fila ComfyUI: {exc}") from exc
    running = len(queue.get("queue_running") or [])
    pending = len(queue.get("queue_pending") or [])
    if running or pending:
        raise SystemExit(
            f"ComfyUI deixou de estar ocioso (running={running}, pending={pending})."
        )


def timed(callable_, iterations: int = 8) -> tuple[torch.Tensor, float]:
    result = callable_()
    torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(iterations):
        result = callable_()
    torch.cuda.synchronize()
    return result, (time.perf_counter() - started) * 1000.0 / iterations


def main() -> None:
    assert_comfy_idle()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA indisponivel no ambiente isolado.")
    torch.manual_seed(20260815)
    device = torch.device("cuda:0")
    capability = torch.cuda.get_device_capability(device)
    if capability != (12, 0):
        raise SystemExit(f"Esperado SM120; detectado {capability}.")

    shape = (1, 16, 2048, 128)
    q = torch.randn(shape, device=device, dtype=torch.float16)
    k = torch.randn(shape, device=device, dtype=torch.float16)
    v = torch.randn(shape, device=device, dtype=torch.float16)

    sdpa_call = lambda: F.scaled_dot_product_attention(q, k, v, is_causal=False)
    sage_call = lambda: sageattn(q, k, v, tensor_layout="HND", is_causal=False)

    for _ in range(3):
        sdpa_call()
        sage_call()
    torch.cuda.synchronize()

    baseline, sdpa_ms = timed(sdpa_call)
    candidate, sage_ms = timed(sage_call)
    baseline_f = baseline.float()
    candidate_f = candidate.float()
    delta = candidate_f - baseline_f
    relative_l2 = float(delta.norm() / baseline_f.norm().clamp_min(1e-12))
    cosine = float(F.cosine_similarity(baseline_f.flatten(), candidate_f.flatten(), dim=0))
    report = {
        "device": torch.cuda.get_device_name(device),
        "compute_capability": list(capability),
        "torch": torch.__version__,
        "shape_hnd": list(shape),
        "finite": bool(torch.isfinite(candidate_f).all()),
        "max_abs_error": float(delta.abs().max()),
        "mean_abs_error": float(delta.abs().mean()),
        "relative_l2_error": relative_l2,
        "cosine_similarity": cosine,
        "sdpa_ms": sdpa_ms,
        "sageattention_ms": sage_ms,
        "kernel_speedup": sdpa_ms / sage_ms,
    }
    report["gate_pass"] = bool(
        report["finite"] and cosine >= 0.995 and relative_l2 <= 0.05
    )
    print(json.dumps(report, indent=2))
    if not report["gate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
