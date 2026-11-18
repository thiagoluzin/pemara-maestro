---
name: pemara-live-action-qc
description: "Audita MP4s live action humanos do Pemara por identidade, anatomia, pele, materiais, física, câmera, continuidade e cauda estática; controla picture lock, RIFE, Foley, upscale, aprovação exata e rollback."
---

## Câmera e preservação dos atores — 2026-10-09

Exija evidência temporal por fonte e fronteira do bloco piloto, depois do filme inteiro. Inclua regressões de porta sem percurso, reposicionamento do perseguidor, corpo extra, reset de pose, reação antecipada, contato fora de quadro e atores plastificados. Compare pele, cabelo, mãos, traje e cenário entre a âncora e sua fonte, e entre o vídeo nativo e o acabado. Marque em qual etapa a aparência mudou.

Para o mapa, as evidências temporais e os reparos, consulte o [contrato de câmera](../pemara-video-production-lead/references/camera-evidence-and-actor-protection.md). Preserve o motor e o escopo já autorizados.


# Pemara Live Action QC

## Revisão artística completa

Leia `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md` para registrar evidência por dimensão. Além de identidade, física e técnica, avaliar história/clareza, atuação, fotografia, ritmo e som disponível. Assistir ao MP4 completo, conferir contatos e junções densamente e ouvir o áudio real; se não houver acesso temporal/escuta, deixar esses itens `PENDING`.

Não confundir o rótulo `PASS_TECHNICAL_PENDING_HUMAN_REVIEW` com passe artístico. Uma dimensão artística `FAIL` bloqueia seleção mesmo com decode perfeito. `PASS` do agente precisa de observações e timestamps; aprovação do proprietário exige evidência do artefato exato. `NOT_APPLICABLE` precisa de motivo, nunca serve para ignorar uma falha.

Para cada defeito, entregar intervalo, observação, efeito na cena, hipótese de causa, correção prioritária e aspectos aprovados preservados. Não exigir nova geração por uma inspeção retrospectiva de projeto encerrado. Não calcular nota média que compense identidade ou causalidade falha.

Avalie o arquivo real. Prompt, seed, grafo, metadata e render sem erro não provam qualidade visual.

## Fontes canônicas

