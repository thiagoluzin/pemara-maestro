# Plano para direção e produção de lutas corporais com realismo

Data: 2026-10-08. Estado: análise concluída e implementação proposta; especialista ampliado ainda não implantado ou qualificado por este trabalho.

## Decisão recomendada

Evoluir a skill canônica `pemara-live-action-combat-director` para o papel **Diretor/produtor de combate corporal Pemara**, mantendo seu identificador e perfil de compatibilidade. O `pemara-video-production-lead` permanece responsável pelo filme inteiro; o especialista assume a sequência de luta, da intenção dramática à revisão da montagem.

O problema principal é aprofundar método, evidência e responsabilidade. Criar mais um nome com instruções semelhantes aumentaria sobreposição. A especialização deve coordenar atuação, fotografia, continuidade e montagem por fase, com até três skills primárias simultâneas e gates obrigatórios. Esses papéis podem ser cumpridos pelo mesmo agente; não exigem processos ou subagentes.

Resultado esperado: cada troca mostra intenção, distância compatível, defesa ativa, apoio corporal, causa física, consequência proporcional e recuperação; a sequência muda iniciativa e estado sem virar demonstração repetitiva de golpes.

## O que foi analisado

Foram lidas as quatro novas skills e seus perfis, o contrato comum, as referências de crítica/exemplos e o relatório/exercícios da atualização de 08/10. Também foram examinados combate, showrunner, atuação, fotografia, montagem, continuidade, supervisão cinética, movimento, direção de take, QC, roteamento, metadados de descoberta e os contratos/compilador H3 relevantes. O TypeSafe foi consultado na documentação viva.

| Camada atual | Contribuição útil | Evolução necessária |
|---|---|---|
| Produção de vídeo | Fecha intenção, sequência, risco e revisão por dimensão | Receber um pacote de luta completo, com progressão e critérios próprios |
| Atuação | Objetivo, percepção, esforço, reação e recuperação | Iniciativa, hesitação, defesa, fadiga e adaptação do parceiro ao longo da luta |
| Fotografia | Blocking, geografia, câmera motivada, luz e legibilidade | Cobertura que mostre distância, base, contatos e consequências corporais |
| Montagem | Causa/reação, fontes aprovadas, ritmo e cortes cinéticos | Preservar leitura do esforço e alternar tensão, contato e recuperação |
| Combate existente | Golpes pertencentes ao personagem, cadeia física e impacto | Distâncias, defesa antecipada, clinch, desequilíbrio, quedas e solo |
| Continuidade e supervisão cinética | Identidade fixa, estado persistente e fronteiras móveis | Estado de pegadas, apoios, controle corporal, iniciativa e fadiga |
| QC | Arquivo real, evidências temporais, falhas independentes | Separar ameaça, defesa voluntária, contato, impacto e recuperação |
| Perfis de agentes | Aliases apontam para skills canônicas | Atualizar descoberta sem duplicar conteúdo ou prometer execução autônoma |

As novas funções melhoram a preparação e a revisão. O relatório anterior registra validações estruturais e exercícios sem render. Este trabalho não assistiu a novos vídeos, não repetiu os testes anteriores e não verificou runtime/fila. Portanto, não estabelece eficácia visual ou aprovação artística dessas funções.

## Achados que devem ser resolvidos primeiro

