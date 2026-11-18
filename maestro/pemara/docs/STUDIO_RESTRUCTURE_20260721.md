# Reestruturacao do Studio Pemara

Estado em 2026-07-21. Este documento trata o jogo somente como destino dos resultados; a estrutura do jogo nao faz parte da reforma do Studio.

## Objetivo operacional

O proprietario deve conseguir entrar em um unico endereco, com seu login, e executar os fluxos do Studio localmente ou pela internet. APIs, motores e portas tecnicas nao sao produtos de usuario e devem permanecer atras do gateway.

## Arquitetura ativa

- Entrada publica principal: `https://maestro.pemaratech.com.br/`.
- Endereco local: `http://127.0.0.1:9501/`.
- Gateway autenticado: `MASTER.py`.
- Studio interno: `127.0.0.1:8029`, acessado no painel por `/api/studio/*`.
- Microservicos auxiliares: somente `127.0.0.1` nas portas `8001`, `8002`, `8003`, `8004`, `8006` e `8007`.
- O caminho de recuperacao automatica do Radar tambem relanca o Studio explicitamente em `127.0.0.1`; uma queda nao reabre a porta na LAN.
- Motores internos: ComfyUI `8188`, Perplexica `3002`, Sprunki `5005` e Ollama `11434`, todos restritos ao computador.
- Interfaces de proprietario: ComfyUI, Sprunki e Perplexica possuem subdominios autenticados que passam pelo mesmo gateway; nenhuma porta de motor e publicada diretamente.
- O Sprunki permanece aberto como servico 24/7: watchdog `SYSTEM` no boot e a cada minuto, sem depender de janela ou sessao de usuario, com verificacao local e do endereco publico protegido.
- Ollama, Studio e microservicos continuam sem hostname publico e so podem ser operados pelo painel/API autenticada do Maestro.

## Controles de acesso implantados

- Login por usuario e senha configurados fora do codigo; a senha agora fica somente como hash `scrypt` com salt aleatorio (`N=32768`, `r=8`, `p=1`).
- `.env`, seu backup saneado, credencial do Cloudflare e arquivo de sessoes possuem ACL NTFS sem heranca: somente o proprietario, SYSTEM e Administradores. A ACL do arquivo de sessoes e reaplicada em toda gravacao atomica.
- `dados/studio` tambem e privado por heranca, para que imagens-ancora, parametros e historico de jobs nao fiquem legiveis por outras contas locais.
- Credenciais, sessoes, historico e `job_inputs` estao explicitamente ignorados pelo Git.
- Cookie de sessao aleatorio; o navegador nao recebe o token interno do Studio.
- Sessoes persistentes, revogaveis e limitadas a 20 dispositivos recentes.
- Cookies `HttpOnly` e `SameSite=Strict`; no endereco publico tambem `Secure`.
- Logout por `POST`, com revogacao no servidor.
- Cinco falhas de login em cinco minutos bloqueiam temporariamente novas tentativas.
- APIs sem sessao respondem `401` em JSON, em vez de devolver a pagina de login com falso `200`.
- Token pela URL foi removido.
- CSP, HSTS, protecao contra iframe, `nosniff`, politica de referencia e permissoes do navegador estao ativos.
- Requisicoes publicas recebidas explicitamente como HTTP retornam `308` para o mesmo caminho em HTTPS antes de exibir login ou aceitar formularios.
- Falhas do proxy nao devolvem excecoes internas ao navegador.
- Cookies e cabecalhos de identidade do navegador nao sao repassados aos microservicos.
- Uploads e downloads atravessam o gateway em blocos de 1 MiB, com limite configuravel, sem copiar arquivos inteiros para a memoria do processo. O Studio repete o limite na borda dos fluxos criativos e tecnicos, sanitiza nomes e grava entradas temporarias com nomes exclusivos.
- A abertura de ComfyUI, Sprunki e Perplexica usa um passe aleatorio de 60 segundos, vinculado ao hostname e descartado no primeiro uso. O cookie do Maestro nao e compartilhado nem encaminhado ao motor.
- Trafego HTTP e WebSocket das ferramentas usa uma lista fixa de tres destinos locais; o navegador nao escolhe host ou porta.

## Fluxos de usuario existentes

1. Studio Criativo
   - Criar imagem.
   - Editar imagem existente.
   - Animar foto por image-to-video.
   - Criar card com foto real.
2. Filmes e Takes
   - Criar e abrir projetos.
   - Consultar takes e estados de producao.
   - Alterar estado por `PATCH` no gateway.
   - Enfileirar takes aprovados para o Wan.
3. Studio tecnico atual
   - Editar e remasterizar video.
   - Converter, transcrever, isolar e tratar audio.
   - Processar imagem.
   - Gerar musica e SFX.
   - Quando nenhum provider de musica/SFX esta configurado, o painel explica a indisponibilidade e bloqueia o envio em vez de deixar um botao que inevitavelmente falharia.
4. Ferramentas e pesquisa
   - ComfyUI, Sprunki e Perplexica abrem pela sessao do proprietario em novas abas protegidas.
   - Acesso direto sem sessao mostra o mesmo login do Maestro.
5. Ferramentas administrativas
   - Organizador, documental, cadastro, historico e telemetria.
