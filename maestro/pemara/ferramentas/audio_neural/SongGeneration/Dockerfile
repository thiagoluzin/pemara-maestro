FROM vllm/vllm-openai:v0.8.5

# The official vllm/vllm-openai image hard-codes
#   ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
# Clearing it makes our CMD ["python3", "app.py"] actually run.
ENTRYPOINT []

USER root

# git-lfs       : pulling model weights from HF
# ffmpeg / libsndfile1 : librosa needs them to decode mp3/m4a/ogg uploads
RUN apt-get update && \
    apt-get install -y --no-install-recommends git-lfs ffmpeg libsndfile1 && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
# Force Python stdout/stderr to be unbuffered so that progress bars (tqdm in
# snapshot_download), vLLM INFO logs and our own prints show up in HF Space
# logs immediately. Without this the container looks "stuck" at the startup
# banner because everything sits in a 4-8 KB block buffer until the process
# exits or the buffer fills up.
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

WORKDIR /app

COPY --chown=user ./requirements.txt requirements.txt
# --prefer-binary : never try to build any wheel from source (flash_attn
#                   would OOM the build container). The base image already
#                   provides torch / vllm / flash_attn / transformers.
#
# NOTE: deliberately NO `--upgrade` here. The base image ships a carefully
# pinned dependency tree (transformers 4.x compatible with
# huggingface-hub<1.0). Using --upgrade lets pip pull huggingface-hub 1.x
# whenever any package's metadata allows it, which then breaks
# `import vllm` at container start.
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Force-upgrade gradio specifically.
#
# The vllm/vllm-openai:v0.8.5 base image ships an old gradio (pre-4.4) that
# is missing newer kwargs like `show_copy_button` on gr.Textbox. Listing
# `gradio>=4.44` in requirements.txt is NOT enough: without --upgrade, pip
# leaves any already-installed gradio in place as long as it parses as
# >=4.44 (and even when it doesn't, the resolver sometimes keeps it for
# compatibility reasons inside this image).
#
# We isolate this to a single line and use:
#   --upgrade                       : actually replace the existing gradio
#   --upgrade-strategy only-if-needed
#                                   : do NOT cascade-upgrade gradio's deps
#                                     (fastapi / pydantic / starlette /
#                                      uvicorn) unless gradio strictly
#                                     requires it -- those are tightly
#                                     coupled to vllm's OpenAI server and
#                                     bumping them can break `import vllm`.
#   --prefer-binary                 : never trigger a source build.
RUN pip install --no-cache-dir --prefer-binary \
        --upgrade --upgrade-strategy only-if-needed \
        "gradio>=4.44,<6"

COPY --chown=user . /app
CMD ["python3", "app.py"]