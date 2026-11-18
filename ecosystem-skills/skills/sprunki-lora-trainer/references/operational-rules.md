# Sprunki LoRA Operational Rules

## Goal

Train LoRAs that generate clean Sprunki-style characters:

- one full-body character;
- centered;
- simple 2D cartoon silhouette;
- clean black outline;
- flat readable colors;
- expressive face;
- no text, watermark, extra characters, background clutter, or accidental horror unless requested.

## Dataset Tiers

`daily_lora_cycle.py` already maps ratings to Kohya repeat folders:

| Rating | Folder | Meaning |
| --- | --- | --- |
| 5 | `30_sprunki_char_gold` | canonical, clean, use heavily |
| 4 | `20_sprunki_char_good` | good training material |
| 3 | `5_sprunki_char_variants` | useful variation, low weight |
| 0-2 | ignored | do not train |

If there is no `ratings.json`, all source images become `20_sprunki_char_good`. That is acceptable
only as bootstrap. For quality work, create/maintain ratings.

## Caption Rules

The trigger token is `sprunki_char`.

Every caption must preserve:

```text
sprunki_char, official Incredibox music game character sprite, simple 2d cartoon character, clean silhouette, full body, centered, flat colors, clean outline, white background
```

Add only useful attributes after that: color, expression, small prop, mood, accessory. Avoid long
story prompts in training captions.

Bad caption patterns:

- generic "cute character" without `sprunki_char`;
- background-heavy captions;
- brand names unrelated to Sprunki;
- horror terms in normal dataset;
- text/logo/label terms unless training a separate UI/logo LoRA.

## Training Policy

Main route:

- train on `FLUX.1-dev`;
- generate/evaluate with ComfyUI using `workflow_api.json`;
- copy evaluation LoRA under unique experiment name before replacing the public `sprunki_lora.safetensors`.

Krea route:

- use for generation A/B and weekly experiment;
- do not replace the main LoRA route unless it beats FLUX across the fixed eval prompts.

## Promotion Gate

Promote to active ComfyUI only when:

1. no broken samples in the first eval batch;
2. at least one strength keeps identity clean;
3. low strength is usable (`0.15` or `0.30`);
4. no repeated extra limbs, text, duplicated faces, ugly blur, cropped body, or background noise;
5. result improves the previous promoted LoRA.

If promotion is uncertain, keep the model only under:

```text
experiments/<run>/sprunki_lora.safetensors
```

and leave active `sprunki_lora.safetensors` unchanged.

## Golden Eval Prompts

Use the prompts in `generate_lora_eval_samples.py` as the fixed first pass. They cover:

- color variation;
- expression variation;
- accessory variation;
- clean white background;
- no text/watermark.

For deeper QC, add a second pass manually with:

- baby/cute variant;
- scary requested variant;
- no-horror normal variant;
- close-to-reference color challenge;
- tiny accessory challenge.

## Common Failure Modes

| Failure | Likely cause | First fix |
| --- | --- | --- |
| samples melt at high strength | overtraining or too much strength | evaluate `0.15/0.30` before retraining |
| weak Sprunki identity | too few gold examples | improve ratings/gold set |
| background clutter | captions include scene/background | clean captions and negative prompts |
| accidental horror | scary examples mixed into normal set | separate horror LoRA or down-rate scary images |
| cropped body | dataset contains cropped samples | demote/remove cropped images |
| repetitive same character | dataset lacks color/expression variety | add rated variants |

## Safe Commands

Dry run:

```powershell
python .\daily_lora_cycle.py --dry-run
```

Dry-run nao usa GPU e deve gerar `experiments/dryrun_*`.

Manual windowed run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily_lora_window.ps1
```

Conservative test:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily_lora_window.ps1 -Steps 900 -Dim 8 -Alpha 8 -LearningRate 0.00002 -EvalSamples 4 -EvalStrengths "0.15,0.30,0.45"
```

Do not bypass `gpu_window_guard` from this skill.
