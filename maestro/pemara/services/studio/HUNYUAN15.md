# HunyuanVideo 1.5 no Maestro

Autorização do proprietário: 2026-11-10. A escolha de Hunyuan amplia o registro ativo ao lado de MiniMax H3. LTX continua removido e não existe fallback entre motores.

O modo preparado é **imagem para vídeo**, original FP16 em 720p, com uma âncora inicial. Na área Criar do Maestro: escolha Animar imagem → HunyuanVideo 1.5 → tipo da produção → âncora aprovada → direção da ação. O perfil usa 24 FPS, 50 passos, guidance 6 e duração de 5–10 segundos na grade 4n+1. O perfil atual não fornece áudio nativo, último quadro fixo, LoRA extra, Ref2VA ou DWPose.

O estado real da instalação está em `hunyuan15_install.json` e no cartão do motor. Os cinco arquivos foram conferidos por tamanho e SHA-256. Um hash modificado ou arquivo substituído invalida a liberação. Houve uma tentativa real de GPU do piloto Scorpion x Sub-Zero, cancelada pelo proprietário por lentidão; nenhum MP4 foi concluído. Instalação e preflight não aprovam qualidade visual.

Evidências: `E:/Pemara/work/hunyuan15_install_20261110/`. O finalizador nessa pasta apenas aguarda arquivos locais e confere seus hashes oficiais; não chama ComfyUI nem gera vídeos. A configuração anterior do downloader foi restaurada. O auxiliar temporário aria2 foi encerrado após a conferência dos arquivos.

Fontes consultadas em 2026-11-10:

- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/ComfyUI/README.md
- https://docs.comfy.org/tutorials/video/hunyuan/hunyuan-video-1-5
- https://huggingface.co/Comfy-Org/HunyuanVideo_1.5_repackaged/tree/1405a2b738c29b890cf6d03fc038d8d3e92eeed7

Foram reutilizados Qwen2.5-VL e SigCLIP já existentes. Os três pesos novos ficam no runtime ativo em D:, sem instalar dependências Python novas nem reiniciar ComfyUI. O Studio foi reiniciado pelo supervisor depois de conferir ausência de trabalhos ativos do gerador.

Validação: 19 testes da integração, workflows, seleção de motores e navegador passaram. A suíte antiga de contratos textuais da UI conserva as mesmas quatro falhas presentes no snapshot anterior, registradas em `ui_contract_baseline.json`; nenhuma nova falha nessa comparação. O H3 mantém sua rota e aceleração anteriores.

Para live action, SR neural do Hunyuan não foi instalado. Acabamento segue a ordem vigente: DLSS somente na âncora; vídeo com Lanczos + NVENC e RIFE 4.25 após aprovação da fonte. Preservar áudio existente, fontes, duração e histórico.

O piloto Scorpion x Sub-Zero está registrado em `ferramentas/video_global_engine/projetos/scorpion_subzero_hunyuan_classic_20261110`. A01 foi produzida com o gerador interno, tratada como âncora e aprovada pelo proprietário por hash. A tentativa MCP `f563a45e-1827-4c31-9439-7c53d8993f1b` foi cancelada; o servidor registrou 12m20s de execução interrompida, com cerca de 145–147s/it após inicialização. Projeto PAUSED, sem nova geração automática.

A revisão de performance está em `PESQUISA_WORKFLOW_COMPLETA.md` na raiz desse projeto. Quatro variantes isoladas passaram validação MCP e permanecem NOT_RUN: Sage2, Sage2 FP8++, Sage2 com compile/não dinâmico por MODEL, Sage2 com EasyCache. Elas não substituem o perfil de produção. A checagem de máscaras é obrigatória antes de executá-las: o KJNodes instalado não contém a proteção upstream para kernels CUDA que não aplicam attn_mask. Preflight não demonstra kernel ativo, fidelidade ou aceleração. Spectrum H3 não serve como patch genérico Hunyuan; nenhum pacote ou checkpoint novo foi instalado nesta pesquisa.
