# Unificação e otimização dos agentes e skills Pemara

Data: 2026-10-08. Estado: auditoria e recomendações; configuração operacional preservada.

## Recomendação principal

Unificar fontes de instrução, roteamento e descoberta. Manter os conhecimentos especializados e carregar cada um somente na fase em que muda uma decisão. A redução desejada é de repetição, conflito e leitura desnecessária; a qualidade depende de preservar requisitos e verificar o comportamento resultante.

## Evidência atual e limites

- 312 arquivos `SKILL.md` encontrados sob `E:/Pemara/.agents/skills`: 311 diretamente em diretórios de skills e um aninhado.
- 31 sob `C:/Users/admin_remoto/.agents/skills` e 17 sob `C:/Users/admin_remoto/.codex/skills`, incluindo os cinco da pasta `.system`.
- Total do recorte: 360 arquivos. Os caches de plugins não foram inventariados. Presença em disco não comprova descoberta ativa nem carregamento na conversa.
- 46 perfis Pemara: 32 aliases, 13 especializações registradas e um dispatcher. O auditor do registro passou sem erros.
- As 50 skills do inventário curado Pemara passaram no validador estrutural. Não foi validado semanticamente todo o conjunto de 360 arquivos.
- 33 dessas 50 não têm `agents/openai.yaml`. Isso é uma oportunidade de melhorar descoberta/interface, não prova de que estejam inutilizáveis.
- Cinco do núcleo têm mais de 150 linhas não vazias segundo o inventário existente: `project-planner`, `phaser-platformer-architect`, `debugger`, `phaser-16bit-platformer`, `performance-optimizer`.
- Nenhum par de arquivos `SKILL.md` do recorte é idêntico byte a byte. Há 11 grupos de nomes repetidos com conteúdo diferente.
- O bloco TURBO foi encontrado em 22 skills; seis compartilham exatamente o mesmo texto normalizado de 3.134 caracteres.

Fontes: [inventário por caminho e hash](inventory.json), [auditor reproduzível](audit_inventory.py), auditor do Messenger Turbo e inventário curado executados nesta tarefa. A auditoria não mediu tokens, latência, dinheiro ou qualidade de vídeos; não promete percentuais de economia.

## Prioridade 1 — Uma única decisão de roteamento

Hoje há instruções de encaminhamento no `pemara-messenger-turbo`, no `pemara-ecosystem-orchestrator` e no perfil `agents-turbo`.

Proposta:

- `pemara-messenger-turbo`: roteador canônico, registro e escolha do conjunto mínimo de skills.
- `agents-turbo`: entrada de compatibilidade que carrega o roteador, como já faz.
- `pemara-ecosystem-orchestrator`: mapa, inventário, auditoria e manutenção do ecossistema; encaminha seleção operacional ao Messenger, sem repetir outra árvore de decisão.

No vídeo, `pemara-video-production-lead` decide a sequência e as fases. Combate, atuação, fotografia e montagem recebem tarefas delimitadas. O registro H3 que lista várias funções não deve ser interpretado como obrigação de carregar ou executar todas simultaneamente.

O catálogo deve indicar: quando usar, quando não usar, entrada, saída, dependências, escopo/stack e qual skill tem precedência. Subagentes continuam condicionados ao pedido e às instruções aplicáveis; a existência de perfis não cria paralelismo automaticamente.

## Prioridade 2 — Consolidar cinco perfis que já são subconjuntos

A comparação linha a linha encontrou zero linhas exclusivas de perfil nestes cinco casos:

| Perfil | Diferença atual em relação à skill | Proposta |
|---|---|---|
| `ai-video-intro-pipeline` | Perfil omite regra específica de FFVIII V8 presente na skill | Alias para a skill, preservando gatilho restrito ao projeto |
| `image-production` | Perfil omite regra de rigs determinísticos do mesmo escopo | Alias para a skill |
| `creative-director` | Perfil omite orientação de cutscenes/live action presente na skill | Alias após resolver precedência de contratos específicos de duração |
| `hero-sprite-scaling` | Perfil omite regras adicionais de escala de chefes | Alias; fatos do jogo ficam em referência específica |
| `phaser-platformer-architect` | Perfil omite doutrina adicional de beat-em-up 2.5D | Alias, mantendo distinção de gênero e projeto |

