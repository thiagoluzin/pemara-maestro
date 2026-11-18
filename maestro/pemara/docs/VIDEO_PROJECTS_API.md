# Contrato interno — Filmes e Takes do Maestro

Este contrato estende o Studio existente. Todas as rotas são internas e devem
ser chamadas pelo proxy autenticado do Maestro (`/api/studio`), nunca expostas
diretamente pelo hostname público do Studio.

## Som sincronizado pelo video

- `GET /api/video-sound/providers`: lista providers e capacidades sem expor comandos internos.
- `POST /api/video-projects/{projectId}/takes/{takeId}/video-sound-jobs`: gera um piloto a partir
  do video aprovado.
- `GET /api/video-sound/jobs/{jobId}`: acompanha o job persistente.
- `POST /api/video-sound/jobs/{jobId}/cancel`: cancela somente o processo do proprio job.
- `POST /api/video-projects/{projectId}/takes/{takeId}/audio-candidate-review`: aprova ou reprova
  o candidato apos escuta humana.

O contrato e independente do modelo. Consulte `docs/VIDEO_TO_SOUND.md`.

## Recursos

### Projeto de filme

```json
{
  "projectId": "intro_ritmos_revolta",
  "name": "Intro Ritmos da Revolta",
  "status": "IN_PROGRESS",
  "createdAt": "2026-07-16T00:00:00-03:00",
  "updatedAt": "2026-07-16T00:00:00-03:00",
  "takeCounts": {"planned": 9, "approved": 0, "rejected": 0},
  "audio": {"musicProvider": null, "voiceProvider": null}
}
```

O diretório físico segue uma estrutura fixa: `input`, `refs`, `keyframes`,
`takes`, `edit`, `qc`, `audio`, `output` e `logs`. Caminhos absolutos não fazem
parte do contrato público da interface.

### Take

```json
{
  "takeId": "06",
  "name": "Onda de silêncio",
  "status": "READY",
  "engine": "WAN22_A14B_Q4",
  "stage": "WAN_VALIDATED_BASE",
  "width": 768,
  "height": 432,
  "fps": 30,
  "durationSeconds": 5,
  "hasKeyframe": true,
  "hasLatent": true,
  "previewUrl": "/api/video-projects/intro_ritmos_revolta/takes/06/media"
}
```

Estados de take: `PLANNED`, `IN_PRODUCTION`, `QUEUED`, `GENERATING`, `READY`, `APPROVED`,
`REJECTED`, `UPSCALING`, `FINAL` e `ERROR`.

### Pedido ao diretor e execução

`directorRequest` registra uma solicitação; ele não é, por si só, um job de
produção. Para pedidos de foto-base (`category: "ANCHOR"`), os estados têm este
significado:

- `PENDING`: pedido persistido na caixa canônica, aguardando executor;
- `IN_PROGRESS`: valor legado ainda aceito, mas sem prova de claim/executor e,
  portanto, também apresentado como **“Pedido registrado, aguardando executor”**;
- `DELIVERED`: a foto-base foi entregue e aguarda decisão humana;
- a produção do vídeo só fica disponível depois de `keyframeApproved=true` e
  `canGenerate=true`.

Um pedido `ANCHOR` nunca acompanha automaticamente o estado de um job de vídeo.
Somente a rota de entrega da foto-base pode marcá-lo como `DELIVERED`. Já
correções de vídeo (`CAMERA`, `DEPTH`, `INTERNAL_ACTION` etc.) podem usar `IN_PROGRESS`
quando existe um job substituto real em `QUEUED` ou `GENERATING`.

Na interface do Maestro, confirmar uma correção de vídeo registra o
`directorRequest` e, em seguida, cria o job substituto. Para fotos-base, o
registro continua separado da execução: somente uma confirmação explícita que
informa o uso de GPU chama `POST /api/video-projects/{projectId}/anchor-jobs`.
Se o executor não iniciar, o pedido permanece preservado na caixa canônica.
O executor é único por projeto, usa lock persistente e processa uma foto por
vez. A confirmação explícita de GPU também grava
`tools/anchor_executor_intent.json`; o Studio retoma somente esses lotes
autorizados após queda de energia ou reinício e apaga a intenção apenas depois
da conclusão integral. Jobs compatíveis já persistidos são reutilizados. O
executor nunca altera aprovação; somente entrega a candidata para revisão
humana.

## Rotas v1

- `GET /api/video-projects?page=1&pageSize=20&status=IN_PROGRESS`
- `POST /api/video-projects`
- `GET /api/video-projects/{projectId}`
- `PATCH /api/video-projects/{projectId}`
- `GET /api/video-projects/{projectId}/anchor-jobs`
- `POST /api/video-projects/{projectId}/anchor-jobs`
- `GET /api/video-projects/{projectId}/takes?page=1&pageSize=50`
- `GET /api/video-projects/{projectId}/takes/{takeId}/thumbnail`
- `PATCH /api/video-projects/{projectId}/takes/{takeId}`
- `POST /api/video-projects/{projectId}/takes/{takeId}/jobs`
- `GET /api/generative/job/{jobId}`

O `POST .../jobs` atual executa somente `WAN_VALIDATED_BASE`: usa a keyframe
aprovada do take, Wan2.2 A14B I2V Q4, 768×432 e 30 fps, seguido de QC antes do
upscale para 720p. O corpo aceita apenas `seed`; uma
segunda solicitação enquanto o take está `QUEUED` ou `GENERATING` retorna `409`.
O estado e o `jobId` são persistidos no `take_queue.json`.

As etapas `UPSCALE_1080P`, `INTERPOLATE_60FPS` e `FINALIZE` permanecem reservadas
para a próxima revisão do contrato. Elas só serão habilitadas depois que o take
720p estiver aprovado e possuir latente validado.

## Erros

Todas as novas rotas retornam:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dados do take inválidos.",
    "details": {}
  }
}
```

Mapeamento: `400` entrada malformada, `403` fora do proxy interno, `404`
recurso ausente, `409` conflito/idempotência, `422` validação semântica e `500`
falha interna sem caminho ou segredo no corpo.

## Integrações de áudio

Música (Lyria MCP) e narração/vozes (Microsoft MCP) entram como providers
opcionais do projeto. A ausência deles não bloqueia imagem, takes, QC, montagem
nem render final; a interface mostra `NÃO CONFIGURADO` até o provider responder.
