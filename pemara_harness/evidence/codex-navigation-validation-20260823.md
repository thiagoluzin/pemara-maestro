# Validação do cockpit Codex — 2026-08-23

## Escopo

Confirmar que o monitor local oferece o fluxo de navegação pedido:

- abrir uma nova conversa pela sidebar;
- consultar e selecionar chats existentes;
- descobrir e selecionar projetos;
- vincular uma pasta de projeto dentro de `E:\Pemara`;
- usar a mesma navegação em viewport móvel.

## Resultado

O smoke foi executado contra `http://127.0.0.1:3080` com Edge/Playwright
isolado, sem iniciar o Qwen. O snapshot carregou e a página não registrou
erros de console, overflow horizontal ou falhas de rede.

| Cenário | Evidência |
| --- | --- |
| Desktop 1440×900: sidebar, chats e projetos | [codex-sidebar-desktop-20260823.png](codex-sidebar-desktop-20260823.png) |
| Desktop: diálogo “Vincular projeto” e sugestões | [codex-project-dialog-desktop-20260823.png](codex-project-dialog-desktop-20260823.png) |
| Mobile 390×844: drawer aberto e backdrop | [codex-sidebar-mobile-20260823.png](codex-sidebar-mobile-20260823.png) |

## Corte visual Maestro

O corte seguinte reutiliza os tokens visuais do Maestro (navy em camadas,
laranja para ação, azul para foco) e inclui o infinito arco-íris de
neurodiversidade como marca-d’água grande, com baixa opacidade e
`pointer-events: none`:

| Viewport | Evidência |
| --- | --- |
| Desktop 1440×900 | [maestro-autism-watermark-desktop-20260823.png](maestro-autism-watermark-desktop-20260823.png) |
| Mobile 390×844 | [maestro-autism-watermark-mobile-20260823.png](maestro-autism-watermark-mobile-20260823.png) |

O smoke confirmou `--accent: #ff7a1a`, a presença do símbolo nos dois
breakpoints, zero overflow horizontal e zero erros de console.

## Contrato exercitado

- `GET /api/snapshot` devolve `projects` e `chats` além dos dados operacionais;
- `GET/POST /api/projects` registra projetos dentro da fronteira;
- `GET/POST/PATCH /api/chats` persiste chats e estado de seleção;
- `POST /api/tasks` exige same-origin, resolve `projectId`/`chatId` e grava o
  workspace selecionado no runner;
- caminhos fora de `E:\Pemara` são recusados com
  `WORKSPACE_OUTSIDE_BOUNDARY`.

## Testes automatizados

```text
node --test test/cockpit-store.test.mjs   2/2
node --test test/task-runner.test.mjs     4/4
node --test test/monitor.test.mjs        10/10
npm test                                138/138
npm run manifest:check                  ok · 129 files
```

O teste completo via `npm test` inclui `test/cockpit-store.test.mjs` e passou
sem falhas. A interface mantém a regra de que
abrir o Harness ou uma conversa nova não liga nem descarrega modelos da GPU.
