# NVIDIA Skills - Triagem Pemara

Data: 2026-07-04

Comando executado:

```powershell
npx skills add NVIDIA/skills
```

Resultado: 236 skills instaladas em `E:\Pemara\.agents\skills`.

## Uteis agora

- `vss-ask-video`: perguntar detalhes visuais sobre videos gerados. Bom para avaliar previews do Wan/LTXV sem depender so do olho humano.
- `vss-summarize-video`: resumir videos e apontar o que acontece em cada trecho. Bom para comparar previews da intro do jogo.
- `vss-generate-video-report`: gerar relatorio de qualidade por clipe. Pode virar auditor de videos do Maestro.
- `vss-search-archive`: indexar/consultar arquivo de videos. Bom quando a pasta de renders crescer.
- `nemo-retriever`: RAG local para documentos, PDFs, imagens, audio e video. Bom para criar memoria pesquisavel do ecossistema Pemara.
- `rag-blueprint`: blueprint NVIDIA para RAG completo. Bom para evoluir o Maestro como painel com busca e memoria.
- `rag-perf`: benchmark de RAG. Bom para medir latencia/throughput quando o Maestro tiver busca propria.
- `nemotron-speech`: ASR/TTS/NMT via Riva/NIM. Candidato para voz em portugues, audio e futuros comandos por fala.
- `nemo-mbridge-perf-memory-tuning`: tecnicas de reducao de VRAM/OOM. Util para treinos LoRA e modelos grandes.
- `nemo-mbridge-perf-cpu-offloading`: guia de offload CPU/RAM. Util para estrategia com 64GB RAM.
- `nemo-mbridge-perf-cuda-graphs`: reduzir overhead em inferencia/treino quando houver pipeline compativel.
- `accelerated-computing-cudf`: acelerar ETL/raspagem/analise de dados grandes com GPU, se houver mais de 100k linhas.

## Uteis depois

- `tao-generate-video-reasoning-annotations`: gerar anotacoes de raciocinio sobre videos. Interessante para datasets de avaliacao de video.
- `physical-ai-video-data-augmentation`: aumento/rotulagem de dados de video, mas parece mais focado em stack NVIDIA/OSMO.
- `dali-dynamic-mode`: DALI para pipeline de imagem/video em PyTorch. Pode ajudar dataset/augmentacao se o treino crescer.
- `deepstream-generate-pipeline`: pipelines GStreamer/DeepStream para deteccao, tracking e stream. Mais util para cameras/RTSP do que geracao.
- `tao-train-action-recognition`: treinar reconhecimento de acao em videos. Pode servir para avaliador de movimento, nao para gerar video.
- `tao-setup-nvidia-gpu-host`: checagem Linux/Docker/Kubernetes para TAO. Em Windows atual, usar apenas como referencia.

## Baixa prioridade / ignorar por enquanto

- Skills Jetson: foco em hardware embarcado, nao na RTX 5080 desktop.
- Skills medicas/DICOM: fora do dominio Pemara.
- cuOpt: otimizacao de rotas/solver; nao ajuda agora em geracao de imagem/video.
- CUDA-Q/PhysicsNeMo/Earth2Studio/Holoscan/Omniverse: interessantes, mas fora da prioridade atual.
- TAO completo: pesado e mais voltado a visao computacional tradicional, nao substitui FLUX/Qwen/Wan/ComfyUI.

## Plano recomendado

1. Integrar primeiro `vss-ask-video`, `vss-summarize-video` e `vss-generate-video-report` como avaliadores dos videos gerados.
2. Usar NVIDIA NIM ja implantado no Maestro para transformar esses relatorios em nota de qualidade e proximas acoes.
3. Criar memoria pesquisavel com `nemo-retriever` ou `rag-blueprint` para docs, logs, prompts, renders e decisoes.
4. Usar as skills de memory/offload como referencia para ajustes de VRAM/RAM, sem trocar o pipeline local de treino.

Regra: essas skills entram como apoio de avaliacao, RAG e orquestracao. Elas nao substituem os treinos locais FLUX/Qwen/Wan/LoRA.
