# Validação multimodal — 2026-08-21

- Qwen: `qwen3.8-27b-uncensored-yarn-524k` via llama-server loopback 11436.
- Whisper: `faster-whisper-large-v3-turbo`, CPU int8.
- Imagem: JPEG 640×360, SHA-256
  `3495a5d10e9b110046e0163a73dced8dd899a06d54aa62b10f6641cdafb198b9`;
  Qwen observou quadro vermelho uniforme com bordas pretas.
- Áudio: WAV 5,955 s, SHA-256
  `c13fb1f2db2f28f065b20398f046a40cc83dbbf01e106c6fb00340dc05053c39`;
  idioma `pt` (0,99917), texto “Pemara confirmou a transcrição número 427.”
- Vídeo: MP4 H.264 640×360, 5,955 s, SHA-256
  `5e198948918e926a130e1ecdf5d20389efc013e1b4fe8dfaa4cc3a099286f434`;
  oito quadros vermelhos confirmados pelo Qwen e a mesma fala transcrita em PT.
- Browser: Edge headless, 1440×900 e 390×844, três prévias; zero erros/warnings,
  zero overflow horizontal e botão de envio 44×44.
- Microfone: Edge/MediaRecorder gravou áudio WebM em fluxo real, anexou a prévia
  removível e encerrou sem erro ou warning no console.
- Suíte completa: 135/135; Qwen profile E2E 1/1; Builder E2E 2/2; compatibilidade
  DSH real `compatible=true`, cinco ferramentas.
- E2E da interface: job `job-2026-08-22T01-43-45-547Z-ae676fb1`, sessão
  `session-42eb14fc-3cda-4c0f-8369-c968bfaa18df`, três uploads, contexto de
  11.851 bytes, resposta multimodal correta e exit code 0.
- Handoff protegido por arquivo: o DSH real respondeu `PEMARA_TASKFILE_OK`; a
  tarefa do cockpit não é colocada em argv nem na linha de comando dos filhos.

Capturas: `multimodal-ui-desktop-20260821.png` e
`multimodal-ui-mobile-20260821.png`.
