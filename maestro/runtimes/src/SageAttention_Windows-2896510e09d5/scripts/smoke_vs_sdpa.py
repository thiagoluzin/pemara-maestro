#!/usr/bin/env python3
"""Smoke / quality / speed comparison: sageattn vs torch SDPA.

Usage (with CUDA GPU + installed sageattention wheel):

    python scripts/smoke_vs_sdpa.py
    python scripts/smoke_vs_sdpa.py --quick
    python scripts/smoke_vs_sdpa.py --bench-only
    python scripts/smoke_vs_sdpa.py --causal-diag
    python scripts/smoke_vs_sdpa.py --dtype fp16

Exit code 0 if quality gates pass (non-causal and causal; SageAttention2++
INT8/FP8 is expected to stay very close to SDPA on both).

Note: run from a directory other than the repo root, or with the package
installed into site-packages — importing the unbuilt source tree will fail
(no compiled .pyd extensions).
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

import torch
import torch.nn.functional as F


def _require_env() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this smoke test.")
    try:
        from sageattention import sageattn  # noqa: F401
        from sageattention.core import SM89_ENABLED, SM80_ENABLED, SM90_ENABLED, TRITON_ENABLED
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            f"Cannot import sageattention ({exc}). Install the wheel into this Python first "
            "(and avoid importing the unbuilt source tree)."
        ) from exc
    # Stash for banner
    _require_env.flags = {
        "SM80": SM80_ENABLED,
        "SM89": SM89_ENABLED,
        "SM90": SM90_ENABLED,
        "TRITON": TRITON_ENABLED,
    }


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    return F.cosine_similarity(a.float().flatten(), b.float().flatten(), dim=0).item()


def max_abs(a: torch.Tensor, b: torch.Tensor) -> float:
    return (a.float() - b.float()).abs().max().item()


def mean_abs(a: torch.Tensor, b: torch.Tensor) -> float:
    return (a.float() - b.float()).abs().mean().item()


def bench(fn: Callable[[], torch.Tensor], warmup: int, iters: int) -> float:
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - t0) * 1000.0 / max(iters, 1)


@dataclass
class CaseResult:
    label: str
    shape: Tuple[int, ...]
    cos: float
    max_abs: float
    mean_abs: float
    finite: bool
    sa_ms: Optional[float]
    sdpa_ms: Optional[float]
    ok: bool
    is_causal: bool


def run_quality_cases(
    dtype: torch.dtype,
    seed: int,
    do_bench: bool,
    warmup: int,
    iters: int,
    cos_thr: float,
    cos_thr_causal: float,
) -> List[CaseResult]:
    from sageattention import sageattn

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    device = "cuda"

    # B, H, Lq, Lk, D, causal, label
    cases: Sequence[Tuple[int, int, int, int, int, bool, str]] = (
        (1, 8, 128, 128, 64, False, "B1 H8 L128 D64"),
        (1, 8, 128, 128, 128, False, "B1 H8 L128 D128"),
        (1, 8, 256, 256, 128, False, "B1 H8 L256 D128"),
        (1, 16, 512, 512, 128, False, "B1 H16 L512 D128"),
        (2, 8, 128, 128, 128, False, "batch=2 L128"),
        (1, 8, 200, 200, 128, False, "unaligned L200 (pad)"),
        (1, 8, 256, 256, 64, False, "B1 H8 L256 D64"),
        (1, 8, 256, 256, 128, True, "causal L256"),
        (1, 8, 512, 512, 128, True, "causal L512"),
        (2, 16, 512, 512, 128, True, "causal B2 H16 L512"),
    )

    results: List[CaseResult] = []
    for B, H, Lq, Lk, D, causal, label in cases:
        q = torch.randn(B, H, Lq, D, device=device, dtype=dtype)
        k = torch.randn(B, H, Lk, D, device=device, dtype=dtype)
        v = torch.randn(B, H, Lk, D, device=device, dtype=dtype)

        def run_sa(q=q, k=k, v=v, causal=causal):
            return sageattn(q, k, v, tensor_layout="HND", is_causal=causal)

        def run_sdpa(q=q, k=k, v=v, causal=causal):
            return F.scaled_dot_product_attention(q, k, v, is_causal=causal)

        with torch.no_grad():
            o_sa = run_sa()
            o_sd = run_sdpa()
            torch.cuda.synchronize()

        c = cosine(o_sa, o_sd)
        ma = max_abs(o_sa, o_sd)
        me = mean_abs(o_sa, o_sd)
        fin = bool(torch.isfinite(o_sa).all().item())
        shape_ok = tuple(o_sa.shape) == tuple(o_sd.shape)

        sa_ms = sdpa_ms = None
        if do_bench:
            sa_ms = bench(run_sa, warmup=warmup, iters=iters)
            sdpa_ms = bench(run_sdpa, warmup=warmup, iters=iters)

        thr = cos_thr_causal if causal else cos_thr
        ok = fin and shape_ok and c >= thr

        results.append(
            CaseResult(
                label=label,
                shape=tuple(o_sa.shape),
                cos=c,
                max_abs=ma,
                mean_abs=me,
                finite=fin,
                sa_ms=sa_ms,
                sdpa_ms=sdpa_ms,
                ok=ok,
                is_causal=causal,
            )
        )
    return results


def run_bench_large(dtype: torch.dtype, warmup: int, iters: int) -> None:
    from sageattention import sageattn

    device = "cuda"
    shapes = (
        (1, 24, 1024, 128),
        (1, 24, 2048, 128),
        (1, 32, 4096, 128),
        (2, 24, 1024, 128),
    )
    print()
    print("=== Larger-shape throughput (ms/iter) ===")
    print(f"{'shape':<28} {'SA_ms':>10} {'SDPA_ms':>10} {'speedup':>9} {'cosine':>9}")
    print("-" * 72)
    for B, H, L, D in shapes:
        q = torch.randn(B, H, L, D, device=device, dtype=dtype)
        k = torch.randn(B, H, L, D, device=device, dtype=dtype)
        v = torch.randn(B, H, L, D, device=device, dtype=dtype)

        def run_sa(q=q, k=k, v=v):
            return sageattn(q, k, v, tensor_layout="HND", is_causal=False)

        def run_sdpa(q=q, k=k, v=v):
            return F.scaled_dot_product_attention(q, k, v, is_causal=False)

        sa_ms = bench(run_sa, warmup=warmup, iters=iters)
        sdpa_ms = bench(run_sdpa, warmup=warmup, iters=iters)
        with torch.no_grad():
            c = cosine(run_sa(), run_sdpa())
        sp = sdpa_ms / sa_ms if sa_ms > 0 else float("nan")
        label = f"B{B} H{H} L{L} D{D}"
        print(f"{label:<28} {sa_ms:10.2f} {sdpa_ms:10.2f} {sp:8.2f}x {c:9.4f}")


def run_causal_diag(dtype: torch.dtype, seed: int) -> None:
    """Confirm causal mask is active and quality stays close to SDPA (INT8/FP8 path)."""
    from sageattention import sageattn

    torch.manual_seed(seed)
    device = "cuda"
    print()
    print("=== Causal diagnostic ===")
    print(
        f"{'L':>5} {'cos SAc/SDPAc':>14} {'cos SAnc/SDPAnc':>16} "
        f"{'cos SAc/SAnc':>13} {'cos SDPAc/n':>12}"
    )
    print("-" * 72)
    for L in (64, 128, 256, 512):
        q = torch.randn(1, 8, L, 128, device=device, dtype=dtype)
        k = torch.randn(1, 8, L, 128, device=device, dtype=dtype)
        v = torch.randn(1, 8, L, 128, device=device, dtype=dtype)
        with torch.no_grad():
            o_sa_c = sageattn(q, k, v, is_causal=True)
            o_sa_n = sageattn(q, k, v, is_causal=False)
            o_sd_c = F.scaled_dot_product_attention(q, k, v, is_causal=True)
            o_sd_n = F.scaled_dot_product_attention(q, k, v, is_causal=False)
        print(
            f"{L:5d} {cosine(o_sa_c, o_sd_c):14.4f} {cosine(o_sa_n, o_sd_n):16.4f} "
            f"{cosine(o_sa_c, o_sa_n):13.4f} {cosine(o_sd_c, o_sd_n):12.4f}"
        )

    print()
    print("Interpretation:")
    print("  • Non-causal SA≈SDPA (cosine ~0.999) => quant + CUDA kernels healthy on Windows.")
    print("  • Causal SA ≈ causal SDPA (also ~0.999) => INT8/FP8 SA2++ causal is high-fidelity.")
    print("  • SA causal ≠ SA non-causal => is_causal mask is engaged (not a dead flag).")
    print("  • Unlike SageAttention3 FP4, SA2++ does not show a large causal quality cliff vs SDPA.")


def print_quality_table(results: List[CaseResult]) -> bool:
    print()
    print("=== Quality vs SDPA ===")
    hdr = (
        f"{'case':<28} {'shape':<22} {'cosine':>9} {'max_abs':>10} {'mean_abs':>10} "
        f"{'sa_ms':>9} {'sdpa_ms':>9} {'spd':>7} {'ok'}"
    )
    print(hdr)
    print("-" * len(hdr))
    all_ok = True
    for r in results:
        sa = f"{r.sa_ms:9.2f}" if r.sa_ms is not None else f"{'n/a':>9}"
        sd = f"{r.sdpa_ms:9.2f}" if r.sdpa_ms is not None else f"{'n/a':>9}"
        if r.sa_ms and r.sdpa_ms and r.sa_ms > 0:
            sp = f"{r.sdpa_ms / r.sa_ms:6.2f}x"
        else:
            sp = f"{'n/a':>7}"
        status = "PASS" if r.ok else "FAIL"
        if not r.ok:
            all_ok = False
        print(
            f"{r.label:<28} {str(r.shape):<22} {r.cos:9.4f} {r.max_abs:10.4f} "
            f"{r.mean_abs:10.4f} {sa} {sd} {sp} {status}"
        )
    return all_ok


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare sageattn vs torch SDPA on CUDA.")
    parser.add_argument("--quick", action="store_true", help="Fewer bench iters / skip large bench.")
    parser.add_argument("--bench-only", action="store_true", help="Only large-shape throughput.")
    parser.add_argument("--no-bench", action="store_true", help="Skip micro-benchmarks in quality grid.")
    parser.add_argument("--causal-diag", action="store_true", help="Extra causal vs non-causal diagnostics.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--dtype", choices=("bf16", "fp16"), default="bf16")
    parser.add_argument(
        "--cos-thr",
        type=float,
        default=0.99,
        help="Non-causal cosine gate (SA2++ is typically ~0.999).",
    )
    parser.add_argument(
        "--cos-thr-causal",
        type=float,
        default=0.99,
        help="Causal cosine gate (SA2++ causal stays near SDPA).",
    )
    args = parser.parse_args(argv)

    _require_env()
    dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float16
    warmup = 3 if args.quick else 10
    iters = 10 if args.quick else 50
    flags = getattr(_require_env, "flags", {})

    print("sageattention vs SDPA smoke")
    print(f"  GPU   : {torch.cuda.get_device_name(0)}  cc={torch.cuda.get_device_capability(0)}")
    print(f"  torch : {torch.__version__}  cuda={torch.version.cuda}")
    print(f"  dtype : {dtype}")
    print(
        f"  ext   : SM80={flags.get('SM80')} SM89={flags.get('SM89')} "
        f"SM90={flags.get('SM90')} TRITON={flags.get('TRITON')}"
    )

    if args.bench_only:
        run_bench_large(dtype, warmup=warmup, iters=iters)
        return 0

    do_bench = not args.no_bench
    results = run_quality_cases(
        dtype=dtype,
        seed=args.seed,
        do_bench=do_bench,
        warmup=warmup,
        iters=iters,
        cos_thr=args.cos_thr,
        cos_thr_causal=args.cos_thr_causal,
    )
    ok = print_quality_table(results)

    if not args.quick:
        run_bench_large(dtype, warmup=warmup, iters=iters)

    if args.causal_diag or not args.quick:
        run_causal_diag(dtype, seed=args.seed)

    print()
    if ok:
        print("OVERALL: PASS (quality gates)")
        return 0
    print("OVERALL: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
