# Motor Global de Animacao - Referencia Pre-Parabens

Fonte analisada: `E:\video_pre_parabens`

Video final de referencia:

`E:\video_pre_parabens\output\Pre-parabens_versao_final.mp4`

## Leitura do pacote

O projeto nao e um unico prompt longo. Ele e um pipeline de animacao por takes curtos:

- imagens-base aprovadas;
- fila de takes em JSON;
- prompts restritivos por cena;
- geracao image-to-video externa via Higgsfield/Kling;
- QC por contact sheet e frame medio;
- rejeicao/refacao de take ruim;
- montagem final com musica normalizada e branding Pemara.

Isso e exatamente o padrao que deve virar motor global: clipes curtos, controlados, avaliados e montados.

## Estrutura encontrada

- `assets_aprovados/`: imagens e musica base aprovadas.
- `takes_higgsfield/`: 16 clipes gerados sem audio.
- `qc/`: contact sheets, frames medios, crops de validacao e reprovados.
- `output/`: preview, versao final, frames da montagem e branding.
- `FULL_TAKE_QUEUE.json`: roteiro completo, tempos, imagens-base e prompts.
- `HIGGSFIELD_JOBS.json`: ids/resultados dos jobs gerados.
- `AUDIO_ANALISE.json`: metadados da musica e regra de loudness.

## Metadados importantes

Video final:

- resolucao: `1920x1080`;
- fps: `24`;
- duracao: `146.58s`;
- video codec: `h264`;
- audio codec: `aac`;
- loudness medido: perto de `-15 LUFS`, true peak perto de `-1.72 dBTP`.

Musica base:

- arquivo: `assets_aprovados/fusao_musical_multiverso_dos_tres.mp3`;
- duracao: `138.371s`;
- bpm: `156.61`;
- regra declarada: a musica deve ser o eixo da timeline.

Observacao: o final ficou maior que a musica base, provavelmente por intro/outro/branding. Para o motor global, isso deve virar regra explicita: `duracao_total = intro + corpo musical + outro`, ou o render deve cortar/fadar para bater exatamente no alvo.

## Padrao visual aprovado

O estilo base e:

- 3D cartoon premium;
- mundo infantil cinematografico;
- cores vivas, luz neon controlada, palco, floresta musical, portais;
- camera suave com push-in, parallax e pequenas variações;
- particulas, confete, notas musicais, brilhos e luzes de palco;
- movimento emocional leve, sem exagero;
- personagens preservados entre takes;
- sem texto gerado pelo modelo;
- sem logo nativo no modelo;
- audio separado da geracao de video.

## Regra de movimento

Os prompts bons usam movimento controlado:

- slow push-in;
- portal shimmer/pulse;
- floating confetti;
- musical notes drifting;
- soft stage lights;
- hair/dress movement;
- tiny idle movement;
- candle flicker;
- breathing/head turns/body sway;
- subtle clap/wave quando necessario.

Evitar prompt vago como “animate beautifully”. O motor deve sempre exigir movimentos concretos por camada:

- camera;
- luz;
- particulas;
- personagem;
- objeto;
- ambiente.

## Regra de identidade

As restricoes de identidade foram fundamentais:

- preservar faces exatamente;
- nao adicionar personagens;
- nao gerar texto;
- nao gerar marca d'agua;
- Pedro observa, nao dança;
- pulseira visivel, mas nao magica;
- Mariana tem uma pinta, Rafaela nao tem;
- Sprunkis preservados;
- trio K-pop preservado no fundo.

Para o motor global, cada projeto precisa de uma ficha de identidade:

- personagens;
- proibicoes;
- detalhes fisicos fixos;
- roupas;
- objetos proibidos;
- nivel permitido de movimento.

## QC encontrado

O pacote ja tinha uma regra boa:

- gerar contact sheet para cada take;
- extrair frame medio;
- validar crops de personagens;
- rejeitar morph de rosto, texto falso, personagem extra, corpo errado, danca indevida, objeto brilhando errado.

O take `16_familia_final` teve versao reprovada por estar pouco animada e foi refeito com prompt mais forte de movimento. Isso confirma uma regra do motor:

Se o take parecer retrato estatico, refazer exigindo microacoes humanas e movimento continuo.

## O que isso ensina para treino

Treinar apenas este video criaria um LoRA estreito demais. O objetivo correto e treinar capacidades globais:

1. Preservacao de identidade em animacao curta.
2. Movimento suave de camera/parallax.
3. Microacoes humanas naturais em estilo 3D cartoon.
4. Particulas e luzes sem destruir personagens.
5. Consistencia entre takes.
6. Transformacao de imagem aprovada em clipe de 8 a 12 segundos.
7. Montagem final guiada por audio.

Esse projeto deve ser usado como referencia ouro, nao como dataset unico.

## Dataset global recomendado

Criar uma biblioteca de projetos com a mesma estrutura:

```text
projeto/
  assets_aprovados/
  take_queue.json
  takes/
  qc/
  output/
  metadata.json
```

Para cada take aprovado, salvar:

- imagem inicial;
- prompt usado;
- video gerado;
- frames: inicial, 25%, 50%, 75%, final;
- contact sheet;
- tags de movimento;
- nota de QC;
- motivo se foi aprovado/reprovado.

Categorias de treino:

- `environment_motion`;
- `character_idle`;
- `gentle_walk`;
- `dance_light`;
- `portal_effect`;
- `stage_lights`;
- `confetti_particles`;
- `family_reaction`;
- `brand_intro`;
- `brand_outro`.

## Motor global proposto

1. Receber objetivo do video.
2. Quebrar em takes curtos de 5s a 12s.
3. Exigir imagem-base aprovada para cada take importante.
4. Gerar prompt a partir de template:
   - acao principal;
   - movimentos permitidos;
   - preservacao de identidade;
   - proibicoes;
   - sem texto/logo/audio nativo.
5. Gerar clipe.
6. Extrair frames e contact sheet.
7. Avaliar com checklist visual.
8. Regerar somente takes ruins.
9. Montar timeline por audio.
10. Normalizar audio e exportar MP4 final.

## Prompt base reutilizavel

```text
Animate this approved image as a polished 3D cartoon cinematic clip.
Use controlled motion only: slow camera push-in, subtle parallax, gentle ambient movement,
soft lighting changes, drifting particles/confetti when appropriate, and natural micro-motions.
Preserve every character identity, face, outfit, object, composition and style exactly.
Do not add new characters, text, logos, watermarks, captions, symbols or native audio.
Avoid exaggerated motion, face morphing, warped hands, unstable eyes, extra limbs and sudden camera cuts.
```

## Prioridade para o ecossistema Pemara

Este pacote deve virar referencia do modulo de videos do Maestro, ao lado da intro de jogo:

- usar como padrao de organizacao de fila de takes;
- usar como padrao de QC;
- usar como estilo-alvo para treinos de video 3D cartoon;
- usar NVIDIA/NIM apenas para analisar prompts, logs e QC, nao como agente autonomo;
- manter geracao/treino local com Wan/LTXV quando for possivel;
- usar Higgsfield/Kling/Veo como referencia externa de qualidade e fallback.

## Proxima acao tecnica

Criar um `video_global_engine` no Maestro com:

- `project_manifest.json`;
- `take_queue.json`;
- gerador de contact sheet;
- extrator de frames;
- validador de metadados;
- montador ffmpeg;
- relatorio de QC;
- pasta padrao para datasets de treino.

Depois, migrar `E:\video_pre_parabens` como primeiro projeto de referencia dentro dessa biblioteca, sem apagar a fonte original.
