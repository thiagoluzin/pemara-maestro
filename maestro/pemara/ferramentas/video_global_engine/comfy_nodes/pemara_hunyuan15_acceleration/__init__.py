"""Hunyuan 1.5 only: per-model Sage2, safe masks, static loading and measured execution."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import time
import types

import torch
import comfy.patcher_extension as pe
from comfy.ldm.modules.attention import attention_pytorch
import folder_paths


def requires_dense(mask, low_precision_attention=True):
    # The installed CUDA Sage2 kernel does not implement attn_mask.
    # Never pass it through **kwargs where it would be silently ignored.
    return mask is not None or low_precision_attention is False


class PemaraHunyuan15SafeAcceleration:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("MODEL",),
            "sage_mode": (["fp8_fp32_accum", "fp8pp"],),
            "disable_dynamic_vram": ("BOOLEAN", {"default": True}),
            "metrics_prefix": ("STRING", {"default": "hunyuan15/performance"}),
        }}

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "patch"
    CATEGORY = "PEMARA/Hunyuan15"
    DESCRIPTION = "Hunyuan15-specific Sage2 CUDA. Masked/precision-sensitive calls remain explicitly dense. No global patches."

    def patch(self, model, sage_mode, disable_dynamic_vram, metrics_prefix):
        config = model.model.model_config.__class__.__name__
        if config != "HunyuanVideo15":
            raise ValueError(f"This patch requires HunyuanVideo15, received {config}")
        from sageattention import sageattn_qk_int8_pv_fp8_cuda
        output_root = Path(folder_paths.get_output_directory()).resolve()
        receipt = (output_root / (metrics_prefix + ".performance.json")).resolve()
        if not receipt.is_relative_to(output_root):
            raise ValueError("metrics_prefix must stay inside the ComfyUI output directory")
        m = model.clone(disable_dynamic=disable_dynamic_vram)
        # AIMDO's lazy Linear state loader keeps the checkpoint tensor dtype,
        # even for a non-dynamic clone explicitly requested as FP8. Honor the
        # dtype stored by the constructor, locally, before sizing/loading it.
        # No checkpoint or global Linear class is modified.
        from comfy.ops import fp8_ops
        materialized_fp8 = 0
        for module in m.model.diffusion_model.modules():
            if (isinstance(module, fp8_ops.Linear)
                    and getattr(module, "weight_comfy_model_dtype", None) == torch.float8_e4m3fn
                    and module.weight.dtype != torch.float8_e4m3fn):
                module.weight = torch.nn.Parameter(
                    module.weight.to(dtype=torch.float8_e4m3fn), requires_grad=False)
                materialized_fp8 += 1
        if materialized_fp8:
            m.size = 0
            logging.info("[Hunyuan15Accel] materialized %d explicitly selected FP8 Linear weights; model bytes=%d",
                         materialized_fp8, m.model_size())
        stats = {}
        seen = set()

        def reset():
            stats.clear()
            stats.update(version=1, engine="hunyuan_video_15", sage_mode=sage_mode,
                         dynamic_vram_disabled=disable_dynamic_vram,
                         sage_attention_calls=0, dense_mask_calls=0,
                         dense_precision_calls=0, full_denoiser_calls=[],
                         denoiser_wrapper_calls=[], cached_denoiser_calls=0, steps=[], status="running",
                         fp8_linear_calls=0, fp8_linear_modules=0)
            seen.clear()

        @torch.compiler.disable()
        def override(func, q, k, v, heads, mask=None, attn_precision=None,
                     skip_reshape=False, skip_output_reshape=False, **kwargs):
            dense = requires_dense(mask, kwargs.get("low_precision_attention", True))
            if dense:
                reason = "dense_mask_calls" if mask is not None else "dense_precision_calls"
                stats[reason] = stats.get(reason, 0) + 1
                if reason not in seen:
                    seen.add(reason)
                    logging.info("[Hunyuan15Accel] preserving %s through PyTorch attention", reason)
                return attention_pytorch.__wrapped__(
                    q, k, v, heads, mask=mask, attn_precision=attn_precision,
                    skip_reshape=skip_reshape, skip_output_reshape=skip_output_reshape, **kwargs)
            original_dtype = v.dtype
            if q.dtype not in (torch.float16, torch.bfloat16):
                raise TypeError(f"Sage2 candidate requires fp16/bf16 attention, received {q.dtype}")
            if skip_reshape:
                b, _, _, dim_head = q.shape
                layout = "HND"
                seq_dim = 2
            else:
                b, _, inner = q.shape
                dim_head = inner // heads
                q, k, v = (x.reshape(b, -1, heads, dim_head) for x in (q, k, v))
                layout = "NHD"
                seq_dim = 1
            if any((x.shape[seq_dim] - 1) * x.stride(seq_dim) >= 2**31 for x in (q, k, v)):
                q, k, v = (x.contiguous() for x in (q, k, v))
            signature = (tuple(q.shape), str(q.dtype), layout)
            if signature not in seen:
                seen.add(signature)
                logging.info("[Hunyuan15Accel] Sage2 CUDA active: shape=%s mode=%s layout=%s mask=None", tuple(q.shape), sage_mode, layout)
            out = sageattn_qk_int8_pv_fp8_cuda(
                q, k, v, tensor_layout=layout, is_causal=False,
                pv_accum_dtype="fp32+fp32" if sage_mode == "fp8_fp32_accum" else "fp32+fp16",
                sm_scale=kwargs.get("scale"), smooth_k=False).to(original_dtype)
            stats["sage_attention_calls"] = stats.get("sage_attention_calls", 0) + 1
            if layout == "HND":
                return out if skip_output_reshape else out.transpose(1, 2).reshape(b, -1, heads * dim_head)
            return out.transpose(1, 2) if skip_output_reshape else out.reshape(b, -1, heads * dim_head)

        m.model_options["transformer_options"]["optimized_attention_override"] = override

        def measured_denoiser(executor, *args, **kwargs):
            torch.cuda.synchronize()
            start = time.perf_counter()
            attention_before = stats["sage_attention_calls"] + stats["dense_mask_calls"] + stats["dense_precision_calls"]
            result = executor(*args, **kwargs)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            stats["denoiser_wrapper_calls"].append(elapsed)
            attention_after = stats["sage_attention_calls"] + stats["dense_mask_calls"] + stats["dense_precision_calls"]
            if attention_after == attention_before:
                stats["cached_denoiser_calls"] += 1
                return result
            stats["full_denoiser_calls"].append(elapsed)
            n = len(stats["full_denoiser_calls"])
            if n <= 4 or n % 5 == 0:
                logging.info("[Hunyuan15Accel] full denoiser call %d: %.3fs; Sage calls=%d, masked dense=%d", n, elapsed, stats["sage_attention_calls"], stats["dense_mask_calls"])
            return result

        def sampling(executor, *args, **kwargs):
            reset()
            # Scope the probe to this model and this sampling run. Native fp8_ops
            # normally catches GEMM failures and silently falls back to FP16;
            # an explicitly selected FP8 speed trial must expose that failure.
            from comfy.ops import fp8_linear
            changed_linears = []
            diffusion_model = m.model.diffusion_model
            fp8_modules = [module for module in diffusion_model.modules()
                           if isinstance(module, torch.nn.Linear)
                           and module.weight.dtype == torch.float8_e4m3fn]
            stats["fp8_linear_modules"] = len(fp8_modules)
            if not fp8_modules and any(parameter.dtype == torch.float8_e4m3fn
                                       for parameter in diffusion_model.parameters()):
                classes = sorted({f"{type(module).__module__}.{type(module).__qualname__}:{module.weight.dtype}"
                                  for module in diffusion_model.modules() if isinstance(module, torch.nn.Linear)})
                raise RuntimeError(f"FP8 weights found without eligible FP8 Linear weights; speed trial blocked: {classes}")

            def strict_fp8_forward(module, value):
                result = fp8_linear(module, value)
                if result is None:
                    raise RuntimeError("Selected FP8 GEMM cannot execute; implicit FP16 fallback blocked")
                stats["fp8_linear_calls"] += 1
                return result

            for module in fp8_modules:
                had_override = "forward" in module.__dict__
                previous_forward = module.__dict__.get("forward")
                changed_linears.append((module, had_override, previous_forward))
                module.forward = types.MethodType(strict_fp8_forward, module)
            logging.info("[Hunyuan15Accel] FP8 GEMM probe: %d native fp8 Linear modules; fallback forbidden for these modules", len(fp8_modules))
            torch.cuda.reset_peak_memory_stats()
            start = time.perf_counter()
            stats["started_at_unix"] = time.time()
            call_args = list(args)
            original_callback = call_args[5] if len(call_args) > 5 else kwargs.get("callback")
            previous = [start, 0]

            def step_callback(step, x0, x, total_steps):
                torch.cuda.synchronize()
                now = time.perf_counter()
                count = len(stats["full_denoiser_calls"])
                row = {"step": int(step) + 1, "total_steps": int(total_steps),
                       "seconds": now - previous[0], "elapsed_sampling_seconds": now - start,
                       "full_denoiser_calls": count - previous[1],
                       "sage_attention_calls_total": stats["sage_attention_calls"],
                       "dense_mask_calls_total": stats["dense_mask_calls"],
                       "fp8_linear_calls_total": stats["fp8_linear_calls"],
                       "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                       "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
                previous[:] = [now, count]
                stats["steps"].append(row)
                logging.info("[Hunyuan15Accel] STEP %d/%d: %.3fs, full calls=%d, elapsed=%.3fs", row["step"], row["total_steps"], row["seconds"], row["full_denoiser_calls"], row["elapsed_sampling_seconds"])
                receipt.parent.mkdir(parents=True, exist_ok=True)
                temporary = receipt.with_suffix(receipt.suffix + ".tmp")
                temporary.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                temporary.replace(receipt)
                if original_callback is not None:
                    return original_callback(step, x0, x, total_steps)

            if len(call_args) > 5:
                call_args[5] = step_callback
            else:
                kwargs["callback"] = step_callback
            try:
                result = executor(*call_args, **kwargs)
                stats["status"] = "completed"
                return result
            except BaseException as exc:
                stats["status"] = "interrupted_or_error"
                stats["exception_type"] = type(exc).__name__
                raise
            finally:
                for module, had_override, previous_forward in changed_linears:
                    if had_override:
                        module.forward = previous_forward
                    else:
                        delattr(module, "forward")
                stats["sampling_wall_seconds"] = time.perf_counter() - start
                stats["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
                stats["peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
                stats["finished_at_unix"] = time.time()
                stats["full_denoiser_call_count"] = len(stats["full_denoiser_calls"])
                stats["note"] = "Includes GPU synchronization; first full calls may include compilation. Cache skips are not full calls."
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                logging.info("[Hunyuan15Accel] sampling %s: %.3fs, %d full calls, receipt=%s", stats["status"], stats["sampling_wall_seconds"], stats["full_denoiser_call_count"], receipt)

        m.add_wrapper_with_key(pe.WrappersMP.DIFFUSION_MODEL, "pemara_hunyuan15_measure", measured_denoiser)
        m.add_wrapper_with_key(pe.WrappersMP.OUTER_SAMPLE, "pemara_hunyuan15_measure", sampling)
        logging.info("[Hunyuan15Accel] configured: Sage2=%s non_dynamic=%s config=%s", sage_mode, disable_dynamic_vram, config)
        return (m,)


NODE_CLASS_MAPPINGS = {"PemaraHunyuan15SafeAcceleration": PemaraHunyuan15SafeAcceleration}
NODE_DISPLAY_NAME_MAPPINGS = {"PemaraHunyuan15SafeAcceleration": "Hunyuan 1.5 Safe Sage2 + Runtime Metrics (PEMARA)"}
