# Bridge editorial Unimedia -> Maestro

## Objetivo

Usar o que o Unimedia tem de mais valioso — `FactPack`, plano de cenas, briefing de arte e
movimento, gates humanos, ledger de custo, overlays e catalogo de assets — como pre-producao do
Maestro, sem substituir o `video_global_engine` e sem copiar codigo ou acervo sem autorizacao.

O bridge e local, opcional e desligado por padrao. Executa somente quando alguem chama o CLI.
Ele nao abre rota web, nao chama provider, nao inicia ComfyUI/GPU, nao gera audio e nao publica.

## Fronteira de responsabilidade

```text
Unimedia/run editorial
        |
        v
review deterministico + SHA-256 + direitos
        |
        v
projeto PLANNED no Maestro
        |
        v
ancora humana -> escolha H3/LTX 2.5 -> RIFE -> QC humano -> upscale -> master
```

O Maestro continua sendo a fonte de verdade para:

- projeto, takes, versoes e timeline;
- escolha obrigatoria entre MiniMax H3 e LTX 2.5, sem default ou fallback;
- fila e uso serial de GPU;
- imagens-ancora e seus sidecars;
- aprovacao de movimento e upscale;
- audio por diretiva exclusiva do proprietario;
- master, hashes, QC e dataset.

## Bundle de entrada

O diretorio do run deve conter:

```text
run/
  plan.json                 obrigatorio
  manifest.json             obrigatorio
  cost.json                 opcional, recomendado
  factpack.json             opcional, fortemente recomendado
  asset-rights.json         obrigatorio somente para copiar bytes de assets
  assets/                   opcional
```

Requisitos principais:

- canvas e aspecto `16:9`, conforme a politica primaria vigente;
- uma a 200 cenas;
- cada cena entre 2 e 10 segundos;
- `templateId`, titulo ou narracao, `artBrief` e `motionBrief` por cena;
- IDs de cena unicos e seguros;
- asset sempre dentro da raiz do run e com SHA-256 correto;
- JSON limitado a 32 MiB e assets limitados a 1 GiB;
- JSON estrito, sem constantes nao finitas como `NaN` ou `Infinity`;
- somente formatos de imagem (`png`, `jpg`, `jpeg`, `webp`) ou video (`mp4`, `webm`, `mov`)
  coerentes com o tipo declarado;
- texto/overlays limitados e cues sempre dentro da duracao da cena;
- `FactPack`, quando presente, com claim, citacao e hash da fonte;
- run degradado ou autoaprovado nunca herda aprovacao no Maestro.

## Passo 1 — emitir a revisao

```powershell
python E:\Pemara\maestro\pemara\ferramentas\video_global_engine\tools\unimedia_editorial_bridge.py `
  E:\caminho\para\run `
  --review-dir E:\Pemara\scratch\unimedia_maestro_bridge\nome-do-run
```

Saidas:

- `editorial-review.manifest.json`: payload deterministico;
- `editorial-review.md`: leitura humana das cenas e gates;
- `approved.example.json`: modelo de aprovacao preso ao SHA do manifest;
- `authorization.example.json`: modelo de autorizacao juridica/proprietaria.

Estados do CLI:

- `AWAITING_HUMAN_REVIEW`: contrato tecnicamente importavel, ainda sem aprovacao;
- `BLOCKED`: existem erros que nao podem ser aceitos, como briefing ausente ou hash divergente;
- `PROJECT_CREATED`: projeto novo criado de forma atomica;
- `PROJECT_ALREADY_IDENTICAL`: repeticao idempotente somente quando bundle, review, aprovacao,
  autorizacao e todos os arquivos originais do import continuam identicos;
- `ERROR`: aprovacao, autorizacao ou estrutura invalidas.

## Passo 2 — aprovacao editorial

Copiar `approved.example.json` para `approved.json` e preencher dados reais:

```json
{
  "approved": true,
  "manifestSha256": "SHA_EXATO_DO_REVIEW",
  "reviewer": "revisor-humano",
  "approvedAt": "2026-08-13T14:00:00-03:00",
  "acceptedRisks": [],
  "importAssets": false,
  "note": "Cria somente projeto PLANNED; nao autoriza GPU ou publicacao."
}
```

Editar `plan.json` depois da aprovacao muda o SHA e invalida o arquivo automaticamente.
Bloqueios nao podem ser colocados em `acceptedRisks`; somente riscos declarados no review.

## Passo 3 — autorizacao de uso

O acesso privado ao repositorio, sozinho, nao e tratado como licenca. O bridge exige evidencia
separada antes de copiar os artefatos editoriais para o Maestro:

