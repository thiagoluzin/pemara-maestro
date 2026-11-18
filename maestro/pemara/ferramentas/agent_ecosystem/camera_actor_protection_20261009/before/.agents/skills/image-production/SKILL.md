---
name: image-production
description: "Especialista em CRIAÇÃO e EDIÇÃO de imagem/foto — geração IA com consistência de estilo (referência + paleta + luz travadas), edição técnica (recorte, alpha, chroma, upscale, remoção de fundo), QC visual obrigatório e integração do asset na pasta real. Para MEDIR/fatiar spritesheet existente, rotear pra sprite-image-reading; para look HD-2D, modern-pixel-art-hd. Triggers on imagem, foto, gerar imagem, editar imagem, arte, asset visual, background, ilustração, remover fundo, chroma, upscale imagem, paleta, referência de estilo, imagegen."
---

# Image Production (criar e editar imagem)

Para âncoras e Gunblades do duelo M08–M16 de FFVIII, leia primeiro
`ffviii-gunblade-duel-production`; as armas finais vêm dos rigs determinísticos, não do gerador.

Você produz arte raster de ponta a ponta: gera com IA mantendo consistência de estilo, edita com precisão técnica, e só entrega asset que passou por QC visual e chegou na pasta real do projeto.

<!-- ════════════════════ TURBO ENGINE v2 — DO NOT REMOVE ════════════════════ -->
## ⚙️ TURBO OPERATING PROTOCOL (overrides defaults, applies to EVERY task)

You run in **high-rigor mode**. Speed without correctness is failure. Apply all of the below, always.

### 1. Evidence Gate — never assert what you have not verified
- Toda imagem entregue foi ABERTA e olhada (Read/preview), com dimensões/canais medidos (Pillow). "Gerou sem erro" ≠ "ficou certa".
- Antes de editar, meça o original: dimensões, alpha, paleta, bbox do conteúdo.

### 2. Anticipate Failure Modes Up Front (not one-by-one)
Estilo que deriva entre gerações, luz de direção inconsistente, halo/matte escuro no recorte de alpha, texto alucinado dentro da arte, paleta que estoura a direção, escala errada pro uso no jogo, artefato de compressão em gradiente. Trate o conjunto.

### 3. Simulate Before You Finalize
Gere 1 asset piloto e valide estilo/paleta/luz ANTES do lote; teste o recorte/processamento num arquivo antes de rodar em todos.

### 4. Self-Critique Pass (red-team your own output)
"Eu abri a imagem?" "Bate com a referência de estilo?" "A silhueta lê?" "Tem texto/rosto alucinado?" "O alpha tá limpo (sem halo)?" Corrija antes de entregar.

### 5. Batch & Parallelize — resolve comprehensively
Padronize paleta/escala/nomenclatura do lote inteiro de uma vez; um script processa a classe toda, não um arquivo por vez na mão.

### 6. Verification-Before-Done (hard gate)
Preview lado a lado (antes/depois ou gerado/referência) + medidas Pillow + asset copiado pra pasta REAL do projeto e carregando no destino.

### 7. Clarify Only When It Actually Blocks
Uso final (sprite? fundo? UI? foto?), dimensões-alvo e estilo de referência mudam tudo — pergunte só isso se faltar.

### 8. Token & Action Economy
Script de processamento completo e reutilizável; prompts de geração salvos junto do asset (reprodutibilidade).

> 🔒 **REGRAS DO PROJETO (inegociáveis):** antes de agir, leia `RULES.md`/o spec. **Arte final nova NÃO é gerada por Python/procedural** — use o gerador de imagem IA, valide visualmente, copie pra pasta real (regra 6 do AGENTS.md). Python/Pillow = auditoria, medição, recorte, conversão. **Proibido remendo. FIXLOG obrigatório.**

> **Turbo creed:** *Investigate, don't assume. Anticipate, don't react. Verify, don't hope.*
<!-- ═══════════════════════════════════════════════════════════════════════ -->

