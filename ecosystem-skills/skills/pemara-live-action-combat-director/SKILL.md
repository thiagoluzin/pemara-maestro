---
name: pemara-live-action-combat-director
description: "Dirige combate live action humano com golpes assinatura, propriedade correta de armas e poderes, massa, contato e reação. Use quando personagens conhecidos precisam lutar sem virar coreografia genérica, efeito decorativo ou ação galhofa."
---

# Pemara Live Action Combat Director

## Receita aprovada pelo proprietário — TEST05, 08/11/2026

Para reutilizar o combate humano com trocas rápidas aprovado no TEST05, consulte
`E:/Pemara/.agents/skills/pemara-combate-aprovado/SKILL.md`. Ela preserva o grafo,
prompt, vídeo exato, hashes e backup; a biblioteca Maestro está em
`maestro/pemara/ferramentas/video_global_engine/workflows/combat_approved/test05_fast_bilateral_v1/recipe.json`.
O TEST05 foi aprovado com dez segundos, H3 Base start-only, Sage + Spectrum, sem
LoRAs adicionais e sem guia corporal. Preserve esses aspectos quando esse esquema
for solicitado; não force a duração de oito segundos dos contratos anteriores.
Continuum e referências persistentes são variantes novas, com revisão própria.
Essa aprovação não certifica física perfeita, novas armas ou um treinamento global.

## Intenção e leitura do combate

Receba o arco da sequência da produção. Cada troca precisa de objetivo, tentativa, defesa/contra-ação e mudança de iniciativa. A tática deve revelar personalidade e informação nova, sem adicionar golpes só para preencher duração.

Com `pemara-performance-director`, dirija olhar, leitura do adversário, esforço, reação e recuperação. Com `pemara-cinematography-director`, mantenha base e linha de ataque/contato legíveis. Clarão, som ou corte não substituem contato. O editor recebe vetores e fases de ação, não apenas poses bonitas.

O contrato de oito segundos abaixo é específico. Se âncoras futuras causarem reação antecipada ou congelamento em duas tentativas, aplicar a rota start-only qualificada de `pemara-live-action-showrunner`; não insistir em duas âncoras por uma regra genérica. Corrigir o método, mantendo H3, identidade e aspectos aprovados. Acabamento segue o AGENTS vigente, sem Foley novo por padrão.

Ausência de alucinação não é aprovação de combate. Um take estável continua reprovado quando não demonstra a identidade motora dos personagens, força ou consequência.

## Fontes canônicas

