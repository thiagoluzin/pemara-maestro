---
name: ai-video-intro-pipeline
description: "Pipeline para criar, refazer ou finalizar intros/cutscenes de jogo com video IA (Veo, Higgsfield, Flow ou similar), montagem ffmpeg, QC visual, musica/SFX, logo oficial, upscaling FHD e pacote de registro. Use quando o pedido mencionar intro, abertura, cutscene, video IA, Veo, cinematic, logo no final, sincronizar musica, upscale/FHD, registros de marca ou direitos autorais de audiovisual."
---

# AI Video Intro Pipeline

## Direção e acabamento vigentes

Usar `pemara-video-production-lead` para intenção/produção, `pemara-cinematography-director` para fotografia, `pemara-performance-director` quando houver personagens e `pemara-film-editor` para ritmo/montagem. Carregar por fase, sem criação automática de subagentes.

O Maestro usa MiniMax H3 com Sage + Spectrum, sem LTX ou troca automática para provedor externo. As regras de slides ambientais/anime abaixo são específicas da intro Ritmos da Revolta quando esse brief as exigir; não proíbem elenco ou impõem anime a outras produções. Preservar versão/identidade e estilo do pedido atual.

Revisar o MP4 inteiro, atuação/ação, fotografia, identidade, geografia e ritmo, além de contatos/junções e técnica. Contact sheet não comprova movimento. Som novo, geração, registro e publicação dependem do escopo; fonte silenciosa não ganha música/Foley por padrão. Não reabrir projetos encerrados.


Para a intro FFVIII e seu duelo M08–M16, leia primeiro `ffviii-gunblade-duel-production` e aplique a
rota V8 antes de gerar, corrigir, montar ou registrar qualquer take desse escopo.

Use esta skill para produzir ou corrigir uma intro/cutscene de jogo com takes gerados por IA, montagem local e validacao tecnica. O objetivo e evitar retrabalho caro: primeiro fechar o material visual certo, depois audio, logo, upscale e registro.

## Ordem de trabalho

1. Leia o brief atual, `intro-60s.md` se existir, prompts em `projeto_animacao_introducao/prompts/`, scripts de render e assets oficiais usados no fechamento.
2. Separe direcao criativa de montagem tecnica: use `creative-director` para prompts/storyboard, `automation-engineer` para scripts/render, `game-audio-designer` ou `audio-analysis` para musica/SFX, e `sprite-image-reading` apenas para medir/extrair assets existentes.
3. Gere ou refaca takes animados antes de montar. Se o problema for falta de cenarios, movimento ruim, pixel art, sprite look, texto falso, pessoas/silhuetas ou cenario repetido, refaca o take. Nao esconda o problema com stills, fotos ou PNGs inseridos no meio do video.
4. Revise a leitura visual sem som quando útil, silenciando o player. Preserve o áudio existente; proxy video-only exige decisão de edição e não substitui a fonte.
5. Depois da aprovação visual/picture lock, aplique a música, os SFX, a mixagem e a marca já autorizados. Cada acabamento gera um candidato com o áudio aprovado.
6. Atualize `assets/videos`, `docs/registro_marca`, pacote `direitos_autorais` e `FIXLOG.md` quando a entrega mudar arquivos finais.

## Geracao de takes

- Use takes curtos e idempotentes, normalmente 8s, com nomes estaveis (`01_...mp4`, `02_...mp4`).
- Prompts de cutscene/transicao deste projeto devem ser ambientais: sem personagens, corpos, rostos, olhos, silhuetas, bosses, monstros, texto legivel, watermark, UI ou logos gerados pelo modelo.
- Reforce estilo quando necessario: `hand-drawn anime cel animation`, `not pixel art`, `not sprites`, `not gameplay footage`.
- Scripts de API devem ter `--dry-run`, `--force`, log, retomada, timeout e tratamento claro de quota/rate limit. Nunca imprimir chave de API.
- Quando houver quota ou chave instavel, registre no log qual take ficou pendente e nunca sobrescreva take bom por arquivo parcial.

## QC visual

Antes de chamar qualquer versao de final:

- Gere contact sheet ou frames amostrados dos takes e da montagem.
- Verifique duracao, resolucao, FPS, frame count e ausencia/presenca de audio conforme a etapa.
- Reprove take com pixel art/16-bit quando o pedido for animacao de verdade.
- Reprove texto falso, logos gerados por IA, rostos/olhos/silhuetas e qualquer ator em slide ambiental.
- Se o usuario apontar defeito de qualidade, investigue causa raiz no take/render/composicao. Evite remendo de camada por cima.

