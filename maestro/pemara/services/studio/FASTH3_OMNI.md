# FastH3-Omni no Maestro

Integração de 2026-10-21. Em **Vídeo > MiniMax H3 > Variante**, selecionar **FastH3-Omni — 8 passos (experimental)**. Atualizar a página caso ela já estivesse aberta. A seleção permanece explícita; projetos anteriores mantêm sua variante.

Checkpoint oficial: [FastVideo/FastH3-Omni-Comfy](https://huggingface.co/FastVideo/FastH3-Omni-Comfy), INT8 ConvRot, `fasth3_omniref_8step_pruned_int8_convrot.safetensors`. SHA-256 `851b2dc9670ed864b7f1e951ac9da047d83b1c04ded9bfcc1a9e5bba0ee33f80`. Carregamento exige recibo ligado ao tamanho e data do arquivo, enum do runtime e nós obrigatórios presentes.

Usa Ref2VA nativo, 8 passos, guidance 1, shifts vídeo 12/áudio 3, RES multistep e a cadeia obrigatória SageAttention → proteção de quatro grupos → Spectrum com audio replay. Áudio nativo permanece opcional, conforme a escolha do usuário. Não usa o backend NVFP4/sparse-attention do FastVideo.

A imagem é uma referência de aparência, não um primeiro quadro exato. O backend conecta imagens, vídeo com sua trilha e áudio de referência pelos sockets nativos. Último quadro exato, guia intermediário, continuação longa e adaptadores criativos não qualificados são bloqueados. O teste real desta instalação cobriu texto para vídeo com áudio; referências foram verificadas por testes de ligação e dispatch, ainda sem qualificação visual comparativa.

O runtime recebeu apenas o ajuste oficial para as 32 cabeças PDD em `comfy/model_detection.py` e `comfy/ldm/minimax/model.py`. A detecção foi verificada com o cabeçalho real do Omni e com cabeças convencionais; o H3 Base também concluiu um render após o ajuste.

Na RTX 5090, uma execução por variante, 1088×608, 124 quadros/24 FPS, mesmo prompt e seed, áudio habilitado: Omni 8 passos levou **65,70 s**; H3 Production Base 10 passos levou **67,65 s**. A amostragem indicada no log caiu de aproximadamente **20 s para 16 s**. O total caiu aproximadamente 2,9% nessa medição. Cache, carregamento e decodificação influenciam o total; isso não é uma média estatística nem garantia para outras cenas, durações ou referências.

São testes nativos de engenharia, sem acabamento ou entrega artística. RIFE, upscale e DLSS não estão incluídos nesses tempos e não foram qualificados novamente nesta mudança. Qualidade do Omni permanece `PENDING_OWNER_REVIEW`; nenhuma mídia histórica foi substituída.

Evidências e rollback: `dados/validation/fasth3_omni_20261021/`. Inclui grafos, resultados MCP, recibo do modelo, logs, hashes, testes, arquivos nativos e cópias `before/`. Duas tentativas falharam durante a atualização do suporte PDD e permanecem no histórico; a tentativa bem-sucedida é `0c455ecd-cf04-46bf-81cc-32b196cd7af6`.
