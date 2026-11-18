# Dataset de Treino Global

## Objetivo

Treinar capacidade global de animacao, nao um video especifico.

O dataset deve ensinar:

- preservar identidade;
- criar micro movimento natural;
- animar ambiente;
- controlar camera;
- criar particulas/luz sem destruir a cena;
- manter consistencia entre takes;
- evitar artefatos comuns.

## O que salvar de cada take aprovado

```text
training_exports/
  take_id/
    base_image.png
    video.mp4
    prompt_image.txt
    prompt_video.txt
    first_frame.jpg
    mid_frame.jpg
    last_frame.jpg
    contact_sheet.jpg
    metadata.json
```

## Metadata minima

```json
{
  "project": "nome_do_projeto",
  "take_id": "01",
  "slug": "abertura",
  "duration_seconds": 8,
  "style_tags": ["3d_cartoon", "cinematic", "soft_motion"],
  "motion_tags": ["slow_push_in", "particles", "light_sweep"],
  "identity_constraints": [],
  "approved": true,
  "qc_notes": "movimento suave, identidade preservada"
}
```

## Categorias globais

- `environment_motion`
- `character_idle`
- `gentle_walk`
- `dance_light`
- `portal_effect`
- `stage_lights`
- `confetti_particles`
- `family_reaction`
- `brand_intro`
- `brand_outro`
- `game_intro`
- `product_cinematic`

## Reprovados tambem importam

Salvar rejeitados em pasta separada com motivo:

- `static_video`;
- `face_morph`;
- `extra_character`;
- `fake_text`;
- `bad_hands`;
- `identity_drift`;
- `camera_shake`;
- `wrong_object_motion`.

Isso ajuda a treinar avaliadores e regras de QC.