```json
{
  "schemaVersion": "1.0",
  "sourceRepository": "flaviomartil/unimedia-engine",
  "authorizationBasis": "repository_owner_written_permission",
  "grantor": "titular-ou-representante",
  "authorizedTo": "Pemara",
  "grantedAt": "2026-08-13T13:30:00-03:00",
  "scopes": ["generated_editorial_metadata"],
  "assetRightsConfirmed": false,
  "evidenceReference": "referencia-da-autorizacao-escrita"
}
```

Bases aceitas pelo contrato:

- `repository_owner_written_permission`;
- `explicit_license`;
- `original_content_owner`.

Isso e um gate operacional, nao uma opiniao juridica. A evidencia precisa existir de verdade.

## Passo 4 — criar o projeto no Maestro

```powershell
python E:\Pemara\maestro\pemara\ferramentas\video_global_engine\tools\unimedia_editorial_bridge.py `
  E:\caminho\para\run `
  --review-dir E:\Pemara\scratch\unimedia_maestro_bridge\nome-do-run `
  --apply
```

Por padrao, `--apply` le:

- `<review-dir>\approved.json`;
- `<review-dir>\authorization.json`;
- `video_global_engine\projetos` como destino.

O Studio descobre o projeto automaticamente. O projeto nasce `PLANNED`, com:

```text
projetos/<project_id>/
  project_manifest.json
  take_queue.json
  input/editorial_source/
  input/editorial_assets/
  editorial/factpack.json
  editorial/cost.json
  editorial/overlay_plan.json
  editorial/asset_catalog.json
  editorial/plan_qc.json
  qc/editorial_import/import-integrity.json
```

Cada cena vira um take com `owner_selection_required`. O proprietario precisa escolher H3 ou
LTX 2.5 no Maestro antes de gerar; o bridge nao antecipa essa decisao. A imagem-base permanece
`pending_human_qc`; por isso o Studio mostra `canGenerate=false` ate existir ancora real,
sidecar, aprovacao humana e motor escolhido. O dossie `import-integrity.json` guarda SHA-256 de
cada arquivo criado ou copiado pelo bridge. Uma repeticao com arquivo ausente, alterado ou com
outro registro humano falha fechada e nunca e declarada identica.

## Importacao opcional de assets

`importAssets=true` exige simultaneamente:

- escopo `generated_assets` em `authorization.json`;
- `assetRightsConfirmed=true`;
- `asset-rights.json` completo;
- asset dentro do run e com SHA-256 igual ao plano;
- licenca, titular, origem e revisor humano por asset.

Exemplo minimo:

```json
{
  "schemaVersion": "1.0",
  "assets": [
    {
      "path": "assets/cena-1.png",
      "sha256": "64_HEXADECIMAIS",
      "license": "Proprietary - written permission",
      "rightsHolder": "titular",
      "sourceReference": "run-id/cena-1",
      "approvedForImport": true,
      "reviewedBy": "revisor-de-direitos",
      "reviewedAt": "2026-08-13T13:45:00-03:00"
    }
  ]
}
```

Mesmo assim, o asset copiado entra como `pending_human_qc` e `reusable=false`. Imagens podem
aparecer apenas como candidatas de `base_image`, ainda bloqueadas para curadoria humana. Videos
permanecem somente no catalogo editorial e nunca entram no campo de imagem-base.

## Compatibilidade do bridge v1_1

A correcao de integridade `v1_1` altera o SHA do review. Reviews ou aprovacoes emitidos pela versao
`v1` devem ser gerados e aprovados novamente; o bridge nao promove automaticamente aprovacao
antiga. Projetos `v1` sem `import-integrity.json` tambem nao sao classificados como repeticao
identica.

## O que foi incorporado

- FactPack com claims, citacoes, inferencias proibidas e hash;
- VideoPlan convertido em takes curtos;
- gate editorial humano ligado a SHA-256;
- briefs separados de arte e movimento;
- ledger de custo preservado;
- plano deterministico de texto/overlays para pos-producao;
- catalogo de assets com proveniencia, direitos, hash e curadoria;
- reutilizacao permitida somente depois de aprovacao humana;
- metricas de duracao, repeticao, cobertura de templates e custo;
- importacao atomica, idempotente por SHA-256 e sem sobrescrever projeto existente.

## O que nao foi incorporado

- codigo-fonte ou templates proprietarios do repositorio;
- os 721 assets auditados sem licenca individual;
- audio Nova Sonic ou audio de qualquer run;
- render Remotion como substituto do motor oficial;
- chamada direta a ComfyUI/RunPod/AWS;
- rota web de upload/importacao;
- aprovacao automatica, publicacao ou GPU.

Uma futura interface web para este bridge muda a superficie de upload e deve passar antes pelo
guardian de seguranca online da Pemara.

## Rollback

O bridge e aditivo e nunca altera projeto existente. Antes de remover um projeto importado,
confirmar `project_id`, revisar o dossie em `qc/editorial_import` e preservar uma copia/hash se ja
houver revisoes humanas. O proprio CLI nao possui comando de exclusao.
