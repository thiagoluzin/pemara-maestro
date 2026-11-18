# Auditoria Maestro Pro - 2026-06-26

Escopo: Maestro Pro, Studio Generative/ComfyUI, Ollama, Hermes, Radar, tarefas agendadas e saude dos microservicos locais.

## Estado geral

Servicos saudaveis no final da auditoria:

| Servico | URL local | Estado |
| --- | --- | --- |
| Loja | http://127.0.0.1:5000/ | OK 200 |
| Maestro web | http://127.0.0.1:9500/ | OK 401 esperado por auth |
| Cadastro | http://127.0.0.1:8001/status | OK 200 |
| Preenchimento | http://127.0.0.1:8002/status | OK 200 |
| Historico | http://127.0.0.1:8004/status | OK 200 |
| Studio antigo | http://127.0.0.1:8005/api/status | OK 200 |
| Studio Generative | http://127.0.0.1:8015/api/generative/status | OK 200 |
| Organizador | http://127.0.0.1:8006/status | OK 200 |
| Dashboard | http://127.0.0.1:8007/snapshot | OK 200 |
| ComfyUI | http://127.0.0.1:8188/system_stats | OK 200 |
| Sprunki | http://127.0.0.1:5005/ | OK 200 |
| Ollama | http://127.0.0.1:11434/api/tags | OK 200 |

Pendente:

| Servico | Sintoma | Situacao |
| --- | --- | --- |
| Conversor | http://127.0.0.1:8003/status retorna 500 | Codigo corrigido, mas o processo antigo PID 25728 esta preso em sessao de servico e o Windows negou encerramento sem elevacao. Troca efetiva no proximo boot/restart elevado. |
| Hermes Telegram | Bot nao fica online | Dependencias instaladas e LLM pronta, mas o `TELEGRAM_BOT_TOKEN` atual e dummy/invalido. Watchdog agora reconhece isso e para sem loop falso. |

## Ollama e modelo LLM local

Ollama foi reinstalado/validado e esta respondendo em `127.0.0.1:11434`.

Modelos instalados:

- `hf.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF:Q4_K_M`
- `hermes-agent:latest`

Alias criado:

```powershell
ollama create hermes-agent -f E:\Pemara\maestro\pemara\ferramentas\hermes\Modelfile.hermes-agent
```

Uso recomendado no ecossistema:

- Hermes: parser local de intencoes de estoque, sempre com confirmacao antes de baixa real.
- Maestro: agente local leve para triagem, comandos, resumo de logs e roteamento de tarefas.
- Loja: atendimento interno, busca de produtos e apoio a campanhas, sem alterar dados criticos sem confirmacao.

## Hermes

Arquivos implantados/alterados:

- `E:\Pemara\maestro\pemara\ferramentas\hermes\ollama_client.py`
- `E:\Pemara\maestro\pemara\ferramentas\hermes\Modelfile.hermes-agent`
- `E:\Pemara\maestro\pemara\ferramentas\hermes\hermes_bot.py`
- `E:\Pemara\maestro\pemara\ferramentas\hermes\config.py`
- `E:\Pemara\maestro\pemara\ferramentas\hermes\watchdog_hermes.ps1`
- `E:\Pemara\maestro\pemara\ferramentas\hermes\watchdog_ollama.ps1`

Validacao do parser local:

```text
vendi duas placas rtx 5080 -> baixa_estoque, qtd 2, produto "placas rtx 5080"
quantas fontes corsair tenho no estoque? -> consulta_estoque, produto "fontes corsair"
baixei 1 monitor samsung 27 -> baixa_estoque, qtd 1, produto "monitor samsung 27"
sincroniza mercado livre com loja -> sincronizar
```

Para ativar o bot Telegram:

1. Colocar um token real em `E:\Pemara\maestro\pemara\ferramentas\hermes\.env`.
2. Rodar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\hermes\watchdog_hermes.ps1 -Once
```

## Radar e watchdogs

Radar atualizado:

- Arquivo: `E:\Pemara\radar\radar_monitor.py`
- Tarefa: `Pemara_Radar`
- Estado final: `Running`

Novas responsabilidades do Radar:

- Checar `Ollama` em `http://127.0.0.1:11434/api/tags`.
- Subir `ollama serve` se cair.
- Checar Hermes por processo Python real.
- Subir Hermes apenas se o token Telegram nao for placeholder/dummy.

Watchdogs recorrentes existentes:

- `Pemara Ollama Watchdog`
- `Pemara Hermes Watchdog`
- `Pemara Studio Generative Watchdog`
- `Pemara ComfyUI Watchdog`
- `Pemara Sprunki Watchdog`
- `Pemara Marketing Fotos Reais`

## MASTER.py

Arquivo alterado:

- `E:\Pemara\maestro\pemara\MASTER.py`

Correcoes:

- Antes de iniciar microservicos, verifica se a porta ja esta em uso.
- Evita duplicatas e erros repetidos de bind em logs.
- Evita duplicar Perplexica, TripoSG e Sprunki quando as portas ja estiverem ocupadas.
- Frontend `9500` tambem respeita porta ja ocupada.

## Conversor

Arquivo corrigido:

- `E:\Pemara\maestro\pemara\services\conversor\main.py`

Problema:

- `/status` usava `which libreoffice`, comando de Linux, e quebrava no Windows.

Correcao:

- Criado detector Windows/Linux para LibreOffice (`libreoffice`, `soffice`, caminhos padrao do Windows).
- `/docx-para-pdf` agora usa o executavel encontrado.
- `/status` nao deve mais derrubar o servico quando a nova versao carregar.

Script de redeploy criado:

- `E:\Pemara\maestro\pemara\services\conversor\redeploy_conversor.ps1`

Observacao operacional:

- O PID antigo da porta 8003 negou `Stop-Process`, `taskkill` e tarefa temporaria sem elevacao.
- Solucao: rodar o script acima em PowerShell administrativo ou reiniciar a maquina. No proximo start, o codigo corrigido entra.

## Studio Generative

Status remoto validado:

- `https://api-studio.pemaratech.com.br/api/generative/status`

Modelos expostos no status:

- Imagem padrao: `flux1-krea-dev_fp8_scaled.safetensors`
- Video padrao: `wan2.2_ti2v_5B_fp16.safetensors`
- LoRAs: `ritmos_pixel_v1`, `ritmos_pixel_v2_8k`, `sprunki_lora`, `sprunki_lora_v1` e variantes.

## Comandos uteis

Validar Ollama:

```powershell
$env:PATH="$env:LOCALAPPDATA\Programs\Ollama;$env:PATH"
ollama list
ollama ps
```

Validar Studio Generative:

```powershell
Invoke-RestMethod https://api-studio.pemaratech.com.br/api/generative/status
```

Validar Radar:

```powershell
Get-Content E:\Pemara\logs\radar_monitor.log -Tail 80
```

Redeploy elevado do Conversor:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\services\conversor\redeploy_conversor.ps1
```
