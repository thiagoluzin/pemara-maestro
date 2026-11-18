# HyperFrames no Maestro

Renderizador local de composições HTML do `Video Global Engine`. Ele complementa os motores de geração por IA: HyperFrames monta títulos, cards, overlays, timelines e vídeos determinísticos; não substitui ComfyUI, LTX, Wan ou MiniMax.

## Estado validado

- HyperFrames `0.7.103`, GSAP `3.14.2` e Inter Variable `5.3.0`, todos fixados no `package-lock.json`.
- Node.js 24, FFmpeg/FFprobe e Chrome Headless reconhecidos.
- Render local por software como padrão (`--no-browser-gpu`, um worker), sem disputar a RTX 5090 com o ComfyUI.
- Editor integrado ao menu lateral do Maestro e publicado somente pelo gateway autenticado em `https://hyperframes.pemaratech.com.br/`; a origem continua local em `127.0.0.1:8032`.
- Whisper e Kokoro são opcionais e não foram instalados; o Maestro já possui rotas próprias de voz e transcrição.

## Comandos

Na pasta deste arquivo:

```powershell
npm ci
npm run doctor
npm run check:pilot
npm run render:pilot
npm run preview:pilot
```

Também existem atalhos:

- `ABRIR_STUDIO_HYPERFRAMES.bat`: abre o preview local na porta 8032 e mantém o processo em primeiro plano.
- `RENDERIZAR_PILOTO.bat`: repete o gate completo e só renderiza se a validação passar.

## Piloto

Projeto: `projects/maestro-pilot`

Saída validada: `projects/maestro-pilot/renders/maestro-hyperframes-pilot.mp4`

Contrato técnico: MP4 H.264, `1280x720`, `30 fps`, `6 s`, `180` frames, `yuv420p`. O JSON lateral registra hashes, comandos e os gates executados. O estado é `READY_PENDING_HUMAN_QC`: integridade técnica não equivale a aprovação visual humana.

## Regras operacionais

1. Executar `check` após qualquer alteração em uma composição.
2. Manter assets, fontes e bibliotecas locais; não depender de CDN no render final.
3. Não usar `--gpu` nem `--browser-gpu` enquanto houver carga na fila do ComfyUI.
4. Não publicar com `hyperframes publish` sem autorização explícita.
5. Todo MP4 que entrar no fluxo do Maestro precisa de JSON lateral e QC humano.
6. O serviço sobe com o `MASTER.py` e o watchdog do Studio o verifica a cada 5 minutos.
7. O subdomínio nunca aponta direto para a porta 8032; todo acesso online passa pela sessão do Maestro.