## Montagem e audio

- Inspeção visual pode silenciar o player; preserve o áudio original. Não remover faixa da fonte nem incorporar trilha nova sem escopo autorizado.
- Prefira encode unico com cortes limpos a concatenar segmentos reencodados com fades em todo corte.
- Para musica final, medir duracao, sample rate, loudness, clipping e silences quando necessario.
- Mix final deve ter headroom para SFX; alvo pratico: perto de `-16 LUFS`, true peak abaixo de `-1.5 dBTP` quando possivel.
- SFX pontuais entram depois da musica base aprovada: impacto, static, neon, cabos, pulso, hit de titulo.

## Logo oficial e encerramento

- Extraia a logo de fonte oficial do projeto, como `assets/backgrounds/menu_bg.png`; salve tambem em `assets/ui` quando o usuario pedir.
- Se a alpha extraction carregar matte escuro ou parecer colada via Paint, nao use overlay RGBA cru. Use composicao por luz, por exemplo `blend=screen`, glow ou recorte melhor a partir da fonte oficial.
- Nao deixe fade-to-black acidental no encerramento. Se a logo e o titulo devem fechar a intro, mantenha a composicao visivel ate o ultimo frame.
- Valide frame de logo e ultimo frame. Quando a visualizacao falhar, meca luminancia do frame para descartar tela preta.

## FHD e upscale

Depois da aprovação da fonte, siga o [contrato de âncoras e acabamento de vídeo](../pemara-video-production-lead/references/dlss5-full-frame-required.md) para o tipo declarado. Preserve o nativo, o candidato, o áudio, os recibos e os hashes. Um redimensionamento isolado não substitui o acabamento autorizado. Foley novo ou enhancer externo exigem escopo próprio.

Entrega de arquivo não significa publicação. Disponibilizar somente as versões solicitadas e identificar o estado de revisão do artefato exato. Registro do projeto preserva fontes/histórico; pacote final usa hashes dos arquivos efetivamente aprovados.

## Registro e rastreabilidade

- Copie finais para `assets/videos/` e para `docs/registro_marca/`.
- Atualize `docs/registro_marca/README.md` com SHA256 dos arquivos finais.
- Reconstrua `docs/registro_marca/direitos_autorais/MANIFEST.csv` quando adicionar ou trocar video, frame, musica, logo ou script relevante.
- Append em `FIXLOG.md` com: data, arquivo:linha, problema, causa raiz, correcao e verificacao.


## Direção executável

- Duração vem dos beats úteis e da grade qualificada; contratos específicos, como FFVIII V8 e combate contínuo, prevalecem sobre exemplos de clipes modulares.
- Não trocar para modelo barato/caro para testar por hábito. Usar um segmento representativo dentro do motor, controles e orçamento autorizados antes de repetir o lote.
- Texto/logo exatos vêm de composição determinística e assets oficiais. Elementos proibidos de um slide ambiental não são restrições universais do elenco de outros projetos.
- Edição técnica e codecs usam `video-production`; correção começa pela causa na fonte, sem emenda para disfarçar falha.

## Verificacao minima

Exemplos históricos da intro Ritmos da Revolta: usar somente se pertencem ao projeto atual e o render/registro já estiver autorizado. Não executar render por uma atualização de agentes:

```powershell
node --check tools\finalize_veo_intro_60s_audio.mjs
npm run render:intro:veo60
npm run render:intro:veo60:final
py -3 -m py_compile tools\asset_pipeline\build_copyright_package.py
py -3 tools\asset_pipeline\build_copyright_package.py
rg -n "ritmos_intro_60s_final_fhd" docs\registro_marca\direitos_autorais\MANIFEST.csv
```

Nao declare pronto sem pelo menos: render OK, duracao/FPS/frame count OK, audio final medido, frame de logo conferido, ultimo frame sem tela preta e registros atualizados.

## Segurança de APIs e takes

Mantenha chaves fora de prompts, comandos, logs e manifests. Antes de enviar imagem, voz ou referência a serviço externo, confirme autorização e ausência de dado pessoal desnecessário. Valide tipo, tamanho e hash do arquivo retornado. Se criar upload, webhook, endpoint ou publicação online para os takes, acione `pemara-online-security-guardian` e não exponha a origem do gerador diretamente.
