# Ollama privado do Maestro

Instalação reproduzível do runtime local usado pelo Editor IA. O servidor escuta
somente em `127.0.0.1:11435` e o modelo configurado é `qwen3.5:4b`.

## Uso

Simule primeiro, sem download nem alterações:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  E:\Pemara\maestro\pemara\ferramentas\ollama\INSTALAR_OLLAMA_MAESTRO.ps1 `
  -DryRun
```

Instale na conta do Windows que usa o Maestro:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  E:\Pemara\maestro\pemara\ferramentas\ollama\INSTALAR_OLLAMA_MAESTRO.ps1
```

O script exige 12 GB livres, baixa exclusivamente
`https://ollama.com/download/OllamaSetup.exe`, valida Authenticode `Valid` e a
organização `Ollama Inc.`, e instala silenciosamente por usuário em
`C:\PemaraAI\ollama`.

Depois da instalação, ele confirma:

- `C:\PemaraAI\ollama\ollama.exe`;
- `C:\PemaraAI\ollama\lib\ollama\llama-server.exe`.

Os modelos em `%USERPROFILE%\.ollama\models` nunca são apagados. Se houver
`pull`, `run` ou outra operação ativa, o script para antes de atualizar.

## Configuração de usuário

```text
OLLAMA_HOST=127.0.0.1:11435
OLLAMA_MODELS=%USERPROFILE%\.ollama\models
MAESTRO_EDITOR_LLM_MODEL=qwen3.5:4b
```

`0.0.0.0` é recusado. O endpoint não é publicado na rede nem no túnel.

O script reinicia a tarefa existente `Pemara_Radar` e não cria outro serviço,
tarefa ou watchdog. Se o Radar não existir, inicia `ollama.exe serve`
diretamente. O log fica em
`C:\PemaraAI\logs\instalar_ollama_maestro.log`.

O instalador não baixa nem apaga pesos. Se o modelo ainda não estiver no cache:

```powershell
C:\PemaraAI\ollama\ollama.exe pull qwen3.5:4b
```

Verificação:

```powershell
C:\PemaraAI\ollama\ollama.exe --version
Invoke-RestMethod http://127.0.0.1:11435/api/tags
Get-ScheduledTask -TaskName Pemara_Radar | Select-Object TaskName, State
```