6. Arquivos
   - Biblioteca unica para imagens, videos e audios ja produzidos.
   - Filtros por tipo, preview sob demanda e abertura do arquivo original.
   - Indexacao limitada aos mil arquivos recentes para manter a interface responsiva.

## Persistencia de trabalhos

Os trabalhos generativos passaram a ser gravados em `dados/studio/generative_jobs.json`, arquivo ignorado pelo Git. O historico guarda estado, progresso, modo, motor, prompt, dimensoes, parametros e resultados. Um trabalho que estava em execucao durante reinicio volta como `interrupted`, em vez de desaparecer ou permanecer eternamente como `running`.

Novos trabalhos tambem preservam as imagens de entrada em `dados/studio/job_inputs`. A recepcao e interrompida em 25 MB por imagem por padrao (configuravel), o repositorio possui teto adicional de 64 MB e todo caminho e validado contra traversal. O painel oferece `Cancelar`, `Tentar novamente` e `Repetir` quando a acao e segura. O cancelamento remove prompts pendentes do ComfyUI ou interrompe somente o prompt ativo identificado; depois de reinicio, um estado `canceling` e confirmado como `canceled`.

O arquivo de jobs usa lock entre processos, releitura antes de cada mutacao, temporario exclusivo, `fsync` e troca atomica. Duas instancias do Studio nao podem mais sobrescrever o historico uma da outra, e uma segunda instancia nao marca como interrompido um job cujo `worker_pid` ainda esta vivo.

O painel consulta `/api/studio/api/generative/jobs` e mostra os trabalhos recentes. Nenhuma inferencia foi iniciada para validar essa infraestrutura.

A biblioteca consulta `/api/studio/api/generative/assets` e indexa as saidas existentes do ComfyUI e do Studio sem duplicar arquivos. Midia e transmitida em streaming com suporte a `Range`, evitando carregar videos inteiros na memoria do gateway. Previews de video e audio so iniciam quando o usuario pede, para nao abrir dezenas de streams simultaneos.

## Validacao concluida

- 15 testes do gateway, hash de senha, sessao, isolamento de cookies, handoff, redirecionamento HTTPS e estado degradado de health.
- 41 testes do Studio, projetos, jobs concorrentes, cancelamento/repeticao, uploads, saidas unicas e workflows.
- Login local e publico, sessao, Studio autenticado, logout e `401` apos logout.
- Todas as portas gerenciadas restritas a `127.0.0.1` e inacessiveis pelo IP da LAN.
- APIs e motores sem interface de proprietario permanecem sem DNS/rota publica; hostnames desconhecidos retornam `404` no gateway.
- ComfyUI, Sprunki e Perplexica validados publicamente por login, handoff de uso unico e proxy autenticado.
- WebSockets validados no ComfyUI e no Perplexica; carga paralela dos 45 assets iniciais do ComfyUI terminou em `45/45 HTTP 200`.
- Browser desktop e mobile: quatro modos criativos, historico, biblioteca, logout e redirecionamento de motores protegidos; zero erro de console, zero resposta HTTP de erro e zero overflow horizontal.
- Auditoria isolada adicional em 320, 768 e 1440 px: zero overflow e zero texto corrompido; Criar exibiu 17 motores, Projetos abriu 7/7 takes registrados e o player leu video `1920x1080`.
- Biblioteca validada com 1.000 itens recentes indexados, 48 cards por pagina e reproducao publica de video por `206 Partial Content`.
- Upload multipart autenticado validado de ponta a ponta pelo proxy em streaming.
- Edicao real de imagem pelo Studio publico validada com PNG `8x6`, sem iniciar inferencia; VRAM permaneceu em `1557 MiB`.
- O backend ativo tambem concluiu provas leves sem inferencia: ajuste de PNG `16x12`, conversao WAV para MP3 valido e edicao H.264 por CPU de um MP4 `512x288`, todos com tipo e nome de download corretos.
- Artefatos existentes confirmaram criacao Flux/Krea e cinco iteracoes reais de Qwen Image Edit em `1280x704`, todos com o workflow Comfy embutido no PNG. Os takes 01-07 confirmam o caminho image-to-video; nenhuma inferencia nova foi iniciada nesta auditoria.
- Latencias locais medianas: status criativo `29,7 ms`, jobs `3,4 ms`, projetos `15,7 ms`, takes `4,1 ms` e biblioteca com 1.000 itens `144,6 ms`.
- Health consolidado final em `12/12`, agora marcado como `degraded` se qualquer componente ficar offline, em vez de declarar sucesso parcial.
- Container do tunel reiniciado depois da aplicacao das ACLs; os quatro hostnames continuaram exigindo login e o fluxo autenticado abriu as tres ferramentas.

## Evolucoes futuras que nao bloqueiam o uso atual

1. Adicionar selecao direta de um item da Biblioteca como entrada de nova criacao e exclusao confirmada.
2. Adicionar retomada por checkpoint para motores que realmente a suportem; hoje o Studio repete com parametros/entradas preservados, sem fingir continuar latentes incompletos.
3. Integrar as funcoes mais usadas de Sprunki e pesquisa diretamente aos fluxos do painel, mantendo as interfaces avancadas atras do gateway autenticado.
4. Configurar ao menos um provider de audio somente quando o proprietario escolher o servico/credencial; ate la a indisponibilidade permanece explicita e segura.
