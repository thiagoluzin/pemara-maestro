---
name: pemara-combate-aprovado
description: "Reutiliza o esquema de combate live action aprovado no TEST05: trocas rápidas de socos e chutes, reação corporal, identidade preservada e continuidade H3/Continuum no Maestro. Use ao criar, continuar ou corrigir cenas de luta; diferencia a base aprovada de novas variantes ainda em avaliação."
---

# Combate aprovado — H3 / Maestro

## Ponto de partida

Comece por `pemara-video-production-lead` e pelas ordens vigentes do projeto. Leia
[a evidência do TEST05](references/test05-evidence.md). O proprietário aprovou o
vídeo e o esquema de luta do TEST05 em 08/11/2026. Preserve esse artefato exato.
Esta skill registra um método observado; não é um LoRA, treinamento de pesos ou
garantia de qualidade para qualquer personagem, arma ou luta.

Reutilize `assets/workflow_aprovado.api.json` e `assets/prompt_aprovado.txt` como
base comparável. O grafo aprovado usa H3 Base FL2VA em I2VA start-only, 1536×864,
243 quadros a 24 FPS, 20 passos, RES multistep/simple, SigmaShift 12/3, seed
202611082204, SageAttention → proteção de quatro grupos → Spectrum. Não adiciona
LoRAs de combate, física ou realismo, nem guia Blender, esqueleto ou profundidade.
Preserve todos os parâmetros Spectrum do grafo, inclusive audio-replay.

## Direção reutilizável

1. Defina quem pressiona, quem recua e uma cadeia curta de ataque → contato →
   separação → reação → recuperação. O contra-ataque começa durante o retorno do
   golpe anterior. Não componha uma sucessão de poses esperando sua vez.
2. Use combinações compactas em velocidade normal, retrações imediatas e avanço
   ligado ao recuo do oponente. O TEST05 pediu nove golpes em dez segundos; isso
   é uma referência de cadência, não uma contagem comprovada nem obrigação geral.
3. Diferencie reação: jab bloqueado causa recuo pequeno; golpe de corpo desloca
   quadril/tronco e obriga passos de recuperação. O receptor continua reagindo
   depois de o punho ou a perna já terem se separado.
4. Chute precisa recolher joelho e pousar rapidamente. Pé de apoio pivota; o corpo
   atingido perde base e a recupera por passos. Evite membros pressionados no alvo,
   apoios sem carga, botas deslizando e balanço sem causa.
5. Mantenha ambos os corpos e pés legíveis, eixo coerente e câmera média aberta
   com acompanhamento contido. Só aumente complexidade de câmera depois de a
   ação/reação funcionar. Não esconda falhas com flash, tremor, corte ou retiming.
6. Mantenha som escolhido. Nesta base: impactos, passos, roupa e vento; sem fala,
   gritos, grunhidos ou música. Não alegue ter usado áudio original do anime.

## Identidade e continuidade

A referência original aprovada governa rosto, cabelo, proporções, figurino e
materiais. Declare `identityContinuityRequired: true`, identifique elenco e salve
caminhos, hashes, escopo e evidência de aprovação. Não mude atores ao dirigir ação.
O último quadro de vídeo aprovado serve de estado cinético; ele não se torna
automaticamente nova referência canônica. Compare início/meio/fim e contatos
contra a referência original, separadamente da qualidade de combate.

Antes de Continuum, inspecione os nós e o código da versão realmente instalada.
O TEST05 não salvou AV latente/estado de Continuum. Continuar dele por quadro final
é um bootstrap condicionado por imagem, não transporte exato de latente. Declare
essa diferença. Não regenere o vídeo aprovado para fabricar um estado anterior.
Ative armazenamento de execução no novo candidato e preserve os estados reais.
Referências persistentes/híbridas são uma variante a qualificar; não confunda
compatibilidade de schema com fidelidade artística. Nunca troque checkpoint
silenciosamente para suportá-las. Não imponha quadro final que estanque a luta.

Não monte takes automaticamente. Compare os intervalos reais nas fronteiras e
aplique a política vigente de conectores quando os estados forem diferentes.

## Preparar, executar, revisar

Use `scripts/materialize.py --verify-only` para verificar a cópia base. Para clonar
sem gerar, passe `--out-dir`, `--name`, `--image` (nome já enviado ao ComfyUI),
`--identity-file` (original aprovado), `--identity-sha256` e `--approval-receipt`.
`--prompt-file` e `--seed` são opcionais. O script cria um grafo start-only e um
recibo; não chama serviço, não aprova referências e não autoriza GPU. Continuação
Continuum exige construir/validar a variante explicitamente, não renomear o grafo.

Confira saúde, fila, GPU, catálogo e grafo exato pelo MCP `comfyui-local`; valide
antes de enviar. Toda operação do Codex sobre ComfyUI usa exclusivamente esse MCP.
Use uma nova tentativa/take e preserve fontes, aprovados e rejeitados.

Na revisão, decodifique o arquivo real e examine intervalos móveis e os contatos:
cadência, separação rápida, apoio, deslocamento corporal, estabilidade de rosto e
figurino, câmera, duração e som. Registre falhas e incertezas. Aprovação do TEST05
não aprova novos resultados. Duas falhas equivalentes exigem mudança de método.

Declare `content_kind: live_action` nesta receita. Preview conserva resolução/FPS
nativos; acabamento autorizado usa Lanczos + NVENC e RIFE 4.25 a 60 FPS exatos.
DLSS 5 somente em âncoras, nunca em vídeo ou quadros; sem SeedVR2 em live action.
Preserve áudio, fontes, geometria, duração e histórico. Projetos cancelados e
treinamento pausado não reabrem por invocar esta skill.
