# Música a partir de um prompt — implantação de 05/10/2026

O modo musical local cria letra e direção com Qwen, compõe e gera o áudio no motor escolhido e prepara o MP3. Voz é o padrão; Instrumental é uma escolha explícita. Letra própria, BPM, modelos ACE-Step e partitura ficam nos ajustes opcionais. A composição automática YuE2 não exige revisão humana intermediária. A avaliação artística do áudio continua pendente de escuta pelo proprietário.

## Escritor e atualização pesquisada

- Padrão: `qwen3.8-27b-uncensored-yarn-524k:latest` no Ollama local `127.0.0.1:11435`, já instalado. A janela desta tarefa é 8192 tokens, sem alterar o perfil longo do OpenCode.
- GPU: `num_gpu=99`, reserva cooperativa do Studio, fila Comfy verificada antes de liberar seus modelos ociosos, mínimo de 22 GiB livres. O escritor verifica que pelo menos 95% do tamanho reportado está na VRAM; CPU/offload significativo bloqueiam o áudio.
- `keep_alive=0`; antes de continuar ao áudio, o escritor confirma pelo `/api/ps` que seu modelo saiu da memória. Os motores usam a GPU em sequência.
- Teste real do escritor: 26,48 s, `writer_vram_bytes=19342200665`; depois o modelo deixou o `/api/ps`. A etapa de confirmação automática de descarregamento adicionada depois foi verificada pelos testes de contrato.
- Fonte oficial consultada: https://huggingface.co/Qwen/Qwen3.8-27B ; revisão `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, última modificação 14/08/2026.
- Fonte dos pesos locais: https://huggingface.co/JonathanColetti/Qwen3.8-27B-Uncensored-GGUF ; revisão atual `45d0fc0ad6cfcf9eeee6008ddaea925536409b18`, última modificação 29/08/2026. O SHA-256 local do Q5_K_M coincide com o LFS atual: `24780644a95f759a9aeeb228c3d852028f2fd40ce0b74d68134246ec4a959547`. Não há pesos novos desse arquivo para baixar.
- Qwen3.6 Balanced Q6_K_P também permanece na revisão atual de seu repositório. A escolha do 3.8 aproveita a geração posterior já instalada. Benchmarks gerais não comprovam superioridade de letras; a amostra fica para avaliação artística.

## YuE2 e teste real

Um trabalho do Maestro encadeia todas as etapas. Para voz em até 60 s, o backend compõe, remove somente a seção instrumental inicial identificada por `% intro` antes de `% verse`/`% chorus`, preserva cabeçalho e notas seguintes e gera o áudio automaticamente. Para músicas longas e instrumentais, o grafo pode ligar composição diretamente à geração. A partitura original e a usada são preservadas no resultado.

Nos testes iniciais de 30 s, a introdução consumia quase toda a amostra. A correção foi conferida no teste final: voz detectada desde o início por Whisper small local em CPU. ASR não comprova pronúncia perfeita, fidelidade musical ou aprovação artística.

- Composição MCP: `d7aac1c3-cd7c-4d2d-a011-f1d85522cd61`.
- Áudio MCP: `c1da8f11-c9a2-4956-8601-cf06ecb85945`.
- Ambos os grafos foram validados contra o runtime ativo sem erros, avisos ou nós pagos. Runtime ComfyUI 0.37.0; RTX 5090.
- Amostra: **Noite de Ferro**, 27,96 s, estéreo 48 kHz. Exportação MP3 real de 320 kbps.
- História Maestro: `music-simple-noite-de-ferro-qwen38-20261005-attempt03`, estado `PENDING_HUMAN_REVIEW`.
- Evidências: `outputs/simple_music_deployment_20261005/`, incluindo letra, grafos, partituras, pesquisas de revisão, áudio original, ASR e resultado de entrega.
- 34 testes focados passaram: prompt vocal sem letra/partitura, escolha explícita instrumental/manual, escritor GPU, rejeição CPU/offload, liberação antes do áudio, cadeia automática, intro curta, LeVo mixed vocal, MP3 e contratos existentes de áudio. JavaScript passou no `node --check`.
- Player público carregou MP3 com duração 27,96 s e sem erro. Controles opcionais fechados, Instrumental desmarcado e modo YuE2 automático selecionado.
- Download real pelo navegador público: `C:\Users\admin_remoto\Downloads\Noite de Ferro.mp3`; codec MP3 320 kbps, estéreo 48 kHz e hash idêntico ao cache servido. Captura: `outputs/simple_music_deployment_20261005/maestro_implantado.png`.

## Limites e recuperação

ACE-Step e LeVo2 receberam o escritor automático. LeVo2 usa `mixed` com letra para voz e mantém `bgm` para instrumental, com seu limite piloto de 5–15 s. Não foi feito novo teste real de voz desses dois motores nesta implantação; seus contratos foram testados. A escolha de motor permanece explícita. Não houve instalação/download de modelos, uso pago, mudança H3 ou substituição de mídia anterior.

O Studio foi reiniciado pelo supervisor somente depois de conferir que não havia trabalhos próprios ativos. O ComfyUI não foi reiniciado. Backup inicial: `backups/simple_music_20261005_143818`. O checkout contém trabalho concorrente; uma recuperação deve reaplicar apenas os trechos desta mudança e não sobrescrever arquivos inteiros indiscriminadamente. Build publicado: `20261005-simple-music-qwen38-gpu-v4`.
