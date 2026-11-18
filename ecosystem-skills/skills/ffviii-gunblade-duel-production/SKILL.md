---
name: ffviii-gunblade-duel-production
description: Produzir ou revisar o duelo live action M08–M16 da intro FFVIII no Maestro pela rota V8, com placas MiniMax H3 e Revolver/Hyperion em render OpenGL local determinístico. Use somente neste projeto e nesse duelo; não aplicar a outros combates.
---

# FFVIII Gunblade Duel Production

Este skill materializa o contrato específico do duelo. Ele complementa
`pemara-cinematic-take-director`, `pemara-video-motion-director`, `ai-video-intro-pipeline` e
`image-production`; dentro deste escopo, suas travas mais estritas prevalecem.

## Antes de agir

Leia integralmente [references/v8-production-contract.md](references/v8-production-contract.md)
antes de alterar manifesto, construir rigs, gerar âncoras/placas, compor armas, fazer QC ou publicar
no Maestro.

Confirme no estado vivo do projeto que a aprovação do método V8 foi registrada e que o gate da etapa
passa. Aprovação do método e do lote não equivale à aprovação visual de um artefato novo.

## Resultado exigido

Entregar todos os takes M08–M16 como candidatas integrais e conectadas em movimento, com clones,
fotografia e costa coerentes e as duas Gunblades mecanicamente invariantes. Cada take deve sobreviver
aos passes de arte, cinema, movimento e técnica antes da revisão humana do arquivo exato.

## Travas rápidas

- H3: placa de atores/câmera/costa e receptores técnicos de tracking 3D; nunca as armas finais.
- OpenGL/compositor: Revolver e Hyperion finais, rígidas, exatas e ligadas ao próprio dono em todos
  os quadros. Unity está bloqueado por falta de licença e não é requisito desta rota.
- Observabilidade: câmera calibrada, conjunto assimétrico `G/R/U/Z/T`, quatro ou mais pontos não
  coplanares, `solvePnP`, profundidade positiva e erro RMS máximo de 2 px. Tracking planar reprova.
- Geometria: sem espelhamento, `mirror_x`, escala negativa ou determinante negativo; mão envolvendo a
  empunhadura sem penetração; corrente do Revolver conectada e fisicamente dinâmica.
- Temporal: H3 somente em `17k+5`, 124–362 quadros; saída integral.
- Movimento: ação útil até o último quadro e handoff explícito de corpo, arma, câmera e cenário.
- Proibido em qualquer fase: hold, freeze, cauda parada, trim, retime, RIFE/interpolação,
  crossfade/xfade ou oclusão de disfarce.
- Fronteira incompatível: rejeitar e gerar microtake físico de ligação por método autorizado.
- Rejeitado: preservar, bloquear e substituir no mesmo escopo; nunca alimentar o próximo take.
- Aprovação: somente humana, do caminho e SHA-256 exatos; não inferir por score ou gate técnico.
- Publicação: somente a composição final limpa pode chegar ao Maestro. Placa bruta, receptor,
  marcador, bastão, cage e prova de rig ficam sempre fora da interface de revisão do proprietário.

Pare antes de gastar GPU quando fila/VRAM/processo não estiverem seguros, os rigs/âncoras da etapa não
estiverem autorizados, ou o motor requerido não estiver realmente carregado. O motor de vídeo H3
permanece fixo; qualquer troca dele exige nova autorização do proprietário.
