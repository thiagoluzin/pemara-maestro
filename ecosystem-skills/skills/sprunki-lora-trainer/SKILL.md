---
name: sprunki-lora-trainer
description: Specialized workflow for Sprunki LoRA training, dataset curation, FLUX/Krea comparison, ComfyUI evaluation samples, promotion gates, GPU-window-safe automation, and troubleshooting in E:/Pemara/maestro/pemara/ferramentas/gerador_sprunki. Use when the user asks about treinar LoRA Sprunki, gerar sprunkis perfeitos, avaliar/prometer sprunki_lora, daily_lora_cycle, Kohya/FLUX training, ratings.json, experiments/lora_*, or Sprunki model quality.
---

# Sprunki LoRA Trainer

## Core Rule

Optimize Sprunki quality, not just training frequency. Never promote a LoRA because training finished;
promote only after eval samples prove clean character identity, silhouette, expression control, and low
artifact rate.

Protect GPU scheduling. Do not start training or ComfyUI generation unless the current user request
explicitly authorizes GPU use now and `E:/Pemara/gpu_window_guard.*` allows it.

## Canonical Project

- Project: `E:/Pemara/maestro/pemara/ferramentas/gerador_sprunki`
- Main daily runner: `run_daily_lora_window.ps1`
- Daily cycle: `daily_lora_cycle.py`
- Trainer: `auto_train.py`
- Eval generator: `generate_lora_eval_samples.py`
- Current public LoRA names:
  - `lora_dataset/model/sprunki_lora_daily_latest.safetensors`
  - `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/models/loras/sprunki_lora.safetensors`

Read `references/operational-rules.md` before changing training presets, dataset tiers, or promotion
logic.

## Workflow

1. Check current state: latest `experiments/lora_*`, latest `summary.json`, dataset counts, and GPU guard.
2. Audit dataset before training:
   - `ratings.json` if present;
   - gold/good/variant counts;
   - duplicate, broken, off-style, cropped, text/watermark, bad anatomy.
3. Keep the main trigger token stable: `sprunki_char`.
4. Train on `FLUX.1-dev` as the main stable route. Treat Krea training as comparative only.
5. Generate eval samples at low/medium strengths first: `0.15,0.30,0.45`.
6. Reject if samples are overcooked, mushy, scary by accident, off-model, cropped, or inconsistent.
7. Promote only with a written reason in experiment `summary.json` or an adjacent QC note.

## Preset Policy

Default stable preset:

- `Steps`: `900`
- `Dim/Alpha`: `8/8`
- `LearningRate`: `0.00002`
- `BatchSize`: `2`
- eval strengths: `0.15,0.30,0.45`

Escalation order:

1. If clean but weak: increase steps to `1200`.
2. If still weak: test `Dim/Alpha 16/16`.
3. If overfit or distorted: reduce strength before changing training.
4. If Krea looks better only for generation, do not move main training off FLUX until A/B proves it.

## Exit Checklist

- [ ] Dataset source and counts recorded.
- [ ] Training config recorded.
- [ ] Eval samples generated or explicitly skipped with reason.
- [ ] Best strength identified.
- [ ] LoRA promotion/rejection status stated.
- [ ] No GPU rule bypassed.

## Dataset and service security gate

- Keep datasets free of unauthorized personal material and secrets.
- Keep ComfyUI/training origins on loopback; expose only through the authenticated gateway.
- Validate uploaded/downloaded media by decoded content, size and server-generated name.
- Invoke `pemara-online-security-guardian` before changing any upload, gallery, rating, job or public endpoint.
