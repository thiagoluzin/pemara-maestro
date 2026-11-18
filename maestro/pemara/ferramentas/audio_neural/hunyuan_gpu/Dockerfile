FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/.cache/huggingface \
    TORCH_HOME=/models/.cache/torch

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    git \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hunyuan

COPY . /opt/hunyuan/

# Runtime neural oficial. PyTorch/CUDA ja vem da imagem-base e nao e reinstalado.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir \
      numpy==1.26.4 scipy diffusers timm accelerate sentencepiece \
      pillow av einops pyyaml omegaconf easydict loguru tqdm \
      pandas pyarrow urllib3==2.4.0 huggingface_hub && \
    python -m pip install --no-cache-dir \
      "git+https://github.com/huggingface/transformers@v4.49.0-SigLIP-2" \
      "git+https://github.com/descriptinc/audiotools" && \
    python -m pip install --no-cache-dir --no-deps -e /opt/hunyuan

RUN python -c "import torch, hunyuanvideo_foley; assert torch.version.cuda == '12.8'; print('Hunyuan runtime pronto:', torch.__version__, torch.version.cuda)"

ENTRYPOINT ["python", "/opt/hunyuan/infer.py"]
