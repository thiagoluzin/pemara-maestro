# Trocar voz de vídeo — Maestro

Fluxo solicitado pelo proprietário em 06/11/2026: importar um vídeo, selecionar uma voz clonada e baixar o áudio com a fala no tempo da gravação original.

## Uso

1. Abra **Vozes → Trocar voz de vídeo**.
2. Importe MP4, MOV, MKV, WebM ou áudio, de até 5 minutos e 1 GB.
3. Escolha uma voz de **Minhas vozes** com referência autorizada de até 30 segundos. Escolha a faixa de áudio quando o arquivo tiver mais de uma.
4. Mantenha **Preservar música e ambiente** para separar a voz antes da conversão e recombinar o fundo. Para fala isolada, desmarque.
5. Clique **Trocar voz e sincronizar**. Ouça a saída, compare com o original e use **Ver vídeo com a nova voz** para a prévia local.
6. Baixe **WAV sincronizado** para substituir a faixa no editor. MP3 é uma exportação de escuta; a referência de duração amostra a amostra é o WAV.

O arquivo importado, referências, saídas nativas, registros e versões anteriores permanecem preservados. A prévia usa o vídeo original com o novo áudio no navegador; não renderiza nem altera o vídeo.

## Método e motores

O proprietário autorizou explicitamente acrescentar **Seed-VC local**, mantendo **Drama 3** no fluxo de texto para narração. Não há fallback entre esses motores.

`Interface Maestro → API autenticada /api/voice-conversion → fila ComfyUI → PemaraVoiceConvert → audio.cpp 0.8.1 (CUDA) → Seed-VC v1 Whisper + BigVGAN`

O conversor recebe a gravação original e a referência vocal. Não transcreve o vídeo para gerar outra leitura TTS. A separação opcional usa HTDemucs local; o fundo é calculado contra a fonte e recombinado com a voz convertida.

- Runtime existente: `D:/PemaraRuntimes/audio-cpp-v0.8.1/bin/audiocpp_cli.exe`, versão 0.8.1, commit `f2b4937`.
- Seed-VC F16: `G:/Pemara_AI_Models/SeedVC/seed-vc-mlx-f16.gguf`, SHA-256 `39b79042fd5560a1c642ac96cef451dbc81c08880f85e9c4b92b685add60f500`.
- HTDemucs F16: `G:/Pemara_AI_Models/SeedVC/htdemucs-f16.gguf`, SHA-256 `f8c54ba35df95aafea7881eac214b58ec18a73cbcb6ff5a90f4b762631a286b6`.
- Pesos públicos fixados na revisão Hugging Face `fd2fe4c3195bc410f8b817bf7c7519fd822686fb`. Downloads e hashes foram verificados. Nenhum texto ou áudio é enviado a API de inferência externa.

## Contrato temporal

- O vídeo define a origem e a duração da linha do tempo. A extração usa os PTS reais decodificados, preservando atraso inicial e compensação de priming do codec.
- Preparação e entrega: PCM estéreo, 44.100 Hz; número final de amostras igual a `round(duração_do_vídeo × 44100)`.
- Voz convertida em janelas de até 20 s, com 1 s de sobreposição. As sobreposições são recombinadas na posição original, sem concatenar e duplicar fala.
- Seed-VC recebe `duration_scale=1.0`. Não há `atempo`, mudança de velocidade ou alongamento artificial para encobrir dessincronia.
- Somente arredondamento nativo de codec de até 80 ms é tolerado. Uma cauda ainda vocalizada não é cortada para encaixar. Desvio maior bloqueia a entrega e preserva as saídas nativas.
- Recibo inclui hashes de fonte, referência, modelo e saída, posição de cada janela e contagem real de amostras. Ganho global de proteção evita clipping na recombinação e fica registrado.

Igualdade da duração total não comprova alinhamento de cada fonema nem qualidade artística. A conversão de voz visa preservar a execução original, mas timbre, sotaque, pausas e sincronização precisam ser conferidos pela escuta e pela prévia. Vozes simultâneas não são individualmente identificadas: toda a fala da faixa escolhida recebe a mesma voz de destino. Separação de fundo pode deixar resíduos.

## Persistência e proteção

Dados em `dados/studio/voice_studio/conversion/`: SQLite para mídias/histórico e diretórios privados `media/` e `jobs/`. A biblioteca vocal é compartilhada com o estúdio existente e suas referências são copiadas por tentativa.

Upload bruto é autenticado antes da leitura do corpo, limitado por tamanho e validado por FFprobe. API aplica a guarda de origem do navegador existente. IDs, faixas e parâmetros são restritos; caminhos de disco não vêm do navegador. Pedidos são idempotentes. Cancelamento sinaliza só o worker e o prompt da própria conversão, sem interrupção global. Reinício acompanha prompt confirmado sem reenviar automaticamente.

O backend continua autônomo. As operações do Codex no ComfyUI seguem o MCP; um reinício de runtime exige fila viva livre. Instalação não significa que o nó novo já foi carregado: o painel só habilita conversão quando a capacidade executável estiver presente.

