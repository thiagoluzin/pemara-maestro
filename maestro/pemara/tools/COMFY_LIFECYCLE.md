# Controle local do ComfyUI — 2026-09-07

MCP, launcher do Windows e reiniciador administrativo usam `comfy_lifecycle.py`.
O servico canonico permanece em `127.0.0.1:8188`, ComfyUI 0.34.2 / torch
2.14.0+cu130, com o mesmo Python isolado, modelos, input/output e user directory.

## Causas corrigidas

- O reiniciador administrativo iniciava um Python em outra sessao do Windows,
  sem registrar o PID no comfy-cli. O novo controlador registra o listener real.
- `comfy_cli.utils.kill_all` matava somente filhos e retornava sucesso sem
  encerrar o proprio PID. Agora encerra e aguarda todos os processos selecionados.
- MCP e CLI discordavam entre `no_recorded_server` e `no_background_server`.
  O reconhecimento aceita ambos, sem engolir timeout ou falha de permissao.
- Launchers independentes podiam disputar a porta. O controle usa um lock de
  arquivo compartilhado entre sessoes e inicio idempotente.
- O watchdog podia desfazer uma parada deliberada. `maintenance.hold` bloqueia
  o inicio automatico; inicio explicito bem-sucedido pelo MCP remove a pausa.

## Operacao

O Codex continua usando exclusivamente `comfyui-local` para operar o servico.
`launch_comfyui({})`, `stop_comfyui({})` e `restart_comfyui({})` usam o adaptador
local. O servico canonico tem argumentos fixos; overrides sao recusados com
erro explicito. O seletor H3/LTX no Maestro permanece independente.

Antes de parar, verifica identidade do runtime e fila viva vazia. Fila desconhecida
ou ocupada recusa a operacao. PID vivo sem listener recusa iniciar uma duplicata
ou declarar parada concluida. Estado de inicio tambem fica registrado para
preservar processos em caso de timeout.

Quando o Windows nega acesso ao PID de outra sessao, o adaptador solicita somente
a parada fixa desse runtime ao Radar existente. O broker revalida processo e fila,
confere validade da solicitacao e identidade do solicitante, confirma a liberacao
da porta e retorna recibo correlacionado. Nenhuma instancia alternativa e criada
se nao houver confirmacao. O Radar precisa estar ativo para esse caso de permissao.

## Evidencias verificadas nesta manutencao

- Instancia provisoria 8190 encerrada via MCP.
- Primeiro restart MCP: PID 7764, sessao 0, encerrado pelo broker; novo PID 8104
  na porta 8188. Recibo em `dados/comfy_lifecycle/broker_result.json`.
- Inicio repetido via MCP manteve PID 8104: `already_running=true`.
- Segundo restart MCP: PID 8104 encerrado e PID 24692 iniciado, aproximadamente
  16 segundos. Processo novo na sessao 1 e porta registrada no comfy-cli.
- `server_info`: 8188 vivo, workspace correto, PID 24692 registrado.
- `nodes get R17H3SageAttention`: patch presente no catalogo vivo canonico.
- Fila viva final: zero em execucao e zero pendentes. Porta 8190 sem listener.
- 11 testes CPU passaram: fila ocupada/desconhecida, runtime divergente, pausa
  automatica, inicio idempotente, lock concorrente, processo sem filhos,
  sobrevivente, aliases de erro, processo orfao e perda do listener.
- Scripts PowerShell passaram na analise sintatica. Nenhum video gerado.

Reboot completo do Windows nao foi executado. Carregamento do Sage foi confirmado
no catalogo; esta manutencao nao executou inferencia para medir desempenho.

## Manutencao e rollback

Fonte do controlador: `tools/comfy_lifecycle.py`. Adaptador instalado no ambiente
MCP por `tools/install_comfy_lifecycle.py`; o instalador nao contata o servico.
Depois de atualizar/reinstalar comfy-cli ou comfy-mcp, reaplicar esse instalador
e executar `tools/test_comfy_lifecycle.py` antes de operar. Os arquivos upstream
modificados ficam em site-packages; nao presumir que pip preserva patches locais.

Backups anteriores a alteracao: `dados/comfy_lifecycle/backup_20260907`.
A copia original de utils esta adicionalmente em
`comfy_cli/utils.py.before_lifecycle_20260907`. A sobreposicao temporaria de URL
8190 foi removida; `COMFY_LOCAL_URL` do MCP voltou a ser a fonte do endereco.
Registros atuais: `runtime.json`, `last_operation.json`, `broker_result.json` e
`comfyui.log` em `dados/comfy_lifecycle`. Nao apagar a pausa para tentar contornar
uma fila desconhecida; consultar a causa e iniciar explicitamente pelo MCP.