1. **Acabamento contraditório em contrato ativo.** O [manifest](E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/manifest.json:71) ainda inclui `chunked_foley_candidate` e `realesrgan_fhd_candidate`. O [compilador](E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py:770) copia essa lista para o plano compilado. A ordem vigente é fonte/picture lock aprovado → SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural → candidata com áudio existente. Não foi observado se algum executor consome a lista para operar acabamento; a contradição no plano compilado já está confirmada.
2. **Proibição excessivamente ampla de movimento antes do contato.** O [validador](E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py:416) exige `defenderMotionBeforeContactForbidden: true`. As skills também usam formulações sobre recuo/reação após contato. O contrato deve distinguir defesa voluntária diante de ameaça percebida da reação causada pelo impacto. Esquiva, guarda e recuo defensivo podem anteceder contato; compressão, recoil ou queda atribuídos ao golpe não podem surgir antes da causa correspondente. A flag atual verifica declaração, não movimento no vídeo.
3. **Cobertura insuficiente de combate corporal.** A referência do especialista concentra-se em golpes assinatura, armas e poderes. Falta uma referência progressiva dedicada a relações entre dois corpos: alcance, apoios, resistência do parceiro, pegadas, equilíbrio e transições.
4. **Descoberta ainda induz microtakes.** O [prompt padrão da skill](E:/Pemara/.agents/skills/pemara-live-action-combat-director/agents/openai.yaml:4) pede transformar a luta em microtakes, embora a própria skill reserve esse método para gestos isolados e preserve combate contínuo para a luta principal.
5. **Geometria precisa de nomenclatura clara.** A skill resume a rota como 1280×720; o [workflow](E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/continuous-bilateral-start-chain-8s.workflow.json:33) distingue amostragem 1344×768 de conformação 1280×720. O especialista deve informar a etapa de cada resolução e nunca alterar parâmetros para reconciliar uma descrição abreviada.
6. **Densidade fixa não serve como critério universal.** Os workflows contínuos e o [validador](E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py:387) exigem pelo menos três trocas e participação dos dois atacantes. Essa rota existente deve ser preservada. Um clinch prolongado, controle no solo ou uma queda única não devem ser comprimidos artificialmente para satisfazê-la: precisam de contrato próprio versionado e qualificado antes de uso.
7. **Peso não significa lançamento obrigatório.** A exigência de deslocamento deve avaliar consequência proporcional ao evento. Bloqueio pode absorver ou redirecionar; golpe evitado não causa impacto; pressão no clinch pode mudar apoio sem voo. Isto é uma proposta de refinamento dos critérios, a validar por referências e vídeo real.

Esses achados são de arquivos atuais. A aprovação histórica citada pelos workflows para a rota Vejito R6 não foi reavaliada aqui e não qualifica automaticamente clinch, quedas, solo ou novos personagens.

## Responsabilidade do especialista

| Papel | Decisão que entrega |
|---|---|
| Diretor | Por que lutam, o que cada um quer, qual troca muda a iniciativa e qual consequência encerra a sequência |
| Produtor da sequência | Cobertura mínima, controles disponíveis, maior risco, tentativas identificadas e dependências antes de repetir o método |
| Coreógrafo de ação | Vocabulário corporal pesquisado, ataque/defesa/contra-ação, distância, apoios e resultado de cada troca |
| Supervisor de integração | Compatibilidade entre ação, atuação, câmera, identidade, som autorizado e montagem |
| Revisor | O que aparece no arquivo, onde falha e qual correção mantém os aspectos aprovados |

O QC conserva seu parecer separado e a aprovação final pertence ao proprietário. Se um mesmo agente dirigir e revisar, registrar essas fases distintamente, sem afirmar independência de revisor inexistente.

