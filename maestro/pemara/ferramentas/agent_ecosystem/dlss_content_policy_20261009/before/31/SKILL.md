---
name: pemara-live-action-showrunner
description: "Planeja live action humano no Pemara, escolhe a rota MiniMax H3 por risco e fecha identidade, âncoras, beats, fotografia e gates antes de qualquer render. Use para Mortal Kombat, Dragon Ball, anime em live action, atores humanos, luta cinematográfica ou sequência com vários takes."
---

# Pemara Live Action Showrunner

## Integração de produção

Receba do `pemara-video-production-lead` a sequência, a curva de tensão e as fichas dos takes. Feche atuação com `pemara-performance-director` e geografia/fotografia com `pemara-cinematography-director` antes de compilar. O operador não decide a dramaturgia durante o render.

Toda geração H3 exige SageAttention + Spectrum conectados ao caminho de amostragem, conforme o contrato vigente; indisponibilidade bloqueia sem trocar motor. Perfis abaixo são restrições técnicas, não garantia artística nem autorização para elevar custo automaticamente. A rota específica de combate contínuo prevalece sobre durações/âncoras genéricas.

Transforme a ideia em contratos pequenos e verificáveis. O objetivo é reduzir a liberdade errada do modelo antes da GPU, não prometer perfeição de primeira.

## Fontes canônicas

