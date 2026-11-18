---
name: pemara-cinematic-take-director
description: "Direção e produção cinematográfica de takes curtos para vídeos Pemara. Use ao roteirizar, revisar ou gerar takes I2V/T2V, definir direção de arte live action, duração, progressão dramática, ação, reação, câmera, motivo de corte, keyframes, contratos de cena e gates antirregressão; especialmente no Maestro com MiniMax H3 e ComfyUI, preservando os contratos específicos."
---

# Pemara Cinematic Take Director

## Direção de produção integrada

Receba tratamento e sequência de `pemara-video-production-lead`. Feche atuação jogável e fotografia antes do prompt: objetivo/obstáculo, estímulo e reação; ponto de vista, blocking, trajetória de câmera, luz e material. Entregue ao editor a informação e o vetor que motivam o corte.

Leia `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md` para a ficha do take e a revisão por dimensões. Um take deve satisfazer intenção, atuação, fotografia, identidade e ritmo, além de movimento e técnica. Sem vídeo observado, não registrar qualidade como verificada. Preserve o H3 com Sage + Spectrum e o acabamento SeedVR2 3B → RIFE exato 60 → DLSS 5, com áudio existente.

No duelo M08–M16 do projeto FFVIII, leia primeiro `ffviii-gunblade-duel-production`; seu contrato
V8 específico prevalece sobre permissões genéricas de geração, remendo e pós-processamento.

Dirigir primeiro; gerar depois. Um take só merece duração quando entrega informação nova.

## Intenção de publicação na internet

Quando o pedido atual indicar publicação na internet, ler integralmente a seção **Intenção de publicação na internet** em `references/production-gates.md` antes de roteiro/âncoras. O gatilho não autoriza publicar ou gerar.

## Sala de direção obrigatória

Assumir três papéis distintos:

1. **Diretor:** definir o que o público deve sentir, onde olhar e qual mudança acontece.
2. **Produtor:** cortar repetição, justificar duração e bloquear gasto de GPU sem contrato aprovado.
3. **Operador técnico:** traduzir o contrato aprovado para modelo, prompt, frames e QC sem reinventar a cena.

Nunca deixar o operador decidir a dramaturgia durante a geração.

## Padrão canônico live action do Maestro

Para produção live action, ler integralmente as seções de padrão canônico, arte, identidade e foto aprovada em `references/production-gates.md`, além de `references/vejito-liveaction-standard.md`. Preservar gates por estágio, referências imutáveis e parecer independente por dimensão.

## Regra antirremendo

RIFE, interpolação, upscale, trim, aceleração e conectores editoriais só podem atuar sobre fontes
que já passaram arte, direção e movimento. Nunca usá-los para salvar identidade, coreografia,
câmera ou estilo defeituosos.

Uma falha isolada autoriza substituir apenas aquele take. Regressão presente em vários takes, nas
fronteiras ou na linguagem visual reprova a rota inteira: retirar da produção ativa, preservar como
rollback, voltar à bíblia/âncoras e gerar uma rota coerente. Não montar primeiro para "ver se fecha".

## Contrato de rejeição

Uma rejeição do proprietário autoriza automaticamente uma nova candidata do mesmo item e escopo.
Preservar a rejeitada como rollback, bloquear seu uso em montagem/promoção e não pedir outra
confirmação para iniciar a correção. A substituta continua pendente de aprovação humana própria.

Corrigir somente o defeito declarado e manter rota, âncoras e ação aprovadas. Não aproveitar a
rejeição para redesenhar a cena. Se duas tentativas com o mesmo método repetirem a falha, trocar a
estratégia de controle qualificada — ajustar staging, densidade de eventos ou âncoras/microtrechos
quando permitidos pela rota — em vez de repetir o mesmo prompt integral.

## Mentalidade cinematográfica

Aplicar princípios, não imitar assinaturas visuais:

- **Clareza e imersão:** colocar o público dentro da experiência; mostrar causa e reação em geografia legível.
- **Épico pelo íntimo:** manter espetáculo curto e visto através dos personagens; voltar sempre ao que eles sentem.
- **Animação com personalidade:** combinar emoção simples, apelo do personagem, timing musical e contraste de energia.
- **História por mudança:** personagem quer algo, algo interfere, ele reage e o plano termina diferente de como começou.

Ler `references/directing-principles.md` quando definir ou revisar uma sequência.

## Regra de duração

Escolher a duração que comunica o beat na grade do modo qualificado. A tabela é uma referência editorial; o contrato específico de combate contínuo de oito segundos prevalece. Não encurtar ou estender fontes aprovadas automaticamente:

| Conteúdo real do plano | Duração padrão |
|---|---:|
| gesto, olhar, detalhe ou revelação simples | 2–3 s |
| ação curta com reação | 3–5 s |
| ação + acontecimento novo + reação | 5–6 s |
| duas viradas dramáticas distintas | 6–8 s |
| 9–10 s | exceção; exigir pelo menos dois eventos novos, mudança emocional e motivo forte para não cortar |

