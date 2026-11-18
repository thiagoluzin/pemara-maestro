# Contrato protegido do Qwen Builder — v1

Autoridade: host/guardião. O Builder lê este contrato, mas não o edita.
Módulo de referência: `src/builder-contract.mjs` · Teste protegido: `test/builder-contract.test.mjs` ·
Gate executável: `scripts/check-protected.mjs`.

## Pacote de tarefa (formato fechado)

Todo campo é obrigatório e todo campo fora da lista é rejeitado:

```yaml
task_id: QB-NNN            # exatamente QB- + 3 dígitos
objective: string          # resultado único e observável
allowed_paths: [string]    # lista fechada; sufixo "/" = diretório
forbidden_paths: [string]  # deve conter o conjunto mínimo abaixo
acceptance_commands: [string]  # definidos pelo host
required_artifacts: [string]   # diff, saída de testes, checkpoint final
skills: [string]           # 3 a 12 nomes, sem repetição
max_rounds: 1..6           # orçamento de rodadas
max_files_changed: 1..5    # orçamento de arquivos
network: denied
service_control: denied
gpu_control: denied
commit_or_publish: denied
stop_conditions: [string]  # paradas obrigatórias
```

## Conjunto mínimo de caminhos protegidos

Toda tarefa deve proibir, no mínimo:

- `RULES.md`
- `SPEC.md`
- `evidence/` (todas as evidências são host-owned)
- `tasks/contracts/` (o próprio contrato)
- `test/builder-contract.test.mjs` (teste do gate)
- `scripts/check-protected.mjs` (gate executável)

Regras de interseção:

1. um caminho permitido nunca pode ser igual a, ou estar dentro de, um caminho proibido;
2. um diretório permitido que contenha um arquivo proibido também é conflito
   (ex.: `src/` permitido × `src/index.mjs` proibido = rejeitado);
3. a hash de cada arquivo protegido é capturada pelo host **antes** de entregar
   a worktree e revalidada **depois**: qualquer mudança ou ausência falha o
   gate (`PROTECTED_FILE_CHANGED` / `PROTECTED_FILE_MISSING`).

## Superfície de ferramentas do Builder

O perfil Builder expõe exatamente estas cinco ferramentas model-facing:

| Ferramenta | Papel |
| --- | --- |
| `harness_task_create` | abre o ledger da tarefa |
| `harness_task_get` | lê tarefa/eventos da sessão |
| `harness_task_begin_round` | consome orçamento de rodada |
| `harness_task_checkpoint` | persiste progresso e próxima ação |
| `harness_task_request_completion` | pede o gate (não aprova) |

Proibidas na superfície (marcadores em nomes de ferramenta):

- promoção: `verify`, `promote`;
- rede: `web_`, `_fetch`, `http`;
- serviço/GPU: `service`, `gpu`, `job_`, `subagent`.

`request_completion` **não** contém marcador de promoção: a promoção é feita
pela CLI/host fora do perfil.

## Comandos do gate (host)

```powershell
# Capturar hashes antes de entregar a worktree
node scripts/check-protected.mjs --capture `
  --files RULES.md,SPEC.md,test/builder-contract.test.mjs,tasks/contracts/qwen-builder-v1.md `
  --out evidence/protected-hashes-<task-id>.json

# Validar um pacote de tarefa
node scripts/check-protected.mjs --package <pacote>.json

# Revalidar hashes e superfície depois do trabalho
node scripts/check-protected.mjs --verify --evidence evidence/protected-hashes-<task-id>.json `
  --tools harness_task_create,harness_task_get,harness_task_begin_round,harness_task_checkpoint,harness_task_request_completion
```

Exit `0` = gate verde. Exit `1` = gate falhou; o relatório JSON lista violações
com códigos estáveis.

## Condições de parada obrigatórias

1. caminho fora do allowlist tocado;
2. teste protegido ou política com hash diferente;
3. rede, serviço, GPU, publicação ou credencial solicitada sem autorização;
4. efeito externo com resultado incerto;
5. orçamento de rodadas ou arquivos esgotado.

Em qualquer parada o Builder checkpointa o estado e pede conclusão com
evidência; quem decide é o verificador independente, não o Builder.

## Versionamento

- `v1` — este documento; orçamento 6 rodadas / 5 arquivos / 3–12 skills /
  3 restarts (restarts pertencem ao supervisor, fase 2).
- Mudanças de contrato exigem nova versão (`qwen-builder-v2.md`) e nova
  captura de hashes; o Builder nunca edita a versão vigente.