Isso permitiria passar de 32 para 37 aliases e de 13 para oito especializações, se a revisão de escopo confirmar a equivalência pretendida. Essa contagem é uma proposta, não uma alteração já aplicada.

Outros perfis ainda têm diferenças próprias. `pemara-online-security-guardian`, `phaser-animation-turbo` e `sprunki-lora-trainer`, por exemplo, têm conteúdo significativamente diferente das skills homônimas. Preservar suas especializações. Nos demais, revisar cada diferença; similaridade textual alta não autoriza eliminar semântica.

## Prioridade 3 — Extrair o método comum sem remover critérios

O mesmo bloco TURBO de 3.134 caracteres aparece em `code-archaeologist`, `debugger`, `performance-optimizer`, `project-planner`, `qa-automation-engineer` e `test-engineer`.

Criar uma referência operacional comum para evidência, verificação, escopo, economia de ações e relatório. As skills devem apontar explicitamente para ela e manter apenas o procedimento da especialidade. Carregar essa referência uma vez por contexto quando necessária; após mudança, conferir sua versão/hash. Não criar uma nova camada hierárquica de agentes para esse propósito.

Antes de mover texto, separar método geral de obrigações particulares. O bloco atual inclui `RULES.md`, `FIXLOG.md`, proibição genérica de `_v2` e afirmação de que a autocrítica sempre deve encontrar algo. Essas formulações não devem ser transplantadas como lei universal: usar convenções do projeto, preservar versionamento de candidatos e permitir revisão sem achados. Autorizações existentes e instruções vigentes prevalecem.

Políticas do proprietário continuam no AGENTS e contratos canônicos. Skills usam referências curtas para H3, Sage/Spectrum, MCP, acabamento e aprovação, evitando reproduzir listas que possam divergir. O manifest de acabamento contraditório identificado na análise de vídeo continua prioridade; sua correção ainda está pendente.

## Prioridade 4 — Unificar famílias por responsabilidade

| Família | Unificação recomendada | Conhecimento que permanece distinto |
|---|---|---|
| Planejamento | `project-planner` como entrada; especificação e decomposição como módulos/fases | Execução incremental não deve ser confundida com aprovação do plano |
| Depuração | `debugger` como entrada; incorporar triagem e recuperação de `debugging-and-error-recovery` em referências após comparação integral | Arqueologia de código continua útil para compreender sistemas desconhecidos |
| Performance | `performance-optimizer` como entrada; procedimentos de `performance-optimization` como módulos por stack | Perfil de web, banco, Unity e GPU exige métricas diferentes |
| Testes | Um contrato comum de evidência e regressão | `test-engineer` para unidade/integração; `qa-automation-engineer` para E2E e infraestrutura |
| Frontend vanilla | `web-frontend-vanilla` como entrada; `vanilla-web-patterns` como biblioteca referenciada/alias de compatibilidade | `frontend-ui-engineering` continua para design, acessibilidade e arquiteturas de outras stacks |
| Segurança | Guardian decide requisitos de liberação; hardening e pentest fornecem técnicas e verificações | Não fundir parecer de liberação, scanner e autorização para testes ativos |
| Jogos | Roteamento conforme motor/gênero do projeto | Phaser, Unity, Godot, construção do jogo e empacotamento não são intercambiáveis |
| Áudio | Uma entrada clara por criação, performance vocal, análise ou integração | Voz, música/SFX, mix e áudio reativo conservam métodos próprios |
| Vídeo | Produção dirige; especialistas carregados por fase | Combate, atuação, fotografia, montagem e QC não viram uma única instrução genérica |

Estas fusões semânticas são candidatas: a auditoria leu descrições/estrutura e trechos relevantes das famílias, não certificou equivalência integral de todos os procedimentos. Sua implementação deve usar mapa requisito → destino e exercícios antes/depois.

## Prioridade 5 — Resolver instalações com o mesmo nome

Há duas versões diferentes de `saas-pentest-hardening` dentro do repositório, uma delas aninhada. Também há dez nomes repetidos entre as duas raízes do usuário: `general-video`, `hyperframes`, `hyperframes-animation`, `hyperframes-audio`, `hyperframes-cli`, `hyperframes-core`, `hyperframes-creative`, `hyperframes-keyframes`, `hyperframes-registry` e `media-use`.

As cópias de `general-video`, por exemplo, diferem em regras de instalação, consulta de uso e caminhos de referências. Escolher simplesmente o arquivo maior ou mais recente não é critério suficiente.

