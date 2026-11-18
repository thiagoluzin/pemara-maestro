# Estudio Pemara de Animacao Profissional

## Objetivo

Criar um estudio gerador de animacoes, nao um pipeline preso a um unico jogo.

`Ritmos da Revolta` e apenas o projeto-teste para validar metodologia, modelos, LoRAs, QC e montagem.

## Formula Universal

1. Brief do projeto.
2. Biblia visual e regras negativas.
3. Storyboard por takes.
4. Keyframe/imagem-base aprovado.
5. JSON fiel do keyframe.
6. Geracao de take curto.
7. QC tecnico e visual.
8. Comparacao A/B de modelo/LoRA.
9. Montagem final.
10. Audio, SFX, musica e mix depois do visual aprovado.

## Modelos Locais Atuais

- Wan2.2 TI2V/I2V 5B: preview principal.
- Wan2.2 A14B GGUF High/Low: render pesado de take aprovado.
- LTXV 13B GGUF: alternativa para movimento/controle.
- Qwen Image: texto e composicao grafica.
- FLUX/Krea: keyframes e imagens-base.

## Treinos Prontos / LoRAs Prontas

Antes de treinar do zero, testar LoRAs prontas:

- LTX Motion Track Control.
- LTX Pose Control.
- LTX Camera Control.
- Wan Camera Push-In.
- Wan FP8 Camera Pack.
- Wan2.2 Distill/Lightning para preview rapido.

Registro oficial:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/templates/studio_video_model_registry.json`

Instalador controlado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\video_global_engine\install_ready_video_loras.ps1 -DryRun
```

Baixar um candidato especifico:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\video_global_engine\install_ready_video_loras.ps1 -Ids wan-camera-push-in
```

## Regra de Teste

Todo novo modelo/LoRA deve passar por:

1. um take dificil;
2. baseline sem LoRA pronta;
3. teste com LoRA pronta;
4. contact sheet;
5. metricas ffprobe;
6. avaliacao visual humana;
7. registro do resultado.

## Benchmark VEO 3.1

Para calibrar o estudio local, usar o video abaixo como golden sample:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/ritmos_intro_60s_final_fhd.mp4`

Relatorio:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/qc/golden_veo31_ritmos_intro_60s_final_fhd/GOLDEN_BENCHMARK.md`

Regra: o alvo local nao e copiar o projeto, e copiar o nivel de producao: acao grande, camera clara, particulas, ambiente rico, cortes com composicao variada, FHD, audio e acabamento.

## Regra de Producao

Nao usar LoRA pronta em producao sem:

- compatibilidade confirmada com o workflow;
- ganho visual claro;
- ausencia de slow motion indesejado;
- ausencia de congelamento de movimento;
- preservacao da identidade visual do projeto.
