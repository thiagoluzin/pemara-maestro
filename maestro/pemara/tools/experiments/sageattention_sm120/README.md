# SageAttention isolado para RTX 5090

Estado: nao promovido. Esta pasta nao modifica o Python do Maestro nem o ComfyUI.

Fonte oficial: `../SageAttention-official`, commit
`d1a57a546c3d395b1ffcbeecc66d81db76f3b4b5`.

## Escolha do piloto

O runtime atual usa Python 3.11, Torch 2.13.0+cu130, CUDA runtime 13.0 e RTX 5090
SM120. SageAttention3 exige oficialmente Python 3.13, portanto nao deve ser injetado
no runtime atual. O primeiro piloto usa a API `sageattention`/SageAttention2++, que
aceita Python 3.9+ e possui caminho SM120 no codigo oficial.

O proprio projeto oficial diz que SageAttention2 e mais preciso e que
SageAttention3 nao garante aceleracao sem perda em todo modelo de video. Por isso,
mesmo um smoke numerico aprovado nao autoriza uso no H3.

## Execucao

Somente com ComfyUI ocioso:

```powershell
.\tools\experiments\sageattention_sm120\run_isolated.ps1
```

O script cria `.venv` com `--system-site-packages`, compila o checkout oficial dentro
desse ambiente e executa `verify_sageattention.py`. Nenhum pacote e instalado no
Python global. Para o stack Torch 2.13/CUDA 13.3, ele usa os hooks oficiais
`CXX_APPEND_FLAGS` e `NVCC_APPEND_FLAGS` para manter C++20 como o ultimo padrao de
linguagem; o `setup.py` oficial ainda declara C++17 antes desses hooks.

## Gate

O smoke exige tensores finitos, cosseno >= 0,995 e erro L2 relativo <= 0,05 contra
SDPA. O relatorio inclui latencia, mas velocidade so e informativa. A promocao exige
depois um A/B H3 separado, mesma seed, mesmos keyframes, sampler, encoder e steps, e
aprovacao visual humana. Qualquer artefato mantem full attention.
