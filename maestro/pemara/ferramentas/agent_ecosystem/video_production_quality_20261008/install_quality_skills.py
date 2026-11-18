from pathlib import Path
import json

ROOT = Path('E:/Pemara')
SKILLS = ROOT / '.agents/skills'
lead = SKILLS / 'pemara-video-production-lead'
files = {
'pemara-video-production-lead/SKILL.md': '''---
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
''',
'pemara-cinematography-director/SKILL.md': '''---
name: pemara-cinematography-director
description: "Dirige fotografia de vídeos Pemara: enquadramento, blocking, ponto de vista, lente, câmera motivada, profundidade, luz e cobertura. Use para imagem bonita mas confusa, câmera gratuita, geografia perdida, iluminação inconsistente ou planejamento visual de cenas."
---

# Fotografia e câmera Pemara

Faça a câmera mostrar a informação certa no momento certo. Aparência cinematográfica depende de composição, espaço e luz consistentes; escrever 'cinematic, epic, 8K' não resolve essas decisões.

Leia o contrato comum em `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md`. Receba propósito e beats do diretor, ficha original e estados de continuidade. Não reescreva identidade, roteiro ou ação aprovados.

## Decupagem e blocking

1. Marque quem ocupa cada região, o destino do movimento, o alvo do olhar e os obstáculos. Desenhe a linha de ação e as posições relativas antes de escolher câmera.
2. Escolha ponto de vista e escala pela informação: plano amplo situa relação e consequência; médio lê corpo e interação; close lê decisão e reação; detalhe revela causa. Um close não pode esconder o contato que a cena precisa demonstrar.
3. Declare o que deve permanecer legível na proporção real de entrega: rosto, mão/arma, contato, produto ou texto. Reserve área segura para elementos gráficos previstos, sem cortar anatomia ou marca.
4. Planeje cobertura útil, sem gerar planos extras por hábito. Um plano de reação só merece existir quando muda a leitura do acontecimento. Preserve a cobertura mínima que conta a cena.

## Câmera motivada

Para cada movimento, escreva **origem → trajetória → informação revelada → estado de saída**. Determine altura, distância relativa e relação com os atores. Descreva perspectiva e oclusões esperadas; não confunda zoom com translação física.

- Acompanhar deslocamento permite ler esforço; aproximar após uma descoberta permite ler decisão; contornar um obstáculo revela algo antes oculto. Escolha um objetivo dominante para o movimento.
- Controle aceleração, mudança de direção e desaceleração. Câmera com operador e massa não teleporta nem recentraliza personagens a cada take.
- Conserve geografia e direção de tela entre planos. Mudança de eixo precisa de reorientação espacial visível; uma troca de lado arbitrária parece reversão da ação.
- A regra vigente dos quatro pilares de movimento continua valendo onde exigida. Escolha uma translação econômica que sirva ao beat, em vez de órbita permanente ou tremor para disfarçar falta de ação. Direção explícita do proprietário prevalece.

Uma distância focal citada em prompt é intenção estética, não medição de lente no arquivo gerado. Não invente exposição, milímetros ou parâmetros físicos como se estivessem verificados.

## Luz, cor e material

Fixe fonte de luz, direção, dureza, contraste e continuidade de temperatura; indique o que as motiva no cenário. Explique como separar silhueta do fundo e manter pele/tecido/metal coerentes com a ficha.

Use sombra de contato, reflexos e resposta de materiais para integrar corpos e VFX. Um poder pode iluminar o entorno quando aparece; não pode mudar todas as fontes de luz sem causa. Evite pele encerada, brilho plástico, pretos esmagados e reflexos que revelam outro mundo.

Em animação, siga a estética autorizada e a hierarquia visual; o gate fotoreal de live action não se transfere automaticamente. Em publicidade, materiais e cor do produto/marca são critérios de fidelidade.

## Revisão do vídeo real

Veja a ação em velocidade normal e inspecione contatos/oclusões quadro a quadro. Confirme foco de atenção, legibilidade do gesto, perspectiva, geografia, luz e material ao longo do take e da junção. Prancha estática ajuda a comparar aparência; não comprova trajetória nem leitura do impacto.

Registre `timestamp → problema visível → efeito na leitura → mudança de câmera/luz/blocking`. Não use desfoque, flare, escuridão, cortes ou partículas para esconder erro de anatomia, contato ou identidade.

## Saída

Entregue ficha de fotografia por take: informação prioritária, escala/ponto de vista, posições/eixo, câmera de entrada/saída, profundidade, luz/material, cobertura e critérios de revisão. Passe a geografia à continuidade e os vetores ao editor. Preserve motor, áudio, timing e escopo; não execute geração por esta skill sozinha.
''',
'pemara-performance-director/SKILL.md': '''---
name: pemara-performance-director
description: "Dirige atuação e performance corporal em vídeo Pemara: objetivo, obstáculo, subtexto, olhar, gesto, timing de reação, peso e recuperação. Use para personagens robóticos, emoção exagerada, ação sem intenção, diálogo artificial ou animação sem personalidade."
---

# Atuação e performance Pemara

Dirija o que o personagem tenta fazer e como a situação muda sua conduta. 'Ficar triste', 'ser épico' ou 'lutar intensamente' não são ações executáveis.

Leia `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md`. Receba ficha de identidade, limites pesquisados do personagem, propósito, geografia e beats. A atuação altera comportamento; não redefine aparência, traje, personalidade canônica ou poderes.

## Partitura de atuação

Para cada personagem/beat, registre:

- **Objetivo imediato:** convencer, impedir, proteger, alcançar, esconder ou descobrir algo concreto.
- **Obstáculo e tática:** o que impede o objetivo e qual ação muda diante disso.
- **Subtexto:** diferença entre o que diz e o que tenta conseguir; quando relevante, traduzir em gesto/pausa observável.
- **Estímulo e olhar:** o que ele percebe, em que direção e quando. Olhar encontra o alvo antes da resposta escolhida; não olhar para câmera sem motivo.
- **Ação corporal:** pé de apoio, transferência de peso, postura, mão dominante, gesto necessário e recuperação.
- **Mudança:** como o novo acontecimento altera postura, decisão, distância ou iniciativa.

Construa a ordem **perceber → decidir → agir → receber consequência**. Reação a impacto nasce depois da causa visível; gesto involuntário e decisão posterior podem ter tempos diferentes. Não invente um atraso universal em milissegundos.

## Naturalidade

Escolha uma ação dominante por beat. Dê ao parceiro uma resposta própria; dois atores não se movem em sincronia automática. Preserve escuta durante a fala alheia e evite sorrisos, piscadas ou balanços repetidos para preencher silêncio.

Contraste contenção e explosão conforme a intenção. Microgestos devem revelar mudança, não acumular tiques. Respiração, recuperação de base, assimetria e fadiga apoiam o estado, sem deformar corpo ou tornar a atuação caricata.

Em animação, calibre antecipação, timing e exagero para o estilo autorizado. Animal, criatura e robô precisam de mecânica e personalidade próprias; não aplique automaticamente expressões ou anatomia humanas.

## Ação física e combate

Todo esforço precisa de apoio, transferência de peso e consequência. Empurrar muda centro de massa; correr exige passada; aterrissar exige absorção e recuperação. Roupa/cabelo respondem ao corpo, sem antecipar contato.

Em luta, `pemara-live-action-combat-director` determina golpes, armas, poderes e ciclo causal. Esta skill dirige intenção, leitura do adversário, reação e recuperação; não adiciona golpes nem transforma um poder em outro.

## Voz integrada

Passe à `pemara-voice-performance-director` intenção por frase, interlocutor, palavra de mudança e pausas necessárias. Evite gritar todo o texto ou atuar cada palavra. Preserve texto, idioma, identidade e sotaque aprovados. A fala deve caber na ação sem apressar fonemas ou congelar o corpo.

Lipsync depende do áudio exato aprovado e é outra candidata; não pode modificar timing, rosto ou personagens silenciosos. Não gerar voz nova nem clonar por causa do planejamento de atuação.

## Revisão e correção

Veja o MP4 completo e escute o áudio disponível. Registre quando o estímulo aparece e quando a resposta começa; confirme olhar, intenção legível, peso, reação e recuperação. Não atribua estados psicológicos apenas ao prompt.

Troque um adjetivo por direção: 'mais raiva' pode virar 'ele interrompe o gesto de recuar, firma a base e avança para impedir a fuga'. Após duas falhas equivalentes, revise ação, quantidade de eventos, staging ou controle; não repita seeds indefinidamente. Preserve todos os aspectos aprovados e o escopo.

## Saída

Entregue partitura por personagem/beat, estímulo-resposta, gesto dominante, direção vocal quando houver e critérios observáveis. Em revisão: arquivo/hash, timestamp, observação, falha, hipótese de causa e correção. Ausência de vídeo/áudio observado deixa o parecer pendente.
''',
'pemara-film-editor/SKILL.md': '''---
name: pemara-film-editor
description: "Dirige montagem de vídeos Pemara: seleção de takes aprovados, cobertura, ritmo, tensão, causa e reação, continuidade e intenção sonora. Use para vídeo arrastado, repetição, corte brusco sem causa, montagem de luta, narrativa confusa ou revisão do filme completo."
---

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

`pemara-live-action-kinetic-supervisor` decide compatibilidade física; `pemara-live-action-continuity` dirige conector causal somente se permitido e autorizado. `generatedConnectorAllowed: false` impede geração e inserção de emendas. Fontes incompatíveis exigem correção da fonte.

Crossfade, hold, repetição de frames, speed ramp, fumaça, escuridão e whip-pan não podem esconder reset ou defeito. RIFE/upscale não recuperam identidade, massa ou causalidade. Transformações/retiming só são possíveis sobre fontes boas e dentro do contrato específico; jamais para disfarçar falha.

## Intenção de som

Marque evento visual, fonte sonora, perspectiva, entrada/saída e equilíbrio de voz/ambiente/música quando houver áudio autorizado. Não usar som de impacto antes do contato nem volume para fingir massa ausente. Não impor trilha a silêncio dirigido.

Preserve Foley, voz e trilha existentes. Novo áudio exige escopo explícito. Alterações de mix são candidatos separados com escuta real; LUFS e sincronismo técnicos não provam emoção, peso ou naturalidade.

## Picture lock e entrega

Revise o filme completo: começo compreensível, progressão, personagens, geografia, luz, danos persistentes, respiração, payoff e últimos segundos. Um conjunto de takes bons pode formar uma sequência ruim. Identifique o problema pelo timestamp da montagem e pelo take de origem.

Entregue tabela de montagem com fontes/hashes, in/out em frames e segundos, motivo de corte, estado cinético e uso de áudio. `video-production` executa e mede a edição. Não converter FPS, escala ou canais silenciosamente.

Picture lock depende da aprovação do proprietário sobre a montagem exata. Depois vem SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural, com áudio existente copiado e fonte preservada. O acabado exige revisão própria. Não publicar nem promover candidato automaticamente.
''',
'pemara-video-production-lead/references/production-quality-contract.md': '''# Contrato de qualidade da produção — 2026-10-08

Este é um guia de decisões e evidências para agentes. Não é um novo schema do backend, classificador automático de qualidade nem autorização de geração. O pedido e o AGENTS vigente prevalecem.

## O que deve existir antes do prompt

Uma ficha curta por take, ligada à sequência:

```text
Take / versão / papel na sequência:
O público deve perceber ou sentir:
Estado inicial → estímulo/interferência → resposta → estado final:
Personagens: objetivo, tática, olhar, ação dominante e recuperação:
Geografia: posições, distâncias relativas, eixo e direção de tela:
Fotografia: escala, ponto de vista, trajetória motivada, luz e material:
Beats 0–30%, 30–70%, 70–100% (duração real e grade do modo escolhido):
Identidade: ficha original; âncoras aprovadas; estados antes/depois:
Som: áudio existente, silêncio ou criação explicitamente autorizada:
Corte: informação/vetor entregue ao próximo; por que termina aqui:
Risco dominante / controle suportado / critério observável de sucesso:
Limites e aspectos já aprovados que não podem mudar:
```

Não completar campos com palavras como 'épico', 'realista', 'qualidade máxima' ou com o nome do próprio campo. Escrever o que deve acontecer e aparecer. Não exigir o mesmo número de takes ou a mesma duração de toda cena; preserve o contrato específico e a qualificação temporal do motor.

## Revisão por dimensões

Use `PASS`, `FAIL`, `PENDING` ou `NOT_APPLICABLE` justificado. PASS do agente é parecer com evidência, nunca aprovação do proprietário. Não calcular média geral que esconda uma falha crítica.

| Dimensão | Evidência procurada | Falha que impede selecionar a fonte |
|---|---|---|
| História/clareza | estímulo, mudança e consequência legíveis | repetição, promessa não cumprida ou ação sem causa |
| Atuação | objetivo legível, escuta, olhar e resposta ao evento | reação antecipada, tiques, gesto vazio ou emoção incompatível |
| Ação/física | apoio, impulso, contato/evasão, deslocamento, recuperação | voo sem causa, pés deslizando, força sem massa |
| Fotografia | foco de atenção, geografia, perspectiva e luz coerentes | câmera gratuita, contato escondido, espaço/luz mudando sem causa |
| Identidade/arte | comparação com ficha original e versão correta | rosto, escala, roupa, anatomia, poder ou material divergentes |
| Continuidade | intervalos móveis dos dois lados e estado persistente | reset, dano desaparecendo, vetor ou proprietário trocado |
| Montagem/ritmo | progressão compreensível no filme completo | cortes redundantes, cauda sem informação, reação mutilada |
| Som, quando houver | reprodução/escuta e relação com a ação | voz errada, fala inventada, clipping, impacto antecipado |
| Integridade técnica | decode, hash, duração, FPS, frames, streams e recibos | corrupção, incompatibilidade ou acabamento ausente |

Inspecione o MP4 inteiro em velocidade normal e todos os beats críticos/junções em revisão temporal densa. Índices 0/25/50/75/100% e contact sheets orientam a inspeção; não bastam para aprovar física, atuação ou ritmo. Verifique o que foi efetivamente visto/escutado. Se a ferramenta só permite imagens, marque movimento/escuta como pendentes.

Não inventar evidência de compreensão do público ou de escuta humana. Diferencie 'parecer do agente' de 'avaliação do proprietário'. Ao entregar para avaliação, declarar pendências e limitar a afirmação ao que foi observado.

## Revisão que produz uma correção

```text
Arquivo/path/hash e take/versão:
Dimensão / PASS|FAIL|PENDING|NOT_APPLICABLE:
Timestamp ou intervalo observado:
Observação concreta (o que aparece/soa):
Consequência para a cena:
Hipótese de causa (marcada como hipótese):
Correção prioritária e controles que mudarão:
Aspectos aprovados preservados:
Condição de reavaliação e pendências:
```

Uma ficha preenchida, um hash certo ou uma validação de grafo não demonstra qualidade artística. Não registrar PASS com base só no prompt. Reprovação do proprietário autoriza substituta no mesmo escopo, preservada a tentativa rejeitada; não autoriza montagem, publicação, motor novo ou expansão.

## Regras operacionais atuais do Maestro

- MiniMax H3 é a escolha vigente; LTX foi removido por ordem do proprietário em 2026-10-08. Não reinstalar nem oferecer como fallback. Preserve materiais e histórico antigos.
- H3 exige SageAttention + Spectrum efetivamente no caminho de amostragem; use o contrato atual de `services/studio/h3_spectrum_master20.json`. Não empilhar FirstBlockCache nem reduzir passos/resolução para fingir sucesso.
- Operação ComfyUI pelo Codex usa somente MCP `comfyui-local`, começando por `server_info`; conferir runtime, fila, VRAM, pausas, nodes e validar o grafo exato antes do envio. Backend autônomo Maestro mantém seu canal autorizado.
- Personagens recorrentes em novas produções exigem `identityContinuityRequired: true` e o contrato `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md`. Animação avulsa de foto fica fora desse gate. Personagem existente exige pesquisa da versão antes de ficha/prompts/âncoras.
- Referência original fixa identidade; último quadro fixa pose/movimento. Frame derivado de vídeo aprovado não ganha automaticamente aprovação canônica. Referências rejeitadas não alimentam geração ou seleção.
- Corte cinético direto é preferível quando válido. Conector é somente para fontes boas, quando permitido; `generatedConnectorAllowed: false` bloqueia emenda. Preservar quatro pilares e contratos específicos, inclusive FFVIII V8.
- Acabamento de vídeo: fonte/picture lock aprovados → SeedVR2 3B int8 → RIFE 4.25 em timestamps j/60 → DLSS 5 Natural → candidato. Usar `E:/Pemara/maestro/pemara/services/studio/upscaling_required.py` e perfis aprovados; copiar o áudio existente. Não adicionar Foley a fonte silenciosa por conta própria.
- Perfil DLSS: NR 1x, intensidade 0.5, estrutura 0.5, tom 0, pele 0.25, detalhe 0.5, cor 0, auto-mask ligado. Preservar geometria, duração, áudio e transparência; formatos não qualificados bloqueiam, sem conversão silenciosa.
- Toda nova saída visual precisa de tratamento DLSS com recibo/hashes; herança válida evita aplicar duas vezes em cópia/mux/proxy/concat. Integridade do recibo não aprova aparência.
- Preservar nativo, reprovados, fontes aprovadas e recibos. Projeto encerrado não reabre por auditoria. Nunca transferir aprovação entre takes, acabamentos ou projetos.

## Tipos de vídeo

| Tipo | Decisão anterior à decupagem | Evidência no filme |
|---|---|---|
| Ficção/live action | desejo, obstáculo, virada e consequência | mudança percebida através da atuação |
| Combate | iniciativa, golpe pertencente ao personagem e resultado | contato/evasão, massa, resposta e recuperação |
| Educação | objetivo de aprendizagem e erro comum | exemplo claro, contraste explicado e pausa interativa quando útil |
| Publicidade | promessa, prova e ação final | demonstração fiel de produto/marca sem alegação inventada |
| Animação | estilo, personalidade e lógica do movimento | timing, silhueta e ação coerentes com esse mundo |

Não forçar desastre, luta, explosão ou texto longo a um tipo que não precisa disso. Texto gráfico deve ser curto e inserido deterministicamente quando a fidelidade exigir; nunca pedir que o vídeo invente logotipo ou frase exata.

## Responsabilidades pesquisadas

Referências consultadas em 2026-10-08; adaptações para agentes e geração local são escolhas desta implementação:

- [Diretor — ScreenSkills](https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/development-film-and-tv-drama-job-profiles/director-film-and-tv-drama/): articulação da visão, blocking dos atores e colaboração entre departamentos ao longo da produção.
- [Fotografia — ScreenSkills](https://www.screenskills.com/skills-checklists/scripted-film-and-tv/camera-department/director-of-photography-skills/): responsabilidade pela imagem e coordenação de câmera/luz com a direção.
- [Montador — ScreenSkills](https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/post-production/editor-film-and-tv-drama/): construir história e performance com o material, refinar com o diretor até picture lock.
- [TypeSafe — documentação viva](https://docs.typesafe.ai/llms.txt): ponto de descoberta consultado. Aplicação local: regras exatas e autorizações não devem ser substituídas por parecer semântico; este pacote não adiciona chamada de API nem envio de dados.
''',
'pemara-video-production-lead/references/review-and-repair.md': '''# Da crítica à correção

Priorize a falha que torna a cena ilegível ou falsa. Identidade, causa física e incompatibilidade de rota são bloqueios independentes; não escondê-los com nota média. Depois trate performance/fotografia/ritmo. Integridade técnica continua obrigatória.

| Sintoma visto/escutado | Investigar na fonte | Correção executável |
|---|---|---|
| Ator robótico ou sem reação | objetivo, estímulo, olhar e excesso de gestos | um gesto dominante; resposta motivada e recuperação |
| Luta genérica | golpe assinatura, iniciativa, defesa e consequência | trave mecânica por personagem e leitura do contato |
| Impacto parece leve | apoio, centro de massa, causa/reação | mostre impulso, contato, deslocamento e perda/recuperação de base |
| Câmera parece aleatória | geografia, informação revelada e saída | trajetória única motivada, eixo claro e handoff compatível |
| Tudo tem aparência plástica | referência, material, luz e contraste | corrigir âncora/rota visual; não tentar salvar com sharpening |
| Rosto/roupa varia | ficha original, condição e anchors | restaurar identidade fixa e estado por take sem apagar danos |
| Corte salta ou reinicia | intervalos móveis e fase da ação | corte cinético direto se compatível; senão regenerar fonte |
| Vídeo longo e vazio | mudança real por beat e duração útil | reduzir repetição ou redesenhar a progressão dentro do contrato |
| Filme confuso mesmo com takes bons | causa, ponto de vista e cobertura | reorganizar fontes aprovadas ou devolver lacuna à direção |
| Som não tem peso | evento visual, timing, perspectiva e mix | corrigir somente áudio autorizado; ouvir a candidata inteira |

## Iteração controlada

1. Registre a crítica do proprietário e o arquivo afetado, sem reinterpretar como aprovação parcial inexistente.
2. Separe observação de hipótese. Exemplo: 'defensor começa a voar antes do contato' é observação; 'guia final está puxando a pose' é hipótese.
3. Preserve aspectos aprovados e faça uma mudança principal de método por tentativa quando viável. Não variar ao mesmo tempo rosto, câmera, golpe, luz e motor.
4. Gere nova tentativa do mesmo escopo quando a crítica autorizar, houver admissão GPU e grafo validado pelo MCP. Pedido de pausa/sem gerar prevalece. Uma falha detectada só pelo agente não amplia autorização nem reabre projeto finalizado.
5. Após duas falhas equivalentes, revise densidade de eventos, staging ou estratégia de controles, mantendo o motor. Não girar seeds indefinidamente. Âncoras extras não são solução universal: em combate contínuo, controles futuros podem antecipar a reação.
6. Compare a substituta com o rejeitado e com a ficha original no defeito e nos aspectos preservados. Mostrar evidência do novo arquivo; não anunciar que resolveu antes de observar.
7. Mantenha rejeitado fora de âncoras/montagem e nova candidata pendente da avaliação do proprietário. Não promover com base em relatório técnico.

Para falha sistêmica, preserve a rota como rollback e prepare uma rota coerente dentro do mesmo escopo. Não iniciar lote extenso até uma tentativa representativa demonstrar que o método mudou o defeito.
''',
'pemara-video-production-lead/references/directing-examples.md': '''# Exemplos de direção — exercícios, sem mídia gerada

Estes exemplos mostram decisões. Duração e quadros finais dependem do modo qualificado e do contrato específico; não são promessa de capacidade do motor.

## Dramático: proteger alguém

Vago: 'personagem triste, câmera cinematográfica, muita emoção'.

Direção: ele tenta tranquilizar a criança enquanto fecha a porta; escuta um ruído externo, interrompe a mão na maçaneta e olha para a fresta; muda de lado para colocar o próprio corpo entre ela e a porta. A criança percebe o gesto e recua. A câmera desloca-se lateralmente o necessário para revelar essa nova relação e a luz que entra pela fresta. Corte quando o ruído ganha uma causa visível no plano seguinte.

Revisão: o ruído precede a decisão? O olhar encontra a fonte? O gesto protege sem virar pose? A criança reage? Identidade e posição da porta persistem? Se só há cara triste e zoom, a intenção não foi executada.

## Combate: impacto com consequência

Vago: 'dois lutadores trocam golpes épicos com energia'.

Direção: o atacante busca abrir a guarda com o golpe pesquisado da versão escolhida; o defensor bloqueia e muda a base. Na segunda iniciativa, a arma/poder próprio segue a trajetória dirigida, encontra bloqueio ou corpo e altera o vetor do defensor. Roupa e detritos respondem depois. Recuperação entrega iniciativa ao próximo take. A câmera mantém os dois apoios e a linha do contato legíveis, com reorientação física que preserva o mesmo cenário.

Revisão: nenhum voo começa antes da causa; golpe e efeito pertencem ao personagem correto; pé não desliza; bloqueio realmente muda trajetória. Se contato estiver escondido por clarão, regenerar a fonte, sem acelerar nem adicionar som para fingir peso. Usar o contrato específico de combate, sem converter este exemplo em novos microtakes arbitrários.

## Educação: comparar e decidir

Objetivo pedagógico: distinguir uma afirmação de sua evidência. Erro comum: aceitar uma resposta bem escrita sem verificar.

Produção: um exemplo concreto aparece em cartões curtos; a animação revela primeiro a afirmação e depois a fonte correspondente. Antes da explicação, o público escolhe qual fonte sustenta a frase. A resposta destaca o trecho relevante e mostra por que o outro cartão não responde à questão. Narração e visual apontam o mesmo elemento no mesmo beat. Texto e fonte são inseridos deterministicamente.

Revisão: o exemplo permite uma escolha real? Há tempo de leitura e pausa? O destaque explica o critério? Evitar locução concorrendo com parágrafo e câmera agitada sem função. Não afirmar que a aprendizagem foi comprovada sem avaliação do público.

## Publicidade: demonstrar a promessa

Vago: 'anúncio premium, produto brilhando, logo gigante'.

Direção: apresentar um problema verificável, mostrar o produto realizando a função autorizada e terminar no resultado. Usar ângulos que revelem a operação, materiais da referência e cores de marca fiéis. Câmera aproxima para mostrar a prova, não para esconder a operação. Encerrar com identificação curta e chamada já autorizada.

Revisão: a função aparece funcionando? Resultado e alegação correspondem? Logo/texto estão corretos? Sem marca inventada, benefício não demonstrado ou mudança de produto entre planos. Produzir o texto/logo por composição determinística a partir de assets autorizados.
'''
}

for rel, content in files.items():
    path = SKILLS / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if rel.endswith('/SKILL.md'):
        name = rel.split('/')[0]
        profile = ROOT/'.agents/profiles'/f'{name}.md'
        profile.write_text(f'''---
name: {name}
description: "Perfil de compatibilidade da skill {name}; fonte operacional canônica única."
---

# {name} — Agent Turbo alias

<!-- AGENTS_TURBO_ALIAS_V1 -->

1. Carregue integralmente `E:/Pemara/.agents/skills/{name}/SKILL.md` antes de atuar.
2. A instrução operacional vive na skill canônica; não copie regras para este alias.
3. Preserve o AGENTS vigente, o escopo e as aprovações exatas do proprietário.
4. Este perfil não cria subagentes, gera mídia ou publica por si só.
''', encoding='utf-8')

print(f'Instaladas {len(files)} fontes e quatro perfis alias.')
