# Status do Treino - Intro Ritmos da Revolta

Atualizado em 2026-06-30.

## Prioridade

Este projeto esta marcado como prioridade maxima de treino de video.

- Flag ativa: `TRAINING_PRIORITY.flag`
- Outros treinos de GPU ficam bloqueados enquanto esta flag existir.
- Geracao manual no Maestro/ComfyUI continua permitida.

## Ordem operacional - 2026-06-30 13:00

Por ordem do usuario, o treino da intro deve iniciar em 2026-06-30 as 13:00 e so parar com
ordem manual explicita.

- Tarefa agendada:
  `RitmosIntroTreinoStart1300UntilStop`
- Script de inicio:
  `start_intro_training_1300_until_stop.ps1`
- Flags que serao ativadas as 13:00:
  - `TRAINING_PRIORITY.flag`
  - `..\ComfyUI\lora_videos\wan_lora_trainer\training_enabled.flag`
  - `..\ComfyUI\lora_videos\wan_lora_trainer\training_override_until_stop.flag`
- Tarefa antiga de parada automatica desativada:
  `RitmosTreinoStopUser`
- Watchdog existente:
  `RitmosTreinoWatchdog`, a cada 5 minutos.

Config de refinamento continuo:

- Arquivo: `..\ComfyUI\lora_videos\wan_lora_trainer\config_intro_60s_5b.yaml`
- `steps: 4000000`
- `lr: 1.2e-5`
- `save_every: 750`
- `max_step_saves_to_keep: 12`

## Dataset

Dataset sintetico inicial criado a partir dos assets reais do projeto.

- Total: 102 clips
- Treino: 84 clips
- Validacao: 18 clips
- FPS base: 12
- Frames por amostra: 5
- Resolucao base: 512x288 e 768x432
- Pasta: `..\ComfyUI\lora_videos\wan_lora_trainer\dataset_intro_60s`

## Configuracao

- Arquivo: `..\ComfyUI\lora_videos\wan_lora_trainer\config_intro_60s_5b.yaml`
- Nome: `intro_ritmos_60s_v1`
- Trigger: `intro60`
- Arquitetura: `wan22_5b`
- Modelo base: `Wan2.2-TI2V-5B-Diffusers`
- Steps alvo: 12000
- Sampling interno: desativado na primeira rodada para evitar estouro de VRAM no VAE.

## Operacao

Comandos uteis:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1 -ForcarInicio
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1 -ForcarParada
Get-Content E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\logs\training.err.err -Tail 80
```

## Proxima validacao

1. Treino pausado em 2026-06-30 para avaliacao visual.
2. Checkpoint publicado no ComfyUI:
   `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\loras\intro_ritmos_60s_v1.safetensors`
3. Primeira previa gerada pelo Studio com Wan 5B + LoRA, reprovada por ficar clara/fofa demais e quase sem evolucao:
   `outputs\clips\intro_preview_lora_20260630_0829.mp4`
4. Frame de controle da primeira previa:
   `outputs\clips\intro_preview_lora_20260630_0829_frame.png`
5. Segunda previa sem LoRA, mais fiel ao clima, mas conservadora/quase congelada:
   `outputs\clips\intro_preview_b_sem_lora_20260630_0842.mp4`
6. Terceira previa com cena Tenebra e LoRA fraco 0.25, melhor direcao visual ate agora:
   `outputs\clips\intro_preview_c_tenebra_lora025_20260630_0850.mp4`
7. Correcao de duracao em 2026-06-30:
   - o Studio antigo estava limitado a 121/129 frames, gerando apenas 4.03s em 30fps;
   - backend e frontend foram ajustados para 241 frames padrao e 361 frames maximo;
   - teste longo validado no Studio temporario `8028`;
   - preview de 8.03s gerado:
     `outputs\clips\intro_preview_d_tenebra_8s_lora025_20260630_0905.mp4`
8. Regra nova de geracao:
   - evitar prompt "cidade musical bonita";
   - usar cenas fortes como chapeu, cidade calada, onda de silencio e estudio vazio;
   - usar LoRA entre 0.20 e 0.35 no primeiro passe;
   - nao aceitar clipe de avaliacao com menos de 8s;
   - validar por clipe curto antes de montar 60s.
9. Proxima etapa: gerar as 9 cenas em clipes de 8s e montar o primeiro MP4 720p/30fps de 60 segundos.
