---
name: performance-optimizer
description: "Mede e corrige gargalos de aplicação, banco, memória e renderização. Entrada canônica de performance, com módulos para a stack existente e comparação antes/depois."
---

# Performance com qualidade preservada

Leia `E:/Pemara/.agents/skills/pemara-messenger-turbo/references/operating-contract.md` uma vez por contexto.

1. Feche comportamento e qualidade que devem permanecer iguais. Identifique stack, dispositivo/carga e sintoma; não otimizar por palpite.
2. Leia [measurement.md](references/measurement.md) e obtenha baseline. Perfis de web, banco, jogo e GPU têm métricas diferentes.
3. Escolha o gargalo demonstrado e uma alteração proporcional. Use [web-and-data-recipes.md](references/web-and-data-recipes.md) apenas se web/React/banco forem pertinentes.
4. Compare antes/depois nas mesmas condições e execute a regressão afetada. Preserve interfaces, acessibilidade, segurança, áudio e resultado visual. Não reduzir passos, resolução, conteúdo, precisão necessária ou trocar motor para anunciar velocidade.
5. Entregue métricas observadas, ambiente, mudança, tradeoffs e limitações. Ausência de medida significa melhoria ainda não demonstrada.

`performance-optimization` encaminha a esta família. Para Unity, Phaser ou GPU, consulte o profiler e documentação da versão/stack escolhida; não impor Lighthouse a runtime nativo. Caches privados/admin, dados financeiros e limites de autorização não podem virar conteúdo público.

## Depois do ComfyUI

Após cada execução concluída conduzida pelo agente, aplicar [post-comfyui.md](references/post-comfyui.md) antes de encerrar a entrega. Medições em código, julgamentos semânticos com [decision-ai](C:/Users/admin_remoto/.codex/skills/decision-ai/SKILL.md), preferência por script/terminal quando adequado ao uso próprio. Esta etapa não instala um hook no servidor.
