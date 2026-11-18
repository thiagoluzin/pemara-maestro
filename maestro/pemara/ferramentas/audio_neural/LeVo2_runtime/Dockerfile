FROM witszhang/songgeneration_vllm:v2

USER root

RUN apt-get update && \
    apt-get install -y git-lfs && \
    git lfs install && \
    rm -rf /var/lib/apt/lists/*

COPY ./vllm_hacked/model_executor/models/llama.py /opt/conda/lib/python3.11/site-packages/vllm/model_executor/models/llama.py
COPY ./vllm_hacked/v1/sample/sampler.py /opt/conda/lib/python3.11/site-packages/vllm/v1/sample/sampler.py
COPY ./vllm_hacked/v1/sample/metadata.py /opt/conda/lib/python3.11/site-packages/vllm/v1/sample/metadata.py
COPY ./vllm_hacked/sampling_params.py /opt/conda/lib/python3.11/site-packages/vllm/sampling_params.py

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY --chown=user . /app
CMD ["python3", "app.py"]