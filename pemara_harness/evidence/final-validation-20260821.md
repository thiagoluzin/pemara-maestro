# Validação final — interface GPT/Codex e núcleo Builder v2

Data: 2026-08-21

## Resultado executável

- Monitor visual respondeu em `http://127.0.0.1:3080/api/health` com
  `ok=true` e `taskSubmission=true`.
- A tela principal é conversation-first, com compositor fixo, Enter para
  enviar, Shift+Enter para nova linha e detalhes técnicos recolhidos.
- O layout foi inspecionado nos artefatos
  `ui-chat-v2-desktop-20260821.png` e
  `ui-chat-v2-mobile500-20260821.png`.
- `Pemara Harness Visual.lnk` aponta para
  `bin/Open-PemaraMonitor.ps1`; `Pemara Harness Qwen.lnk` continua disponível
  como rollback operacional do launcher de terminal.

## Gates automatizados

- `npm test`: 124/124 testes aprovados.
- `npm run test:builder:e2e`: 2/2 E2Es aprovados contra a CLI TypeScript real
  do DeepSeek Harness e endpoint OpenAI-compatible determinístico.
- `npm run test:qwen:e2e`: 1/1 E2E aprovado pela seam local determinística,
  sem carregar o GGUF.
- `npm run test:dsh:compat`: `compatible=true`, cinco ferramentas operacionais.
- `node --check`: 60 arquivos JavaScript/TypeScript compatíveis aprovados.
- Builder v2: scratch temporário gravável provado; rede, HTTP/2, Resolver DNS,
  bindings internos e escrita lateral na worktree continuaram negados.

## Estado preservado

- Qwen permaneceu offline em `127.0.0.1:11436` durante toda a validação final.
- Snapshot da RTX 5090: 32.607 MiB totais, 10.969 MiB usados e 21.218 MiB
  livres; nenhum processo foi encerrado para produzir este resultado.
- ComfyUI respondeu com zero itens em execução e zero pendentes.
- DeepSeek Harness permaneceu limpo em
  `141eb6fef83422698aef7a981029e843e8161534`.
- Sandeco Reversa permaneceu limpo em
  `f3c36892e8aefa44f020f7ad74917089e67ddaa3`.

## Gates humanos ainda abertos

- Aprovação da migração/promulgação do supervisor no ledger operacional v1.
- Duas qualificações do Builder v2 com o GGUF Qwen real, quando autorizadas.
- Três tarefas reais em shadow mode e decisão explícita do proprietário sobre
  promoção limitada ou correção.

Esses gates não reduzem a conclusão técnica desta entrega; impedem declarar
autonomia operacional ou equivalência com Codex/Claude Code sem evidência real
e aprovação humana.
