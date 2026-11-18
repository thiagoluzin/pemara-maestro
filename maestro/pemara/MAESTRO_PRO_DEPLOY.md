# Maestro Pro Refatorado

Atualizado em 2026-07-21.

## O que mudou

- `app/index.html` foi refeito como painel operacional.
- `app/assets/maestro.css` concentra o visual.
- `app/assets/maestro.js` concentra a integracao com APIs.
- `MASTER.py` agora funciona como gateway para as APIs internas:
  - `/api/cadastro/*` -> porta `8001`
  - `/api/doc/*` -> porta `8002`
  - `/api/historico/*` -> porta `8004`
  - `/api/studio/*` -> porta definida em `MAESTRO_STUDIO_PORT` (`8029` atual)
  - `/api/org/*` -> porta `8006`
  - `/api/dashboard/*` -> porta `8007`
  - `/api/maestro/health` -> health consolidado do ecossistema
- O frontend agora roda em servidor threaded, para uma geracao longa nao travar o painel inteiro.
- ComfyUI, Sprunki e Perplexica agora abrem pelo login do proprietario em subdominios protegidos pelo mesmo gateway.
- O Perplexica foi reparado com `npm install --legacy-peer-deps` e voltou a responder na porta `3002`.

## Acesso validado agora

Endereco correto via internet:

```text
https://maestro.pemaratech.com.br/
```

Instancia local refatorada:

```text
http://127.0.0.1:9501/
```

Porta local definitiva do painel Maestro:

```text
9501
```

Credenciais e portas ficam em:

```text
E:\Pemara\maestro\pemara\.env
```

Exemplo sem segredos:

```text
E:\Pemara\maestro\pemara\.env.example
```

Variaveis principais:

```text
MAESTRO_FRONTEND_PORT=9501
MAESTRO_STUDIO_PORT=8029
MAESTRO_ADMIN_USER=...
MAESTRO_ADMIN_PASSWORD=
MAESTRO_ADMIN_PASSWORD_HASH=scrypt$32768$8$1$...$...
MAESTRO_SESSION_MAX_AGE=2592000
MAESTRO_FRONTEND_TOKEN=...
STUDIO_INTERNAL_TOKEN=...
```

O token interno nunca deve ser colocado na URL ou enviado ao navegador. O acesso de usuario e feito somente pela tela de login.

A senha administrativa nao fica em texto puro. O hash `scrypt` usa salt aleatorio e a migracao preservou a credencial que o proprietario ja utilizava. O campo legado `MAESTRO_ADMIN_PASSWORD` deve permanecer vazio.

## Cloudflare / Docker

- `E:\Pemara\maestro\.cloudflared\config.yml` aponta `maestro`, `comfy`, `sprunki` e `perplexica` para o unico gateway em `host.docker.internal:9501`.
- O container `maestro-cloudflared` publica o tunel, sem expor porta Docker diretamente, e esta com restart policy `always`.
- A protecao do painel usa sessao revogavel no `MASTER.py`; o token interno do Studio permanece somente no salto local do proxy.
- ComfyUI, Sprunki e Perplexica possuem interface publica autenticada, mas suas portas `8188`, `5005` e `3002` continuam locais. O acesso de um clique usa passe de uso unico; o cookie central nao chega aos motores.
- O Sprunki possui watchdog `SYSTEM` com gatilho no boot e repeticao a cada minuto, permitido em bateria, `StartWhenAvailable` e limite de cinco minutos por verificacao. O reset elevado do Maestro reaplica essa configuracao automaticamente.
- Ollama, Studio e APIs auxiliares nao possuem hostname publico ativo. A regra final do tunel retorna `404` para qualquer hostname nao listado.
- Os listeners gerenciados ficam em `127.0.0.1` e nao respondem pelo IP da rede local.
- `.env`, credencial do tunel e sessoes ficam protegidos por ACL NTFS de proprietario/SYSTEM/Administradores. `dados/studio` herda a mesma politica para entradas e historico de jobs.
- O reinicio elevado reaplica essas ACLs; a gravacao atomica das sessoes tambem reaplica a protecao, evitando regressao apos login ou logout.

## Validacoes feitas

- `python -m py_compile MASTER.py`
- `node --check app/assets/maestro.js`
- HTTP `200` para `index.html`, CSS e JS em `9501`
- Proxy autenticado:
  - `/api/maestro/health`
  - `/api/dashboard/snapshot`
  - `/api/cadastro/status`
  - `/api/studio/api/generative/status`
- Browser headless abriu o painel desktop e mobile sem erros de console, respostas HTTP de erro ou overflow.
- Health final: 12/12 servicos online.
- Browser headless abriu ComfyUI, Sprunki e Perplexica pelo handoff autenticado. ComfyUI apresentou 56 botoes e 2 canvases, equivalentes ao acesso local.
- WebSockets de ComfyUI e Perplexica retornaram `101 Switching Protocols` pelo gateway.
- O carregamento paralelo dos 45 assets iniciais do ComfyUI retornou `45/45 HTTP 200`.
- Suites finais: 14 testes do gateway e 33 do Studio; `py_compile`, `node --check` e parse PowerShell passaram.
- Health publico final: `12/12`; qualquer falha parcial agora e apresentada como estado degradado.
- Leitura dos jobs, biblioteca, projetos e edicao de imagem PNG foram exercitadas pelo endereco publico autenticado, sem executar inferencia.
