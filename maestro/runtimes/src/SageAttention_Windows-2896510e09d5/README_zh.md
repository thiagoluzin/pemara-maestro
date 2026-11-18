# SageAttention Windows 版

**英文版文档：[README.md](README.md)**（中文内容如下）

面向 **Windows** 的 **SageAttention 2.x / 2++** 构建工程（INT8 / FP8 Attention 内核，覆盖 Ampere、Ada、Hopper 与 **Blackwell**）。

本仓库基于官方 [thu-ml/SageAttention](https://github.com/thu-ml/SageAttention) 源码，加入 **MSVC / Windows 编译与运行适配**，可在原生 Windows 上生成可用的 wheel（无需 WSL）。本仓库 **不包含** SageAttention3 Blackwell 源码；若需要 FP4，请使用独立的 SA3 工程（例如 [Sageattention3_Blackwell_Windows](https://github.com/sjh00/Sageattention3_Blackwell_Windows)）。

> 上游项目：[thu-ml/SageAttention](https://github.com/thu-ml/SageAttention)  
> 论文：[SageAttention](https://arxiv.org/abs/2410.02367) · [SageAttention2](https://arxiv.org/abs/2411.10958) · [SageAttention2++](https://arxiv.org/pdf/2505.21136)  
> English docs: [README.md](README.md)

---

## 为什么需要这个仓库

官方 SageAttention 以 Linux 为主。在 Windows + MSVC 上常见问题：

1. **编译失败**——GCC 专用标志（`-fopenmp`、`-lgomp`）、与新版 PyTorch 头文件不匹配的 C++ 标准、`nvcc` 路径处理不当。
2. **编译脆弱**——half 相关标志冲突（`D9025`）、切换 Python 版本导致 ABI 混用、未加载 MSVC 环境（`DISTUTILS_USE_SDK`）。
3. **运行 / 导入问题**——wheel 与运行时的 PyTorch ABI 不一致；在源码目录 `import` 却没有编译出的 `.pyd`；即使只需要 CUDA 内核（如 RTX 50 / `sm_120`）也强依赖 Triton。

本仓库提供一套已验证的 Windows 适配（见 [Windows 修复说明](#windows-修复说明)）。参考成功环境：

| 项目 | 示例 |
|------|------|
| 系统 | Windows 11 |
| 显卡 | RTX 50 系（compute capability 12.0） |
| Python | 3.13（uv venv） |
| PyTorch | 2.13 + CUDA 13.2 |
| CUDA Toolkit | 13.2 |
| MSVC | **Visual Studio 2026** Build Tools（MSVC 14.5x；安装目录可能为 `...\18\BuildTools`） |
| 应用 | ComfyUI + KJNodes `PatchSageAttention`，或任意 PyTorch 脚本 |

---

## 功能概览（上游 SageAttention 2.2）

- 面向 **Ampere / Ada / Hopper / Blackwell** 的 CUDA 内核（sm80 / sm89 / sm90 / sm100–sm121）。
- \(QK^\top\) 的 INT8 量化与平滑（per-warp / per-thread 粒度）。
- \(PV\) 的 FP8 量化，以及 FP16 / 两级累加器（**SageAttention2++**：`pv_accum_dtype="fp32+fp16"`）。
- 自动 API `sageattn` 按 GPU 架构选择后端。
- 可选 **Triton** 后端（varlen / sm86 / per-thread 量化）；**Blackwell（`sm_120`）默认 CUDA 路径不依赖 Triton**。

---

## 环境要求

### 硬件

| 架构 | 示例 | 默认内核路径 |
|------|------|--------------|
| sm80 | RTX 3090、A100 | CUDA FP16 PV（`_qattn_sm80`） |
| sm86 | RTX 3080 Ti 等 | Triton（需 `triton-windows`） |
| sm89 | RTX 4090、L40 | CUDA FP8 PV（`_qattn_sm89`） |
| sm90 | H100、H800、H20 | CUDA FP8 Hopper（`_qattn_sm90`） |
| sm100 / sm120 / sm121 | B100 / **RTX 50** | 编译到 `sm_XXXa` 的 sm89 FP8 CUDA 路径 |

### 软件

- **Python** 3.10+（推荐 3.12 / **3.13**；**构建与运行 ABI 必须一致**）
- **带 CUDA 的 PyTorch**（Blackwell / SA2++：建议 CUDA **12.8+**，更推荐 **13.x**）
- **CUDA Toolkit**（需有 `nvcc`）：
  - Blackwell（`sm_100` / `sm_120` / `sm_121`）或 SageAttention2++：`>= 12.8`
  - Ada FP8（`sm_89`）：`>= 12.4`
  - Hopper FP8（`sm_90`）：`>= 12.3`
  - Ampere（`sm_80`）：`>= 12.0`
- **Visual Studio 2026** Build Tools，勾选 **使用 C++ 的桌面开发**  
  （`build_wheel.bat` 若本机仍装有 VS 2022 也可探测；**当前以 2026 为主要验证环境**）
- **ninja / packaging / wheel / build**（`build_wheel.bat` 通过 **`uv pip`** 安装；无 uv 时才回退 `python -m pip`）
- 可选：**[uv](https://github.com/astral-sh/uv)**（推荐，用于管理 Python 与依赖）
- 可选：**[triton-windows](https://github.com/triton-lang/triton-windows)**（仅 Triton API 需要：`sageattn_varlen`、sm86、`qk_quant_gran="per_thread"`）

---

## 快速开始：编译 wheel

1. 准备带 CUDA 的环境（uv 示例）：

```bat
uv venv .venv --python 3.13
uv pip install --python .venv\Scripts\python.exe torch --index-url https://download.pytorch.org/whl/cu132
```

2. 在本目录打开 `cmd`（脚本会自行加载 MSVC 环境）：

```bat
build_wheel.bat
```

若存在 `.venv\Scripts\python.exe`，脚本会优先使用该解释器。

常用参数：

```bat
rem 清理旧产物再编（切换 Python ABI 后强烈建议）
build_wheel.bat --clean

rem 指定目标 Python（uv venv / ComfyUI embed）
build_wheel.bat --python ".venv\Scripts\python.exe"

rem ComfyUI 便携 Python
build_wheel.bat --python "D:\ComfyUI\python_embeded\python.exe"

rem 指定 CUDA Toolkit 路径
build_wheel.bat --cuda "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2"

rem 并行编译任务数（默认 2，内存不够可改 1）
build_wheel.bat --jobs 1

rem 强制目标架构列表（可选；默认自动检测本机 GPU）
build_wheel.bat --arch "12.0"
```

成功后 wheel 在 `dist\`：

```text
dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

完整编译日志：`build.log`。脚本还会扫描硬错误与易混淆告警（如 `D9025`）。

### 手动编译（进阶）

```bat
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set DISTUTILS_USE_SDK=1
set CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2
set PATH=%CUDA_HOME%\bin;%PATH%

rem uv 环境请用 uv pip（venv 默认没有 pip 模块）
uv pip install --python .venv\Scripts\python.exe -U setuptools wheel ninja packaging build
.venv\Scripts\python.exe -m build --wheel --no-isolation
```

---

## 安装 wheel

**构建用的 Python 与运行环境必须一致**（ABI 标签要对上，例如 `cp313`）：

```bat
rem 推荐：uv
uv pip install --python .venv\Scripts\python.exe --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl

rem 传统 pip（仅当本机确有 pip 时）
python -m pip install --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

ComfyUI 便携包示例：

```bat
uv pip install --python "D:\ComfyUI\python_embeded\python.exe" --force-reinstall --no-deps dist\sageattention-2.2.0-cp313-cp313-win_amd64.whl
```

安装后请 **完全重启 ComfyUI**（或你的应用）。

> **导入提示：** 未安装 wheel 时，不要在仓库根目录直接 `import sageattention`——本地包目录没有编译好的 `.pyd`。请从已安装环境导入（或先 `cd` 到其他目录）。

### 冒烟测试

最小导入检查：

```bat
python -c "import torch; from sageattention import sageattn; q=torch.randn(1,8,128,64,device='cuda',dtype=torch.float16); print(sageattn(q,q,q).shape)"
```

与 torch SDPA 对比（质量 + 大 shape 速度 + 因果诊断）：

```bat
python scripts/smoke_vs_sdpa.py
python scripts/smoke_vs_sdpa.py --quick
python scripts/smoke_vs_sdpa.py --dtype fp16
python scripts/smoke_vs_sdpa.py --causal-diag
```

请使用 **已安装的 wheel** 运行（不要从未经编译的源码树直接 import）。可选参数：`--bench-only`、`--no-bench`、`--cos-thr`、`--seed`。

#### 实测结论（参考环境）

环境：Windows 11 · RTX 50 系（`sm_120`）· Python 3.13 · PyTorch 2.13 + CUDA 13.2 · 本仓库 `cp313` wheel · `SM89=True`，无需 Triton。

| 检查项 | 结果 |
|--------|------|
| 质量网格（bf16 / fp16） | 全部 **PASS** — 相对 SDPA 余弦相似度 **约 0.9993–0.9995**（非因果与因果均如此） |
| shape / 有限值 | 输出 shape 与 SDPA 一致；全为 finite |
| 非对齐 `L=200` | PASS（内部 pad 路径） |
| 因果 mask | 因果 SA ≈ 因果 SDPA（~0.999）；因果 ≠ 非因果 ⇒ mask 已生效 |
| 大 shape 吞吐（bf16，ms/iter） | 例如 `B1 H24 L2048 D128` 约 **4.3×** vs SDPA；`B1 H32 L4096 D128` 约 **5.7×**；余弦仍约 0.999 |

说明：

- SageAttention2++ 为 INT8/FP8 量化，**非 bit-exact**，但余弦稳定在 **~0.999**（明显优于 SageAttention3 FP4，尤其是因果路径）。
- 小 shape 可能受启动延迟主导（微基准里 SA 不一定更快）；序列变长 / 头数变多后加速更明显。
- 退出码 `0` 表示质量门槛通过（默认余弦阈值 **0.99**）。

---

## 使用方法

```python
from sageattention import sageattn

# q, k, v: FP16 或 BF16
# 默认布局 HND: (batch, heads, seq_len, head_dim)
# NHD (batch, seq_len, heads, head_dim) 时设 tensor_layout="NHD"
out = sageattn(q, k, v, tensor_layout="HND", is_causal=False)
```

### 可用 API

| API | 说明 |
|-----|------|
| `sageattn` | 按 GPU 自动选择后端（推荐） |
| `sageattn_qk_int8_pv_fp16_cuda` | INT8 QK + FP16 PV（CUDA，Ampere） |
| `sageattn_qk_int8_pv_fp8_cuda` | INT8 QK + FP8 PV（CUDA；SA2++ 用 `pv_accum_dtype="fp32+fp16"`） |
| `sageattn_qk_int8_pv_fp8_cuda_sm90` | Hopper 优化的 FP8 路径 |
| `sageattn_qk_int8_pv_fp16_triton` | Triton 路径（需 Triton） |
| `sageattn_varlen` | 变长序列（需 Triton） |

在 **sm120 / sm121 / sm100** 上，`sageattn` 使用 CUDA FP8 路径且 `qk_quant_gran="per_warp"`（**不需要 Triton**）。

### 简单模型的即插即用

```python
import torch.nn.functional as F
from sageattention import sageattn

F.scaled_dot_product_attention = sageattn
```

并非所有模型都适合全局 monkey-patch。扩散 / 视频 DiT 建议只替换 Attention 类（见 `example/modify_*.py`）。

### ComfyUI（KJNodes）

1. 将 wheel 装进 ComfyUI 使用的 Python。
2. 完全重启 ComfyUI。
3. 使用 **Patch Sage Attention** / KJNodes 中调用 `sageattn` 或 `sageattn_qk_int8_pv_fp8_cuda` 的后端（Blackwell 上除非安装了 triton-windows，否则不要只用 Triton 模式）。

---

## Windows 修复说明

相对上游默认 `setup.py` / 导入路径，本仓库主要改动：

| 方面 | 修复内容 |
|------|----------|
| MSVC 主机标志 | `/std:c++20`（新版 PyTorch 头文件需要）、`/Zc:__cplusplus`、`/Zc:preprocessor`、`/permissive-`、`/bigobj`、`NOMINMAX` |
| NVCC | C++20、Windows 安全的 `nvcc` 路径拼接、`-Usmall`、去掉 torch half 禁用 `-D`（避免 `D9025`）、架构 `sm_90a` / `sm_120a` 等 |
| 扩展选择 | 仅编译本机 GPU 需要的内核（如 sm120 → `_qattn_sm89` + `_fused`，去掉 Linux OpenMP 标志） |
| 链接 | Windows 上 Hopper 使用 `libraries=["cuda"]` 与 CUDA `lib\x64` |
| Triton | 可选导入——无 Triton 也能用 CUDA 后端（RTX 50 默认路径关键） |
| 工具链 | `build_wheel.bat` 优先 **`uv pip`**，把 venv 的 `Scripts` 加入 PATH 以找到 `ninja`，并在 Python ABI 切换时自动清理旧 `build\` |

---

## 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 `cl.exe` / `vcvars` | 安装 **VS 2026** Build Tools + C++ 工作负载后重新运行 `build_wheel.bat` |
| 找不到 `nvcc` | 安装 CUDA Toolkit，或使用 `--cuda` |
| Torch 头文件报需要 C++20（`C7555` / `C7582`） | 确认 Windows 构建使用 `/std:c++20`（本 fork 默认已启用） |
| 安装成功但 import 失败 / 缺 DLL 符号 | 用与运行环境 **同一** Python 与 **同一** torch CUDA 构建重新编译 |
| uv 环境提示 `No module named pip` | 使用 **`uv pip install ...`**，不要用 `python -m pip` |
| `No module named triton` | 仅 Triton API 需要；sm120 默认路径请安装本 fork 的 wheel（Triton 可选） |
| 从源码树导入却没有内核 | 离开仓库根目录再 import，或把 wheel 装进 site-packages |
| 编译内存不足 / 编译器崩溃 | `build_wheel.bat --jobs 1` |
| 切换 Python 版本后异常 | `build_wheel.bat --clean` |

---

## 目录结构

```text
SageAttention_Windows/
  build_wheel.bat      # 一键 Windows 编译（MSVC + uv pip + wheel）
  setup.py             # CUDA 扩展与 MSVC / nvcc 标志
  sageattention/       # Python API
  csrc/                # CUDA / C++ 内核
  scripts/             # smoke_vs_sdpa.py 质量 / 速度检查
  example/             # 模型接入示例
  bench/               # 内核基准测试
  LICENSE              # Apache-2.0（上游）
  README.md
  README_zh.md
```

---

## 性能说明

内核速度与端到端图表见 `assets/`（上游数据）。在 RTX 50 系上，本 Windows 打包主要面向 SageAttention2++ 的 CUDA 路径；相对 SDPA 通常非常接近（INT8/FP8 量化，非 bit-exact）。

---

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。  
上游版权归属 SageAttention team / THU-ML。

---

## 引用

若使用本代码或认为工作有价值，请引用原作者：

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

## 免责声明

这是 **非官方** 的 Windows 打包与可移植性补丁集合，**不是** THU-ML 官方发行版。  
Python 包名仍为 **`sageattention`**，以便与 ComfyUI-KJNodes 等现有工具直接兼容。
