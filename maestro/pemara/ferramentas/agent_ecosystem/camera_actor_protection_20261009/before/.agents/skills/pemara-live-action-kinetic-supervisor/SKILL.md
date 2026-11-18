---
name: pemara-live-action-kinetic-supervisor
description: "Supervisiona o meio-termo entre identidade humana, movimento real e continuidade cinética em live action. Use quando personagens precisam permanecer fiéis sem parecer bonecos, ou quando junções entre takes perdem impulso, pose, câmera, objeto, efeito ou geografia."
---

# Pemara Live Action Kinetic Supervisor

## Fronteiras no filme completo

Receba da produção os beats e do editor os intervalos reais escolhidos. Compare movimento antes/depois do corte, estímulo/resposta, intenção, iniciativa e estado ambiental. Similaridade de pose não garante velocidade ou causalidade.

Registre observações com timestamps e frame de contato/reação quando disponíveis; não invente medida física ou escore decimal. Entregue separadamente compatibilidade cinética, falhas de identidade e falhas de atuação/fotografia para os especialistas; um canal não compensa outro. A montagem completa também precisa ser revista.

O método não cria áudio nem autoriza geração de emendas. H3 permanece com Sage + Spectrum, acabamento e aprovação exata seguem o AGENTS atual.

Trave quem o personagem é; dirija como ele se move; conecte o estado físico, não apenas imagens parecidas.

## Fontes canônicas

- Continuidade: `E:/Pemara/.agents/skills/pemara-live-action-continuity/SKILL.md`
- Combate: `E:/Pemara/.agents/skills/pemara-live-action-combat-director/SKILL.md`
- Workflow de handoff: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/moving-connector.workflow.json`
- Compilador: `E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py`
- Gate de movimento: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/tools/transition_motion_gate.py`

Leia `references/kinetic-affinity-contract.md` ao planejar ou revisar duas unidades adjacentes.

## O meio-termo

Separe o contrato em três camadas:

1. **Identidade imutável:** rosto, idade, proporções, anatomia, cabelo, roupa, material, dano, arma e poder pertencente.
2. **Envelope de performance:** guarda, assimetria, ritmo, amplitude, fadiga, distribuição de peso e ações permitidas. Isso pode variar naturalmente sem trocar o personagem.
3. **Estado cinético de fronteira:** posição, vetor e classe de velocidade do centro de massa, pé de apoio, rotação do tronco, fase dos membros, olhar/alvo, contato, câmera, objetos, efeitos e ambiente.

Não congele a camada 2 para proteger a 1. Uma pose idêntica em todos os quadros preserva aparência, mas mata a performance. Não libere a camada 1 para ganhar movimento; rosto ou corpo instável continua reprovado.

## Âncoras e liberdade controlada

- Use uma referência de casting/mundo para regenerar âncoras de ação consistentes.
- Para combate bilateral, use 192 quadros/8 s, 1280×720 e 20 passos. Comece com duas fronteiras dinâmicas somente enquanto o MP4 provar ação útil; se a âncora final produzir interpolação de poses ou cauda congelada, mude a rota para uma única âncora inicial dinâmica, como no take de combate owner-approved do Vejito R6.
- Fixe identidade, geografia, dono dos golpes e resultado global. Na rota start-chain, dê ao H3 liberdade controlada para passadas, bloqueios, contrapeso, recoil, tecido, recuperação e saída; a saída móvel tecnicamente aceita vira por hash a entrada do take seguinte.
- Reserve três âncoras/124 quadros para gesto técnico isolado, transformação, instrumento, arma ou pose icônica. Não monte uma luta longa como cadeia de microtakes independentes de cinco segundos.

## Junção natural

Planeje a fronteira antes de gerar os dois takes. O padrão é uma âncora dinâmica compartilhada e o mesmo estado cinético descrito no final de A e no começo de B.

Escolha:

- `DIRECT_KINETIC_CUT`: todos os canais relevantes são compatíveis; corte durante movimento útil.
- `GENERATED_MOVING_CONNECTOR`: os takes são individualmente bons e existe uma ação curta, causal e irreversível capaz de conciliar a diferença.
- `REGENERATE_SOURCE`: há reset de corpo, guarda, velocidade, câmera, geografia, dano, arma ou efeito. Não colar fontes incompatíveis.

Um conector nunca começa recompondo pose, nunca termina em pose e nunca serve para ocultar erro com galho, fumaça, fogo, whip-pan, escuridão ou tremor.

Quando o proprietário rejeita microtakes ou conectores curtos para a sequência,
somente `DIRECT_KINETIC_CUT` ou `REGENERATE_SOURCE` permanecem válidos. Essa
decisão deve constar no contrato da rota e nenhum clipe de ligação pode ser gerado,
interpolado ou inserido depois como correção editorial.

Uma cauda congelada por end-anchor não é uma fronteira válida. Corte antes dela só
quando o último quadro útil mantiver o vetor necessário e o take seguinte partir desse
mesmo quadro hash-travado sem incubação estática perceptível; caso contrário,
`REGENERATE_SOURCE`.

## Realidade do movimento

Exigir:

- centro de massa seguindo trajetória contínua;
- apoio e reação do chão antes da aceleração;
- rotação de quadril e tronco coerente com o membro ou arma;
- reação do atingido após causa visível, com atraso de roupa, cabelo, água e destroços;
- imperfeição humana controlada: passos de recuperação, diferença entre lados, fadiga e microcorreções;
- câmera com massa e operador: acelera, acompanha e desacelera; não teleporta nem reinicia para centralizar atores.

## Gate de afinidade

Compare os canais do contrato em vídeo, não apenas os frames de borda. Faça revisão temporal densa e confirme a ordem `propulsão → contato → reação`: se o defensor se move antes do contato, há falha causal. Confirme também cada apoio, passada, skid, rolamento, arrasto, decolagem e aterrissagem. Não invente uma pontuação decimal de precisão falsa. Marque cada canal `MATCH`, `RECOVERABLE_BY_CAUSAL_CONNECTOR` ou `SOURCE_REGEN_REQUIRED`.

Qualquer `SOURCE_REGEN_REQUIRED` em corpo principal, fase da ação, câmera/geografia, identidade ou propriedade de efeito bloqueia a montagem. RIFE, retime, Foley e upscale não mudam essa decisão.

## Saída

Entregue a matriz de fronteiras, decisão por junção, razão física, âncoras/hashes, gates pendentes e qual fonte precisa ser refeita. Nunca chame continuidade técnica de aprovação humana.
