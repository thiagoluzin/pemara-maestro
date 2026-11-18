# DLSS 5 obrigatório

Política autorizada pelo proprietário em 2026-10-06 após avaliar o comparativo RE1.

O handler atua nos exportadores visuais OUTPUT_NODE com entradas ou saídas IMAGE/VIDEO. Inclui SaveImage, PreviewImage, SaveVideo, SaveWEBM e VHS_VideoCombine, independentemente do builder, motor ou origem do grafo. Não reescreve grafos históricos. O acabamento reutiliza o runtime isolado e a DLL NVIDIA original fixados por SHA-256 em `services/studio/dlss5_finishing.py`.

O perfil obrigatório é `dlss5_required_natural_re1_v1`: NR 1x, Natural, intensidade/estrutura/detalhe 0.5, tom/cor 0, pele 0.25, auto-mask. A etapa ocorre dentro da execução serial do ComfyUI, depois de liberar os modelos. Imagens mantêm dimensões e alpha; vídeos mantêm dimensões, frames, FPS, duração e payload do áudio. Arquivos `.before_dlss5.*` conservam as fontes. Recibos `.dlss5.json` ligam a saída ao tratamento e ao log do NR.

Maestro também aplica o acabamento no editor, remaster, imagens processadas, upscale e novos masters. Arquivos tratados podem transmitir o recibo a proxies e montagens por cópia do bitstream, evitando efeito duplicado. A aprovação artística continua por artefato.

Qualificação atual: PNG/JPEG/WebP estáticos e MP4/MOV/MKV/WebM, SDR 8-bit. GIF/APNG animados, alta profundidade e exportadores visuais sem arquivo verificável falham de forma explícita. Não há saída silenciosa sem DLSS. Modelos, FPS e resolução escolhidos não mudam para contornar incompatibilidade.

Instalação ativa: copiar esta pasta para `D:\PemaraRuntimes\ComfyUI-v0.36.0-pemara\custom_nodes\pemara_dlss5_required` e recarregar exclusivamente via MCP com fila vazia. Verificar `PemaraDLSS5Policy` e executar os dois grafos POLICY_SMOKE_IMAGE/VIDEO pelo MCP. Repetir o grafo deve salvar nova saída tratada.
