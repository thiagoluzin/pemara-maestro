# ZICO no Maestro

Origem: ZIP `ZICO_AUDIO_STUDIO_1.0_WINDOWS_RTX5090_FINAL.zip` fornecido pelo proprietário em Downloads. A cópia original foi preservada.

## Uso

- Painel integrado, após recarregar o Studio: `http://127.0.0.1:8029/api/zico`.
- Painel independente local: `http://127.0.0.1:8790/api/zico`.
- A área **Tratar audio** do Maestro contém o botão **ZICO — pipelines de som**.
- **MMAudio** aparece como provider `zico_mmaudio` no fluxo existente de som de takes aprovados. É uma escolha adicional; HunyuanVideo-Foley não foi substituído.
- **Fish Speech** tem geração explícita de texto para fala pelo painel e por `POST /api/zico/fish/jobs`. Não clona referências. O retorno é um job consultável em `GET /api/zico/jobs/{job_id}`, com candidato para escuta humana.
- **Chatterbox**, **Qwen3-TTS**, **ACE-Step** e reinstrumentação reutilizam os pipelines existentes do Maestro. O roteador apenas sugere uma rota; não dispara geração nem troca o motor escolhido.
- Mixagem: `POST /api/zico/mix`, com `dialogue`, `music`, `sfx` e `target_lufs`. Salva um novo WAV PCM 24-bit/48 kHz em pasta única, preservando fontes. `loudnorm` de uma passagem; não confundir com masterização de duas passagens nem aprovação artística.

## O que foi corrigido em relação ao ZIP

O ZIP implementava apenas roteamento e mixagem e anunciava outras capacidades sem adaptadores. Seu instalador também usava `uv venv` sem garantir pip e não verificava códigos de saída. Esta integração instala ambientes separados, usa os motores existentes quando presentes, acrescenta os runners de Fish/MMAudio e diferencia software instalado, pesos verificados e inferência validada.

Não execute o instalador/desinstalador legado do ZIP sobre esta integração: ele aponta para `%LOCALAPPDATA%`, outra instalação. Para abrir a integração use `scripts/start_maestro_zico.ps1`.

## Ambientes

- Núcleo: `.venv`, Python 3.11.
- MMAudio: `engines/mmaudio/repo/.venv`, PyTorch 2.8.0+cu128, torchvision 0.23.0, torchaudio 2.8.0. CLIP local em `engines/mmaudio/clip`; pequena alteração isolada permite esse caminho sem baixar novamente durante inferência.
- Fish: `engines/fish/repo/.venv`, sincronizado pelo `uv.lock` oficial com extra `cu128`, PyTorch 2.8.0+cu128.
- Fish usa o override de protobuf declarado no próprio projeto oficial (`>=3.20,<6`). `uv pip check` acusa o pin antigo de descript-audiotools; a API e o import do modelo passam com o override oficial. Não rebaixar protobuf sem revisar esse contrato.
- TorchCodec opcional do MMAudio não carrega neste Windows por dependência DLL/FFmpeg. O runner usa o caminho oficial de vídeo com PyAV e torchaudio 2.8/SoundFile, sem TorchCodec. Não declarar esse codec auxiliar validado.

## Pesos e validação

`scripts/download_weights.py` baixa arquivos de repositórios oficiais Hugging Face, fixa a revisão consultada, verifica tamanho/ranges e SHA-256 antes de promover cada arquivo. Pode ser retomado sem apagar blocos válidos. Os recibos `mmaudio_weights_verified.json` e `all_weights_verified.json` registram revisões, caminhos, tamanhos e hashes.

Há gates de fila ComfyUI, VRAM e reserva cooperativa antes da geração. Nenhum processo alheio é encerrado. A consulta ao ComfyUI nesses runners pertence ao backend autônomo do Maestro, após uma solicitação de geração. Operação de ComfyUI pelo Codex continua exclusivamente via MCP.

Os testes desta instalação cobrem API, autorização, roteamento sem envio, mixagem CPU preservando originais, recusa antes dos pesos e regressão do provider. Não foi feita avaliação artística nem inferência de fala/Foley na GPU. Instalação técnica não equivale a qualidade de áudio aprovada.

## Arquivos de integração e rollback

- `services/studio/zico_audio.py`: painel/API e jobs de fala.
- `services/studio/main.py`: registro do router.
- `services/studio/video_sound.py`: verificação opcional de arquivos necessários ao provider.
- `ferramentas/audio_neural/video_sound/providers.json`: provider MMAudio.
- `app/index.html`: botão do painel.
- Backup das versões anteriores em `backups/zico_install_20260912_214113`.

Para rollback, primeiro conferir se não há jobs ativos; remover somente o registro/arquivos ZICO e restaurar os trechos alterados a partir do backup. Não sobrescrever alterações posteriores nem apagar modelos, saídas ou projetos. O serviço original do Studio requer elevação administrativa para reiniciar nesta máquina.