Identificar origem, versão, forma de instalação, referências relativas e precedência real de descoberta. Selecionar a instalação canônica compatível, preservar cópia integral e recibo antes de retirar outra da descoberta. Se o gerenciador oferecer escopo por projeto, usar essa capacidade; a disponibilidade desse mecanismo ainda precisa ser verificada. Não editar caches de plugins nem criar links simbólicos como solução automática.

Pacotes HyperFrames devem ser acionados por projetos/composições dessa stack. Não podem tomar o lugar da produção H3 do Maestro pelo nome genérico `general-video`. Pacotes NVIDIA/TAO/NeMo/Jetson devem permanecer disponíveis sob demanda da stack, sem carregar instruções deles em tarefas que não as utilizam.

## Prioridade 6 — Contexto curto e referências completas

Enxugar primeiro as cinco skills longas do núcleo. Manter no SKILL: gatilhos, responsabilidades, entradas/saídas, sequência de trabalho, bloqueios pertinentes e links explícitos. Mover exemplos, comandos extensos e fatos de projetos para referências por assunto. Um alvo editorial de cerca de 80–150 linhas pode orientar a revisão, mas nunca deve remover regra necessária apenas para cumprir tamanho.

Separar método reutilizável de projetos: medidas de sprites do Ritmos, FFVIII V8 e padrões de um take histórico só devem entrar quando o escopo correspondente exigir. Criar um mapa atual que referencie os históricos por data. O `PEMARA_PROJECT_MAP.md` ainda contém políticas antigas de Wan, 30 FPS e durações que não representam a regra atual H3; o `pemara-skill-map.md` ainda omite as quatro novas funções na lista principal de vídeo. Não apagar os históricos; impedir que sejam confundidos com instrução atual.

Completar metadados nas skills frequentes antes de fazê-lo indiscriminadamente em todo o catálogo. Descrições devem discriminar ações próximas, como direção de montagem versus execução de codecs, e evitar gatilhos universais como “sempre que houver erro”.

## Prioridade 7 — Demonstrar que a qualidade foi preservada

Antes da consolidação, registrar hashes, versões e todos os requisitos exclusivos. Depois, conferir que cada requisito continua em local acessível pelo gatilho correto. Guardar as fontes anteriores para retorno e revisar a lista de alterações por família.

Usar cenários representativos: planejamento sem geração; crítica de take dentro do mesmo escopo; operação ComfyUI apenas por MCP; criação de frontend vanilla; erro de build; empacotamento de jogo com motor já escolhido; dúvida de isolamento de tenants; análise de áudio; projeto HyperFrames; tarefa Unity. Para cada cenário, registrar skills esperadas, entrega, regras indispensáveis e ações que dependem do escopo.

Avaliar antes/depois: acerto de roteamento, referências de fato lidas, requisitos preservados, perguntas repetidas, chamadas redundantes e conclusão do trabalho. Medir tokens/latência somente se disponíveis no ambiente; bytes de arquivo não equivalem a custo real. Auditoria estrutural e tabela de cenários não substituem execução observada de testes de comportamento.

No vídeo, preservar revisão do arquivo real e aprovação artística do proprietário. No código, executar os testes afetados e negativos relevantes. Qualidade não será obtida reduzindo passos, resolução, duração aprovada ou trocando motor. O alvo é evitar decisões contraditórias e trabalho repetido.

TypeSafe segue obrigatório como método. Uma API adicional não é necessária para esta limpeza: caminho, hash, versão, dependência e alias são verificações determinísticas. Se futuramente houver benefício de seleção semântica, avaliar exemplos reais antes de adicionar custo e chamadas. A [documentação viva](https://docs.typesafe.ai/concepts/system-one) consultada nesta conversa informa entrada textual; isso não fornece revisão visual de mídia.

## Ordem recomendada de execução

1. Roteador único, fonte comum e cinco aliases candidatos.
2. Correção de precedência e conflitos atuais de vídeo; mapas atualizados.
3. Canonicalização das instalações repetidas após descobrir sua origem e precedência.
4. Metadados e leitura progressiva nas skills frequentes.
5. Consolidação semântica de planejamento, depuração e performance, uma família por vez.
6. Comparação de comportamento e registro dos ganhos efetivamente medidos.

Este trabalho criou apenas o relatório e as evidências da auditoria. Skills, perfis, registro, instalações e serviços não foram alterados.
