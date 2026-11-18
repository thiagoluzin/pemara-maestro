# Especificação do primeiro núcleo

## Objetivo

Fornecer uma camada de execução durável para trabalho longo de LLM que sobreviva a reinícios sem depender da memória do processo nem repetir efeitos externos de forma cega.

## Requisitos implementados

- tarefas persistidas em SQLite com estados explícitos;
- event log append-only com sequência contígua por tarefa;
- lease exclusivo com expiração, heartbeat, liberação e recuperação;
- orçamento durável de rodadas;
- checkpoint com resumo, próxima ação, artefatos e dados opcionais;
- efeitos externos em quatro fronteiras: preparar, iniciar, confirmar ou marcar falha;
- deduplicação por chave de idempotência local à tarefa;
- conversão de efeito interrompido em `OUTCOME_UNKNOWN` e bloqueio humano;
- reconciliação host-only de efeito incerto e retomada auditável da tarefa;
- retomada host-only após rejeição do gate, vedada enquanto houver efeito incerto;
- conclusão em duas etapas: solicitação pelo agente e aprovação independente;
- plugin externo para o DeepSeek Harness, sem patch no upstream;
- rota padrão Qwen3.8 local, loopback-only, via adaptador oficial `llm-pi-ai`;
- launcher workspace-aware, interativo e sem remoção automática de trabalho GPU;
- CLI operacional para inspeção, recuperação e verificação.

## Critérios de aceitação do corte 0.1

1. Fechar e reabrir o processo preserva tarefa, checkpoint e eventos.
2. Dois workers não possuem a mesma tarefa simultaneamente.
3. Um lease expirado é liberado de forma durável.
4. O limite de rodadas termina a tarefa em `FAILED_EXHAUSTED`.
5. Uma queda após `effect.started` nunca causa repetição automática.
6. A mesma chave de idempotência não cria dois efeitos.
7. O modelo não alcança `COMPLETED_VERIFIED` sozinho.
8. O plugin é aceito pelo `ToolRuntime` real do commit fixado do DSH.
9. Um smoke headless determinístico percorre as ferramentas no loop real do DSH.
10. Uma tarefa bloqueada só retoma depois de reconciliar todos os efeitos incertos.
11. O perfil composto seleciona o Qwen local e executa ferramentas Pemara pelo protocolo OpenAI-compatible.
12. O launcher executa com `process.cwd()` no workspace escolhido e publica as skills desse workspace ao agente.

## Fora deste corte

- supervisor que relança e retoma automaticamente um processo DSH encerrado;
- reconciliadores específicos para Git, filesystem, HTTP e publicação;
- migração de schema SQLite;
- painel gráfico e notificações entre processos;
- publicação online ou configuração de credenciais reais.