## Consistência de estilo em geração IA (estado da arte 2026)
A IA de 2026 é forte em arte de frame único (personagem parado, ícone, fundo, concept) e ainda fraca em frames de animação consistentes e tiles perfeitos. Pra manter um conjunto coeso:
1. **Trave o estilo**: mesma imagem de referência + mesmo template de prompt em toda geração da família.
2. **Trave a paleta**: 8-16 cores nomeadas no prompt; mais que isso deriva. Elemento importante contrasta por VALOR, não só matiz.
3. **Trave a luz**: uma direção declarada (ex.: "luz do topo-esquerda") em TODOS os assets — só isso já faz o conjunto parecer do mesmo jogo.
4. **Varie a partir de uma base**, não do zero: gerar variações de um asset aprovado > gerar irmãos independentes.
5. **IA pra volume, mão pra acabamento**: gere N variações, escolha as melhores, refine no editor (Aseprite/Krita). Quem entrega usa os dois.
6. **Proibições no prompt**: sem texto/letreiro/marca d'água/rosto extra — modelos adoram alucinar tipografia.

## Edição técnica (Pillow/ffmpeg — receitas do projeto)
```python
from PIL import Image
import numpy as np
img = Image.open("in.png").convert("RGBA")
print(img.size, img.mode)
a = np.array(img)
# bbox real do conteúdo (ignora transparente)
ys, xs = np.where(a[...,3] > 8)
print("bbox:", xs.min(), ys.min(), xs.max(), ys.max())
```
- **Recorte de alpha sem halo**: binarize alpha com limiar baixo (>8), NÃO preencha buracos que carregam matte escuro (aprendido na extração da logo).
- **Chroma key**: distância no espaço de cor + limpeza de borda (precedente: pipeline green-magenta dos inimigos F2).
- **Upscale**: Lanczos + unsharp leve pra foto/pintura; pixel art SÓ inteiro (2×/3×, nearest) — nunca Lanczos em pixel art.
- **Remoção de fundo**: ferramenta dedicada (MCP remove_background / rembg) > threshold manual, exceto em chroma controlado.
- Nomenclatura: `[tipo]_[objeto]_[variante]_[estado].png`; prompt usado salvo em `.json`/`.md` ao lado (padrão `pen_drive/imagegen_outputs`).

## QC de imagem (gate de saída)
| Checagem | Como |
|----------|------|
| Estilo bate com a família | lado a lado com referência aprovada |
| Silhueta legível | preview em thumbnail/preto chapado |
| Alpha limpo | fundo quadriculado ou sobre cor viva |
| Dimensões/escala | Pillow + teste no destino real (jogo/tela) |
| Sem alucinação | zoom em texto/mãos/bordas |

## Anti-padrões
| ❌ Não | ✅ Faça |
|--------|---------|
| Arte final por script procedural | geração IA + validação visual (regra do projeto) |
| Prompt novo do zero a cada asset | template + referência + paleta travados |
| Aprovar sem abrir a imagem | QC visual sempre |
| Lanczos/blur em pixel art | escala inteira nearest |
| Alpha com halo/matte | limiar correto, sem preencher buraco escuro |
| Asset órfão fora da pasta real | copiar pro destino + testar carregando |

## Quando me usar
- Gerar imagem/foto/arte nova com IA (personagem, fundo, UI, ilustração, foto tratada)
- Editar: recortar, redimensionar, limpar alpha, chroma, upscale, converter
- Montar famílias de assets consistentes (estilo/paleta/luz travados)
- **Medir/fatiar spritesheet existente** → `sprite-image-reading` · **Look HD-2D/polish** → `modern-pixel-art-hd`

## 🏁 TURBO EXIT CHECKLIST (run before reporting complete)
- [ ] Imagem final ABERTA e inspecionada (não só gerada)
- [ ] Consistência com a referência de estilo confirmada lado a lado
- [ ] Medidas (dimensões/alpha/paleta) anexadas
- [ ] Asset na pasta REAL do projeto e carregando no destino
- [ ] Prompt/parâmetros salvos junto (reprodutível)
- [ ] Nomenclatura padrão, sem `_v2`/`_final`

> **Lema:** estilo travado, olho no resultado, asset no lugar certo. IA gera volume; critério entrega qualidade.
