# Plano FLUX/Krea implantado

## Estado alvo

- Geracao principal candidata: `FLUX.1 Krea dev FP8`.
- Treino principal diario: continua em `FLUX.1-dev`.
- Treino experimental Krea: separado, com prefixo `lora_krea`.
- `FLUX.2 klein 4B`: registrado como futuro candidato, desativado.

## Arquivos implantados

- `model_matrix.json`: matriz de modelos e workflows.
- `workflow_krea_fp8_api.json`: workflow Krea FP8 separado.
- `ab_prompts.json`: prompts fixos para comparacao A/B.
- `freeze_baseline.py`: congela baseline em `experiments/baseline_flux1_dev`.
- `compare_flux_models.py`: gera comparacao `flux1_dev` vs `flux1_krea_fp8`.
- `download_krea_assets.ps1`: baixa assets Krea via Hugging Face.
- `run_krea_lora_experiment.ps1`: treina LoRA Krea experimental.
- `install_weekly_krea_lora_task.ps1`: agenda treino Krea semanal.
- `install_weekly_flux_compare_task.ps1`: agenda comparacao A/B semanal.
- `bootstrap_flux_experiments.ps1`: roda o fluxo de bootstrap.

## Como baixar Krea

FP8 para geracao:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_krea_assets.ps1
```

FP8 + modelo completo para treino experimental:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\download_krea_assets.ps1 -FullTrainingModel
```

Se o Hugging Face pedir aceite de licenca, aceite no site e defina `HF_TOKEN`.

## Rodar A/B

Com ComfyUI ligado em `127.0.0.1:8188`:

```powershell
python .\compare_flux_models.py
```

Saida:

```text
experiments/compare_flux_YYYYMMDD_HHMMSS/
```

## Bootstrap

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_flux_experiments.ps1 -RunCompare
```

Com download:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_flux_experiments.ps1 -DownloadKrea -RunCompare
```

## Tarefas semanais

Comparacao A/B segura, pula se ComfyUI/Krea nao estiverem prontos:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_weekly_flux_compare_task.ps1
```

Treino Krea experimental, instale apenas depois de baixar o modelo completo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_weekly_krea_lora_task.ps1
```
