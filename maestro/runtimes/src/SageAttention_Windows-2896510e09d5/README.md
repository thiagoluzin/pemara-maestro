# SageAttention for Windows

**中文版文档：[README_zh.md](README_zh.md)**（English below）

Windows-oriented build of **SageAttention 2.x / 2++** (INT8 / FP8 attention kernels for Ampere, Ada, Hopper, and **Blackwell**).

This repository is based on the official [thu-ml/SageAttention](https://github.com/thu-ml/SageAttention) sources, with **MSVC / Windows build fixes** so you can produce a working wheel on native Windows (no WSL required). SageAttention3 Blackwell sources are **not** included here; use a separate SA3 tree (e.g. [Sageattention3_Blackwell_Windows](https://github.com/sjh00/Sageattention3_Blackwell_Windows)) if you need FP4.

> Upstream: [thu-ml/SageAttention](https://github.com/thu-ml/SageAttention)  
> Papers: [SageAttention](https://arxiv.org/abs/2410.02367) · [SageAttention2](https://arxiv.org/abs/2411.10958) · [SageAttention2++](https://arxiv.org/pdf/2505.21136)  
> Chinese docs: [README_zh.md](README_zh.md)

---

## Why this fork exists

Official SageAttention is Linux-first. On Windows + MSVC people often get:

1. **Compile failures** — GCC-only flags (`-fopenmp`, `-lgomp`), wrong C++ standard for modern PyTorch headers, path handling for `nvcc`.
2. **Fragile builds** — half-precision flag conflicts (`D9025`), ABI mix-ups when switching Python versions, missing MSVC env (`DISTUTILS_USE_SDK`).
3. **Runtime / import issues** — wheel built against a different PyTorch ABI; source-tree `import` without `.pyd` extensions; hard Triton dependency even when only CUDA kernels are needed (e.g. RTX 50 / `sm_120`).

This tree applies practical Windows fixes (see [Windows fixes](#windows-fixes)), verified on:

| Item | Example working setup |
|------|------------------------|
| OS | Windows 11 |
| GPU | RTX 50-series (compute capability 12.0) |
| Python | 3.13 (uv venv) |
| PyTorch | 2.13 + CUDA 13.2 |
| CUDA Toolkit | 13.2 |
| MSVC | **Visual Studio 2026** Build Tools (MSVC 14.5x; path may show as `...\18\BuildTools`) |
| App | ComfyUI + KJNodes `PatchSageAttention`, or any PyTorch script |

---

## Features (upstream SageAttention 2.2)

- Optimized CUDA kernels for **Ampere, Ada, Hopper, and Blackwell** (sm80 / sm89 / sm90 / sm100–sm121).
- INT8 quantization and smoothing for \(QK^\top\) (per-warp / per-thread granularities).
- FP8 quantization for \(PV\), with FP16 / two-level accumulators (**SageAttention2++**: `pv_accum_dtype="fp32+fp16"`).
- Auto API `sageattn` selects a backend by GPU architecture.
- Optional **Triton** backends (varlen / sm86 / per-thread quant); **not required** for the default Blackwell (`sm_120`) CUDA path.

---

## Requirements

### Hardware

| Arch | Examples | Default kernel path |
|------|----------|---------------------|
| sm80 | RTX 3090, A100 | CUDA FP16 PV (`_qattn_sm80`) |
| sm86 | RTX 3080 Ti class | Triton (needs `triton-windows`) |
| sm89 | RTX 4090, L40 | CUDA FP8 PV (`_qattn_sm89`) |
| sm90 | H100, H800, H20 | CUDA FP8 Hopper (`_qattn_sm90`) |
| sm100 / sm120 / sm121 | B100 / **RTX 50** | CUDA FP8 via sm89 kernels built for `sm_XXXa` |

### Software

- **Python** 3.10+ (3.12 / **3.13** recommended; **build ABI must match** the runtime that loads the wheel)
- **PyTorch** with CUDA (for Blackwell / SA2++: torch with CUDA **12.8+**, ideally **13.x**)
- **CUDA Toolkit** with `nvcc`:
  - `>= 12.8` for Blackwell (`sm_100` / `sm_120` / `sm_121`) or SageAttention2++
  - `>= 12.4` for Ada FP8 (`sm_89`)
  - `>= 12.3` for Hopper FP8 (`sm_90`)
  - `>= 12.0` for Ampere (`sm_80`)
- **Visual Studio 2026** Build Tools with **Desktop development with C++**  
  (`build_wheel.bat` also detects VS 2022 if present; **2026 is the primary verified host**)
- **ninja**, **packaging**, **wheel**, **build** — installed by `build_wheel.bat` via **`uv pip`** (falls back to `python -m pip` only if `uv` is missing)
- Optional: **[uv](https://github.com/astral-sh/uv)** for Python envs and package installs (recommended)
- Optional: **[triton-windows](https://github.com/triton-lang/triton-windows)** for Triton APIs (`sageattn_varlen`, sm86 path, `qk_quant_gran="per_thread"`)

---

## Quick start (build wheel)

1. Create a CUDA-enabled env (example with uv):

```bat
uv venv .venv --python 3.13
uv pip install --python .venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cu132
```

2. Open a normal `cmd` window in this folder (the script loads MSVC itself):

```bat
build_wheel.bat
```

`build_wheel.bat` prefers `.venv\Scripts\python.exe` when present.

Useful options:

```bat
rem Clean previous artifacts (recommended after switching Python ABI)
build_wheel.bat --clean

rem Explicit Python (uv venv / ComfyUI embed)
build_wheel.bat --python ".venv\Scripts\python.exe"

rem ComfyUI portable Python
build_wheel.bat --python "D:\ComfyUI\python_embeded\python.exe"

rem Point at a specific CUDA Toolkit
build_wheel.bat --cuda "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2"

rem Parallel compile jobs (default 2; use 1 if the machine OOMs)
build_wheel.bat --jobs 1

rem Force target arch list (optional; default: detect local GPU)
build_wheel.bat --arch "12.0"
```

On success, wheels appear under `dist\`:

```text
dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

Full compiler log: `build.log`. The script also scans for hard failures and noisy warning classes (`D9025`, etc.).

### Manual build (advanced)

```bat
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set DISTUTILS_USE_SDK=1
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2
set PATH=%CUDA_HOME%\bin;%PATH%

rem Prefer uv pip (uv venvs do not ship the pip module by default)
uv pip install --python .venv\Scripts\python.exe -U setuptools wheel ninja packaging build
.venv\Scripts\python.exe -m build --wheel --no-isolation
```

---

## Install the wheel

Match the **same Python** you used to build (ABI tag must match, e.g. `cp313`):

```bat
rem Recommended with uv
uv pip install --python .venv\Scripts\python.exe --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl

rem Classic pip (only if pip is available)
python -m pip install --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

ComfyUI portable example:

```bat
uv pip install --python "D:\ComfyUI\python_embeded\python.exe" --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

Then **restart ComfyUI** (or your app).

> **Import tip:** do not `import sageattention` from the source tree root without installing the wheel — the local package folder has no compiled `.pyd` files. Import from the installed environment (or another working directory).

### Smoke test

Minimal import check:

```bat
python -c "import torch; from sageattention import sageattn; q=torch.randn(1,8,128,64,device='cuda',dtype=torch.float16); print(sageattn(q,q,q).shape)"
```

Compare against torch SDPA (quality + larger-shape speed + causal diagnostics):

```bat
python scripts/smoke_vs_sdpa.py
python scripts/smoke_vs_sdpa.py --quick
python scripts/smoke_vs_sdpa.py --dtype fp16
python scripts/smoke_vs_sdpa.py --causal-diag
```

Run with the **installed** wheel (not an unbuilt source-tree import). Options: `--bench-only`, `--no-bench`, `--cos-thr`, `--seed`.

#### Verified results (example host)

Environment: Windows 11 · RTX 50-series (`sm_120`) · Python 3.13 · PyTorch 2.13 + CUDA 13.2 · this fork’s `cp313` wheel · `SM89=True`, Triton not required.

| Check | Result |
|-------|--------|
| Quality grid (bf16 / fp16) | All cases **PASS** — cosine vs SDPA **~0.9993–0.9995** (non-causal and causal) |
| Shape / finite | Output shape matches SDPA; all finite |
| Unaligned `L=200` | PASS (internal pad path) |
| Causal mask | Causal SA ≈ causal SDPA (~0.999); causal ≠ non-causal ⇒ mask is active |
| Large shapes (bf16, ms/iter) | e.g. `B1 H24 L2048 D128` ~**4.3×** vs SDPA; `B1 H32 L4096 D128` ~**5.7×**; cosine still ~0.999 |

Notes:

- SageAttention2++ uses INT8/FP8 quantization — **not bit-exact** vs SDPA, but cosine stays near **0.999** (much tighter than SageAttention3 FP4, especially on causal).
- Small shapes can be latency-bound (SA microbench may look slower than SDPA); speedup shows up as sequence length / heads grow.
- Exit code `0` means quality gates passed (default cosine threshold **0.99**).

---

## Usage

```python
from sageattention import sageattn

# q, k, v: FP16 or BF16
# default layout HND: (batch, heads, seq_len, head_dim)
# for NHD (batch, seq_len, heads, head_dim) set tensor_layout="NHD"
out = sageattn(q, k, v, tensor_layout="HND", is_causal=False)
```

### Available APIs

| API | Notes |
|-----|--------|
| `sageattn` | Auto-selects backend by GPU (recommended) |
| `sageattn_qk_int8_pv_fp16_cuda` | INT8 QK + FP16 PV (CUDA, Ampere) |
| `sageattn_qk_int8_pv_fp8_cuda` | INT8 QK + FP8 PV (CUDA; SA2++ uses `pv_accum_dtype="fp32+fp16"`) |
| `sageattn_qk_int8_pv_fp8_cuda_sm90` | Hopper-optimized FP8 path |
| `sageattn_qk_int8_pv_fp16_triton` | Triton path (needs Triton) |
| `sageattn_varlen` | Variable sequence lengths (needs Triton) |

On **sm120 / sm121 / sm100**, `sageattn` uses the CUDA FP8 path with `qk_quant_gran="per_warp"` (no Triton).

### Plug-and-play (simple models)

```python
import torch.nn.functional as F
from sageattention import sageattn

F.scaled_dot_product_attention = sageattn
```

Not every model works with a global monkey-patch. For diffusion / video DiTs, prefer replacing only the attention class (see `example/modify_*.py`).

### ComfyUI (KJNodes)

1. Install the wheel into ComfyUI’s Python.
2. Fully restart ComfyUI.
3. Use **Patch Sage Attention** / KJNodes backends that call `sageattn` or `sageattn_qk_int8_pv_fp8_cuda` (not Triton-only modes on Blackwell unless you install triton-windows).

---

## Windows fixes

Relative to stock upstream `setup.py` / import paths:

| Area | Fix |
|------|-----|
| MSVC host flags | `/std:c++20` (required by recent PyTorch headers), `/Zc:__cplusplus`, `/Zc:preprocessor`, `/permissive-`, `/bigobj`, `NOMINMAX` |
| NVCC | C++20, Windows-safe `nvcc` path join, `-Usmall`, strip torch half-disable `-D` (avoid MSVC `D9025`), arch `sm_90a` / `sm_120a` / … |
| Extension selection | Build only kernels needed for detected GPU (e.g. sm120 → `_qattn_sm89` + `_fused`, not Linux-only OpenMP flags) |
| Linking | `libraries=["cuda"]` + CUDA `lib\x64` on Windows for Hopper |
| Triton | Optional import — CUDA backends work without Triton (critical for RTX 50 default path) |
| Tooling | `build_wheel.bat` prefers **`uv pip`**, puts venv `Scripts` on `PATH` for `ninja`, auto-cleans stale ABI `build\` trees |

---

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| `cl.exe` / `vcvars` not found | Install **VS 2026** Build Tools + C++ workload; re-run `build_wheel.bat` |
| `nvcc` not found | Install CUDA Toolkit; pass `--cuda "..."` |
| Torch headers need C++20 (`C7555` / `C7582`) | Ensure Windows build uses `/std:c++20` (default in this fork) |
| Wheel installs but import fails / missing DLL symbols | Rebuild with the **same** Python + **same** torch CUDA build as runtime |
| `No module named pip` in uv venv | Use **`uv pip install ...`**, not `python -m pip` |
| `No module named triton` | Only needed for Triton APIs; for sm120 default path reinstall this fork’s wheel (Triton is optional) |
| Import picks source tree without kernels | `cd` away from the repo root, or uninstall and reinstall the wheel into site-packages |
| Build OOM / compiler crash | `build_wheel.bat --jobs 1` |
| Switching Python versions fails oddly | `build_wheel.bat --clean` |

---

## Project layout

```text
SageAttention_Windows/
  build_wheel.bat      # one-click Windows build (MSVC + uv pip + wheel)
  setup.py             # CUDA extensions + MSVC / nvcc flags
  sageattention/       # Python API
  csrc/                # CUDA / C++ kernels
  scripts/             # smoke_vs_sdpa.py quality / speed checks
  example/             # model integration examples
  bench/               # kernel benchmarks
  LICENSE              # Apache-2.0 (upstream)
  README.md
  README_zh.md
```

---

## Performance notes

Kernel speed charts and end-to-end numbers are from upstream (see `assets/`). On RTX 50-series, SageAttention2++ CUDA paths are the primary target of this Windows packaging; quality vs SDPA is typically very close (INT8/FP8 quantization, not bit-exact).

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).  
Upstream copyright: SageAttention team / THU-ML.

---

## Citation

If you use this code or find the work valuable, please cite the original authors:

```bibtex
@inproceedings{zhang2025sageattention,
  title={SageAttention: Accurate 8-Bit Attention for Plug-and-play Inference Acceleration},
  author={Zhang, Jintao and Wei, Jia and Zhang, Pengle and Zhu, Jun and Chen, Jianfei},
  booktitle={International Conference on Learning Representations (ICLR)},
  year={2025}
}
@inproceedings{zhang2024sageattention2,
  title={Sageattention2: Efficient attention with thorough outlier smoothing and per-thread int4 quantization},
  author={Zhang, Jintao and Huang, Haofeng and Zhang, Pengle and Wei, Jia and Zhu, Jun and Chen, Jianfei},
  booktitle={International Conference on Machine Learning (ICML)},
  year={2025}
}
@article{zhang2025sageattention2++,
  title={Sageattention2++: A more efficient implementation of sageattention2},
  author={Zhang, Jintao and Xu, Xiaoming and Wei, Jia and Huang, Haofeng and Zhang, Pengle and Xiang, Chendong and Zhu, Jun and Chen, Jianfei},
  journal={arXiv preprint arXiv:2505.21136},
  year={2025}
}
```

---

## Disclaimer

This is an **unofficial Windows packaging / portability patch set**, not an official THU-ML release.  
Python package name remains **`sageattention`** for drop-in use with existing tools (e.g. ComfyUI-KJNodes).
