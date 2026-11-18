# Recibo do gate de segurança

Use `scripts/security_release_gate.py` para criar e validar um recibo por sistema ou release.

## Criar

```powershell
python scripts\security_release_gate.py init --target "Loja" --release-boundary local --out E:\Pemara\logs\security_audit\loja-release.json
```

Preencher cada controle e validação com:

- `status`: `pass`, `fail`, `not_applicable`, `quarantined` ou `unknown`;
- `evidence`: lista não vazia de caminhos, comandos/resultados ou testes, sem valores secretos.

`not_applicable` exige justificativa concreta. `quarantined` significa inacessível e monitorado; não significa aprovado.

## Validar

```powershell
python scripts\security_release_gate.py validate --receipt E:\Pemara\logs\security_audit\loja-release.json
```

O gate calcula a decisão:

- falha ou escopo não autorizado -> `BLOCKED`;
- item desconhecido/sem evidência -> `REVIEW_REQUIRED`;
- item em quarentena -> `QUARANTINE`;
- todos os itens aplicáveis aprovados -> `PASS`.

Somente `PASS` retorna código `0`. O recibo não substitui os relatórios brutos; ele aponta para eles.
