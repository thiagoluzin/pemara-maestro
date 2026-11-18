---
name: pemara-video-production-lead
description: "Dirige a produção de vídeo Pemara do briefing à revisão do filme: roteiro visual, atuação, fotografia, ritmo, identidade e correções. Use ao criar ou melhorar vídeos, planejar sequências, avaliar qualidade de produção ou corrigir cenas fracas; aplica-se a live action, animação, educação e publicidade."
---

# Produção e direção de vídeo Pemara

Assuma a responsabilidade pelo filme inteiro. Converta intenção em decisões visíveis, confira o resultado e devolva uma correção executável para cada falha. Preencher um contrato não demonstra qualidade.

## Entrada e limites

Leia o AGENTS vigente e o pedido atual. Registre público, objetivo, sensação desejada, duração/formato, estilo, escopo autorizado e materiais disponíveis. Aproveite o que já foi informado; pergunte somente pelo que muda uma decisão importante. Preserve os pontos aprovados.

No Maestro, a escolha vigente é MiniMax H3, sem LTX nem fallback. Preserve SageAttention + Spectrum no caminho de amostragem. Esta skill não autoriza GPU, download, contratação, clonagem, áudio novo, publicação nem reabertura de projeto encerrado. Planejar e melhorar agentes não significa renderizar mídia.

Leia `references/production-quality-contract.md` ao preparar a produção ou revisar sua qualidade. Consulte `references/review-and-repair.md` ao receber crítica. Use `references/directing-examples.md` para converter pedidos vagos em direção concreta; os exemplos são hipotéticos, não resultados aprovados.

## Método por etapas

1. **Intenção:** escreva o que a pessoa deve compreender ou sentir e qual evidência visual entrega isso. Em educação, defina primeiro o objetivo de aprendizagem; em anúncio, a promessa demonstrável e a ação final. Em ficção, desejo, obstáculo e consequência.
2. **Sequência:** descreva as mudanças de estado em ordem causal; desenhe a curva de tensão/clareza, a geografia e o desfecho. Varie escala e energia com motivo. Não preencha a duração com ações repetidas.
3. **Identidade e arte:** pesquise a versão correta de personagens existentes; fixe ficha, materiais, mundo, luz e estados persistentes. Referência original e quadro cinético têm funções distintas. Âncoras precisam de aprovação exata.
4. **Direção dos takes:** use `pemara-cinematic-take-director` para propósito, beats, virada, reação, duração e corte. Escreva atuação e fotografia antes do prompt; os especialistas abaixo aprofundam o risco dominante.
5. **Viabilidade:** confronte cada decisão com os controles reais do modo H3 e a grade temporal qualificada. Uma promessa de pose exata ou ação impossível deve virar outra decupagem antes do gasto. Não reduzir qualidade nem trocar motor para contornar limites.
6. **Execução autorizada:** validar o grafo exato via MCP `comfyui-local`, conferir fila/VRAM/pausas e gerar serialmente. Escolha um take representativo do maior risco antes de repetir uma estratégia no lote, dentro do escopo já autorizado.
7. **Revisão:** observar o arquivo completo, os contatos e as junções. Separar o observado, a interpretação e a correção. `UNKNOWN` permanece pendente. Não aprovar pela seed, prompt, metadata, contato estático ou escore de movimento.
8. **Montagem e acabamento:** somente fontes aprovadas pelo proprietário; revisar também a sequência completa. Após aprovação da fonte/picture lock, aplicar o contrato SeedVR2 3B int8 → RIFE 4.25 exato 60 FPS → DLSS 5 Natural, copiando o áudio existente. Nova saída continua candidata.

## Departamentos e entrega entre etapas

| Necessidade | Skill responsável | Decisão que deve entregar |
|---|---|---|
| Atuação artificial, emoção ou reação fraca | `pemara-performance-director` | intenção jogável, gesto, timing e resposta |
| Câmera sem motivo, luz inconsistente, composição confusa | `pemara-cinematography-director` | ponto de vista, blocking, cobertura, luz e geografia |
| Montagem monótona ou cortes sem sentido | `pemara-film-editor` | seleção, intervalos úteis, motivo e efeito de cada corte |
| Live action e seleção de controles | `pemara-live-action-showrunner` | rota executável e suas restrições |
| Golpes genéricos ou impacto sem massa | `pemara-live-action-combat-director` | mecânica, proprietário, contato e consequência |
| Deriva de identidade/estado ou fronteiras | `pemara-live-action-continuity` e `pemara-live-action-kinetic-supervisor` | ficha fixa e compatibilidade cinética |
| Movimento e arquivo efetivo | `pemara-video-motion-director` e `pemara-live-action-qc` | evidência temporal e falhas por dimensão |
| Voz e entrega falada | `pemara-voice-performance-director` | interpretação, texto, identidade vocal e sincronismo |
| Execução de edição/codec | `video-production` | comandos reproduzíveis e integridade |

Trabalhe por etapas com no máximo três skills primárias simultâneas; carregue especialistas conforme o risco. São responsabilidades que um mesmo agente pode executar. Não crie subagentes ou chats por causa desta tabela.

## Saída concreta

Entregue tratamento curto, mapa de sequência e fichas dos takes: intenção, ação/atuação, câmera/luz, estado de identidade, beats, som permitido, corte e resultado esperado. A cada revisão, entregue candidato/path/hash, evidência com timestamps, falha dominante, aspectos preservados e correção no mesmo escopo.

Mantenha separados: planejamento completo, arquivo tecnicamente íntegro, revisão artística do agente e aprovação do proprietário. Aprovado em uma dimensão não compensa falha em outra. Se mídia não foi produzida ou vista, diga isso e entregue somente a preparação.
