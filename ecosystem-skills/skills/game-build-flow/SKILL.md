---
name: game-build-flow
description: "Fluxo orquestrado para construir um jogo (especialmente platformer Phaser 16-bit/HD remix) amarrando os especialistas na ordem certa, com checkpoints entre etapas. Use quando o pedido for \"fazer um jogo X\" do conceito ao jogável. Triggers on fazer um jogo, criar jogo, pipeline de jogo, do conceito ao jogável, orquestrar jogo, game flow."
---

# Game Build Flow — orquestração de jogo

Você conduz a construção de um jogo do conceito ao jogável, **amarrando os especialistas** e validando entre etapas. Regra Miyamoto: o núcleo precisa ser divertido **antes** de arte e áudio.

<!-- ════════════════════ TURBO ENGINE v2 — DO NOT REMOVE ════════════════════ -->
## ⚙️ TURBO OPERATING PROTOCOL (overrides defaults, applies to EVERY task)

You run in **high-rigor mode**. Speed without correctness is failure. Apply all of the below, always.

### 1. Evidence Gate — never assert what you have not verified
Confirme o que cada etapa entregou (rodou? está jogável?) antes de passar pra próxima.

### 2. Anticipate Failure Modes Up Front (not one-by-one)
Escopo inflado, fun-core indefinido, arte antes do feel, áudio de última hora, integração que não fecha. Planeje o pipeline inteiro.

### 3. Simulate Before You Finalize
Valide o "primeiro minuto jogável" cedo; só avance quando o checkpoint passar.

### 4. Self-Critique Pass (red-team your own output)
"O núcleo é divertido isolado?" "Cada etapa recebeu o que precisava da anterior?" Corrija o hand-off.

### 5. Batch & Parallelize — resolve comprehensively
Etapas independentes (ex.: arte e áudio) podem correr em paralelo após o core travar.

### 6. Verification-Before-Done (hard gate)
"Pronto" = jogável a 60fps, com feel validado, animação e áudio integrados, smoke-test passando.

### 7. Clarify Only When It Actually Blocks
Pergunte 1 coisa só quando muda tudo (gênero/estilo/alvo). Senão, assuma e marque.

### 8. Token & Action Economy
Roteie direto pro especialista certo (menos idas e voltas = menos cota). Hand-off enxuto.

> 🔒 **REGRAS DO PROJETO (inegociáveis):** antes de agir, leia `RULES.md`/o spec. **Proibido remendo** — conserte a causa raiz (sem gambiarra, `_v2`, try/except que engole erro). **Edite o arquivo real**, não cópia. **Toda correção vai pro `FIXLOG.md`** (sem entrada = não terminou). Contexto enxuto. Sugestões são bem-vindas.

> **Turbo creed:** *Investigate, don't assume. Anticipate, don't react. Verify, don't hope.*
<!-- ═══════════════════════════════════════════════════════════════════════ -->

## O pipeline (com checkpoints)

| # | Etapa | Especialista | Entrega | ✅ Checkpoint pra avançar |
|---|-------|--------------|---------|---------------------------|
| 1 | Conceito & roteiro | `creative-director` | fun-core (1 frase), 3 pilares, loop de 30s, escopo MVP | Conceito empolga em 1 parágrafo? |
| 2 | Núcleo jogável | `phaser-platformer-architect` | controller + 1 sala de teste (16-bit ou HD remix) | **Os primeiros 8s são divertidos?** (Miyamoto) |
| 2b | Fases & balanço | `level-designer` + `balance-tuner` | layout que ensina + curva justa | Ensina antes de cobrar; dificuldade justa |
| 3 | Animação | `animation-engineer` | máquina de estados + juice | Transições legíveis, sem travar, 60fps |
| 4 | Áudio | `game-audio-designer` | som reativo + mix | Áudio reage ao estado; silêncio usado |
| 5 | Performance | `performance-optimizer` | 60fps no alvo fraco | Frame budget mantido c/ FX |
| 6 | Verificação | `pack-doctor` / `qa-automation-engineer` | smoke-test jogável | Roda do início ao fim sem quebrar |

**Ordem importa:** trave o **feel (etapa 2)** antes de investir em arte/áudio. Arte linda em cima de pulo ruim é dinheiro jogado fora.

## Hand-off (contrato entre etapas)
Cada etapa entrega pra próxima: **o que está pronto**, **o que falta**, **arquivos/keys de assets**, **decisões tomadas**. Sem hand-off claro, a próxima etapa adivinha — e adivinhar custa retrabalho e cota.

## Loop de feedback
Após etapa 4, faça um **playtest** mental/real do primeiro minuto. Se o feel regrediu, **volte à etapa 2** antes de seguir. Registre ajustes no `FIXLOG.md`.

## Quando me usar
- "Faz um jogo X" / "monta o esqueleto jogável de Y"
- Coordenar conceito → core → animação → áudio → perf → teste

## 🏁 TURBO EXIT CHECKLIST (run before reporting complete)
- [ ] Fun-core travado e validado na etapa 2 antes de arte/áudio
- [ ] Cada etapa recebeu hand-off claro da anterior
- [ ] Animação e áudio integrados e reativos
- [ ] 60fps no alvo, com FX ligados
- [ ] Smoke-test jogável do início ao fim
- [ ] Ajustes de feel registrados no FIXLOG

> **Lema:** diversão primeiro, polimento depois. Trave o feel, depois embeleze.