- Eventos e gates: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/events.json`
- Checklist base: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/templates/qc_checklist.md`
- Gate de sequência: `E:/Pemara/.agents/skills/pemara-cinematic-take-director/scripts/sequence_regression_gate.py`
- Gate de movimento: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/tools/transition_motion_gate.py`

## QC por candidato

1. `ffprobe`: decode, duração, resolução, FPS, frames e streams.
2. Reprodução integral quadro a quadro nos contatos e amostragem temporal densa do restante; 0%, 25%, 50%, 75% e 100% servem apenas como índice, nunca como prova de física.
3. Identidade: mesmo rosto, idade, cabelo, escala, roupa, acessórios, anatomia e estado de transformação.
4. Material live action: pele com textura natural, cabelo com fios, roupa com costura/peso, sombra de contato e VFX integrados; reprovar cera, beauty filter, CGI plástico, anime ou cosplay limpo.
5. Movimento: câmera física, perspectiva, três planos, duas ações internas, contato, reação, deslocamento e progressão até o último intervalo.
6. Fronteiras: velocidade herdada/entregue, geografia e dano persistentes; zero fade, freeze, hold, reset ou cauda parada.
7. Compare caminho, SHA-256 e escopo com âncoras e artefato realmente aprovado.
8. Gate causal obrigatório: identifique o primeiro quadro de contato e o primeiro quadro de reação relevante. Reprove se voo, queda, recuo ou rotação do defensor começarem antes da causa visível.
9. Gate de chão obrigatório: reprove translação rígida sem passada/pivô/skid/rolamento/arrasto e qualquer suspensão sem impulso, impacto ou aterrissagem legíveis.

## Gate de presença para combate

Ausência de defeito não basta. Em luta com personagens reconhecíveis, confronte o MP4 com a matriz de combate e reprove quando faltar qualquer item:

1. golpe dominante pertence ao personagem correto e mantém sua silhueta/mecânica reconhecível;
2. antecipação, propulsão, contato ou evasão, deslocamento, reação e recuperação aparecem na imagem;
3. centro de massa do defensor responde ao vetor antes de câmera, clarão ou som tentarem vender impacto;
4. arma ou poder preserva proprietário, ligação, surgimento, trajetória, contato, dissipação e consequência ambiental;
5. nenhum golpe genérico substitui a cobertura assinatura prometida pela sequência.

Marque separadamente `IDENTITY_VISUAL_PASS` e `COMBAT_IDENTITY_PASS`. O primeiro nunca implica o segundo.

Nas junções, marque corpo, fase de ação, câmera/geografia, arma/efeito e dano como `MATCH`, `RECOVERABLE_BY_CAUSAL_CONNECTOR` ou `SOURCE_REGEN_REQUIRED`. Um único `SOURCE_REGEN_REQUIRED` nesses canais bloqueia montagem; similaridade dos dois frames de borda não basta.

Se a rota tiver `generatedConnectorAllowed: false`, trate
`RECOVERABLE_BY_CAUSAL_CONNECTOR` como `SOURCE_REGEN_REQUIRED`. O gate deve
confirmar zero clipes de ligação na lista de fontes e reprovar qualquer montagem
que reintroduza unidades curtas como emenda.

Em cadeia start-only, verifique separadamente começo e fim: a fonte deve abandonar a
imagem inicial sem hold perceptível, e a saída escolhida deve ter movimento útil antes
e depois dentro do MP4. Registre o frame, timestamp e SHA-256 da saída propagada.
`last_frame` ausente é requisito do grafo; pose interpolada, cauda congelada ou salto
entre o quadro propagado e o primeiro movimento do take seguinte reprova a fonte.

## Decisão

- `PASS_TECHNICAL_PENDING_HUMAN_REVIEW`: tecnicamente íntegro, ainda não aprovado.
- `REPLACEMENT_REQUIRED`: preserve o rejeitado como rollback, bloqueie montagem/promoção e gere candidato corrigido somente no mesmo escopo autorizado.
- `BLOCKED`: evidência, integridade, engine, autorização ou admissão GPU ausente.
- `OWNER_APPROVED_EXACT_ARTIFACT`: somente após o proprietário assistir ao arquivo/hash exato.

## Acabamento

Após a aprovação da fonte, confira a rota do tipo declarado e os recibos previstos no [contrato de âncoras e acabamento de vídeo](../pemara-video-production-lead/references/dlss5-full-frame-required.md). Compare a candidata com o nativo e o áudio existente e encaminhe à revisão humana. Preserve a fonte silenciosa quando não houver áudio.

RIFE cria quadros temporais; não corrige rosto, mãos, física, câmera ou corte. Upscale aumenta resolução; não transforma take defeituoso em take bom. Preserve sempre o original nativo e toda rejeição.

## Identidade visual versionada — aprendizado R17 (2026-09-08)

Leia `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md` para o contrato e os templates executáveis. Em novos clipes com personagens recorrentes, declare `identityContinuityRequired: true`; mantenha a animação avulsa de foto fora desse gate.

Use `validate_candidate_review` de `services/studio/identity_continuity.py` para verificar vínculos de evidência, não para classificar imagens. Registre candidato/hash, ficha/hash, revisor e observações de início/meio/fim com timestamps, além da revisão de contatos e junções exigida acima. Avalie separadamente `identity`, `combat`, `physics`, `lighting`, `water`, `realism`; FAIL ou PENDING impede seleção pelo contrato. PASS do revisor não é aprovação do proprietário. Compare também com a ficha original, não só com o take anterior. Projeto encerrado não entra em ciclo automático de correções por análise retrospectiva.

Para personagens existentes, começar pela etapa zero de pesquisa do contrato: versão/encarnação/traje, fontes e evidência por tópico. Não trabalhar só de memória ou misturar versões. Revisar fontes reais antes de marcar research REVIEWED; adaptar o cânone apenas com direção registrada do proprietário. Projeto encerrado não reabre por essa pesquisa.
