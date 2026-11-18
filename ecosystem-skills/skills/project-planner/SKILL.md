---
name: project-planner
description: "Planeja escopo, arquitetura e dependências de projetos ou mudanças relevantes. Entrada canônica de especificação e decomposição; reutiliza decisões aprovadas e a stack existente."
---

# Planejamento Pemara

Leia `E:/Pemara/.agents/skills/pemara-messenger-turbo/references/operating-contract.md` uma vez por contexto.

## Entrada e escopo

Leia pedido, decisões anteriores, AGENTS, plano existente e estrutura real do projeto. Preserve contexto, sistema operacional e caminhos explícitos. Não deduza o motor pela pasta. Faça descoberta local quando faltar mapa; não exija um agente Explorer nem ferramentas que não existem.

Um pedido de análise entrega análise; um pedido de plano entrega plano; um pedido de implementação já autorizado permite executar depois da preparação necessária. A skill não ativa o modo Plan do aplicativo nem cria novas rodadas de aprovação. Questões só quando alteram uma decisão ainda não resolvida.

## Modos progressivos

| Necessidade | Referência canônica e saída |
|---|---|
| Requisitos incompletos, arquitetura ou critérios de sucesso | [specification.md](references/specification.md): especificação proporcional |
| Requisitos claros, dependências e tarefas | [task-breakdown.md](references/task-breakdown.md): sequência verificável |
| Critério de conclusão do projeto | Aceite por tarefa, verificações afetadas e evidência real em [task-breakdown.md](references/task-breakdown.md) |
| Execução aprovada | `incremental-implementation`: incrementos no escopo; usar especialistas por risco |

As skills `spec-driven-development` e `planning-and-task-breakdown` são entradas de compatibilidade para esses modos. Não as carregue novamente se a referência necessária já foi lida.

## Decisões obrigatórias no plano

Declare objetivo, escopo, stack, componentes afetados, dependências reais, critério de aceite, verificação e recuperação. Cada tarefa tem entrada → saída → evidência. Tamanho é proporcional ao risco; não impor quantidade de arquivos, duração fictícia ou número fixo de etapas.

Use o caminho de plano já adotado pelo projeto ou solicitado pelo usuário. Somente quando ferramentas existentes esperarem `tasks/plan.md` e `tasks/todo.md`, mantenha essa convenção. Sem convenção, escolha um nome claro e não crie arquivos de plano concorrentes. Verifique que o arquivo foi salvo.

Gates de segurança entram desde a fundação se houver nova fronteira online: `pemara-online-security-guardian`, autorização no servidor, isolamento/RLS ou motivo de não aplicação, segredos, inputs hostis, testes negativos, rollback e artefato implantado. Não adiar para depois da publicação.

Selecione especialistas presentes no registro do Messenger. Papéis e dependências não autorizam subagentes. Preserve sequenciamento de arquivos compartilhados, schema/consumidores e migrações; paralelismo só quando permitido e sem dependência.

## Verificação e continuidade

Use comandos reais do projeto, conferidos antes de executar; exemplos antigos de outro jogo não são bateria obrigatória. Não marcar tarefa concluída sem resultado observado. Diferencie plano pronto, implementação, teste técnico e aprovação do proprietário. Atualize o plano se uma decisão mudar e preserve histórico pertinente.
