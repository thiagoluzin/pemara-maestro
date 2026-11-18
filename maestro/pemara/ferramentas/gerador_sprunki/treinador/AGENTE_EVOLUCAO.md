# 🤖 Agente de Evolução LoRA Sprunki

Sistema completo de evolução automática que treina uma IA para gerar **Sprunkis perfeitos** através de ciclos iterativos de geração, avaliação e retreino.

## 📦 O Que Foi Criado

### Scripts Principais

| Arquivo | Descrição |
|---------|-----------|
| `run_evolution.py` | **Script principal** - automação completa do ciclo de evolução |
| `quality_evaluator.py` | Métricas objetivas de qualidade (CLIP, cores, anatomia, estilo) |
| `agent_evolution.py` | Motor do agente de evolução (gera → avalia → seleciona → treina) |
| `auto_train.py` | Treino automático LoRA via Kohya SS |
| `setup_evolution.py` | Setup automático de todo o ambiente |
| `run_evolution.bat` | Script Windows para execução rápida |

### Arquivos Modificados

| Arquivo | Mudanças |
|---------|----------|
| `generate_50_lora_samples.py` | Integração com evaluator, modo evolution |
| `lora_prep.py` | Modo incremental para adicionar imagens ao dataset |

## 🚀 Como Usar

### Opção 1: Setup Automático (Primeira Vez)

```bash
python setup_evolution.py
```

Isso vai:
- Instalar dependências Python
- Configurar Kohya SS (se necessário)
- Criar estrutura de diretórios
- Verificar GPU e modelos

### Opção 2: Execução Rápida (Windows)

Duplo clique em `run_evolution.bat` ou:

```bash
# Modo teste (só gera e avalia)
python run_evolution.py --dry-run --generations 10 --max-epochs 5

# Modo automático completo
python run_evolution.py --target-score 85 --max-epochs 20
```

### Opção 3: Comandos Individuais

```bash
# 1. Gerar dataset inicial
python generate_50_lora_samples.py 50

# 2. Avaliar qualidade de um Sprunki
python quality_evaluator.py --image "static/generated/sprunki_00001.png"

# 3. Treinar LoRA manualmente
python auto_train.py --dataset lora_dataset/img/20_sprunki_char --steps 1500

# 4. Rodar evolução completa
python run_evolution.py --target-score 85 --max-epochs 20
```

## 📊 Métricas de Qualidade

Um Sprunki é considerado **"perfeito"** quando atinge **score ≥85**:

| Métrica | Peso | Descrição |
|---------|------|-----------|
| CLIP Score | 25% | Fidelidade ao prompt |
| Color Coherence | 25% | Coerência cromática |
| Anatomy Quality | 25% | Proporções corretas |
| Style Similarity | 25% | Consistência com referências |

## 🔄 Ciclo de Evolução

```
┌─────────────────────────────────────────────────────────┐
│  EPOCH 1                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ GERAR 15 │→│ AVALIAR  │→│ SELECIONAR│→│ TREINAR │ │
│  │ Sprunkis │  │ Quality  │  │ TOP 5    │  │ LoRA    │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│         ▲                                          │    │
│         │                                          ▼    │
│         │                                    SCORE: 72   │
│         └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  EPOCH 2-10... (repete com LoRA melhorada)               │
│  Score melhora gradualmente: 72 → 78 → 82 → 85+         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  EPOCH 12 - TARGET ALCANÇADO!                            │
│  ✓ Score máximo: 87.23                                   │
│  ✓ Sprunkis perfeitos gerados: 60                        │
└─────────────────────────────────────────────────────────┘
```

## ⚙️ Parâmetros

| Parâmetro | Default | Descrição |
|-----------|---------|-----------|
| `--target-score` | 85 | Score mínimo para "perfeito" |
| `--max-epochs` | 20 | Máximo de ciclos de evolução |
| `--generations` | 15 | Sprunkis gerados por epoch |
| `--top-k` | 5 | Melhores selecionados para treino |
| `--dry-run` | False | Só gera/avalia, não treina |
| `--kohya-path` | C:\kohya_ss | Caminho do Kohya SS |

## 📁 Estrutura de Arquivos

