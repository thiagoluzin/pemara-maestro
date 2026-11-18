# Correcao ComfyUI 8188

Data: 2026-06-25

## Problema encontrado

O ComfyUI estava respondendo em `http://127.0.0.1:8188/system_stats`, mas a porta real estava aberta em:

```text
0.0.0.0:8188
```

Isso enganava os watchdogs: a API respondia, entao eles registravam `OK`, mas o processo estava exposto fora do localhost e tinha sido iniciado pelo `MASTER.py` com `--listen 0.0.0.0`.

## Correcao aplicada

- `start_comfyui.ps1` agora so aceita ComfyUI saudavel se a porta estiver local-only.
- `watchdog_comfyui.ps1` agora falha quando encontra `0.0.0.0:8188`.
- `MASTER.py` agora inicia ComfyUI com `--listen 127.0.0.1 --port 8188 --cuda-device 0`.
- `radar_monitor.py` agora trata ComfyUI exposto como falha e recupera via Maestro.
- `loja/services/system_service.py` e `loja/scripts/verificar_comfy.py` agora tambem iniciam ComfyUI local-only.
- `check_comfy_ecosystem.ps1` mostra o binding real da porta.

## Estado validado

```text
127.0.0.1:8188 pid=29068
argv: main.py --listen 127.0.0.1 --port 8188 --cuda-device 0
queue_running: vazio
queue_pending: vazio
```

Logs confirmados:

- `logs/comfyui.watchdog.log`: voltou a registrar `OK local=http://127.0.0.1:8188/system_stats`.
- `E:\Pemara\logs\radar_monitor.log`: Radar detectou o estado exposto, executou recuperacao e depois validou ComfyUI saudavel.

## Regra daqui para frente

ComfyUI para o ecossistema Pemara deve rodar somente em:

```text
http://127.0.0.1:8188
```

Qualquer launcher que usar `--listen 0.0.0.0` deve ser considerado bug.
