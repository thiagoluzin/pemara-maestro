# Treino diario da LoRA Sprunki

Esta automacao roda diariamente das `00:00` ate `04:00`.

## Skill operacional

A partir de 2026-07-14, tarefas de treino, avaliacao e promocao de LoRA Sprunki devem usar a skill:

`E:\Pemara\.agents\skills\sprunki-lora-trainer`

Regra central: nao promover LoRA porque o treino terminou. Promover somente depois das amostras de
avaliacao provarem identidade Sprunki limpa, silhueta boa, corpo inteiro, expressao controlada e baixa
taxa de artefato.

## Fluxo

1. Cria um experimento em `experiments/lora_YYYYMMDD_HHMMSS`.
2. Monta um dataset versionado em `experiments/<run>/dataset/img`.
3. Usa `lora_dataset/img/20_sprunki_char/ratings.json`, quando existir:
   - nota 5: `30_sprunki_char_gold`
   - nota 4: `20_sprunki_char_good`
   - nota 3: `5_sprunki_char_variants`
   - nota 0-2: ignora
4. Sem ratings, usa todas as imagens em `20_sprunki_char_good`.
5. Normaliza captions com `sprunki_char`.
6. Executa `auto_train.py`.
7. Gera amostras de avaliacao em `experiments/<run>/eval_samples`, por padrao nas forcas `0.15`, `0.30` e `0.45`.
8. Salva `config.json`, `summary.json`, `train.log`, `eval_samples.log` e modelo no experimento.
9. Copia a LoRA final para:
   - `lora_dataset/model/sprunki_lora_daily_latest.safetensors`
   - `E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\loras\sprunki_lora.safetensors` via `auto_train.py`

## Instalar tarefa

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_daily_lora_task.ps1
```

## Testar sem treinar

```powershell
python .\daily_lora_cycle.py --dry-run
```

O `--dry-run` pode rodar fora da janela de GPU porque nao inicia treino nem ComfyUI. Ele cria uma
pasta `experiments/dryrun_YYYYMMDD_HHMMSS` para auditar dataset/captions sem confundir com treino real.

## Rodar manualmente dentro da janela

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily_lora_window.ps1
```

## Rodar ate ordem de parada

Use somente quando a prioridade atual for Sprunki:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_sprunki_until_stop.ps1
```

Parar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_sprunki_training.ps1
```

Esse modo cria `SPRUNKI_TRAINING_PRIORITY.flag` e alterna presets conservadores com avaliacao
automatica. O guard libera apenas jobs de treino com nome `sprunki`.

## Ajustar intensidade

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_daily_lora_task.ps1 -Steps 900 -Dim 8 -Alpha 8 -LearningRate 0.00002
```

## Preset atual

Depois da rodada `lora_20260618_000101`, que gerou imagens quebradas em forcas altas, o preset diario foi reduzido e a janela foi encurtada para liberar a loja a partir de `05:30`:

- `Steps`: `900`
- `Dim/Alpha`: `8/8`
- `LearningRate`: `0.00002`
- `BatchSize`: `2`
- avaliacao automatica: `4` prompts em `0.15`, `0.30` e `0.45`

Esse preset prioriza estabilidade. Se as amostras ficarem limpas porem fracas, aumente primeiro `Steps` para `1200`; se ainda estiver fraco, teste `Dim 16 -Alpha 16`, mantendo `LearningRate 0.00002`.
