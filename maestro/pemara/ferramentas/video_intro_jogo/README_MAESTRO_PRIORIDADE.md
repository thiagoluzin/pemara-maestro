# Prioridade no Maestro

Esta pasta foi movida para dentro do Maestro em:

`E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo`

O pacote original estava em:

`E:\PROJETOS\projeto_animacao_introducao`

## Arquivos principais

- Visao criativa: `docs\00_visao_criativa_intro.md`
- Plano operacional 60s: `docs\05_plano_operacional_intro_60s.md`
- Fila de cenas: `manifest\intro_60s_jobs.json`
- Prompt mestre: `prompts\01_prompt_video_master.md`
- Prompts por cena: `prompts\02_prompts_cena_por_cena.md`
- Checklist: `prompts\04_checklist_qualidade.md`

## Regra de prioridade

Quando o assunto for geracao de video do jogo, esta intro tem prioridade sobre testes genericos,
cavaleiro, hobby e treinos nao relacionados.

## Treino prioritario ativo

O treino LoRA dedicado da intro foi colocado acima dos demais treinos de video.

- Flag de prioridade: `TRAINING_PRIORITY.flag`
- Dataset gerado: `..\ComfyUI\lora_videos\wan_lora_trainer\dataset_intro_60s`
- Config de treino: `..\ComfyUI\lora_videos\wan_lora_trainer\config_intro_60s_5b.yaml`
- Nome do LoRA: `intro_ritmos_60s_v1`
- Trigger word: `intro60`
- Watchdog: `..\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1`
- Log do watchdog: `..\ComfyUI\lora_videos\wan_lora_trainer\logs\watchdog.log`
- Log do treino: `..\ComfyUI\lora_videos\wan_lora_trainer\logs\training.err.err`

Enquanto `TRAINING_PRIORITY.flag` existir, os guards bloqueiam outros treinos de GPU que nao sejam
da intro/ritmos-video-lora. O uso manual do Maestro/ComfyUI para gerar imagem ou video continua livre.

## Saidas esperadas

- Clips de cena: `outputs\clips`
- Montagens temporarias: `outputs\work`
- Final aprovado: `outputs\final\ritmos_da_revolta_intro_60s.mp4`
