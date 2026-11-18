# Gerador de Vozes CLTube integrado ao Pemara Maestro

Este app é um cliente local do Editor do Maestro. Ele divide roteiros, gera prévias e cria narrações em WAV dentro do projeto escolhido, adicionando os assets à timeline quando essa opção está marcada.

## Motor recomendado

- **Chatterbox Multilingual V3**: TTS neural local recomendado para português, expressividade e perfis de voz autorizados.
- **Voz do Windows**: fallback leve, sem GPU e sem clonagem.
- **Qwen3.5 4B no Ollama**: já instalado no ecossistema para assistência textual futura; não é necessário para gerar voz.

Nenhuma chave API é usada. O texto é enviado somente ao backend local do Maestro em `/api/editor`.

## Executar

Pré-requisitos: Node.js e o Studio do Maestro ativo (por padrão em `http://127.0.0.1:8029`).

```powershell
npm install
npm run dev
```

Abra `http://localhost:3000`. O Vite encaminha `/api/editor` para o Studio local.

Se o build for servido por trás do frontend autenticado do Maestro, configure `VITE_MAESTRO_API_BASE=/api/studio/api/editor`; o proxy do Maestro injeta o token interno no servidor, sem expor credenciais ao navegador.

Para outra porta do Studio:

```powershell
$env:MAESTRO_STUDIO_URL = "http://127.0.0.1:8029"
npm run dev
```

O Chatterbox é detectado pelo backend em `C:\PemaraAI\chatterbox\.venv` ou em `ferramentas\chatterbox\.venv`.
