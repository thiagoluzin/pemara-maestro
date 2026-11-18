# Roadmap

## Supervisor durável — implementado, promoção pendente

- journal, exclusão multiprocesso, `--once`, restart limitado e backoff: concluídos;
- releitura de checkpoint antes de cada vida: concluída;
- parada em estado bloqueado, pendente de verificação ou terminal: concluída;
- kill/restart real sem órfão ou checkpoint duplicado: concluído;
- mesma sessão headless: impossível pela seam atual; adotada nova sessão por
  tentativa conforme ADR-001;
- promoção no ledger operacional: pendente do gate do proprietário.

## Adaptadores de efeito — implementados

- filesystem atômico, hash, confinamento e reconciliação: concluído;
- Git local candidato, base/patch determinísticos e sem mover `HEAD`: concluído;
- subprocesso permitido com fingerprint, PID, timeout, saída limitada, ambiente
  saneado, rede negada e reconciliação: concluído;
- HTTP, publicação e operações online: deliberadamente fora do contrato atual.

## Operação

- comando `doctor` com `PRAGMA quick_check` e invariantes do event log;
- métricas de rodadas, tokens, falhas, leases e tempo até retomada;
- cockpit visual local com envio de uma tarefa por vez em `127.0.0.1:3080`:
  concluído, incluindo worker separado, logs persistidos e autostart seguro;
- acrescentar aprovações host-only ao cockpit sem expô-las como ferramentas;
- retenção e exportação assinada do ledger;
- migração transacional v1 → v2: implementada; ativação operacional pendente.

## Integração de modelos

- rota Qwen3.8 local OpenAI-compatible: concluída no perfil e no E2E determinístico;
- rota e contenção do GGUF Qwen3.8 real: validadas sem desalojar o Maestro;
- contrato e perfil Builder v2 com edição/teste estreitos e E2E DSH: concluídos;
- qualificar o Builder v2 duas vezes no GGUF real quando a GPU estiver livre e
  o proprietário autorizar;
- executar três tarefas S/M em shadow mode e submetê-las ao gate humano;
- adicionar novos perfis locais somente com contrato e teste de protocolo próprios;
- roteamento por tarefa e orçamento;
- compactador especializado que preserve objetivo, decisões, hashes e próxima ação;
- avaliador separado do agente executor.
