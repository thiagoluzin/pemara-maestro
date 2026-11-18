# Direção e produção de vídeo — atualização de 2026-10-08

Foram criados quatro agentes com skills canônicas, perfis de compatibilidade e metadados para descoberta. A revisão cobre todos os pontos pedidos: atuação/ação, fotografia/câmera, identidade/continuidade e ritmo/montagem.

| Agente | O que passa a decidir |
|---|---|
| [Produção e direção](E:/Pemara/.agents/skills/pemara-video-production-lead/SKILL.md) | objetivo do filme, sequência, fichas dos takes, riscos e correções |
| [Fotografia](E:/Pemara/.agents/skills/pemara-cinematography-director/SKILL.md) | enquadramento, blocking, câmera motivada, luz, profundidade e geografia |
| [Atuação](E:/Pemara/.agents/skills/pemara-performance-director/SKILL.md) | intenção, escuta, olhar, gesto, peso, reação e recuperação |
| [Montagem](E:/Pemara/.agents/skills/pemara-film-editor/SKILL.md) | seleção das fontes aprovadas, cobertura, ritmo, cortes e revisão do filme |

## Como usar nos próximos vídeos

O AGENTS de E:/Pemara e os roteadores agora direcionam novos pedidos de produção/qualidade para `pemara-video-production-lead`. A skill chama os especialistas por fase e por risco, com até três skills primárias simultâneas. Um mesmo agente pode cumprir os papéis; não há criação obrigatória de subagentes.

O catálogo H3 do Maestro também inclui as quatro funções nas etapas pertinentes. A alteração em `services/studio/h3_workflow.py` limita-se a `WORKFLOW_SKILLS` e às descrições de `STAGES`; builders, validações, geração, parâmetros e funções de runtime permanecem iguais. As novas instruções estão gravadas; a lista de etapas do processo Studio já iniciado é recarregada na próxima inicialização. O Studio não foi reiniciado nesta tarefa.

## Melhorias nos especialistas existentes

- Diretor cinematográfico, direção de movimento, showrunner, combate, continuidade, supervisão cinética, QC e voz agora recebem decisões de produção, atuação, fotografia e montagem.
- Revisão exige o arquivo completo e evidências temporais por dimensão. Campo preenchido, seed, contact sheet, grafo válido ou nota de movimento não significam qualidade artística nem aprovação do proprietário.
- Crítica vira observação concreta, hipótese de causa e correção executável, preservando os aspectos aprovados. Após duas falhas equivalentes, mudar o método qualificado em vez de girar seeds indefinidamente.
- Corte cinético direto é válido com fontes móveis compatíveis. Conector exige permissão da rota e escopo; não pode esconder falha da fonte.
- A proibição de elenco foi limitada ao brief ambiental que a exige. A exigência genérica de âncoras futuras foi reconciliada com a rota start-only de combate.
- `video-production`, seu perfil especializado e a intro de jogo receberam o acabamento vigente e preservação de áudio. Conceito de jogos e contratos especiais, incluindo FFVIII V8, foram mantidos.
- Removidas instruções ativas de seleção LTX e acabamento scale/unsharp/Real-ESRGAN. Mantidos H3, Sage + Spectrum e SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural, copiando o áudio existente.

## Verificação e limites

- **17 skills criadas/alteradas** passaram no `quick_validate.py`.
- **50 skills** do inventário Pemara válidas; registro com **32 aliases e 13 especializações**, sem erro.
- Metadados das quatro novas skills e referências progressivas conferidos. Um caminho relativo entre skills foi explicitado durante a revisão.
- **12 testes existentes de H3** passaram: `python -B -X utf8 -m unittest test_h3_workflow`, executado no diretório `services/studio`.
- **34 backups** conferidos por SHA-256; alterações de código H3 restritas ao catálogo/descrições.
- [Exercícios de aplicação](EXERCICIOS_DIRECAO.md): cena dramática, combate original e vídeo educativo. São ensaios de direção sem render e sem aprovação artística.

Nenhuma mídia foi gerada, nenhum job GPU foi enviado e nenhum projeto encerrado foi reaberto. O pacote melhora o método e a revisão; a qualidade do próximo vídeo precisa ser avaliada no resultado real.

Fontes profissionais e aplicação do TypeSafe estão registradas no [contrato comum](E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md). A estrutura profissional de direção, fotografia e montagem orientou esta adaptação para agentes; não é uma promessa de resultado do modelo.

## Evidências e recuperação

- [Verificação](verification.json)
- [Arquivos alterados e novos, com hashes](file_changes.json)
- [Inventário](inventory.json)
- [Índice de backups](source_before.json)
- `source_before/`: cópias imutáveis das fontes anteriores, preservadas para comparação/rollback.

Os scripts de implantação deste diretório são registros da execução, não comandos para repetir sobre arquivos já alterados. `verify.py` pode ser executado novamente para conferir o pacote atual. Uma restauração deve selecionar somente os arquivos desta atualização e preservar mudanças posteriores.