Performance repetida, caminhada sem obstáculo, conversa sem virada ou “imagem respirando” nunca pode ocupar 10 s.

## Gate de sequência e escala

Dirigir a sequência inteira antes de otimizar cada take. Para sequências cuja promessa seja destruição ambiental progressiva (colapso, guerra, desastre ou apocalipse), aplicar os itens pertinentes abaixo. Queda corporal comum, duelo e corrupção abstrata não acionam automaticamente este gate. Legenda/narração só são obrigatórias quando pertencem ao tratamento aprovado; dano/escalada devem seguir o arco, sem exigir destruição nova em cada plano:

- `sequence_stakes`: o que está sendo destruído ou perdido;
- uma legenda/narração oficial por bloco e sua tradução visual concreta;
- `environment_state_before` e `environment_state_after` em cada microtake;
- `environment_damage`: dano físico novo, não apenas luz, fumaça ou partículas;
- `scale_evidence` nos três planos: primeiro plano, plano médio e fundo;
- `escalation_level` crescente e continuidade do dano entre cortes;
- pelo menos uma reação ambiental irreversível por microtake: queda, ruptura, apagamento em cadeia, colapso, deslocamento ou transformação do espaço.

Movimento forte não substitui stakes. Uma câmera veloz sobre cenário intacto continua sendo uma falha de direção. Se a legenda diz “a cidade foi varrida”, mostrar mais de um quarteirão ou fornecer evidência inequívoca de propagação urbana; um único objeto com partículas não basta.

Quando um bloco narrativo precisar de causa e consequência, planejar a cobertura necessária conforme a rota e duração qualificadas. Microtakes separados são uma opção editorial, não obrigação que substitua o combate contínuo ou uma tomada aprovada.

## Gate universal de transicoes

Antes de qualquer take/transição I2V/T2V, ler integralmente **Gate universal de transicoes** em `references/production-gates.md`. Manter os quatro pilares e os beats ativos; corte cinético direto é válido quando comprovadamente compatível. Contratos específicos e direção explícita prevalecem.

## Contrato de take

Exigir antes de qualquer prompt de vídeo:

- `story_purpose`: o que o take acrescenta à história;
- `dramatic_question`: o que o público espera descobrir;
- `story_change`: diferença concreta entre primeiro e último quadro;
- três beats temporais: apresentação, perturbação/virada, reação/payoff;
- `reaction`: quem percebe e como responde;
- `cut_motivation`: por que cortar exatamente ali;
- `duration_reason`: por que não pode ser mais curto;
- `distinct_story_events`: eventos novos, não movimentos repetidos;
- keyframes aprovadas conforme o modo qualificado; start-only não recebe destino final ou intermediário por uma regra genérica.

Antes de liberar vídeo, localizar o gate e o manifest reais do projeto e verificar seu schema. `tools/cinematic_direction_gate.py` pertence apenas a projetos que fornecem esse arquivo; não presumir que exista no cwd.

Para manifests de sequência live action compatíveis, o utilitário desta skill é `E:/Pemara/.agents/skills/pemara-cinematic-take-director/scripts/sequence_regression_gate.py`. Consulte `--help`; passe o caminho real do manifest e `--stage contract`, `anchors` ou `assembly` conforme a fase. Não aplicar esse schema a todo vídeo nem preencher caminhos fictícios. O gate específico do contrato qualificado tem precedência. Falha em gate aplicável bloqueia o envio; resultado estrutural não aprova a arte.

## Direção de ação

Escrever cada take como `estado inicial → interferência → reação → corte`.

- Dar uma ação dominante por personagem; não empilhar coreografia para preencher tempo.
- Preferir reação legível a partículas decorativas.
- Se o plano funciona igual removendo os segundos finais, encurtar.
- Se há apenas movimento repetido, cortar no primeiro ciclo completo.
- Câmera só se move para revelar informação, reforçar emoção ou organizar geografia.
- Fundo não corre para fingir ação; evento deve existir dentro da cena.

## Exemplos

**Banda:** tocar 2 s → tremor distorce notas e sacode janela → músicos param e olham para a rua → cortar.

**Maestro e filhas:** ensinar 2 s → vela inclina e piano vibra sozinho → Maestro protege as filhas e olha para a porta → cortar.

## QC editorial

Reprovar mesmo com imagem bonita quando:

- os últimos segundos repetem os primeiros;
- mão/corpo mexe sem consequência narrativa;
- evento acontece e ninguém reage;
- câmera substitui atuação;
- o take não termina diferente;
- o espectador já entendeu o plano antes da metade;
- identidade, rosto, cenário ou ritmo derivam.
- a escala prometida pela legenda não aparece na imagem;
- o cenário termina intacto depois de uma catástrofe declarada;
- partículas e clarões fingem destruição sem dano físico persistente;
- o corte seguinte esquece os danos do corte anterior.

Só depois do QC editorial executar QC técnico de frames, fps, compressão e upscale.
