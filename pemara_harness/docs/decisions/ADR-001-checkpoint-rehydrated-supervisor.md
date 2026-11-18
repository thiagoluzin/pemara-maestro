# ADR-001: Retomar por checkpoint com tarefa estável e nova sessão DSH

## Status

Aceita em 2026-08-21. A promoção sobre o ledger operacional continua pendente
do gate explícito do proprietário.

## Contexto

O supervisor precisa sobreviver à morte completa do processo sem repetir
efeitos. A identidade realmente durável do Pemara já é `task_id`, com objetivo,
orçamento, checkpoint, eventos e efeitos no SQLite.

O bundle headless fixado do DeepSeek Harness não oferece retomada pela CLI:

- `packages/bundle/headless/src/startup.ts` aceita apenas a tarefa posicional;
- `packages/bundle/headless/src/index.ts` chama `agents.create` com um
  `session-${randomUUID()}` a cada processo;
- `agents.resume` existe em hosts programáticos/API, como prova
  `examples/headless-agent/tests/resume.e2e.ts`, mas não é uma opção do runner
  headless usado pelo perfil Pemara.

Modificar o upstream ou inventar um `--resume` local violaria o contrato de
reversibilidade e produziria uma identidade não comprovada.

## Decisão

O supervisor mantém o mesmo `task_id` Pemara em todas as vidas. Cada tentativa:

1. recebe um `attempt_id` persistido e orçamento de restart;
2. relê objetivo e último checkpoint confirmado;
3. inicia uma nova sessão headless DSH;
4. registra PID, início, fingerprint do comando, saída e resultado;
5. nunca reinicia tarefa bloqueada, aguardando verificação ou terminal.

O campo `session_id` do journal é opcional e só pode conter uma identidade DSH
real quando ela for capturada por uma seam pública. Ausência de captura não é
substituída por um ID inventado. Continuidade significa a mesma tarefa e o mesmo
checkpoint, não a mesma conversa DSH.

Se um PID ainda existir após a queda, ele só é reconhecido com início e
fingerprint correspondentes. PID vivo sem identidade comprovada resulta em
`OUTCOME_UNKNOWN/BLOCKED`, nunca em relançamento cego.

## Alternativas consideradas

### Passar `--resume` ao perfil headless

Rejeitada. O parser do aplicativo headless não declara essa opção e o runner
sempre cria uma sessão aleatória nova.

### Alterar o DeepSeek Harness fixado

Rejeitada. Aumentaria a superfície de manutenção e quebraria a exigência de
upstream byte-identical e rollback simples.

### Trocar agora para o host HTTP/API do DSH

Adiada. Esse host possui cold-resume público, mas adiciona servidor, lifecycle e
superfície de autorização que não pertencem ao corte headless atual. Poderá
substituir esta decisão em outro ADR após gate próprio.

## Consequências

- retomada é auditável mesmo quando a conversa DSH desaparece;
- o contexto reidratado é menor e explícito, reduzindo deriva entre tentativas;
- detalhes não presentes no checkpoint não são recuperáveis automaticamente;
- três restarts e backoffs 5/15/45 s permanecem persistidos;
- promover o supervisor no ledger operacional exige cópia, migração v2,
  `integrity_check`, kill/restart e aprovação do proprietário.

## Rollback

O supervisor é aditivo. Parar `pemara-supervisor` restaura o launcher headless
direto; tabelas v2 permanecem como journal. O ledger v1 operacional não é
migrado automaticamente.
