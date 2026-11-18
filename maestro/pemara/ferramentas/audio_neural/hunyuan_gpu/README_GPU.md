# HunyuanVideo-Foley GPU runtime

- Modelo: Tencent HunyuanVideo-Foley XXL.
- Runtime: Docker Linux + PyTorch CUDA 12.8.
- GPU alvo: NVIDIA GeForce RTX 5090, CUDA device 0.
- Politica: nunca usar `--enable_offload`; falhar se CUDA nao estiver disponivel.
- Pesos: `G:\Pemara_AI_Models\HunyuanVideo-Foley`.
- Entradas e saidas: projeto Mortal Kombat em `E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s`.

O contêiner apenas orquestra os pesos neurais treinados. Nenhuma onda, instrumento ou mixagem e criada proceduralmente em Python.
