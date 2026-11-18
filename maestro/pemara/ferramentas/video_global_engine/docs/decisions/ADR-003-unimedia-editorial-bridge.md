# ADR-003: Unimedia como bridge editorial opcional do Maestro

## Status

Aceito para integracao local condicionada. Nao autoriza adocao de codigo/ativos, geracao GPU,
piloto externo ou producao sem os gates descritos abaixo.

## Data

2026-08-13

## Contexto

O repositorio privado `flaviomartil/unimedia-engine` demonstrou capacidades uteis de pre-producao:
FactPack com citacoes, plano de cenas, briefs de arte/movimento, gates humanos, custo, overlays,
catalogo reutilizavel e metricas. Ele tambem apresentou bloqueios para incorporacao direta:

- ausencia de arquivo de licenca no snapshot auditado;
- assets sem licenca individual registrada;
- maturidade experimental e inconsistencias de plataforma/documentacao;
- sobreposicao com a orquestracao de takes ja aprovada no Maestro.

O Maestro possui uma decisao vigente que exige escolha explicita entre MiniMax H3 e LTX 2.5,
RIFE, revisao humana, upscale tardio e audio por ordem do proprietario. Substituir essa cadeia
ou escolher um motor implicitamente quebraria a politica atual.

## Decisao

Adotar somente uma fronteira de dados do tipo bridge/strangler:

1. O Unimedia pode fornecer artefatos editoriais de um run.
2. O bridge valida o contrato e emite review deterministico ligado por SHA-256.
3. Aprovacao editorial humana e autorizacao de uso sao gates independentes.
4. Cada cena aprovada vira um take nativo `PLANNED` do Maestro.
5. Imagem-base, video, audio, GPU, QC, upscale, master e dataset permanecem sob o Maestro.
6. Codigo-fonte do repositorio de origem nao e copiado.
7. Assets so podem ser copiados com autorizacao de escopo, manifest por SHA-256 e direitos
   individuais; ainda assim entram em curadoria pendente.
8. Audio sempre nasce `visual_only`; nenhuma informacao de audio do run e herdada.
9. O CLI e a unica superficie inicial. Nao criar upload/API publica nesta fase.
10. O bridge grava `owner_selection_required`; somente o proprietario escolhe H3 ou LTX 2.5.

## Contratos de seguranca e qualidade

- fail-closed para hash, paths, cena, duracao, briefing, autorizacao e aprovacao;
- assets nao podem escapar da raiz do run;
- JSON, extensao, tipo, tamanho, overlays e cues possuem limites antes de qualquer copia;
- projeto existente nunca e sobrescrito;
- criacao usa staging e promocao atomica;
- repeticao identica exige SHA-256 valido para todo o dossie importado e para os registros humanos;
- video editorial nunca e classificado como candidato de imagem-base;
- JSON de entrada e estrito e rejeita valores nao finitos;
- bloqueios nao podem ser transformados em simples aceite de risco;
- run autoaprovado ou degradado exige novo julgamento humano no Maestro;
- FactPack ausente fica visivel como risco, nunca como fonte presumida;
- a importacao nao inicia rede, GPU, audio, render ou publicacao;
- futuras rotas online passam pelo guardian de seguranca da Pemara.

## Consequencias

### Positivas

- O Maestro ganha planejamento editorial verificavel sem perder sua fonte de verdade.
- Roteiro, custo, citacoes, overlays e proveniencia ficam preservados no projeto.
- O Studio reconhece o projeto sem mudanca de API.
- A fronteira juridica e de assets fica explicita e auditavel.
- O recurso e reversivel e desativado por padrao.

### Custos e limites

- O titular precisa fornecer autorizacao escrita ou licenca explicita.
- Runs antigos podem precisar exportar `factpack.json`, `artBrief` e `motionBrief`.
- Assets existentes sem direitos individuais nao entram.
- Texto/overlay e preservado como plano de pos-producao; nao ha renderer Remotion embutido nesta
  decisao.
- Um projeto importado ainda exige todo o trabalho humano de ancora, movimento e QC.

## Alternativas consideradas

### Copiar o repositorio inteiro para o Maestro

Rejeitada. Duplicaria motores, quebraria a politica vigente e copiaria material sem licenca
confirmada.

### Substituir o video_global_engine pelo Unimedia

Rejeitada. O Unimedia agrega mais na camada editorial do que na cadeia oficial de takes, GPU e QC.

### Apenas documentar ideias, sem integracao executavel

Rejeitada. Nao preservaria hashes, aprovacoes, custos nem compatibilidade real com o Studio.

### Bridge local por contrato

Escolhida. Entrega valor imediatamente, mantem a fronteira reversivel e permite evolucao futura
sem criar dependencia de runtime ou superficie online.

## Evidencia de validacao

- suite dedicada: 18 testes de contrato, hash, risco, paths, autorizacao, assets, limites,
  idempotencia,
  payload, Studio e politica RIFE;
- `py_compile` do bridge e dos testes;
- parse JSON do template editorial;
- projeto sintetico reconhecido por `video_projects.list_projects`;
- takes sinteticos expostos como `PLANNED` e `canGenerate=false`;
- `ltx_review_pipeline` aceitou a politica RIFE bloqueada;
- smoke real auditado foi corretamente recusado por ausencia de `artBrief`/`motionBrief`, com
  riscos de FactPack ausente, autoaprovacao e degradacao;
- zero trabalho GPU e audio `visual_only` durante toda a validacao.

Em 2026-08-13, o debug do bridge elevou a versao para `v1_1`: review adulterado, projeto
incompleto, aprovacao divergente e JSON nao finito agora falham fechados; MP4 permanece no catalogo
editorial e nao entra em `base_image.candidate_assets`.

## Rollback

Remover ou arquivar apenas projetos importados explicitamente, depois de preservar seus dossies e
hashes. O bridge nao altera projetos anteriores e nao oferece exclusao automatica. Para retirar a
capacidade, reverter os commits aditivos do CLI, testes, template e documentacao.