```
gerador_sprunki/
├── run_evolution.py          ← SCRIPT PRINCIPAL
├── quality_evaluator.py      ← Métricas de qualidade
├── agent_evolution.py        ← Motor de evolução
├── auto_train.py             ← Treino LoRA automático
├── setup_evolution.py        ← Setup do ambiente
├── run_evolution.bat         ← Execução rápida Windows
├── generate_50_lora_samples.py  ← Gerador de samples
├── lora_prep.py              ← Preparação dataset
├── EVOLUTION_README.md       ← Documentação completa
├── AGENTE_EVOLUCAO.md        ← Este arquivo
│
├── lora_dataset/
│   ├── img/
│   │   └── 20_sprunki_char/  ← Dataset de treino
│   ├── model/                ← LoRA treinada
│   └── log/
│
├── static/
│   ├── generated/            ← Imagens geradas
│   └── referencias/          ← Sprunkis de referência
│
└── evolution_history.json    ← Histórico de evolução
```

## 🎯 Pré-requisitos

1. **Python 3.10+**
2. **GPU NVIDIA** (8GB+ VRAM recomendado)
3. **ComfyUI** rodando em `localhost:8188`
4. **API Flask** rodando em `localhost:5005`
5. **Kohya SS** instalado (para treino automático)
6. **Modelo Flux.1-dev** (~24GB)

## 📝 Exemplo de Saída

```
======================================================================
  AGENTE DE EVOLUÇÃO SPRUNKI - INICIANDO
======================================================================
  Target Score: 85.0
  Máximo Epochs: 20
  Gerações/Epoch: 15
  Top-K: 5
======================================================================

──────────────────────────────────────────────────────────────────────
  EPOCH 1/20
──────────────────────────────────────────────────────────────────────

[1/4] Gerando 15 Sprunkis...

  [1/15]
  → Job enfileirado: abc123-def456
    Gerando... 100%
  → Score: 72.34

  [2/15]
  → Score: 68.91

...

[2/4] Selecionando top-5 melhores...
  Melhores:
    78.45 — red cute smile
    76.32 — blue happy grin
    74.89 — green normal neutral
    73.21 — purple angry open
    71.56 — orange cute shocked

[3/4] Verificando target...
  Melhor epoch: 78.45 | Melhor histórico: 78.45 | Target: 85.0

[4/4] Retreinando LoRA...
  → Adicionado: evolved_1_00.jpg
  → Fine-tuning concluído!
  ✓ LoRA atualizada no ComfyUI

  Aguardando 5s...

...

======================================================================
  RESUMO FINAL DA EVOLUÇÃO
======================================================================
  Epochs executadas: 12
  Melhor score: 87.23
  Target: 85.0
  Status: ✓ SUCESSO
  Sprunkis perfeitos: 60
======================================================================

  TOP 5 SPRUNKIS PERFEITOS:
    1. Score 87.23 — pastel blue
       cute eyes, smile mouth
       headphones, microphone
    
    2. Score 86.91 — vibrant red
       glowing eyes, open mouth
       cap, guitar
```

## 🐛 Troubleshooting

### ComfyUI não conectado
```bash
# Inicie o ComfyUI
cd ComfyUI
python main.py
```

### Kohya SS não encontrado
```bash
# Use modo dry-run para só gerar/avaliar
python run_evolution.py --dry-run

# Ou configure o caminho
python run_evolution.py --kohya-path "C:\seu\caminho\kohya_ss"
```

### Score baixo (<70)
- Aumente `--max-epochs`
- Verifique se LoRA está carregada no ComfyUI
- Gere mais samples iniciais com `generate_50_lora_samples.py`

### GPU Memory OOM
```bash
# Reduza batch size no auto_train.py
# Ou use resolução menor
python auto_train.py --batch-size 1
```

## 📈 Próximos Passos

1. ✅ Scripts de automação criados
2. ⚠️ Testar pipeline completo (dry-run primeiro)
3. ⚠️ Ajustar pesos das métricas conforme resultados
4. ⚠️ Adicionar dashboard de progresso (gráficos)
5. ⚠️ Implementar validação humana (aprovar/rejeitar)

## 📚 Documentação Adicional

- `EVOLUTION_README.md` - Guia completo de uso
- `plano_aider.md` - Arquitetura e planejamento
- `README.md` - Documentação do projeto original

## ⚡ Comandos Úteis

```bash
# Verificar status
python run_evolution.py --help

# Testar sem treinar
python run_evolution.py --dry-run --generations 5 --max-epochs 2

# Avaliar imagem específica
python quality_evaluator.py --image "static/generated/sprunki_00001.png"

# Ver histórico
type evolution_history.json

# Limpar e重新开始
rmdir /s temp_evolution
rmdir /s lora_dataset\img\20_sprunki_char
```

---

**Pronto para gerar Sprunkis perfeitos!** 🎨✨

Execute: `python run_evolution.py --dry-run` para testar primeiro.