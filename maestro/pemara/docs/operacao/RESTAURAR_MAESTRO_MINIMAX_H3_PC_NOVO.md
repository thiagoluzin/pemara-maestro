# Restaurar Maestro MiniMax H3 em outro PC

## O que o backup do sistema contem

- codigo do Maestro/Studio, ComfyUI e custom nodes, sem `.env`;
- catalogo `.agents` e a skill oficial H3 pinada;
- codigo e configuracao dos adaptadores H3, Qwen, RIFE, RealESRGAN e Foley;
- manifestos SHA-256, inventario do ambiente e scripts de validacao.

O pacote gerado por `tools/backup_maestro_minimax_h3.ps1` e **somente do sistema**. Pesos de
modelos, credenciais, projetos privados, renders e `.env` ficam fora. A pasta `INSTALAR_MODELOS`
leva somente BATs, o downloader e o manifesto travado; os pesos sao baixados no PC novo.

## Pre-requisitos do PC novo

- Windows 11 64-bit;
- GPU NVIDIA com VRAM adequada ao H3 e driver compativel;
- Python 3.11 x64;
- Git, FFmpeg/ffprobe com `h264_nvenc`, Vulkan e Docker Desktop para o Foley;
- espaco livre superior ao tamanho registrado em `SNAPSHOT_METADATA.json`.

## Restauracao

1. Copie o backup para um disco local.
2. No PowerShell, execute `VALIDAR_BACKUP.ps1`; qualquer hash do sistema divergente bloqueia.
3. Execute `RESTAURAR_PC_NOVO.ps1 -TargetRoot E:\Pemara` numa pasta vazia.
4. Copie `.env.example` para `.env` e preencha segredos localmente; nunca use um `.env` de origem
   desconhecida.
5. Instale dependencias conforme `PYTHON_FREEZE.txt` e os requirements do ComfyUI/Studio. O freeze
   e evidencia da maquina fonte, nao autorizacao para instalar pacotes sem revisar.
6. Rode `tools\model_installers\00_DIAGNOSTICAR_PC.bat`.
7. Rode `tools\model_installers\INSTALAR_TUDO_MODELOS.bat`. Ele baixa H3, Qwen, RIFE,
   RealESRGAN e Foley XXL, retoma interrupcoes, verifica SHA-256 e constroi o runtime Docker Foley.
8. Rode `tools\model_installers\VERIFICAR_MODELOS.bat` e depois
   `VALIDAR_INSTALACAO.ps1 -RequireModels`.
9. Inicie ComfyUI em `127.0.0.1:8188` e Studio em `127.0.0.1:8029`.
10. Abra `Criar > Video` e confirme `Workflow MiniMax H3 completo: Pronto`.
11. Compile um prompt e execute o preflight de um projeto de teste. Nao rode inferencia pesada ate
   autorizar uma janela de GPU.

O instalador completo exige mais de 60 GB para os artefatos e mantem uma reserva de 20 GB. Para
simular sem baixar, use `INSTALAR_TUDO_MODELOS.bat --dry-run`. Os BATs confirmam as licencas
comunitarias MiniMax H3 e Tencent Hunyuan ao serem executados.

## Gate de aceite

- todos os hashes obrigatorios conferem;
- listeners permanecem em loopback;
- `/api/generative/h3/workflow` responde apenas pela origem interna autorizada;
- H3, Qwen3-VL, VAEs, RIFE, RealESRGAN e Foley aparecem presentes;
- suites H3/UI/API passam;
- nenhuma credencial aparece no pacote;
- um primeiro render continua dependendo de aprovacao explicita e QC humano.