- Workflows: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/manifest.json`
- Compilador e gerador de grafo ComfyUI API: `E:/Pemara/maestro/pemara/services/studio/live_action_workflows.py`
- Direção de take: `E:/Pemara/.agents/skills/pemara-cinematic-take-director/SKILL.md`
- Direção de combate assinatura: `E:/Pemara/.agents/skills/pemara-live-action-combat-director/SKILL.md`
- Supervisão de identidade, performance e junções: `E:/Pemara/.agents/skills/pemara-live-action-kinetic-supervisor/SKILL.md`
- Prompt H3 oficial: `E:/Pemara/maestro/pemara/third_party/MiniMax-H3-official/skills/h3-prompt-writing/SKILL.md`

Leia somente a rota escolhida no manifest: `identity-performance`, `physical-action` ou `moving-connector`.

## Contrato de entrada

Feche antes do vídeo:

1. propósito dramático, estado inicial, virada e estado final de cada take;
2. matriz por personagem: rosto, escala corporal, roupa/material, anatomia, proibições e estado em 0–30%, 30–70% e 70–100%;
3. geografia compartilhada, lente, câmera física, três planos de profundidade e duas ações internas;
4. âncoras exatas com caminho, SHA-256, escopo e aprovação humana;
5. risco `normal`, `high` ou `critical`, proporção e diretiva de áudio;
6. escolha explícita `minimax_h3`, `fallbackAllowed: false`.

## Seleção da rota

| Necessidade dominante | Workflow | Modo H3 |
|---|---|---|
| Rosto, diálogo, atuação, identidade | `h3_live_action_identity_performance` | Ref2VA |
| Golpe, transformação, pose ou consequência física | `h3_live_action_physical_action` | FL2VA |
| Gesto isolado, arma ou pose icônica | `h3_live_action_signature_combat` | FL2VA |
| Luta bilateral contínua | `h3_live_action_continuous_bilateral_combat_8s` | FL2VA; start-only qualificada quando aplicável |
| União natural entre takes já aprovados | `h3_live_action_moving_connector` | FL2VA |

Ref2VA mantém referências de aparência, mas não oferece pose geométrica exata. Nunca anuncie referência de vídeo como DWPose ou mocap exato.

## Qualidade e velocidade

- `normal`: Production, `1088x608 / 10 steps / 24 fps`.
- close-up humano sobe para `high`: Hero, `1344x768 / 14 steps / 24 fps`.
- `critical`: Master, `1344x768 / 20 steps / 24 fps` nas rotas isoladas compatíveis. Combate bilateral de oito segundos usa o perfil específico 1280×720/20 passos/24 fps e proíbe âncora intermediária; a rota start-only usa apenas a inicial.
- Vertical troca a geometria, não o contrato.

## Ordem obrigatória

1. Story contract e takes da rota escolhida conectados por causa → interferência → reação → corte. Em combate reconhecível, trave também a matriz de golpes por personagem, a cobertura da sequência e um golpe dominante por unidade; nunca delegue a escolha do golpe ao modelo. Planeje o estado cinético compartilhado de cada fronteira antes de gerar os dois lados.
2. Âncoras e matriz de identidade aprovadas.
3. Compilação local do plano e preflight fechado.
4. Materialização CPU-only do grafo com `build_live_action_comfy_graph`; isso ainda não enfileira nada.
5. Autorização atual do proprietário e admissão nova de fila/VRAM.
6. Geração serial de candidato MiniMax H3.
7. Revisão do MP4 completo por história, atuação, fotografia, identidade, ação/física e continuidade, além do QC técnico; aprovação humana do artefato exato.
8. Cortes cinéticos diretos entre fontes aprovadas; conectores causais somente quando permitidos e autorizados. Revisão da montagem inteira e picture lock humano.
9. SeedVR2 3B int8 → RIFE 4.25 em j/60 → DLSS 5 Natural, copiando o áudio existente, preservando nativo/recibos e submetendo o acabado à revisão própria. Não criar Foley por padrão.

Se o proprietário reprovar a estratégia de microtakes ou conectores curtos, registre
`generatedConnectorAllowed: false` na rota. Nesse caso, não tente outra emenda de
4–5 s: regenere as fontes principais de oito segundos e use somente corte direto
motivado pela ação entre fronteiras cineticamente compatíveis.

Se duas tentativas FL2VA mostrarem interpolação lenta entre poses ou cauda congelada
causada pela âncora final, não continue variando seed ou texto sob o mesmo controle.
Troque a fonte de combate para I2VA de oito segundos com uma única âncora inicial
dinâmica. Depois do QC integral e da aprovação do take pelo proprietário, proponha uma saída realmente móvel
do MP4 como âncora cinética inicial do take seguinte. Registre caminho, hash, função e aprovação exata dessa referência antes do envio; derivar um quadro não concede aprovação canônica automática. A ficha original continua padrão de identidade. Âncoras futuras pré-desenhadas
passam a ser referência de composição, nunca destino obrigatório do combate.

Preflight não autoriza render; QC técnico não aprova conteúdo; indisponibilidade nunca autoriza fallback.

Um take sem alucinação ainda reprova quando a luta é genérica, não desloca centros de massa ou usa poder como decoração. Para essa reprovação, volte ao contrato e às âncoras; não tente salvar com RIFE, Foley ou upscale.

## Saída

Entregue roteiro de takes, workflow por take, risco efetivo, perfil H3, hashes de âncoras, prompt no formato oficial, estado do gate, próximo evento permitido e motivo de qualquer bloqueio. Não marque candidato como master.

## Identidade visual versionada — aprendizado R17 (2026-09-08)

Leia `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md` para o contrato e os templates executáveis. Em novos clipes com personagens recorrentes, declare `identityContinuityRequired: true`; mantenha a animação avulsa de foto fora desse gate.

Planeje ficha canônica e estado de continuidade antes das âncoras. Distribua responsabilidades entre continuidade, combate e QC; um mesmo agente pode executá-las, e esta regra não solicita delegação. Registre evidência real de aprovação de referências; ângulos faltantes ficam como lacuna, nunca como material aprovado inventado. Use o compilador com `identityContinuityRequired: true`. Ao encerrar, registre avaliação do proprietário e hashes finais; melhorias de processo não reabrem o clipe.

Para personagens existentes, começar pela etapa zero de pesquisa do contrato: versão/encarnação/traje, fontes e evidência por tópico. Não trabalhar só de memória ou misturar versões. Revisar fontes reais antes de marcar research REVIEWED; adaptar o cânone apenas com direção registrada do proprietário. Projeto encerrado não reabre por essa pesquisa.
