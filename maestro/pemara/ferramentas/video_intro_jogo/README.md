# Projeto Animacao Introducao - Ritmos da Revolta

Este pacote foi separado para treinar/gerar uma intro animada do jogo em outro computador.
Ele nao e uma build do jogo. E um pacote de referencia criativa: imagens, sprites, audio,
documentacao e prompts.

## Objetivo

Criar uma abertura em video com tom de misterio, estilo intro de jogo de PlayStation 1 e
Super Nintendo, mas com acabamento atual:

- 16:9, preferencia 1920x1080 ou 1280x720.
- 24 fps ou 30 fps.
- Duracao principal sugerida: 90 segundos.
- Visual: pixel art/2.5D/parallax, luz dramatica, composicao cinematografica, camera lenta.
- Sensacao: cidade musical tomada pelo silencio, Tenebra nascendo como ausencia de ritmo.
- Musica: dark synth industrial, grave, misteriosa, sem vocal na trilha se houver narrador.

## Regra de direcao do projeto

Para cutscene/intro narrativa do jogo, os frames finais devem ser ambientais:

- Sem herois, chefes, monstros, humanos, corpos, rostos ou silhuetas.
- Sem texto inventado dentro das imagens.
- A historia deve ser contada por objetos, luz, cidade, instrumentos, chapeu, rachaduras,
  cabos, palco vazio, static, notas musicais quebradas e energia.
- Os sprites estao no pacote como referencia de identidade, paleta, proporcao e mundo,
  nao como obrigacao de aparecerem no video final.

## Estrutura

- `assets_referencia/backgrounds/` - abertura, fases, menu e cenarios do jogo.
- `assets_referencia/transicoes/` - slides ambientais ja aprovados para transicoes/final.
- `assets_referencia/sprites/herois/` - sprites finais dos herois e Gray.
- `assets_referencia/sprites/inimigos_f2/` - inimigos comuns.
- `assets_referencia/sprites/chefes/` - chefes e Tenebra.
- `assets_referencia/audio/music/` - musicas candidatas e referencias de clima.
- `assets_referencia/audio/sfx/` - efeitos sonoros uteis para montagem.
- `docs_referencia/` - docs originais e configs runtime do jogo.
- `storyboard/` - roteiro e lista de assets por cena.
- `prompts/` - prompts prontos para video, cenas, musica e voz.
- `manifest/MANIFEST_ARQUIVOS.csv` - lista de arquivos copiados.

## Ordem recomendada no outro computador

1. Leia `docs/00_visao_criativa_intro.md`.
2. Leia `storyboard/01_roteiro_intro_90s.md`.
3. Use `prompts/01_prompt_video_master.md` como prompt base.
4. Gere por cenas usando `prompts/02_prompts_cena_por_cena.md`.
5. Gere a trilha e/ou narracao com `prompts/03_prompt_musica_voz.md`.
6. Compare cada resultado com `prompts/04_checklist_qualidade.md`.

## Saida esperada

Um video de abertura que pareca canonico para Ritmos da Revolta:

- Comeca com uma cidade que tinha musica.
- Mostra o estudio de Maestro sem mostrar pessoas.
- Mostra o Chapeu do Espectro e o nascimento do silencio.
- Mostra a cidade perdendo cor e ritmo.
- Sugere que uma revolta vai comecar.
- Fecha com `RITMOS DA REVOLTA`.

