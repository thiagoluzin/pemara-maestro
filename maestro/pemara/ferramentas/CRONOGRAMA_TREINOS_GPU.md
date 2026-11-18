# Cronograma de Treinos e Uso da GPU

## Regra principal

REGRA GLOBAL EM VIGOR desde `2026-06-29`:

- Treinos e rotinas automaticas pesadas que usam GPU ficam BLOQUEADOS de `05:00` ate `00:30`.
- Treinos automaticos que usam GPU so podem rodar de `00:31` ate `04:59`.
- Uso rotineiro/manual continua liberado: ComfyUI, Gerador IA do Maestro, cards, videos, edicao e testes sob demanda.
- Essa regra vale ate segunda ordem.
- Raspagem de imagens reais da loja nao usa GPU e pode continuar 24h.

Override manual ativo em `2026-06-29 14:17` por autorizacao direta do usuario:

- Arquivo: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\training_override_until_stop.flag`
- Efeito: libera o treino LoRA de video/Ritmos fora da janela ate ordem de parada.
- Para parar: remover esse arquivo e executar `watchdog_treino.ps1 -ForcarParada`.

Override manual renovado em `2026-07-14` para treino serio de video na RTX 5090:

- Flag de prioridade: `E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo\TRAINING_PRIORITY.flag`
- Config ativa: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\config_intro_60s_5090.yaml`
- Perfil: Wan2.2 TI2V 5B, LoRA rank `160`, `13` frames, `resolution [640]`, `bf16`, `adamw8bit`.
- Log de progresso: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\logs\training.err.err`
- PID principal atual fica em: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\logs\training.pid`
- Para parar com seguranca: `powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\scripts\watchdog_treino.ps1 -ForcarParada`

## Janelas oficiais

| Horario | Rotina | GPU | Status |
| --- | --- | --- | --- |
| `00:31-04:59` | Janela permitida para treinos GPU automaticos | Sim | ativo |
| `05:00-00:30` | Treinos GPU automaticos bloqueados | Sim | bloqueado |
| 24h | Uso manual/rotineiro de ComfyUI, Maestro e Gerador IA | Sim | liberado |
| 24h | Loja/marketing: baixar fotos reais e validar manifesto | Nao | ativo |

## O que fica bloqueado fora da janela

- Treino Sprunki LoRA automatico.
- Treino LoRA de animacao/Wan automatico.
- Comparativos/experimentos automaticos de treino.
- Qualquer script novo de treino automatico deve chamar `E:\Pemara\gpu_window_guard.ps1` ou `E:\Pemara\gpu_window_guard.py`.

## O que NAO fica bloqueado

- ComfyUI como servico.
- Gerador IA do Maestro para uso manual.
- Geracao manual de imagem/video.
- Cards/anuncios sob comando direto.
- Edicao de imagem, video e audio sob demanda.
- Raspagem de fotos reais da loja.

## Estado atual das tarefas

| Tarefa | Horario | Observacao |
| --- | --- | --- |
| `Pemara Sprunki LoRA Daily Training` | diario `00:31` | guard central bloqueia treino fora da janela |
| `Pemara Sprunki FLUX Weekly Compare` | domingo `01:30` | dentro da janela |
| `Pemara Sprunki LoRA Krea Weekly Experiment` | domingo `03:00` | dentro da janela |
| `RitmosTreinoWatchdog` | a cada 5 min | treino automatico bloqueado fora de `00:31-04:59` |
| `RitmosTreinoStartUser` | diario `00:31` | inicio permitido |
| `RitmosTreinoStopUser` | diario `04:59` | parada obrigatoria |
| `Pemara ComfyUI Watchdog` | a cada 1 min | mantem ComfyUI online para uso rotineiro |
| `Pemara Marketing Fotos Reais` | continuo/diario | nao usa GPU; pode rodar 24h |
| `Intro Ritmos 5090 Manual` | override ate ordem de parada | perfil 5090 max pragmatico ativo em 14/07/2026 |

## Trilha de video em treino

- LoRA de video/Ritmos: `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer`
- Flag ativa para treino automatico: `training_enabled.flag`
- Benchmark cinematico criado em `wan_lora_trainer\benchmarks\cavaleiro_campo_aberto_20260629`
- Baseline aprovado: `baseline_video_00003_720p30.mp4`
- Observacao: o baseline saiu em MP4 720p/30fps, mas com `4.03s`; pedidos de `20s` devem ser tratados por segmentos consistentes, nao por 600 frames diretos em 720p na RTX 5080 16GB.

## Guard central

Scripts principais:

- `E:\Pemara\gpu_window_guard.ps1`
- `E:\Pemara\gpu_window_guard.py`

Teste manual fora da janela:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\Pemara\gpu_window_guard.ps1" -Name teste-treino -Kind training
```

Resultado esperado fora de `00:31-04:59`:

```text
BLOCK ... window=00:31-04:59
```

Override emergencial, somente manual e temporario:

```powershell
$env:PEMARA_GPU_WINDOW_OVERRIDE="1"
```
