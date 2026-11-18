# Instaladores pesados do Maestro MiniMax H3

Esta pasta permanece pequena. Os modelos nao entram no backup: os BATs baixam e verificam os
artefatos no PC restaurado.

## Ordem simples

1. Restaure o sistema Maestro.
2. Instale o driver NVIDIA, Python 3.11+, FFmpeg e Docker Desktop.
3. Rode `00_DIAGNOSTICAR_PC.bat`.
4. Rode `INSTALAR_TUDO_MODELOS.bat` ou os instaladores numerados.
5. Rode `VERIFICAR_MODELOS.bat`.
6. Rode `VALIDAR_INSTALACAO.ps1 -RequireModels` no pacote de backup.

O instalador completo baixa mais de 60 GB e preserva 20 GB livres como margem. Ele usa retomada,
retry, revisoes fixadas e SHA-256. Uma segunda execucao pula artefatos ja verificados.

## Componentes

- `01_INSTALAR_H3.bat`: FL2VA e Ref2VA pruned INT8 ConvRot, mais os VAEs oficiais para o ComfyUI.
- `02_INSTALAR_QWEN_H3.bat`: Qwen3-VL-32B NVFP4/AWQ usado pelo H3.
- `03_INSTALAR_RIFE_FHD60.bat`: RIFE 4.6 portatil e RealESRGAN x2 para acabamento FHD60.
- `04_INSTALAR_FOLEY_XXL.bat`: pesos XXL Tencent, SigLIP2, CLAP e imagem Docker do Foley.
- `INSTALAR_TUDO_MODELOS.bat`: executa a pilha inteira.
- `VERIFICAR_MODELOS.bat`: confirma arquivos, hashes, extracao do RIFE e runtime Foley.

Para simular sem alterar nada:

```bat
set PEMARA_NO_PAUSE=1
INSTALAR_TUDO_MODELOS.bat --dry-run
```

Se o sistema foi restaurado em outra pasta, defina-a antes:

```bat
set PEMARA_ROOT=D:\Pemara
INSTALAR_TUDO_MODELOS.bat
```

Ao executar os instaladores, o proprietario confirma as licencas comunitarias MiniMax H3 e
Tencent Hunyuan. Nenhum token e gravado no manifesto ou nos logs.
