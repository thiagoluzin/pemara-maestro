# Watchdog do ComfyUI

O ComfyUI e monitorado por health check real em:

```text
http://127.0.0.1:8188/system_stats
```

## Arquivos

- `start_comfyui.ps1`: sobe ou reinicia o ComfyUI.
- `watchdog_comfyui.ps1`: checa health e chama o start quando necessario.
- `install_comfyui_watchdog_task.ps1`: cria tarefa do Windows a cada minuto.
- `logs/comfyui.watchdog.log`: historico do monitor.
- `logs/comfyui.out.log` e `logs/comfyui.err.log`: saida do processo.

## Regra de saude

O ComfyUI so e considerado saudavel quando:

- `http://127.0.0.1:8188/system_stats` responde;
- a porta `8188` esta em `127.0.0.1`;
- nao existe listener em `0.0.0.0:8188` ou `:::8188`.

Essa regra evita o falso positivo antigo, onde a API respondia mas estava exposta em `0.0.0.0`.

## Uso manual

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_comfyui.ps1
```

## Instalar tarefa

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_comfyui_watchdog_task.ps1
```

## Observacao

O `Pemara_Radar` tambem valida o ComfyUI. Ele roda como `S4U / Highest`, entao consegue recuperar casos em que um processo antigo prendeu a porta e a sessao RDP normal nao tinha permissao para encerrar.

A tarefa antiga `PemaraComfyUI` ainda existe na inicializacao do sistema. Ela nao substitui o watchdog/Radar; a regra de producao continua sendo: ComfyUI principal em `127.0.0.1:8188`.
