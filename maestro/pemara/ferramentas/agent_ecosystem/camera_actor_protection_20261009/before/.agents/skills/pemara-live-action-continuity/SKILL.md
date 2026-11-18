---
name: pemara-live-action-continuity
description: "Cria continuidade física e conectores MiniMax H3 entre takes live action sem crossfade, freeze, cauda estática ou reset. Use para juntar takes naturalmente, manter direção, velocidade, geografia, luta e movimento de câmera."
---

# Pemara Live Action Continuity

## Continuidade de intenção e estado

Além do vetor físico, preservar o que cada personagem sabe, procura, teme e acabou de perceber. Um corte pode manter a pose e perder a reação ou a iniciativa; compare os beats da produção e a partitura de atuação.

Entregar ao `pemara-film-editor` intervalos úteis, estado cinético e motivo de junção. Campos de ação irreversível dentro do conector aplicam-se apenas quando existe conector permitido; corte direto não exige gerar uma ponte. O quadro propagado preserva pose/movimento; rosto, materiais e proporções continuam comparados com a ficha original.

Não pedir conector automaticamente para toda fronteira. Falha de identidade, física ou geografia exige fonte corrigida. Repetição de dano desaparecendo não se resolve por transição editorial.

Una takes pela ação física, não por disfarce editorial.

## Fontes canônicas

- Workflow: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/moving-connector.workflow.json`
- Compilador: `E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py`
- Gate: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/tools/transition_motion_gate.py`
- Direção de movimento: `E:/Pemara/.agents/skills/pemara-video-motion-director/SKILL.md`
- Supervisão cinética: `E:/Pemara/.agents/skills/pemara-live-action-kinetic-supervisor/SKILL.md`

## Handoff obrigatório

Para cada fronteira, registre:

1. último intervalo útil do take A e primeiro intervalo útil do take B;
2. direção e velocidade de corpo, objeto, efeito e câmera nos dois lados;
3. pose, guarda, transformação, dano e estado ambiental persistentes;
4. geografia de foreground, midground e background;
5. uma ação irreversível que progride dentro do conector;
6. frames inicial e final vindos de trechos com movimento antes e depois, ambos aprovados por hash.
7. estado cinético dos personagens: centro de massa, classe de velocidade, pé de apoio, rotação do tronco, fase dos membros, olhar e contato;
8. estado de câmera, arma/poder e dano ambiental, com decisão `DIRECT_KINETIC_CUT`, `GENERATED_MOVING_CONNECTOR` ou `REGENERATE_SOURCE`.

Planeje a fronteira antes dos dois takes. Prefira uma âncora dinâmica compartilhada e corte cinético direto. Gere conector somente quando as duas fontes já forem boas e uma ação curta, causal e irreversível puder conciliar a diferença. Havendo reset de corpo, câmera, identidade, geografia, arma, efeito ou dano, regenere a fonte.

Uma reprovação explícita do proprietário à estratégia de conectores é um bloqueio
de rota, não uma sugestão estética. Marque `generatedConnectorAllowed: false`,
retire todos os conectores da montagem ativa e resolva a sequência por regeneração
dos planos principais e cortes de ação. Não reduza o mesmo remendo para outra
duração nem o publique oculto.

Para uma cadeia de combate I2VA, a fronteira nasce do material aceito: selecione um
quadro com corpo, câmera, roupa e ambiente ainda em movimento, preserve seu hash e
use-o como única âncora inicial da fonte seguinte. Não imponha uma âncora final quando
ela já tiver produzido desaceleração, pose ou congelamento. No corte, remova somente
o quadro duplicado; qualquer incubação estática ou salto de vetor exige regeneração,
não hold, crossfade ou conector.

## Construção

- Use `h3_live_action_moving_connector`, MiniMax H3 FL2VA e duração narrativa de 4–5 s na grade temporal suportada.
- Materialize o grafo real com `build_live_action_comfy_graph`; construir o JSON é CPU-only e não autoriza nem inicia a fila.
- Comece já com a velocidade herdada; não gaste o primeiro segundo recompondo uma pose.
- Faça 0–30% continuar a entrada, 30–70% executar o evento e 70–100% entregar consequência ainda em movimento.
- Preserve eixo e espaço compartilhado, mas permita reorientação física de câmera quando a perspectiva continuar legível.
- Use `MiniMaxH3AddGuide` somente para um beat intermediário aprovado; não anuncie pose exata.

## Reprovação automática

- qualquer crossfade/xfade;
- freeze, frame duplicado deliberado, hold ou cauda estática;
- zoom digital sem translação/perspectiva;
- âncora retirada de pose parada;
- reset de direção, guarda, golpe, dano, escala ou cenário;
- partículas/luz como único movimento;
- RIFE usado para esconder falha de continuidade.
- primeiro segundo gasto para recompor pose, centralizar atores ou recuperar velocidade;
- conector usado para esconder troca com fumaça, fogo, galho, whip-pan, escuridão ou tremor.

## Gate e saída

Rode o contrato antes da GPU e o gate de aprovação sobre o MP4 real depois. Inspecione 0%, 25%, 50%, 75%, 100% e a fronteira quadro a quadro. Entregue `PASS_TECHNICAL_PENDING_HUMAN_REVIEW`, `REPLACEMENT_REQUIRED` ou bloqueio explícito; nunca inferir aprovação do proprietário.

## Identidade visual versionada — aprendizado R17 (2026-09-08)

Leia `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md` para o contrato e os templates executáveis. Em novos clipes com personagens recorrentes, declare `identityContinuityRequired: true`; mantenha a animação avulsa de foto fora desse gate.

Mantenha a ficha canônica original e a tabela de estados por take. Compare as âncoras com a ficha e com a saída anterior; o último frame é referência cinética, nunca a única referência de identidade. Registre lama, água, rasgos, danos e acessórios em entrada/saída; mudanças precisam de causa. Em I2VA start-only, não acrescente guias finais para cumprir a ficha: a conferência ocorre na preparação da âncora, no bloco fixo do prompt e no QC. Registre o estado de saída em arquivo com hash para a próxima entrada.

Para personagens existentes, começar pela etapa zero de pesquisa do contrato: versão/encarnação/traje, fontes e evidência por tópico. Não trabalhar só de memória ou misturar versões. Revisar fontes reais antes de marcar research REVIEWED; adaptar o cânone apenas com direção registrada do proprietário. Projeto encerrado não reabre por essa pesquisa.
