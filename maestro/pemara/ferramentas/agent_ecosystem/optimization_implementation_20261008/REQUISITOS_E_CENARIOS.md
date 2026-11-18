# Requisitos preservados e exercícios

Data: 2026-10-08. Escopo: implementação da ordem aprovada em `optimization_audit_20261008/RECOMENDACOES.md`.

## Mapa de requisitos

| Origem / requisito | Destino atual | Evidência / limite |
|---|---|---|
| Messenger, Ecosystem e dispatcher escolhiam especialistas | Messenger e `references/routing-map.md`; Ecosystem mantém catálogo; dispatcher encaminha | Registro validado, oito casos independentes |
| Cinco perfis sem linhas exclusivas | Alias para skill homônima | Backup do perfil e auditor de aliases |
| Oito perfis com semântica própria | Especializações preservadas no registro | Phaser 16-bit mantém foco Phaser 3 e referencia receitas comuns |
| Seis protocolos TURBO idênticos | `pemara-messenger-turbo/references/operating-contract.md` | Evidência, escopo, stack, verificação, autorizações e recuperação preservados |
| RULES/FIXLOG obrigatórios e veto genérico `_v2` | Convenções reais do projeto; versionamento de candidatos permitido | Removidos como imposição universal nas famílias consolidadas; não varridos indiscriminadamente em terceiros |
| Planejamento: requisitos, arquitetura, dependências e aceite | `project-planner`, `references/specification.md`, `references/task-breakdown.md` | Wrappers spec-driven e task-breakdown preservam nomes de invocação |
| Debug: reprodução, causalidade, ferramentas e recuperação | `debugger`, `references/investigation.md`, `references/recovery.md` | Wrapper debugging-and-error-recovery; não promete correção sem log/reprodução |
| Performance: medir, localizar, alterar, comparar | `performance-optimizer`, `references/measurement.md`, `web-and-data-recipes.md` | Métrica por stack, condições equivalentes, sem redução de qualidade ou cache privado público |
| Testes unitários versus E2E | `test-engineer` versus `qa-automation-engineer` | Método comum; responsabilidades separadas |
| Frontend: semântica, teclado, contraste, responsividade, suporte real | `web-frontend-vanilla`; biblioteca `references/patterns.md` | `vanilla-web-patterns` é wrapper; checklist proporcional |
| Phaser: receitas, feel, colisão, pixels, versões e gênero | Entradas curtas + `references/topic-*.md` | APIs verificadas na instalação; exemplo de projeto não vira regra universal |
| SaaS: scanner local, sete famílias e técnicas importadas | Entrada raiz + sete referências da subpasta preservada | Entrada aninhada desativada, biblioteca e scanner mantidos |
| Segurança: revisão de código e liberação têm evidências diferentes | Guardian com limite explícito por fase | Falta de evidência = REVIEW_REQUIRED, conforme recibo; scans ativos continuam delimitados |
| H3, Sage/Spectrum, identidade e aprovação exata | AGENTS vigente + production-lead + especialistas | Sem migração de histórico ou troca de motor |
| Combate: causalidade, defesa ativa, rota e geometria | Combat director + showrunner | Defesa antecipatória distinguida de queda antecipada; campo legado mantido compatível |
| Acabamento que ainda dizia RealESRGAN/Foley novo | Manifest atual alinhado a upscaling_required.py | Plano compilado verificado em suíte de 20 testes |
| Cinemática genérica: evitar gate de catástrofe em queda corporal | Cinematic take director | Comando específico deixou de ser instrução universal; schema/manifest real exigidos |
| Música recente: direção, arranjo, mix e escuta | Quatro skills/aliases musicais preservados | Alterações concorrentes revisadas e registradas em concurrent_preserved.json |
| HyperFrames instalado em duas raízes | `.agents/skills` do usuário canônico, origem gerenciada HeyGen | Cópia antiga e ZIP íntegros; overrides de descoberta exigem reinício |
| HyperFrames não deve tomar H3 ou impor execução para plano | Gatilho delimitado e escopo local na entrada HyperFrames | Plano não dispara usage/init/upgrade/render |
| Análise de áudio não implica geração ou normalização | `audio-analysis` | Inspeção existente; pico por canal; indicação não equivale a clipping audível |
| Mapas antigos úteis como história | Snapshot anterior + mapa atual com links | Wan/LTX/30 FPS antigos deixam de reger produção atual |

## Exercícios observados

Um avaliador independente recebeu oito pedidos hipotéticos e as skills, sem acesso aos relatórios, conclusões pretendidas ou propostas de correção. Ele leu as referências para decidir a execução. Não recebeu projetos de teste completos e não executou os trabalhos hipotéticos. Logo, este é um exercício de decisão observado, não um benchmark de produção ou um teste de filme renderizado.

| Caso | Decisão observada | Qualidade/escopo preservados |
|---|---|---|
| Planejar luta corporal original sem gerar | Produção → atuação/combate → fotografia/showrunner por fase | Contrato causal, identidade original, sem GPU; oito segundos por take não vira duração total inventada |
| Rosto/água bons, queda antes do contato | Produção/combate/QC; primeiro localizar arquivo e observar tempos | Preserva aspectos aprovados; crítica autoriza correção no mesmo escopo; MCP para futura execução |
| Botão inacessível HTML/CSS/JS | Frontend vanilla; depuração só se necessária | Sem framework; semântica/foco/teclado e regressão da ação |
| Build Unity e empacotamento | Debugger/unity-debug; fluxo Unity e CLI instalada | Recusou aplicar empacotamento Phaser/Electron só por nome de skill |
| Isolamento de tenants por código | Guardian/revisão estática e negativos pertinentes | Sem scan público, deploy ou alegação de estado implantado |
| Analisar áudio existente | Audio-analysis | Sem Qwen/produção musical, normalização ou instalações implícitas |
| Plano HyperFrames | HyperFrames/creative/core conforme fase | Sem encaminhamento H3, init ou render só para planejar |
| Endpoint em 2 segundos | Performance, baseline e decomposição | Sem redução de payload/segurança/frescor para anunciar velocidade |

O primeiro passe encontrou ambiguidades reais em frontend, áudio, guardian, cinematic, showrunner e HyperFrames. Elas foram corrigidas e houve releitura independente. O reteste intermediário confirmou frontend/áudio/guardian/mapa e revelou pequenos resíduos; os resíduos foram corrigidos, incluindo pico por canal, checklist proporcional, aprovação de âncora derivada, gatilho de catástrofe e comando específico de projeto. O resultado do último passe está em `REVISAO_INDEPENDENTE_FINAL.md`.

Limites: referências auxiliares `unity-android-release` e `unity-web-release` citadas por uma skill externa não foram encontradas nos roots que o avaliador examinou. O encaminhamento funciona com a CLI do plugin e scripts reais do projeto; não se inventaram skills nem se instalou pacote. Uma manutenção do pacote Unity deve resolver seus links na origem. Nenhum resultado artístico ou redução de tempo/custo foi certificado por estes exercícios.