- Workflow: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/signature-combat.workflow.json`
- Compilador: `E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py`
- Showrunner: `E:/Pemara/.agents/skills/pemara-live-action-showrunner/SKILL.md`
- Movimento: `E:/Pemara/.agents/skills/pemara-video-motion-director/SKILL.md`
- QC: `E:/Pemara/.agents/skills/pemara-live-action-qc/SKILL.md`

Leia `references/signature-combat-contract.md` ao criar ou revisar o contrato de uma luta com personagens e golpes reconhecíveis.

## Regra de direção

Trave a escolha do golpe antes do prompt. O modelo pode resolver somente equilíbrio, passos de ligação, tecido e microvariações humanas. Nunca escreva “deixe o modelo escolher os golpes”, “luta intensa” ou equivalente como fonte principal da coreografia.

Para cada personagem, registre:

- personalidade corporal, guarda, distância preferida e ritmo;
- golpes, armas, poderes, cor e mecanismo que realmente lhe pertencem;
- golpes, poderes e cores proibidos;
- sinal visual mínimo que torna o personagem reconhecível durante a ação, não apenas parado.

Distribua os golpes assinatura na sequência. Presença nominal no prompt não conta: o golpe deve controlar preparação, trajetória, contato e consequência visíveis.

## Plano contínuo de combate H3

Para pancadaria bilateral, use `h3_live_action_continuous_bilateral_combat_8s`: MiniMax H3 FL2VA, 192 quadros nativos a 24 fps, 1280×720 e 20 passos. O padrão comprovado é um plano ininterrupto de oito segundos no qual os dois lutadores atacam, defendem, são deslocados e recuperam iniciativa. Unidades independentes de aproximadamente cinco segundos não são o padrão de montagem de luta: aumentam resets e emendas.

Na rota FL2VA de duas âncoras, use exatamente duas imagens aprovadas e vinculadas por hash; a rota start-only qualificada, quando aplicável, exige somente a inicial:

1. início dinâmico, já pagando o movimento herdado;
2. fim dinâmico, entregando vetor corporal e de câmera ao corte seguinte.

Não injete âncora intermediária de contato em combate contínuo. Uma pose futura fixada no meio do latent pode puxar a reação do defensor para antes do golpe. Golpes, bloqueios e contatos internos são dirigidos pelo ledger temporal e verificados no MP4 completo.

`h3_live_action_signature_combat` com 124 quadros e três âncoras fica restrito a gesto técnico isolado, arma, transformação ou pose icônica cuja geometria não caiba com segurança em um plano bilateral. Ele não deve ser encadeado como fonte principal de uma luta longa.

## Cadeia física obrigatória

Todo golpe precisa mostrar `anticipation → propulsion → contact/evasion → displacement → reaction → recovery`.

- A força nasce no chão, quadril, tronco ou trajetória da arma.
- O centro de massa do atacante se desloca; o defensor perde base ou muda vetor.
- Roupa, cabelo, lama, água, casca, folhas ou destroços respondem depois do corpo, com atraso e direção coerentes.
- A câmera mostra a linha do ataque e o contato. Tremor, clarão, corte ou oclusão não carregam o impacto no lugar dos corpos.
- O take termina durante queda, perseguição, recuperação ou entrega vetorial; nunca em pose sustentada.
- A resposta involuntária ao impacto (voo, queda ou recuo causado pelo golpe) não precede o contato. Esquiva, bloqueio, passo de defesa e contra-ação motivados pela leitura do atacante podem começar antes; cada evento precisa declarar sua causa.
- Deslocamento no chão exige passada, pivô, sulco de frenagem, rolamento ou arrasto visível; translação rígida dos pés reprova o take.
- Salto exige compressão e impulso antes da fase aérea, arco balístico legível e aterrissagem; suspensão sem causa reprova o take.

## Ciclo de arma ou poder

Registre `ownerId`, tipo, ligação física, surgimento, trajetória, contato, dissipação e consequência ambiental. Energia e arma não podem trocar de proprietário, atravessar corpos sem resultado, virar feixe solto nem permanecer depois que a ação terminou.

Exemplos de distinção:

- energia presa à silhueta ou membro acompanha a mecânica corporal; não substitui o membro;
- fogo nasce de uma ação declarada e ilumina material próximo; não surge como faixa decorativa no chão;
- corrente tem origem, tensão, peso, arco, ponto de fixação e retorno; não flutua nem multiplica.

## Reprovação

Reprovar mesmo com rosto, anatomia e decode perfeitos quando:

- qualquer lutador poderia trocar de roupa e a cena continuaria igual;
- o golpe assinatura aparece só como nome, flash ou cor;
- contato não desloca centros de massa;
- o adversário espera o golpe, cai por conta própria ou recupera a guarda sem inércia;
- o efeito pertence ao personagem errado;
- câmera, RIFE ou Foley fingem velocidade e peso ausentes na fonte.

Uma falha sistêmica de combate reprova a rota inteira. Preserve o master como rollback, bloqueie montagem e acabamento, registre a correção no mesmo escopo e volte ao contrato e às âncoras. RIFE, Foley e upscale começam somente após picture lock humano.

## Saída

Entregue a matriz de combate, cobertura de golpes na sequência, contrato por take da rota escolhida, plano de âncoras, perfil H3, estado dos gates e motivo exato de qualquer bloqueio. Não gere nem promova vídeo sem os eventos de aprovação e admissão GPU exigidos.

## Identidade visual versionada — aprendizado R17 (2026-09-08)

Leia `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md` para o contrato e os templates executáveis. Em novos clipes com personagens recorrentes, declare `identityContinuityRequired: true`; mantenha a animação avulsa de foto fora desse gate.

Receba a ficha canônica da continuidade. O bloco fixo de identidade/material é compilado de `identityContinuity.bible`; trabalhe no bloco variável de ação, câmera e magia. Não limpar traje, trocar braceletes, alterar corpo/rosto ou reapresentar personagens ao corrigir combate. Preserve física, iluminação, água e materialidade já aprovadas. Use revisão separada: `identity` não implica `combat`, e `combat` não compensa falha de `identity`.

Para personagens existentes, começar pela etapa zero de pesquisa do contrato: versão/encarnação/traje, fontes e evidência por tópico. Não trabalhar só de memória ou misturar versões. Revisar fontes reais antes de marcar research REVIEWED; adaptar o cânone apenas com direção registrada do proprietário. Projeto encerrado não reabre por essa pesquisa.

O campo legado `defenderMotionBeforeContactForbidden` continua obrigatório para compatibilidade com o compilador; expressa a proibição de resposta ao impacto antes da causa, não a imobilização do defensor. Não altere o schema de produções históricas. Declare defesas antecipatórias separadamente no ledger e revise sua causalidade no MP4. A geometria do perfil `h3_approved_action_720p8s` é 1280×720; outros perfis Hero/Master usam 1344×768. Confirme o perfil resolvido no plano; não confundir as rotas.
