# Sprunki Generator — Pemara Tech

## Estrutura

```
sprunki_project/
├── pipeline.py            ← RODA TUDO (ponto de entrada principal)
├── sb3_extractor.py       ← extrai .sb3 → organized/
├── sprunki_db_builder.py  ← constrói sprunki.db
├── auto_slicer.py         ← corta sprites em partes para OC Maker
├── brand_analyzer.py      ← analisa marca (cores + CLIP)
├── lora_prep.py           ← prepara dataset para treinar LoRA
├── prompt_builder.py      ← motor de prompt (OC Maker + Brand Analyzer)
├── app.py                 ← servidor Flask :5005
├── sprunki_generator.py   ← geração via Flux.1-dev (sem ComfyUI)
├── workflow_api.json       ← template workflow ComfyUI
├── requirements.txt
├── static/
│   ├── index.html         ← portal de entrada
│   ├── oc_maker.html      ← compositor de partes
│   └── brand_analyzer.html← analisador de marca
├── sb3_files/             ← coloque seus .sb3 aqui
├── organized/             ← sprites extraídos (gerado pelo pipeline)
├── static/icons/          ← partes do OC Maker (gerado pelo pipeline)
├── static/generated/      ← imagens geradas pela IA
└── lora_dataset/          ← dataset de treino (gerado pelo pipeline)
```

---

## Setup

```bash
# 1. Ambiente Python 3.11+
conda create -n sprunki python=3.11
conda activate sprunki

# 2. PyTorch com CUDA 12.8 (RTX 50xx)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# 3. Dependências
pip install -r requirements.txt
```

---

## Uso

### Passo 1 — Coloque os .sb3 na pasta

```
sb3_files/
├── Incredibox - Sprunki Phase 1.sb3
├── Sprunki Pyramixed.sb3
└── ...
```

### Passo 2 — Roda o pipeline completo

```bash
python pipeline.py --sb3-dir sb3_files
```

Isso faz tudo automaticamente:
- Extrai sprites e sons de cada .sb3
- Constrói o banco SQLite (sprunki.db)
- Corta os sprites em partes (body/eyes/mouth/hat/accessory)
- Prepara o dataset para treinar a LoRA

### Passo 3 — Sobe o servidor

```bash
# Requer ComfyUI rodando em :8188 para geração com IA
python app.py
# Acesse: http://localhost:5005
```

### Passo 4 — Treinar a LoRA (opcional mas recomendado)

```bash
# Instalar kohya_ss primeiro
git clone https://github.com/bmaltais/kohya_ss
cd kohya_ss && pip install -r requirements.txt

# O comando exato é impresso pelo lora_prep.py ao final
# Exemplo:
python train_network.py \
  --pretrained_model_name_or_path flux1-dev.safetensors \
  --train_data_dir ../lora_dataset/img \
  --output_dir ../lora_dataset/model \
  --output_name sprunki_lora \
  --network_module networks.lora_flux \
  --network_dim 16 --network_alpha 16 \
  --max_train_steps 1500 \
  --learning_rate 1e-4 \
  --resolution 512,512 \
  --train_batch_size 2 \
  --mixed_precision bf16
```

---

## Etapas individuais do pipeline

```bash
python pipeline.py --only extract   # só extrai os .sb3
python pipeline.py --only db        # só reconstrói o banco
python pipeline.py --only slice     # só reslica os sprites
python pipeline.py --only lora      # só reprepara o dataset
```

---

## ComfyUI — workflow

1. Abra o ComfyUI
2. Importe `workflow_api.json` (Load → API Format)
3. Ajuste o nome do modelo em `flux1-dev.safetensors`
4. Ajuste o nome da LoRA em `sprunki_lora.safetensors`
5. Export → Save (API Format) → substitua `workflow_api.json`

---

## Performance RTX 5080

| Modo               | Tempo |
|--------------------|-------|
| Extração 50 .sb3   | ~30s  |
| Auto-slice         | ~2min |
| Geração 1024px     | ~20s  |
| Geração 768px fast | ~8s   |
| Treino LoRA 1500 steps | ~20min |