A combinação de direção e coreografia se inspira na prática de contar história pelo corpo descrita pelo fight director [Dan Johnson](https://www.dj-danjohnson.com/action). A organização para agentes e H3 é uma proposta local, não certificação profissional ou promessa de capacidade do gerador.

## Conhecimento e referências que devem ser construídos

Adotar três regimes explícitos: realismo corporal, ação estilizada com causalidade e fantasia fiel à versão pesquisada. O briefing escolhe o regime; o especialista não remove poderes aprovados nem impõe acrobacias a uma luta realista.

Começar com combate em pé. Depois aprofundar clinch/pressão, desequilíbrio/quedas e transições no solo. Boxe, Muay Thai, wrestling, judô e jiu-jitsu são categorias de pesquisa possíveis, sem presumir que misturá-las melhora toda cena. Fixar experiência e vocabulário de cada personagem.

Cada referência deve ter fonte, versão/data, intervalo relevante quando houver vídeo, afirmação sustentada, limitações e separação entre observado e adaptação dirigida. Usar fontes de entidades da modalidade, demonstrações de profissionais identificados e making-of oficial pertinente. Personagens existentes exigem pesquisa da encarnação antes de fichas ou âncoras.

Biblioteca inicial: entrada e distância; defesa e contra-ação; troca de iniciativa; pressão com resistência; perda/recuperação de equilíbrio; queda e aterrissagem; transição de solo; fadiga/respiração; ambiente e roupa. Evitar valores universais de força, tempo de reação, lesão ou deslocamento. Aparência fotográfica não permite medir essas grandezas com precisão.

## Contrato de direção proposto

É um template editorial nesta fase, ainda não um schema integrado ao backend.

```text
Sequência/take/versão e regime de realismo:
Intenção de A e B; obstáculo; iniciativa de entrada/saída:
Referências pesquisadas; vocabulário permitido/proibido:
Distância e posições relativas; eixo; alcance qualitativo:
Estado inicial: guarda, apoios, pegadas, fadiga, danos e ambiente:
Por troca: estímulo percebido → decisão → preparação → ação
           → defesa/contato/evasão → consequência → recuperação:
Quem age e quem responde; contato corporal ou com o chão:
Tipo de resposta: defesa voluntária, reação ao impacto ou recuperação:
Apoios/transferência de peso; trajetória e consequência esperada:
Estado final e mudança dramática:
Fotografia: escala, linha de visão, base/contato legíveis e câmera motivada:
Som existente/autorizado; corte; continuidade para a próxima fonte:
Risco dominante; controle disponível; hipótese de correção:
Critério observável; aspectos aprovados; evidências e pendências:
```

Separar timeline planejada da observada. Na revisão, registrar tempo/frame do estímulo, início da defesa, contato efetivo, reação atribuída a ele e recuperação. Quando um contato estiver oculto ou entre amostras insuficientes, marcar evidência pendente; não inventar precisão. A defesa antecipada precisa de ameaça perceptível, sem tratar qualquer recuo como impacto prematuro.

No clinch, declarar pontos de contato, resistência e mudança de apoio. Na queda, declarar desequilíbrio, suporte perdido, trajetória e aterrissagem. No solo, declarar orientação, apoios, controle e resistência, evitando fusão de membros ou mudanças instantâneas de posição. São critérios de representação audiovisual, sem prometer simulação física exata ou controle de pose/mocap inexistente.

## Plano de implantação por fases

| Fase | Trabalho e entrega | Critério para avançar |
|---|---|---|
| 1. Reconciliar contratos | Corrigir acabamento ativo e descoberta; distinguir defesa/impacto; documentar geometria e compatibilidade da flag antiga | Novos planos compilados obedecem à regra atual; esquiva planejada não exige impacto; casos antigos não são migrados automaticamente |
| 2. Especializar a skill | Ampliar a skill existente e criar referências de combate corporal, produção de ação e revisão temporal; atualizar alias/metadados | Uma responsabilidade canônica por decisão; referências lidas por risco; exercícios produzem decisões concretas |
| 3. Preparação sem render | Aplicar o template a troca em pé, defesa, contra-ação, pressão no clinch, queda e solo; marcar rotas ainda não qualificadas | Causas, apoios, estado e correção estão claros; nenhum caso promete controles ausentes |
| 4. Qualificar combate em pé | Em produção explicitamente autorizada, testar a rota contínua existente e observar defesa, impacto, recuperação e continuidade | Arquivo real permite evidência temporal por dimensão e avaliação do proprietário |
| 5. Qualificar contato prolongado | Preparar contratos próprios para clinch/quedas/solo; validar CPU e MCP antes de testes autorizados | Não forçar três trocas onde não cabem; preservar H3 e parâmetros escolhidos; qualificação separada para cada capacidade |
| 6. Integrar e operar | Ajustar roteamento/catálogo por fase, testes pertinentes e documentação de uso | Instruções descobertas levam ao papel correto; plano, execução, revisão e aprovação permanecem distinguíveis |

Arquivos previstos: ampliar `.agents/skills/pemara-live-action-combat-director/SKILL.md`; acrescentar referências de combate corporal e templates nesse diretório; atualizar `agents/openai.yaml`, alias em `.agents/profiles/`, registro `pemara-messenger-turbo/references/turbo_registry.json`, roteadores e metadados pertinentes de `h3_workflow.py`.

As correções de contratos envolvem `manifest.json`, os dois workflows contínuos e `live_action_workflows.py`, com versionamento e testes de compatibilidade. Não renomear campos existentes sem mapear consumidores; preservar interpretação histórica e restringir a regra nova explicitamente a reação causada por impacto. Integração no Maestro deve preservar stack e autonomia do backend.

Fases de geração só começam com escopo autorizado e fontes/âncoras aprovadas. O plano atual não inicia essas fases.

## Qualificação e critérios de êxito

Banco inicial de casos, preparado primeiro em texto; não constitui lote de render autorizado:

| Caso | O que precisa ficar legível | Falha a detectar |
|---|---|---|
| Ataque e esquiva | Ameaça percebida, saída de linha, golpe que não encontra corpo | Esquiva tratada como impacto proibido ou recoil sem contato |
| Ataque e bloqueio | Defesa oportuna, ponto de contato e força absorvida/redirecionada | Guarda decorativa, membro atravessando o parceiro |
| Contra-ação | Recuperação e mudança de iniciativa sem espera educada | Turnos mecânicos ou golpe escolhido genericamente |
| Clinch/pressão | Pegadas, resistência, passadas e distância mantida | Corpos fundidos, translação sem apoio ou adversário passivo |
| Desequilíbrio/queda | Causa, perda de base, arco e aterrissagem | Voo antes da causa, chão atravessado ou levitação |
| Solo/continuação | Apoios, orientação, resistência e estado herdado | Membros extras, troca instantânea de controle ou reset no corte |

Comparar candidatas com baseline exato e falha dominante identificada, mantendo personagem, regime, ambiente, câmera e parâmetros quando compatíveis. Uma tentativa isola a principal hipótese; não variar tudo para depois atribuir melhora à skill.

Inspecionar MP4 inteiro em velocidade normal, revisar temporalmente contatos e junções e ouvir áudio quando disponível. Falta de acesso a movimento/escuta mantém essas dimensões pendentes. Registrar `PASS`, `FAIL`, `PENDING` ou `NOT_APPLICABLE` justificado para identidade, mecânica/causalidade, anatomia/contato, atuação, fotografia, continuidade, montagem, áudio e técnica. Não calcular média que esconda falha crítica.

Um piloto bem-sucedido demonstra apenas a capacidade e condições observadas. Clinch, solo, outra orientação, outro estilo ou acabamento diferente precisam de sua própria evidência. O aceite deve citar arquivo/hash, intervalos, aspectos aprovados e pendências.

Após duas falhas equivalentes, rever staging, densidade ou controle dentro do escopo; não repetir seeds indefinidamente. Crítica do proprietário continua autorizando correção do mesmo item conforme AGENTS, preservando rejeitados e aspectos aprovados. Não usar a qualificação para reabrir projetos encerrados.

Testes de implementação devem cobrir falhas reais: saída de acabamento atual; distinção entre defesa e impacto; campos/compatibilidade versionados; rejeição de apoio/contato faltante no contrato; manutenção das rotas contínuas e proibição de guias futuros na start-chain; roteamento/aliases. Testes de schema verificam declarações, não física filmada. Executar auditoria do registro, inventário e testes existentes afetados após alterações, sem anunciar resultados antes de executá-los.

## Aplicação do TypeSafe

A documentação atual informa que Jev aceita texto e decisões tipadas; não aceita imagem, áudio ou vídeo. Consequentemente, ele não será o juiz visual de contato, física ou naturalidade. Fonte: [System One](https://docs.typesafe.ai/concepts/system-one), consultada em 08/10/2026.

Uma integração futura, se necessária e autorizada, pode ajudar a encaminhar crítica textual para atuação, câmera ou combate, ou avaliar suficiência do relatório textual em perguntas pequenas. O [cookbook de sugestão de skills](https://docs.typesafe.ai/cookbooks/skill_suggestion) exemplifica seleção progressiva; sua aplicação ao Pemara precisaria de avaliação local.

Hashes, versões, contratos, pausas e autorizações permanecem em código e evidência explícita. Probabilidades não aprovam mídia nem suprem observação ausente. Neste plano não houve chamada de inferência paga, leitura de credencial ou envio de materiais à API.

## Regras preservadas e conclusão da análise

MiniMax H3 com SageAttention + Spectrum, sem LTX/fallback. Antes de geração autorizada, operar ComfyUI exclusivamente por MCP `comfyui-local`, começando por `server_info` e verificando runtime/fila/VRAM/nós e grafo exato. Nenhuma inferência de fila ou capacidade viva foi feita nesta análise de disco.

Preservar originais, rejeitados, referências, hashes, histórico e aprovação exata. Fonte/picture lock aprovados precedem SeedVR2 3B int8 → RIFE exato 60 → DLSS 5 Natural, com áudio existente. O acabamento recebe avaliação própria; não cria Foley nem corrige luta ruim.

A prioridade é: reconciliar contratos → aprofundar o especialista existente → ensaiar direção → qualificar combate em pé → qualificar clinch/quedas/solo. O próximo marco útil é um diretor que entrega ação executável e detecta suas falhas com evidência. O título de especialista só ganha sustentação pela qualidade observada nas capacidades qualificadas.

Este trabalho entregou somente análise e plano. Não alterou skills, workflows ou serviços, não gerou mídia e não promoveu candidatos.
