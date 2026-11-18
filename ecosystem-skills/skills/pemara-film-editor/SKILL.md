---
name: pemara-film-editor
description: "Dirige montagem de vídeos Pemara: seleção de takes aprovados, cobertura, ritmo, tensão, causa e reação, continuidade e intenção sonora. Use para vídeo arrastado, repetição, corte brusco sem causa, montagem de luta, narrativa confusa ou revisão do filme completo."
---

## Câmera e preservação dos atores — 2026-10-09

Planeje cada fronteira antes da geração e revise os dois intervalos móveis, incluindo direção, velocidade, fase da ação e marcos do espaço. Exija revisão temporal do bloco piloto antes de repetir a cobertura no lote. Um conector precisa entregar uma ação narrativa ausente; mudanças inexplicadas de posição ou fundo exigem fonte corrigida. Registre revisão das fontes exatas e do filme inteiro no contrato de câmera, sem inventar escuta/reprodução.

Para o mapa, as evidências temporais e os reparos, consulte o [contrato de câmera](../pemara-video-production-lead/references/camera-evidence-and-actor-protection.md). Preserve o motor e o escopo já autorizados.


# Montagem e ritmo Pemara

Monte a experiência do público. Cada corte deve entregar informação, mudar a relação emocional ou continuar uma ação; alinhar tudo à batida musical não conta uma história por si só.

Leia `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md`. Receba sequência, geografia, partitura de atuação, fontes exatas aprovadas e restrições da rota. No FFVIII M08–M16, o contrato V8 específico prevalece sobre permissões genéricas de trim, retime e conectores.

## Antes de editar

Veja os takes inteiros e registre path, SHA-256, duração/FPS reais, intervalo útil, situação de aprovação e estado de saída/entrada. Não selecione rejeitados, 'melhores trechos' de fontes artisticamente contaminadas ou bitstreams apenas parecidos com os aprovados.

Planeje a cobertura ainda no roteiro. Se falta uma causa, reação ou consequência essencial, devolva a lacuna ao diretor; uma montagem não pode inventar o material ausente. Pedido de edição não autoriza novo render de cena.

## Ritmo e seleção

1. Pergunte a cada plano: que informação nova oferece, quando o público a entende e que expectativa passa ao seguinte?
2. Preserve o tempo para perceber o estímulo e ler a resposta. Remova repetição somente quando isso não mutilar atuação, movimento aprovado ou contrato específico.
3. Varie intensidade e escala para construir contraste; urgência não exige todos os planos curtos. Mantenha pausa deliberada quando contém decisão/tensão e foi dirigida.
4. Organize causa → reação → consequência. Corte cedo demais perde peso; tarde demais produz pose e redundância. Determine entrada/saída pelos frames reais, sem números inventados.
5. Teste a compreensão visual sem som quando adequado ao destino; depois revise com áudio. Preserve o áudio original na mídia de trabalho e na entrega, mesmo nessa inspeção silenciosa.

## Junções e continuidade

Prefira `DIRECT_KINETIC_CUT` quando os intervalos móveis concordam em vetor, fase da ação, identidade, eixo, objeto/poder e dano. Compare sequências de frames dos dois lados, não apenas um par de fotos.

`pemara-live-action-kinetic-supervisor` verifica a compatibilidade física. Estados diferentes com caminho causal exigem conector Flow dirigido por `pemara-live-action-continuity` na rota autorizada. Se `generatedConnectorAllowed: false`, a junção permanece bloqueada até haver fontes compatíveis. Sem caminho causal compatível, corrija a fonte.

Crossfade, hold, repetição de frames, speed ramp, fumaça, escuridão e whip-pan não podem esconder reset ou defeito. RIFE/upscale não recuperam identidade, massa ou causalidade. Transformações/retiming só são possíveis sobre fontes boas e dentro do contrato específico; jamais para disfarçar falha.

## Intenção de som

Marque evento visual, fonte sonora, perspectiva, entrada/saída e equilíbrio de voz/ambiente/música quando houver áudio autorizado. Não usar som de impacto antes do contato nem volume para fingir massa ausente. Não impor trilha a silêncio dirigido.

Preserve Foley, voz e trilha existentes. Novo áudio exige escopo explícito. Alterações de mix são candidatos separados com escuta real; LUFS e sincronismo técnicos não provam emoção, peso ou naturalidade.

## Picture lock e entrega

Revise o filme completo: começo compreensível, progressão, personagens, geografia, luz, danos persistentes, respiração, payoff e últimos segundos. Um conjunto de takes bons pode formar uma sequência ruim. Identifique o problema pelo timestamp da montagem e pelo take de origem.

Entregue tabela de montagem com fontes/hashes, in/out em frames e segundos, motivo de corte, estado cinético e uso de áudio. `video-production` executa e mede a edição. Não converter FPS, escala ou canais silenciosamente.

A aprovação do proprietário sobre a montagem exata estabelece o picture lock. Para acabamento autorizado, siga o [contrato de âncoras e acabamento de vídeo](../pemara-video-production-lead/references/dlss5-full-frame-required.md). Preserve a fonte e copie o áudio existente. A nova saída exige revisão própria antes de qualquer promoção ou publicação.

## Conectores entre estados diferentes — regra obrigatoria do proprietario

Se a saida e a entrada de takes estiverem em estados diferentes, usar conector causal com Flow; corte direto so para estados compativeis comprovados. Ler e seguir `E:/Pemara/.agents/skills/pemara-film-editor/references/flow-joins-required.md`. Registro de grafo nao substitui execucao nem revisao temporal.
