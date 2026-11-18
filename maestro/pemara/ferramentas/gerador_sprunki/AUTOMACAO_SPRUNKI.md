# Automacao do Portal Sprunki

O Sprunki e um motor interno do Maestro e deve responder somente em `127.0.0.1:5005`. Desde 2026-07-21 ele nao possui dominio publico direto.

## Arquivos

- `app.py`: agora tem `/api/health` e aceita `SPRUNKI_PORT`, `SPRUNKI_HOST`, `SPRUNKI_COMFYUI_HOST` e `SPRUNKI_COMFYUI_PORT`.
- `start_sprunki.ps1`: sobe ou reinicia o Flask se o health local falhar.
- `watchdog_sprunki.ps1`: checa o health local, religa o backend quando necessario e confirma que o endereco publico protegido continua respondendo.
- A instalacao feita pelo reset do Maestro usa `SYSTEM`, gatilho de inicializacao e checagem a cada minuto; por isso o Sprunki nao depende de uma janela aberta nem de usuario conectado.
- `install_sprunki_watchdog_task.ps1`: instala uma tarefa do Windows para rodar o watchdog no logon e a cada minuto.
- `logs/`: criado automaticamente pelos scripts.

## Uso manual

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_sprunki.ps1
```

## Instalar watchdog no Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_sprunki_watchdog_task.ps1
```

## Testes rapidos

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\watchdog_sprunki.ps1 -Once -PublicUrl "https://sprunki.pemaratech.com.br/"
Invoke-WebRequest http://127.0.0.1:5005/api/health -UseBasicParsing
```