## Verificação

Testes isolados cobrem importação real de contêiner com áudio atrasado e silêncio final, montagem por sobreposição sem duplicação, recusa de desvio temporal/cauda vocal/amostras inválidas, autenticação antes do upload, guarda de origem, seleção de faixa/voz, idempotência, integridade, persistência e download. Chromium verifica importação, seleção, reprodução comparativa, prévia sincronizada, histórico e telas de 320, 768, 1024 e 1440 px. Os testes de interface usam conversão sintética identificada; não são prova de síntese real.

Skill TypeSafe lida e documentação viva consultada. O fluxo utiliza decisões determinísticas e modelos de áudio locais; não adiciona uma chamada semântica externa.

Fontes: [Voice Changer do ElevenLabs](https://elevenlabs.io/docs/eleven-creative/playground/voice-changer), [Seed-VC original](https://github.com/Plachtaa/seed-vc), [documentação audio.cpp do commit instalado](https://raw.githubusercontent.com/0xShug0/audio.cpp/f2b4937/docs/models/seed_vc.md) e esquemas locais `model_specs/seed_vc.json` e `htdemucs.json`. Consultadas em 06/11/2026.

## Implantação e teste real em 06/11/2026

O nó `PemaraVoiceConvert` foi reconhecido no catálogo vivo após reinício pelo MCP com fila comprovadamente livre. O Studio foi recarregado pelo Radar. O painel de capacidade retornou `ready=true` e `backgroundReady=true`. Os grafos passaram no preflight MCP sem erros, avisos ou nós pagos. Nenhum projeto anterior foi alterado.

Pela interface real do Maestro foi importado `Rui_Fachada_Take01_Master20_CaminhadaFrontal_CameraLenta_v05.mp4`, selecionada a referência Rui Lucato autorizada neste chat e ligada a preservação de música/ambiente. Resultado v02: job `5d022ed3232847c0a0d11a492c700971`, prompt `6022a808-15e0-41fb-8527-c4948736e1c6`. WAV estéreo PCM 44.100 Hz, 602.671 amostras de entrada e saída, 13,666009 s. Apenas 47 amostras de arredondamento nativo foram preenchidas no final (1,07 ms); nenhuma mudança de velocidade. Motor e separador executaram localmente por CUDA. A conversão levou cerca de 9,2 segundos, excluindo upload/fila. A versão instalada aceita `duration_scale=1.0`; `length_adjust` falhou apesar do esquema legado. A tentativa v01 falha foi preservada.

A transcrição local CPU das duas faixas reconheceu as mesmas 33 palavras normalizadas. Os inícios de palavra estimados independentemente diferiram no máximo 60 ms, mediana 0 ms. ASR não é alinhamento fonético exato nem escuta humana. Prévia com vídeo mudo + novo áudio e download WAV foram executados no Maestro; o SHA-256 do download coincidiu com a saída: `22f0e4182795baba16ee0d3c8d6b2b5a724be935e3a36d3f0cd22a92a7824599`.

Verificação adicional de janelas: fonte técnica de 40,998 s formada por três cópias do áudio original preservado, identificada como teste e importada pela interface, sem preservação de fundo. Job `8e365bb15b9342f8a1d2faa3d5fbfe08`, prompt `de73dc2f-48f3-43ee-baee-5048bc51fc65`. Três janelas convertidas, 1.808.013 amostras na entrada e na saída, sem alongamento. Isso verifica o caminho de montagem por sobreposição; não qualifica toda gravação de cinco minutos nem a qualidade artística.

Validação: 38 testes de backend/worker/autenticação/navegador, 25 testes existentes de autenticação/proxy e seis testes de navegação passaram. Após a correção para que o histórico não substitua uma nova importação, o fluxo Chromium foi repetido com regressão específica e passou; nove testes de conversão também passaram com o limite de cinco minutos efetivamente coberto.

Entrega para escuta e revisão: `E:/Pemara/deliveries/voice_conversion_20261106/teste_real_rui`. Timbre, naturalidade e aprovação de uso continuam sob avaliação do proprietário; não foi declarada equivalência de qualidade com ElevenLabs.

No teste técnico de 41 s, o ASR independente apontou três substituições em 99 palavras (`encontra`/`encontre`). Isso pode envolver reconhecimento ou conversão; requer escuta. O teste comprova execução de múltiplas janelas e duração, mas não foi promovido como fala lexicalmente exata. As duas transcrições e `lexical_comparison.json` permanecem junto ao job. A entrega principal é o vídeo A01 v02 de 13,666 s, cuja comparação ASR coincidiu.

Também corrigidos na revisão final: ordem de importação antes da escolha vocal nas telas estreitas e limpeza da seleção antiga do arquivo ao abrir outra mídia do histórico. Teste Chromium de importação, prévia, download e layouts repetido com verificação da ordem visual, sem falhas.
